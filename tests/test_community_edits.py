import asyncio
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.services import community as board
from app.services import community_restore as restore
from app.routers import community as routes
from tests.test_community_restore import RestoreTests,Request

class EditTests(RestoreTests):
    def payload(self,item,body='Caretaker corrected text'):
        return {'title':item['title'],'body':body,'previous_title':item['title'],'previous_body':item['body']}
    def test_edit_markers_restore_codes_and_conflicts(self):
        original=board.thread(self.post['id'])['post'];payload=self.payload(original)
        board.edit(self.post['id'],payload)
        changed=board.thread(self.post['id'])['post']
        self.assertEqual(changed['name'],original['name']);self.assertEqual(changed['created_at'],original['created_at'])
        self.assertEqual(changed['caretaker_edit']['revisions'],1)
        self.assertEqual(board.listing()['threads'][0]['caretaker_edit']['revisions'],1)
        with self.assertRaises(board.BoardError) as caught:board.edit(self.post['id'],payload)
        self.assertEqual(caught.exception.status,409)
        backup=board.snapshot(self.root/'edited.sqlite3');self.change_live()
        restore.apply(restore.prepare(backup,'caretaker')['token'],'caretaker')
        self.assertEqual(board.thread(self.post['id'])['post']['caretaker_edit']['revisions'],1)
        reply=board.thread(self.post['id'])['replies'][0];board.edit(reply['id'],self.payload(reply))
        board.remove(self.post['id'],self.post['deletion_code'],peer='author')
        with board.connect() as db:self.assertEqual(db.execute("SELECT count(*) FROM metadata WHERE key GLOB 'edited:*'").fetchone()[0],0)
    def test_noop_and_failed_edit_leave_message_unmarked(self):
        original=board.thread(self.post['id'])['post']
        self.assertFalse(board.edit(self.post['id'],self.payload(original,original['body']))['edited'])
        with self.assertRaises(board.BoardError):board.edit(self.post['id'],self.payload(original,''))
        self.assertIsNone(board.thread(self.post['id'])['post']['caretaker_edit'])
    def test_edit_invalidates_restore_preview(self):
        preview=restore.prepare(self.file,'caretaker');original=board.thread(self.post['id'])['post'];board.edit(self.post['id'],self.payload(original))
        with self.assertRaises(board.BoardError) as caught:restore.apply(preview['token'],'caretaker')
        self.assertEqual(caught.exception.status,409)
    def test_edit_route_requires_caretaker(self):
        with patch.object(board,'auth_attempt'),patch.object(routes,'authorized',return_value=False),patch.object(board,'edit') as edit:
            with self.assertRaises(HTTPException) as caught:asyncio.run(routes.edit(1,Request()))
            self.assertEqual(caught.exception.status_code,401);edit.assert_not_called()

if __name__=='__main__':unittest.main()
