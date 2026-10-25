import asyncio
import json
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.services import community as board
from app.services import community_restore as restore
from app.routers import community as routes

class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        live=self.root/'live';live.mkdir();backups=self.root/'backups';backups.mkdir()
        self.patches=[patch.object(board,'DATABASE',live/'board.sqlite3'),patch.object(restore,'BACKUPS',backups)]
        for item in self.patches:item.start()
        board.initialize()
        self.post=board.create({'name':'Original author','category':'general','title':'Original conversation','body':'Original body'},'author')
        self.reply=board.create({'name':'Neighbor','body':'Original reply'},'neighbor',self.post['id'])
        board.set_notice('**Original banner**',color='#123456')
        self.file=board.snapshot(self.root/'backup.sqlite3')
    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()
    def change_live(self):
        board.remove(self.post['id'],self.post['deletion_code'],peer='author')
        result=board.create({'name':'Current author','category':'offers','title':'Current conversation','body':'Current body'},'current')
        board.set_notice('Current banner',color='#abcdef')
        return result
    def test_preview_is_non_destructive_and_restore_keeps_codes_and_color(self):
        changed=self.change_live()
        preview=restore.prepare(self.file,'caretaker')
        self.assertEqual(preview['backup']['posts'],1);self.assertEqual(preview['backup']['replies'],1)
        self.assertEqual(board.thread(changed['id'])['post']['title'],'Current conversation')
        result=restore.apply(preview['token'],'caretaker')
        self.assertTrue(result['restored'])
        self.assertEqual(board.thread(self.post['id'])['replies'][0]['body'],'Original reply')
        self.assertEqual(board.notice()['color'],'#123456')
        safety=restore.BACKUPS/result['safety_backup'];self.assertTrue(safety.is_file())
        db=sqlite3.connect(safety)
        try:self.assertEqual(db.execute('SELECT title FROM messages WHERE parent_id IS NULL').fetchone()[0],'Current conversation')
        finally:db.close()
        board.remove(self.post['id'],self.post['deletion_code'],peer='author')
        self.assertEqual(board.listing()['total'],0)
        with self.assertRaises(board.BoardError):restore.apply(preview['token'],'caretaker')
    def test_safety_backup_can_undo_restore_and_reply_code_survives(self):
        changed=self.change_live()
        first=restore.apply(restore.prepare(self.file,'caretaker')['token'],'caretaker')
        board.remove(self.reply['id'],self.reply['deletion_code'],peer='neighbor')
        self.assertEqual(board.thread(self.post['id'])['replies'],[])
        safety=restore.BACKUPS/first['safety_backup']
        undo=restore.apply(restore.prepare(safety,'caretaker')['token'],'caretaker')
        self.assertTrue(undo['restored'])
        self.assertEqual(board.thread(changed['id'])['post']['body'],'Current body')
        self.assertEqual(board.notice()['color'],'#abcdef')
        board.remove(changed['id'],changed['deletion_code'],peer='current')
        self.assertEqual(board.listing()['total'],0)

    def test_banner_appearance_round_trip_and_validation(self):
        board.set_notice('Gold notice',color='#203e54',text_color='#d4af37',width='margin',margin=12.5,margin_top=24,margin_bottom=8,font='old-english',position='bottom')
        backup=board.snapshot(self.root/'appearance.sqlite3')
        board.set_notice('Changed',width='fit',text_color='auto')
        restore.apply(restore.prepare(backup,'caretaker')['token'],'caretaker')
        current=board.notice()
        self.assertEqual(current['font'],'old-english')
        self.assertEqual(current['position'],'bottom')
        self.assertEqual((current['margin_top'],current['margin_bottom']),(24,8))
        self.assertEqual((current['text_color'],current['width'],current['margin']),('#d4af37','margin',12.5))
        for setting in [{'position':'absolute'},{'font':'url(evil)'},{'margin_top':-1},{'margin_bottom':201},{'width':'evil'},{'margin':-1},{'margin':float('nan')},{'text_color':'red;display:none'}]:
            with self.subTest(setting=setting),self.assertRaises(board.BoardError):board.set_notice('Bad',**setting)

    def test_new_post_after_preview_blocks_replacement(self):
        preview=restore.prepare(self.file,'caretaker')
        new=board.create({'name':'','body':'A new reply'},'new-device',self.post['id'])
        with self.assertRaises(board.BoardError) as caught:restore.apply(preview['token'],'caretaker')
        self.assertEqual(caught.exception.status,409)
        self.assertEqual(len(board.thread(self.post['id'])['replies']),2)
        self.assertFalse(list(restore.BACKUPS.glob('before-restore-*')))
    def test_peer_expiry_and_invalid_tokens_do_not_restore(self):
        preview=restore.prepare(self.file,'caretaker')
        with self.assertRaises(board.BoardError) as caught:restore.apply(preview['token'],'other-device')
        self.assertEqual(caught.exception.status,403)
        with patch.object(restore.time,'time',return_value=time.time()+601):
            with self.assertRaises(board.BoardError) as caught:restore.apply(preview['token'],'caretaker')
        self.assertEqual(caught.exception.status,410)
        with self.assertRaises(board.BoardError):restore.apply('../../board.sqlite3','caretaker')
        self.assertEqual(board.listing()['total'],1)
    def test_safety_snapshot_failure_rolls_back(self):
        changed=self.change_live();preview=restore.prepare(self.file,'caretaker')
        with patch.object(board,'snapshot',side_effect=OSError('disk full')):
            with self.assertRaises(board.BoardError) as caught:restore.apply(preview['token'],'caretaker')
        self.assertEqual(caught.exception.status,503)
        self.assertEqual(board.thread(changed['id'])['post']['title'],'Current conversation')
        self.assertEqual(board.notice()['color'],'#abcdef')
    def test_malformed_and_modified_staging_are_rejected(self):
        bad=self.root/'bad.sqlite3';bad.write_bytes(b'not a database')
        with self.assertRaises(board.BoardError):restore.prepare(bad,'caretaker')
        preview=restore.prepare(self.file,'caretaker')
        (restore.folder()/(preview['token']+'.sqlite3')).write_bytes(b'tampered')
        with self.assertRaises(board.BoardError) as caught:restore.apply(preview['token'],'caretaker')
        self.assertEqual(caught.exception.status,409);self.assertEqual(board.listing()['total'],1)
    def test_unexpected_schema_dangling_reply_and_hash_are_rejected(self):
        for statement in ["CREATE TRIGGER surprise AFTER INSERT ON messages BEGIN DELETE FROM messages; END",'UPDATE messages SET parent_id=999 WHERE parent_id IS NOT NULL',"UPDATE messages SET delete_hash='not-a-hash'"]:
            bad=self.root/'invalid.sqlite3';bad.write_bytes(self.file.read_bytes())
            db=sqlite3.connect(bad)
            try:db.execute(statement);db.commit()
            finally:db.close()
            with self.subTest(statement=statement),self.assertRaises(board.BoardError):restore.prepare(bad,'caretaker')
        self.assertEqual(board.listing()['total'],1)
    def test_explicit_capacity_limits_and_pending_preview_replacement(self):
        with patch.object(restore,'MAX_UPLOAD',16):
            with self.assertRaises(board.BoardError):restore.prepare(self.file,'caretaker')
        a=restore.prepare(self.file,'caretaker');b=restore.prepare(self.file,'caretaker')
        with self.assertRaises(board.BoardError):restore.apply(a['token'],'caretaker')
        self.assertTrue(restore.apply(b['token'],'caretaker')['restored'])
    def test_cleanup_failure_after_commit_is_reported_as_success(self):
        self.change_live();preview=restore.prepare(self.file,'caretaker')
        original=Path.unlink
        def unlink(path,*args,**kwargs):
            if path==restore.folder()/(preview['token']+'.sqlite3'):raise OSError('cleanup failed')
            return original(path,*args,**kwargs)
        with patch.object(Path,'unlink',unlink):result=restore.apply(preview['token'],'caretaker')
        self.assertTrue(result['restored']);self.assertIn('warning',result)
        self.assertEqual(board.thread(self.post['id'])['post']['title'],'Original conversation')

    def test_restore_insert_failure_rolls_back_live_delete(self):
        changed=self.change_live()
        with board.connect() as db:
            db.execute("CREATE TRIGGER fail_restore BEFORE INSERT ON messages BEGIN SELECT RAISE(ABORT,'simulated write failure'); END")
        preview=restore.prepare(self.file,'caretaker')
        with self.assertRaises(board.BoardError) as caught:restore.apply(preview['token'],'caretaker')
        self.assertEqual(caught.exception.status,503)
        self.assertEqual(board.thread(changed['id'])['post']['title'],'Current conversation')
        self.assertEqual(board.notice()['color'],'#abcdef')
    def test_only_three_pre_restore_snapshots_are_retained(self):
        for _ in range(4):
            preview=restore.prepare(self.file,'caretaker');result=restore.apply(preview['token'],'caretaker')
        self.assertEqual(len(list(restore.BACKUPS.glob('before-restore-*.sqlite3'))),3)
        self.assertTrue((restore.BACKUPS/result['safety_backup']).is_file())

