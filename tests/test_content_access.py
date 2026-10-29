import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import quote

from tools import publish_content
from deploy.install_content_access import candidate_samba, APACHE

class PortableContentTests(unittest.TestCase):
    def test_relative_links_and_original_content_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = 'Reference & notes.zim'
            original = b'archive-content'
            (root / name).write_bytes(original)
            (root / 'kiwix-viewer').mkdir()
            (root / 'kiwix-viewer' / 'kiwix-desktop.exe').write_bytes(b'reader')
            (root / 'bugout-drop').mkdir()
            (root / 'bugout-drop' / 'private.pdf').write_bytes(b'not published')
            count = publish_content.publish(root)
            self.assertEqual(count, 2)
            self.assertEqual((root / name).read_bytes(), original)
            page = (root / 'START-HERE.html').read_text(encoding='utf-8')
            self.assertIn(quote(name, safe='/'), page)
            self.assertIn('Reference &amp; notes.zim', page)
            self.assertNotIn('private.pdf', page)
            self.assertNotIn('fetch(', page)
            self.assertIn('kiwix-viewer/kiwix-desktop.exe', page)
            self.assertIn(r'\\dataark\Offline-Archives', page)
            self.assertEqual(publish_content.publish(root), 2)
            browse = (root / 'BROWSE.html').read_text(encoding='utf-8')
            self.assertIn('kiwix-viewer/kiwix-desktop.exe', browse)
            self.assertNotIn('private.pdf', browse)

    def test_empty_library_and_html_escaping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(publish_content.publish(root), 0)
            self.assertIn('No content files', (root / 'START-HERE.html').read_text(encoding='utf-8'))
            for name in publish_content.OUTPUTS:
                self.assertTrue((root/name).stat().st_mode & 0o004, name+' must be publicly readable')
        page, _ = publish_content.render([{'path':'<script>.pdf','bytes':1}], 'today', False)
        self.assertIn('&lt;script&gt;.pdf', page)
        self.assertNotIn('<script>.pdf', page)

    def test_optional_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'example.zim').write_bytes(b'example')
            publish_content.publish(root, True)
            catalog = json.loads((root / 'DATA-ARK-CATALOG.json').read_text(encoding='utf-8'))
            self.assertEqual(catalog['files'][0]['sha256'], hashlib.sha256(b'example').hexdigest())
            self.assertTrue(catalog['checksums'])

    def test_foreign_orientation_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'START-HERE.html').write_text('My existing page', encoding='utf-8')
            with self.assertRaises(RuntimeError):
                publish_content.publish(root)
            self.assertEqual((root / 'START-HERE.html').read_text(), 'My existing page')
            self.assertFalse((root / 'DATA-ARK-CATALOG.json').exists())

class ContentShareTests(unittest.TestCase):
    ORIGINAL = '''[global]
    workgroup = WORKGROUP
[Offline-Archives]
    path = /mnt/storage/shared
    force user = pi
    guest ok = yes
    writable = yes
    write list = someone
[Bugout-Staging]
    path = /mnt/storage/bugout-drop
    force user = pi
    guest ok = yes
    read only = no
[dataark]
    path = /opt/dataark
    read only = no
'''

    def test_targeted_share_repair_and_idempotence(self):
        import configparser
        updated = candidate_samba(self.ORIGINAL)
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(updated)
        self.assertEqual(config['Offline-Archives']['path'], '/mnt/storage')
        self.assertEqual(config['Offline-Archives']['read only'], 'yes')
        self.assertEqual(config['Offline-Archives']['write list'], '')
        self.assertNotIn('writable', config['Offline-Archives'])
        self.assertEqual(config['Bugout-Staging']['force user'], 'admin')
        self.assertEqual(config['Bugout-Staging']['read only'], 'yes')
        self.assertEqual(config['dataark']['path'], '/opt/dataark')
        self.assertEqual(config['global']['workgroup'], 'WORKGROUP')
        self.assertEqual(candidate_samba(updated), updated)

    def test_ambiguous_configuration_rejected(self):
        with self.assertRaises(ValueError):
            candidate_samba(self.ORIGINAL.replace('[Offline-Archives]', '[Other]'))
        with self.assertRaises(ValueError):
            candidate_samba(self.ORIGINAL + '\n[Offline-Archives]\npath = /elsewhere\n')

    def test_web_share_is_static_and_staging_denied(self):
        self.assertIn('SetHandler default-handler', APACHE)
        self.assertIn('AllowOverride None', APACHE)
        self.assertIn('<Directory "/mnt/storage/bugout-drop">\n    Require all denied', APACHE)

if __name__ == '__main__':
    unittest.main()
