import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import install_communication as module
class CommunicationTests(unittest.TestCase):
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
