from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import write_build_info

class BuildInfoTests(unittest.TestCase):
    def test_fingerprint_tracks_code_and_excludes_private_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'app').mkdir();source=root/'app/example.py';source.write_text('first')
            with patch.object(write_build_info,'ROOT',root),patch.object(write_build_info,'git',return_value='example-revision'):
                first=write_build_info.build_info()
                (root/'private-password.json').write_text('not part of the code fingerprint')
                self.assertEqual(first['source_fingerprint'],write_build_info.build_info()['source_fingerprint'])
                source.write_text('second')
                self.assertNotEqual(first['source_fingerprint'],write_build_info.build_info()['source_fingerprint'])
            self.assertTrue(first['published_at'].endswith('+00:00'))

if __name__=='__main__':unittest.main()
