import tempfile,unittest
from pathlib import Path
from app.services.system import installed_ram
class HardwareRamTests(unittest.TestCase):
 def test_revision_capacity_and_unknown(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'revision'
   self.assertIsNone(installed_ram(p))
   for revision,expected in [(0xb03112,'2 GB'),(0xc03112,'4 GB'),(0xd03114,'8 GB'),(0xe04170,'16 GB'),(0xf04170,None),(0x0002,None)]:
    p.write_bytes(revision.to_bytes(4,'big'));self.assertEqual(installed_ram(p),expected)
   p.write_bytes(b'bad');self.assertIsNone(installed_ram(p))
if __name__=='__main__':unittest.main()
