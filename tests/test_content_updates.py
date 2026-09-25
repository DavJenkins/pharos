import hashlib
from pathlib import Path
import tempfile
import unittest
from tools.stage_content_updates import validate_plan, verify


class ContentUpdateTests(unittest.TestCase):
    def item(self, payload=b'ZIM\x04test'):
        return {'filename': 'example_2026-09.zim', 'bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest(),
            'url': 'https://download.kiwix.org/zim/wikipedia/example_2026-09.zim'}

    def test_plan_rejects_traversal_duplicate_and_untrusted_source(self):
        valid=self.item()
        self.assertEqual(validate_plan({'archives':[valid]}), [valid])
        for bad in [{**valid, 'filename':'../escape.zim'}, {**valid, 'url':'https://example.org/a.zim'}, {**valid, 'bytes':-1}]:
            with self.assertRaises(ValueError):
                validate_plan({'archives':[bad]})
        with self.assertRaises(ValueError):
            validate_plan({'archives':[valid,valid]})

    def test_verification_rejects_corruption_without_changing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'download.part'
            original=b'ZIM\x04test'
            path.write_bytes(original)
            verify(path,self.item())
            corrupted=b'ZIM\x04fail'
            path.write_bytes(corrupted)
            with self.assertRaises(ValueError):
                verify(path,self.item())
            self.assertEqual(path.read_bytes(),corrupted)

    def test_html_response_and_truncated_download_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'download.part'
            path.write_bytes(b'<html>oops')
            with self.assertRaises(ValueError):
                verify(path,self.item(b'<html>oops'))
            path.write_bytes(b'ZIM\x04')
            with self.assertRaises(ValueError):
                verify(path,self.item())