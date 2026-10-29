import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import install_communication as module
class CommunicationTests(unittest.TestCase):
 def test_configured_bootstrap_asset_registers_without_replacing_android_entry(self):
  from app.services.manifest import load_manifest
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp);manifest=folder/'dataark.yaml';manifest.write_bytes((module.ROOT/'dataark.yaml').read_bytes())
   config=json.loads(module.CATALOGUE.read_text(encoding='utf-8'))
   def path(value):
    if str(value)=='/var/lib/dataark/updates/worker.lock':return folder/'worker.lock'
    return Path(value)
   with patch.object(module,'Path',side_effect=path):module.register(config,manifest)
   data=load_manifest(manifest);assets={a['id']:a for a in data['assets']}
   self.assertEqual(assets['data-ark-bootstrap-kit']['expected_hash'],config['bootstrap']['sha256'])
   self.assertEqual(assets['communicate-keyboard-android']['relative_path'],'communication/android/'+config['keyboard']['apk'])
   self.assertEqual(next(r for r in data['repositories'] if r['id']=='communication-accessibility')['title'],'DEJ Software')

 def test_bootstrap_is_verified_content_with_local_download_and_checksums(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)/'content';cache=Path(temp)/'cache';root.mkdir();files=[]
   for name,data in [('communicate/index.html',b'<html>Communicate</html>'),('android/example.apk',b'PKapk'),('ark-bootstrap/kit.tar.gz',b'public kit fixture')]:
    path='communication/'+name;p=cache/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    files.append({'id':name,'path':path,'url':'https://publisher.test/'+name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
   config={'files':files,'keyboard':{'apk':'example.apk','versionName':'example','sha256':files[1]['sha256']},'bootstrap':{'version':'preview.1','path':files[2]['path']}}
   catalogue=Path(temp)/'catalogue.json';catalogue.write_text(json.dumps(config))
   with patch.object(module,'CATALOGUE',catalogue),patch.object(module,'download') as network:
    module.install(root,cache);network.assert_not_called()
   page=(root/'communication/index.html').read_text()
   self.assertIn('id="bootstrap"',page);self.assertIn('href="ark-bootstrap/kit.tar.gz" download',page)
   self.assertIn('<h1>DEJ Software</h1>',page)
   self.assertEqual((root/'communication/ark-bootstrap/SHA256SUMS').read_text(),files[2]['sha256']+'  kit.tar.gz\n')
   self.assertEqual(json.loads((root/'communication/ark-bootstrap/release.json').read_text())['version'],'preview.1')
   (cache/files[2]['path']).write_bytes(b'bad package');self.assertFalse(module.verify(cache/files[2]['path'],files[2]))

 def test_verified_cache_installs_full_web_assets_and_labeled_apk(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)/'content';cache=Path(temp)/'cache';root.mkdir();files=[]
   for name,data in [('communicate/index.html',b'<html>Communicate</html>'),('communicate/icon.png',b'icon'),('android/example.apk',b'PKapk')]:
    path='communication/'+name;p=cache/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    files.append({'id':name,'path':path,'url':'https://dejsoftware.com/'+name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
   catalogue=Path(temp)/'catalogue.json';catalogue.write_text(json.dumps({'files':files,'keyboard':{'apk':'example.apk','versionName':'0.2.1-dev.13','sha256':files[-1]['sha256']}}))
   with patch.object(module,'CATALOGUE',catalogue),patch.object(module,'download') as network:
    module.install(root,cache);network.assert_not_called()
    self.assertTrue(all(module.verify(root/f['path'],f) for f in files))
    page=(root/'communication/index.html').read_text();self.assertIn('Development build 0.2.1-dev.13',page);self.assertIn('href="android/example.apk"',page);self.assertIn('offline voice',page)
    module.install(root,cache);network.assert_not_called()
    (cache/files[1]['path']).write_bytes(b'bad');self.assertFalse(module.verify(cache/files[1]['path'],files[1]))
if __name__=='__main__':unittest.main()
