import tempfile,unittest
from pathlib import Path
from tools.render_dashboard import raspberry_pi_hardware

class CreditTests(unittest.TestCase):
 def test_only_reported_pi_hardware_gets_credit(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'model'
   for value,expected in [(b'Raspberry Pi 4 Model B Rev 1.2\0',True),(b'Raspberry Pi 5 Model B Rev 1.0',True),(b'QEMU Virtual Machine',False),(b'Other ARM board',False)]:
    p.write_bytes(value);self.assertEqual(raspberry_pi_hardware((p,)),expected)
   self.assertFalse(raspberry_pi_hardware((Path(t)/'missing',)))
