import asyncio
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.services import community as board
from app.routers import community as routes

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.config=json.loads(board.CONFIG.read_text())
        self.patch_db=patch.object(board,'DATABASE',self.root/'board.sqlite3');self.patch_db.start()
        self.patch_settings=patch.object(board,'settings',side_effect=lambda:self.config.copy());self.patch_settings.start()
        board.initialize()
    def tearDown(self):
        self.patch_settings.stop();self.patch_db.stop();self.temp.cleanup()
    def post(self,peer='device',**changes):
        return board.create({'name':'','title':'Can offer a ride','category':'offers','body':'Available this afternoon.',**changes},peer)
    def test_posts_replies_persistence_and_public_boundary(self):
        created=self.post(body='<script>alert(1)</script>')
        reply=board.create({'name':'Neighbor','body':'Thank you'},'other',created['id'])
        result=board.thread(created['id'])
        self.assertEqual(result['post']['name'],'Anonymous')
        self.assertEqual(result['post']['body'],'<script>alert(1)</script>')
        self.assertEqual(result['replies'][0]['id'],reply['id'])
        self.assertNotIn('delete_hash',json.dumps(result))
        self.assertNotIn(created['deletion_code'],json.dumps(result))
        self.assertEqual(board.listing('offers')['threads'][0]['replies'],1)
        self.assertEqual(board.listing('requests')['total'],0)
        board.initialize();self.assertEqual(board.thread(created['id'])['post']['title'],'Can offer a ride')
    def test_wrong_code_then_author_reply_and_thread_removal(self):
        post=self.post();reply=board.create({'name':'','body':'Reply'},'other',post['id'])
        with self.assertRaises(board.BoardError):board.remove(post['id'],'wrong',peer='device')
        self.assertEqual(len(board.thread(post['id'])['replies']),1)
        board.remove(reply['id'],reply['deletion_code'],peer='other')
        self.assertEqual(board.thread(post['id'])['replies'],[])
        board.create({'name':'','body':'Second reply'},'third',post['id'])
        board.remove(post['id'],post['deletion_code'],peer='device')
        with self.assertRaises(board.BoardError):board.thread(post['id'])
        with board.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM messages').fetchone()[0],0)
    def test_author_cannot_delete_another_message_and_hash_is_stored(self):
        a=self.post();b=self.post('other')
        with self.assertRaises(board.BoardError):board.remove(b['id'],a['deletion_code'],peer='device')
        with board.connect() as db:
            stored=db.execute('SELECT delete_hash FROM messages WHERE id=?',(a['id'],)).fetchone()[0]
        self.assertNotEqual(stored,a['deletion_code']);self.assertEqual(len(stored),64)
    def test_rate_limits_and_no_raw_addresses(self):
        self.config['posts_per_minute_per_device']=1
        self.post('192.168.4.12')
        with self.assertRaises(board.BoardError) as caught:self.post('192.168.4.12')
        self.assertEqual(caught.exception.status,429)
        self.post('192.168.4.13')
        with board.connect() as db:self.assertNotIn('192.168.',str([tuple(x) for x in db.execute('SELECT * FROM limits')]))
    def test_global_limit_capacity_and_reply_limit(self):
        self.config['posts_per_minute_total']=1
        post=self.post()
        with self.assertRaises(board.BoardError):self.post('other')
        self.config['posts_per_minute_total']=100;self.config['max_messages']=1
        with self.assertRaises(board.BoardError) as caught:self.post('other')
        self.assertEqual(caught.exception.status,507)
        self.config['max_messages']=10;self.config['max_replies']=1
        board.create({'name':'','body':'one'},'other',post['id'])
        with self.assertRaises(board.BoardError):board.create({'name':'','body':'two'},'third',post['id'])
    def test_invalid_fields_and_nested_replies_rejected(self):
        for changes in [{'category':'other'},{'title':''},{'body':'x'*4001},{'name':'x'*41},{'body':'bad\x00text'},{'body':'bad\ud800text'},{'extra':'no'}]:
            with self.subTest(changes=changes),self.assertRaises(board.BoardError):self.post(**changes)
        post=self.post();reply=board.create({'name':'','body':'Reply'},'other',post['id'])
        with self.assertRaises(board.BoardError):board.create({'name':'','body':'nested'},'third',reply['id'])
    def test_paginated_listing_and_sql_literal(self):
        self.config['posts_per_minute_per_device']=100
        for index in range(52):self.post(title="title ' OR 1=1 -- "+str(index))
        self.assertEqual(len(board.listing()['threads']),50)
        self.assertEqual(len(board.listing(offset=50)['threads']),2)
        self.assertEqual(board.listing()['total'],52)
    def test_failed_delete_attempts_are_limited(self):
        post=self.post()
        for _ in range(6):
            with self.assertRaises(board.BoardError) as caught:board.remove(post['id'],'wrong',peer='attacker')
            self.assertEqual(caught.exception.status,403)
        with self.assertRaises(board.BoardError) as caught:board.remove(post['id'],'wrong',peer='attacker')
        self.assertEqual(caught.exception.status,429)
    def test_backup_integrity_and_restored_deletion_code(self):
        post=self.post();file=board.snapshot(self.root/'backup.sqlite3')
        board.remove(post['id'],moderator=True)
        with sqlite3.connect(file) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0],'delete')
        self.assertFalse(list(self.root.glob('*.partial*')))
        with patch.object(board,'DATABASE',file):
            self.assertEqual(board.thread(post['id'])['post']['title'],'Can offer a ride')
            board.remove(post['id'],post['deletion_code'],peer='device')

