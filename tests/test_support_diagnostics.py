import tempfile
from pathlib import Path
import unittest
from tools.support_diagnostics import sanitize,tail

class SupportDiagnosticsTests(unittest.TestCase):
    def test_structured_secrets_and_log_values_are_removed(self):
        value=sanitize({'password':'top secret','details':['password="several secret words"','Authorization: Basic abc123','https://someone:private@example.org/file'],'hostname':'dataark'})
        text=str(value)
        for secret in ('top secret','several secret words','abc123','someone:private'):self.assertNotIn(secret,text)
        self.assertEqual(value['hostname'],'dataark')

    def test_log_tail_is_bounded_and_ignores_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'events.log';path.write_text('old\n'*100+'latest\n')
            self.assertIn('latest',tail(path,30))
            self.assertLess(len(tail(path,30)),100)
            link=Path(folder)/'link';link.symlink_to(path)
            self.assertEqual(tail(link),'Not available')

if __name__=='__main__':unittest.main()
