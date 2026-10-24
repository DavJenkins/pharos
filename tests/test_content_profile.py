import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import content_profile as m
class ContentProfileTests(unittest.TestCase):
 def test_paths_and_sources(self):
  root=Path('/tmp/profile-test')
  for path in ['../escape','/absolute','a/../../escape','a\\..\\escape']:
   with self.assertRaises(ValueError):m.inside(root,path)
  c={'schema':1,'reserve_gib':10,'archives':[{'id':'a','path':'a.zim','url':'https://example.org/a.zim','sha256':'a'*64}]}
  m.validate(c)
  c['archives'][0]['url']='https://user:password@example.org/a.zim'
  with self.assertRaises(ValueError):m.validate(c)
 def test_selection_preserves_disabled_and_dependencies(self):
  c={'archives':[{'id':'keep','path':'a','enabled':True},{'id':'removed','path':'b','enabled':False}],'recipes':[{'id':'forms','enabled':True},{'id':'family','enabled':True,'requires':['forms']}]}
  self.assertEqual([r['id'] for _,r in m.selected(c,['archives'])],['keep'])
  self.assertEqual([r['id'] for _,r in m.selected(c,['family'])],['forms','family'])
  with self.assertRaises(ValueError):m.selected(c,['typo'])
 def test_download_verification_keeps_original(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);target=root/'test.pdf';target.write_bytes(b'original')
   item={'id':'test','path':'test.pdf','url':'https://example.org/test.pdf','bytes':7,'sha256':hashlib.sha256(b'correct').hexdigest()}
   def bad(*args,**kwargs):(root/'test.pdf.restore-part').write_bytes(b'badfile')
   with patch.object(m.subprocess,'run',side_effect=bad),patch.object(m.shutil,'disk_usage',return_value=type('Space',(),{'free':10**12})()):
    with self.assertRaises(ValueError):m.download(item,root,{'reserve_gib':1},True)
   self.assertEqual(target.read_bytes(),b'original')
   def good(*args,**kwargs):(root/'test.pdf.restore-part').write_bytes(b'correct')
   with patch.object(m.subprocess,'run',side_effect=good),patch.object(m.shutil,'disk_usage',return_value=type('Space',(),{'free':10**12})()):self.assertEqual(m.download(item,root,{'reserve_gib':1},True),'restored')
   self.assertEqual(target.read_bytes(),b'correct')
 def test_bundle_file_allowlist(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'content.yaml').write_text('schema: 1');(root/'public-manifest.yaml').write_text('assets: []');(root/'secret.txt').write_text('must not be bundled')
   files=list(m.portable_files({'manifest':'public-manifest.yaml','snapshots':[]},root))
   self.assertNotIn('secret.txt',[p.name for p,_ in files])
 def test_family_restore_includes_separate_guidance_repositories(self):
  for repository in ['food-preservation','sanitation','drinking-water']:
   with self.subTest(repository=repository), tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);family=root/'family-resources';family.mkdir()
    for name in ['index.html','sources.json','existing.pdf']:(family/name).write_text('fixture')
    manifest={'assets':[
     {'id':'ordinary','repository_id':'family-resources','relative_path':'family-resources/existing.pdf'},
     {'id':'guide','repository_id':repository,'relative_path':'family-resources/guide.pdf'}]}
    with patch.object(m,'read',return_value=manifest),patch.object(m.subprocess,'run') as run:
     m.recipe({'id':'family'},{},root,root)
     run.assert_called_once()
     self.assertIn('install_family_resources.py',str(run.call_args))
    (family/'guide.pdf').write_text('fixture')
    with patch.object(m,'read',return_value=manifest),patch.object(m.subprocess,'run') as run:
     m.recipe({'id':'family'},{},root,root)
     run.assert_not_called()
if __name__=='__main__':unittest.main()
