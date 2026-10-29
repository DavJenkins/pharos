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
            (source/'nested/schema.json').write_text('{"schema":1}',encoding='utf-8')
            old = root / 'dataark-docs'
            old.mkdir()
            (old / 'keep.txt').write_text('previous deployment', encoding='utf-8')
            for name in ('run-one', 'run-two'):
                output = root / name
                output.mkdir()
                self.assertEqual(publish(source, output), 2)
                self.assertIn('href="nested/guide.html"', (output / 'index.html').read_text(encoding='utf-8'))
                self.assertIn('Ark’s content', (output / 'nested/guide.html').read_text(encoding='utf-8'))
                self.assertEqual((output/'nested/schema.json').read_bytes(),(source/'nested/schema.json').read_bytes())
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


class HandbookCodeFormatting(unittest.TestCase):
    def test_fenced_commands_are_literal_and_escaped(self):
        from tools.publish_docs import markdown_to_html
        rendered=markdown_to_html('# Example\n```sh\ncat <file>\n[not a link](secret.md)\n```\n')
        self.assertIn('<pre><code>',rendered)
        self.assertIn('cat &lt;file&gt;',rendered)
        self.assertNotIn('href="secret.html"',rendered)
        self.assertIn('</code></pre>',rendered)

    def test_inline_code_is_escaped(self):
        from tools.publish_docs import inline_html
        self.assertIn('<code>&lt;path&gt;</code>',inline_html('Use `<path>`'))


class MarkdownListConsistency(unittest.TestCase):
    def test_equivalent_markers_and_blank_lines_share_one_list(self):
        from tools.publish_docs import markdown_to_html
        rendered=markdown_to_html('# Contents\n- [First](one.md)\n\n* [Second](two.md)\n\n+ [Third](three.md)\n\nAfter the list.')
        self.assertEqual(rendered.count('<ul>'),1)
        self.assertEqual(rendered.count('<li>'),3)
        self.assertNotIn('<p>* ',rendered)
        self.assertIn('</ul>\n<p>After the list.</p>',rendered)
