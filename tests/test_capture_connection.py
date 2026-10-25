import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

spec=importlib.util.spec_from_file_location('capture',Path(__file__).resolve().parents[1]/'tools/browser-capture/native_host.py')
capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
class ConnectionTests(unittest.TestCase):
 def config(self):
  return dict(ark_host='192.168.40.70',ark_fallback_hosts=['192.168.4.1'],ssh_host_key_alias='192.168.40.70',ssh_executable='ssh',ssh_key='paired-key')
 def test_fallback_preserves_host_verification(self):
  with patch.object(capture.subprocess,'run',side_effect=[SimpleNamespace(stdout='',stderr='unreachable',returncode=255),SimpleNamespace(stdout='{"ok":true}',stderr='',returncode=0)]) as run:
   self.assertTrue(capture.run_ark({},self.config())['ok'])
   self.assertEqual(run.call_count,2)
   self.assertIn('root@192.168.4.1',run.call_args.args[0])
   self.assertIn('HostKeyAlias=192.168.40.70',run.call_args.args[0])
   self.assertIn('StrictHostKeyChecking=yes',run.call_args.args[0])
 def test_rejection_not_retried(self):
  with patch.object(capture.subprocess,'run',return_value=SimpleNamespace(stdout='{"ok":false,"error":"wrong document"}',stderr='',returncode=0)) as run:
   self.assertFalse(capture.run_ark({},self.config())['ok']);self.assertEqual(run.call_count,1)
 def test_unknown_destination_rejected_before_ssh(self):
  config=self.config();config['ark_fallback_hosts']=['evil.example']
  with patch.object(capture.subprocess,'run') as run:
   with self.assertRaises(ValueError):capture.run_ark({},config)
   run.assert_not_called()
if __name__=='__main__':unittest.main()
