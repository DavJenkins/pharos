import hashlib,tempfile,unittest,io
from PIL import Image
from pathlib import Path
from unittest.mock import patch
from app.services.manifest import prepare_artwork

class ImmutableArtwork(unittest.TestCase):
 def test_reuses_identical_artwork_without_requesting_write_access(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);buffer=io.BytesIO();Image.new('RGB',(1,1),'white').save(buffer,format='PNG');blob=buffer.getvalue();source=root/'source.png';source.write_bytes(blob)
   target=root/'out/assets/manifest'/(hashlib.sha256(blob).hexdigest()+'.png');target.parent.mkdir(parents=True);target.write_bytes(blob)
   with patch('app.services.manifest.atomic_write',side_effect=PermissionError('root-published directory')) as write:
    art=prepare_artwork({'path':'source.png'},root,root/'out',root/'cache')
    self.assertTrue(art['src'].endswith(target.name));write.assert_not_called()
 def test_changed_destination_is_not_silently_accepted(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);buffer=io.BytesIO();Image.new('RGB',(1,1),'white').save(buffer,format='PNG');blob=buffer.getvalue();(root/'source.png').write_bytes(blob)
   target=root/'out/assets/manifest'/(hashlib.sha256(blob).hexdigest()+'.png');target.parent.mkdir(parents=True);target.write_bytes(b'wrong bytes')
   with patch('app.services.manifest.atomic_write',side_effect=PermissionError('read-only')):
    with self.assertRaises(PermissionError):prepare_artwork({'path':'source.png'},root,root/'out',root/'cache')
