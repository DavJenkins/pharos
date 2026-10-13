from pathlib import Path
import tempfile
import unittest
from tools.publish_docs import publish


class DocumentationPublishingTests(unittest.TestCase):
    def test_independent_builds_preserve_previous_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'docs'
            (source / 'nested').mkdir(parents=True)
            (source / 'index.md').write_text('# Ark\n[Guide](nested/guide.md)', encoding='utf-8')
            (source / 'nested/guide.md').write_text('# Reader\nArk’s content', encoding='utf-8')
            old = root / 'dataark-docs'
            old.mkdir()
            (old / 'keep.txt').write_text('previous deployment', encoding='utf-8')
            for name in ('run-one', 'run-two'):
                output = root / name
                output.mkdir()
                self.assertEqual(publish(source, output), 2)
                self.assertIn('href="nested/guide.html"', (output / 'index.html').read_text(encoding='utf-8'))
                self.assertIn('Ark’s content', (output / 'nested/guide.html').read_text(encoding='utf-8'))
            self.assertEqual((old / 'keep.txt').read_text(), 'previous deployment')
            with self.assertRaisesRegex(ValueError, 'new or empty'):
                publish(source, old)
            self.assertEqual((old / 'keep.txt').read_text(), 'previous deployment')

    def test_missing_or_empty_sources_fail_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, 'missing'):
                publish(root / 'missing', root / 'output')
            (root / 'empty').mkdir()
            with self.assertRaisesRegex(ValueError, 'No documentation'):
                publish(root / 'empty', root / 'output')
            self.assertFalse((root / 'output').exists())
