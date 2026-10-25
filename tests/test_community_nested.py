import sqlite3
import unittest
from app.services import community as board
from app.services import community_restore as restore
from tests import test_community_restore as fixtures

class NestedTests(unittest.TestCase):
    setUp=fixtures.RestoreTests.setUp
    tearDown=fixtures.RestoreTests.tearDown
    def add_reply(self,target,peer):return board.reply_to(target,{'name':'Neighbor','body':'**Nested** reply'},peer)
    def test_nested_replies_remain_in_conversation_and_reparent_on_delete(self):
        child=self.add_reply(self.reply['id'],'child');grandchild=self.add_reply(child['id'],'grandchild')
        rows={item['id']:item for item in board.thread(self.post['id'])['replies']}
        self.assertEqual(rows[child['id']]['parent_id'],self.post['id']);self.assertEqual(rows[child['id']]['reply_to'],self.reply['id'])
        board.remove(self.reply['id'],self.reply['deletion_code'],peer='neighbor')
        rows={item['id']:item for item in board.thread(self.post['id'])['replies']}
        self.assertEqual(rows[child['id']]['reply_to'],self.post['id']);self.assertEqual(rows[grandchild['id']]['reply_to'],child['id'])
        board.remove(child['id'],child['deletion_code'],peer='child')
        self.assertEqual(board.thread(self.post['id'])['replies'][0]['reply_to'],self.post['id'])
    def test_nested_backup_restore_and_root_deletion(self):
        child=self.add_reply(self.reply['id'],'child');backup=board.snapshot(self.root/'nested.sqlite3')
        board.remove(self.reply['id'],self.reply['deletion_code'],peer='neighbor')
        restore.apply(restore.prepare(backup,'caretaker')['token'],'caretaker')
        rows={item['id']:item for item in board.thread(self.post['id'])['replies']}
        self.assertEqual(rows[child['id']]['reply_to'],self.reply['id'])
        self.assertEqual(rows[child['id']]['body'],'**Nested** reply')
        board.remove(self.post['id'],self.post['deletion_code'],peer='author')
        with board.connect() as db:self.assertEqual(db.execute("SELECT count(*) FROM metadata WHERE key GLOB 'reply_to:*'").fetchone()[0],0)
    def test_invalid_cross_thread_and_cyclic_restore_relationships_rejected(self):
        other=board.create({'name':'Other','category':'general','title':'Other','body':'Other'},'other')
        with self.assertRaises(board.BoardError):board.create({'name':'','body':'Bad'},'bad',other['id'],self.reply['id'])
        child=self.add_reply(self.reply['id'],'child');backup=board.snapshot(self.root/'bad.sqlite3')
        db=sqlite3.connect(backup);db.execute('UPDATE metadata SET value=? WHERE key=?',(str(child['id']),'reply_to:'+str(child['id'])));db.commit();db.close()
        with self.assertRaises(board.BoardError):restore.prepare(backup,'caretaker')

if __name__=='__main__':unittest.main()
