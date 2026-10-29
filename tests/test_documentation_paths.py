from pathlib import Path
import tempfile,unittest
from tools.documentation_paths import validate

class PublicDocumentationPaths(unittest.TestCase):
    def test_rejects_machine_local_paths_without_echoing_them(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'guide.md'
            for text in [r'Open F:\PrivateWorkspace\test',r'Use C:/Work/project',r'Open /Users/someone/Desktop/report']:
                source.write_text(text,encoding='utf-8')
                with self.assertRaises(ValueError) as caught:validate([source],root)
                self.assertIn('guide.md:1',str(caught.exception))
                self.assertNotIn(text,str(caught.exception))

    def test_accepts_relative_host_commands_and_ark_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'guide.md'
            source.write_text('Use ./seed/admin-ed25519 and /opt/dataark. Open https://example.com/docs or '+r'\\dataark\Offline-Archives'+'.',encoding='utf-8')
            validate([source],Path(folder))
