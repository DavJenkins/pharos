import tempfile
import unittest
from pathlib import Path
from tools.render_dashboard import version_static_pages

class StaticAssetVersions(unittest.TestCase):
    def test_library_root_relative_assets_change_version_when_content_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'assets/js').mkdir(parents=True)
            script=root/'assets/js/library.js';script.write_text('first')
            page=root/'library.html';page.write_text('<script src="/assets/js/library.js"></script>')
            version_static_pages(root)
            first=page.read_text();self.assertIn('/assets/js/library.js?v=',first)
            version_static_pages(root);self.assertEqual(first,page.read_text())
            script.write_text('second');version_static_pages(root)
            self.assertNotEqual(first,page.read_text())
            self.assertEqual(page.read_text().count('?v='),1)

    def test_relative_assets_work_and_external_urls_stay_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'assets/css').mkdir(parents=True)
            (root/'assets/css/site.css').write_text('body{}')
            page=root/'content.html';page.write_text('<link href="assets/css/site.css"><script src="https://example.org/file.js"></script>')
            version_static_pages(root)
            self.assertIn('assets/css/site.css?v=',page.read_text())
            self.assertIn('src="https://example.org/file.js"',page.read_text())
