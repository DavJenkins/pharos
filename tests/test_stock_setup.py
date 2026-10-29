import io,json,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from deploy import bootstrap_stock_pi as b
from tools import replicate_drive as r
class StockSetupTests(unittest.TestCase):
 def config(self):return json.loads((Path(__file__).resolve().parents[1]/'config/stock-pi.json').read_text())
 def test_baseline_configuration(self):
  c=self.config();b.validate(c)
  self.assertIn('docker.io',c['packages']);self.assertIn('docker-cli',c['packages'])
  for key,value in [('content_root','/'),('admin_user','root'),('kiwix_image','anything:latest'),('wifi_country','US; bad')]:
   invalid=self.config();invalid[key]=value
   with self.assertRaises(ValueError):b.validate(invalid)
 def test_ap_profile_precedes_role_helper_installation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);state={'completed':[]};installer=b.Installer(self.config(),root,state,root/'journal.json');events=[]
   def output(args):
    if args[:3]==['nmcli','-g','DEVICE']:return 'wlan0\neth0'
    if args[:3]==['nmcli','-g','NAME']:return ''
    raise AssertionError(args)
   with patch.object(b,'output',side_effect=output),patch.object(b,'run',side_effect=lambda args,**kw:events.append(args)),patch.object(installer,'script',side_effect=lambda name,*args:events.append([name,*args])),patch.object(b.shutil,'which',return_value=None):
    installer.network()
   profile_up=events.index(['nmcli','connection','up','DataArk'])
   roles=events.index(['install_wifi_roles.py'])
   self.assertLess(profile_up,roles)
   self.assertLess(roles,events.index(['/usr/local/libexec/dataark-wifi-roles','--boot']))
 def test_fresh_public_shares_created_read_only_without_radio_setup(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);smb=root/'smb.conf';smb.write_text('[global]\nworkgroup = WORKGROUP\n');installer=b.Installer(self.config(),root,{'completed':[]},root/'journal.json');calls=[]
   def path(value):
    if str(value)=='/etc/samba/smb.conf':return smb
    if str(value)=='/var/backups/dataark-bootstrap':return root/'backup'
    return Path(value)
   with patch.object(b,'Path',side_effect=path),patch.object(installer,'script',side_effect=lambda name,*args:calls.append(name)):
    installer.content_access();first=smb.read_text();installer.content_access()
   self.assertEqual(first,smb.read_text())
   self.assertIn('[Offline-Archives]',first);self.assertIn('[Bugout-Staging]',first)
   self.assertEqual(first.count('read only = yes'),2);self.assertNotIn('read only = no',first)
   self.assertEqual(calls,['install_content_access.py','install_ftp.py']*2)
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
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)
   for name in ['forms','bugout-drop','.private','System Volume Information']:(source/name).mkdir()
   with patch.object(r,'SOURCE',source):names=r.payload_paths()
   self.assertIn('forms',names)
   self.assertFalse(any('bugout' in n or n.startswith('.') for n in names));self.assertNotIn('System Volume Information',names)
 def test_public_copy_relative_layout_and_no_symlinks(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);source=base/'source';target=base/'target';(source/'forms').mkdir(parents=True);target.mkdir();(source/'forms/example.pdf').write_bytes(b'public fixture');(source/'private').mkdir();(source/'private/secret').write_text('not copied');(source/'forms/link').symlink_to(source/'private/secret')
   with patch.object(r,'SOURCE',source):r.copy_public_content(target,['forms'])
   self.assertEqual((target/'forms/example.pdf').read_bytes(),b'public fixture');self.assertFalse((target/'private').exists());self.assertFalse((target/'forms/link').exists());self.assertFalse((target/'mnt').exists())
if __name__=='__main__':unittest.main()
