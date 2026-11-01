"""An archive built on Windows must still contain runnable Linux shell files."""
from pathlib import Path
import io
import subprocess
import tarfile
import tempfile
import unittest


class ShellArchiveTests(unittest.TestCase):
    def test_shell_archive_ignores_windows_checkout_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL)
            git('init')
            (root / '.gitattributes').write_bytes((Path(__file__).resolve().parents[1] / '.gitattributes').read_bytes())
            (root / 'reader.sh').write_bytes(b'#!/bin/sh\r\nset -eu\r\nprintf ready\r\n')
            git('-c', 'core.autocrlf=true', 'add', '.')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'fixture')
            archive = git('-c', 'core.autocrlf=true', 'archive', 'HEAD')
            with tarfile.open(fileobj=io.BytesIO(archive)) as files:
                script = files.extractfile('reader.sh').read()
            self.assertNotIn(b'\r', script)
            self.assertEqual(script, b'#!/bin/sh\nset -eu\nprintf ready\n')