class Request:
    def __init__(self,value=None,headers=None,raw=None):
        self.body=json.dumps(value or {}).encode() if raw is None else raw
        self.headers={'content-type':'application/json','host':'dataark','origin':'http://dataark','x-dataark-peer':'192.168.4.2',**(headers or {})}
        self.client=SimpleNamespace(host='127.0.0.1')
    async def stream(self):yield self.body

class RouteTests(unittest.TestCase):
    def test_origin_content_type_size_and_object_checks(self):
        requests=[Request(headers={'origin':'http://unrelated.example'}),Request(headers={'content-type':'text/plain'}),Request(raw=b'x'*24001),Request(raw=b'[]')]
        for request,status in zip(requests,[403,415,413,400]):
            with self.subTest(status=status),self.assertRaises(HTTPException) as caught:asyncio.run(routes.payload(request))
            self.assertEqual(caught.exception.status_code,status)
    def test_moderation_requires_password_and_author_does_not(self):
        with patch.object(board,'auth_attempt'),patch.object(routes,'authorized',return_value=False),patch.object(board,'remove') as remove:
            with self.assertRaises(HTTPException) as caught:asyncio.run(routes.remove(1,Request({'moderator':True})))
            self.assertEqual(caught.exception.status_code,401);remove.assert_not_called()
        with patch.object(board,'auth_attempt'),patch.object(routes,'authorized',return_value=True),patch.object(board,'remove',return_value={'removed':True}) as remove:
            self.assertTrue(asyncio.run(routes.remove(1,Request({'moderator':True})))['removed'])
            self.assertTrue(remove.call_args.kwargs['moderator'])
        with patch.object(routes,'authorized') as auth,patch.object(board,'remove',return_value={'removed':True}) as remove:
            asyncio.run(routes.remove(1,Request({'code':'author-code'})))
            auth.assert_not_called();self.assertEqual(remove.call_args.kwargs['code'],'author-code')
    def test_backup_requires_caretaker_and_is_not_cacheable(self):
        with patch.object(board,'auth_attempt'),patch.object(routes,'authorized',return_value=False),patch.object(routes,'export_backup') as export:
            with self.assertRaises(HTTPException):asyncio.run(routes.backup(Request()))
            export.assert_not_called()
        with patch.object(board,'auth_attempt'),patch.object(routes,'authorized',return_value=True),patch.object(routes,'export_backup',return_value=b'SQLite fixture'):
            result=asyncio.run(routes.backup(Request()))
            self.assertEqual(result.headers['cache-control'],'no-store')

if __name__=='__main__':unittest.main()
