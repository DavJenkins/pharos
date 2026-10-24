import io,json,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from deploy import bootstrap_stock_pi as b
from tools import replicate_drive as r
class StockSetupTests(unittest.TestCase):
 def config(self):return json.loads((Path(__file__).resolve().parents[1]/'config/stock-pi.json').read_text())
 def test_baseline_configuration(self):
  c=self.config();b.validate(c)
  for key,value in [('content_root','/'),('admin_user','root'),('kiwix_image','anything:latest'),('wifi_country','US; bad')]:
   invalid=self.config();invalid[key]=value
   with self.assertRaises(ValueError):b.validate(invalid)
 def test_archive_rejects_traversal_and_links(self):
  for name,kind in [('../outside',tarfile.REGTYPE),('/absolute',tarfile.REGTYPE),('link',tarfile.SYMTYPE)]:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);archive=root/'source.tar.gz'
    with tarfile.open(archive,'w:gz') as t:
     m=tarfile.TarInfo(name);m.type=kind;m.size=0;m.linkname='/etc/passwd';t.addfile(m,io.BytesIO())
    with self.assertRaises(ValueError):b.extract_source(archive,root/'target')
 def test_safe_archive_extracts(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive=root/'source.tar.gz'
   with tarfile.open(archive,'w:gz') as t:
    m=tarfile.TarInfo('docs/readme.txt');m.size=2;t.addfile(m,io.BytesIO(b'OK'))
   b.extract_source(archive,root/'target');self.assertEqual((root/'target/docs/readme.txt').read_text(),'OK')
 def test_phases_resume_after_success_and_record_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);state={'completed':[]};i=b.Installer({},root,state,root/'journal.json');calls=[]
   i.phase('one',lambda:calls.append('one'));i.phase('one',lambda:calls.append('duplicate'));self.assertEqual(calls,['one'])
   def fail():raise RuntimeError('test interruption')
   with self.assertRaises(RuntimeError):i.phase('two',fail)
   self.assertNotIn('two',state['completed']);self.assertEqual(json.loads((root/'journal.json').read_text())['running'],'two')
   i.phase('two',lambda:calls.append('two'));self.assertEqual(state['completed'],['one','two']);self.assertNotIn('error',state)
 def test_live_media_not_a_replication_destination(self):
  for target in [Path('/'),Path('/mnt/storage')]:
   with self.assertRaises(ValueError):r.safe_target(target)
 def test_payload_selection_excludes_private_directories(self):
  names=r.payload_paths();self.assertTrue(names)
  self.assertFalse(any('bugout' in n or n.startswith('.') for n in names));self.assertNotIn('System Volume Information',names)
 def test_public_copy_relative_layout_and_no_symlinks(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);source=base/'source';target=base/'target';(source/'forms').mkdir(parents=True);target.mkdir();(source/'forms/example.pdf').write_bytes(b'public fixture');(source/'private').mkdir();(source/'private/secret').write_text('not copied');(source/'forms/link').symlink_to(source/'private/secret')
   with patch.object(r,'SOURCE',source):r.copy_public_content(target,['forms'])
   self.assertEqual((target/'forms/example.pdf').read_bytes(),b'public fixture');self.assertFalse((target/'private').exists());self.assertFalse((target/'forms/link').exists());self.assertFalse((target/'mnt').exists())
if __name__=='__main__':unittest.main()
