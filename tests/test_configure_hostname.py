import unittest,tempfile
from pathlib import Path
from deploy.configure_hostname import configure
class HostnameTests(unittest.TestCase):
 def test_cloud_init_and_hosts_are_consistent_and_repeatable(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'etc/cloud/cloud.cfg.d').mkdir(parents=True);hosts=root/'etc/hosts';hosts.write_text('127.0.0.1 localhost\n127.0.1.1 old old\n::1 localhost\n')
   configure('dataark-test',root);first=hosts.read_text();configure('dataark-test',root)
   self.assertEqual(first,hosts.read_text());self.assertIn('127.0.1.1 dataark-test',first);self.assertNotIn(' old',first)
   self.assertIn('preserve_hostname: true',(root/'etc/cloud/cloud.cfg.d/99-dataark-hostname.cfg').read_text())
   self.assertIn('old old',(root/'var/backups/dataark-bootstrap/hosts.before-hostname').read_text())
 def test_invalid_hostname_is_rejected(self):
  with self.assertRaises(ValueError):configure('bad name')