class Request:
    def __init__(self,body=b'{}',headers=None):
        self.body=body;self.headers={'host':'dataark','origin':'http://dataark','content-type':'application/json',**(headers or {})}
        self.client=SimpleNamespace(host='127.0.0.1')
    async def stream(self):yield self.body

class RouteTests(unittest.TestCase):
    def test_preview_requires_auth_before_reading_upload(self):
        with patch.object(board,'auth_attempt'),patch.object(routes,'authorized',return_value=False),patch.object(restore,'prepare') as prepare:
            with self.assertRaises(HTTPException) as caught:asyncio.run(routes.restore_preview(Request(headers={'content-type':'application/vnd.sqlite3'})))
            self.assertEqual(caught.exception.status_code,401);prepare.assert_not_called()
    def test_preview_rejects_cross_origin_and_oversized_upload(self):
        with self.assertRaises(HTTPException) as caught:asyncio.run(routes.restore_preview(Request(headers={'origin':'http://other.example','content-type':'application/vnd.sqlite3'})))
        self.assertEqual(caught.exception.status_code,403)
        with patch.object(board,'auth_attempt'),patch.object(routes,'authorized',return_value=True),patch.object(restore,'MAX_UPLOAD',16):
            with self.assertRaises(HTTPException) as caught:asyncio.run(routes.restore_preview(Request(headers={'content-type':'application/vnd.sqlite3','content-length':'17'})))
        self.assertEqual(caught.exception.status_code,413)
    def test_apply_requires_confirmation_and_caretaker(self):
        with patch.object(restore,'apply') as apply:
            with self.assertRaises(HTTPException):asyncio.run(routes.restore_apply(Request(b'{"token":"x"}')))
            apply.assert_not_called()
        body=json.dumps({'token':'x'*32,'confirmation':'RESTORE'}).encode()
        with patch.object(board,'auth_attempt'),patch.object(routes,'authorized',return_value=False),patch.object(restore,'apply') as apply:
            with self.assertRaises(HTTPException) as caught:asyncio.run(routes.restore_apply(Request(body)))
            self.assertEqual(caught.exception.status_code,401);apply.assert_not_called()

if __name__=='__main__':unittest.main()
