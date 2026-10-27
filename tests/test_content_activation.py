from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.activate_content_updates import replacement_manifest, switch_files, restore_files, archive_names, finish, validate_records


class ActivationTests(unittest.TestCase):
    def test_manifest_updates_only_selected_asset_and_removes_old_mirror(self):
        original='''system: {version: "1.4"}
assets:
  - id: sample
    repository_id: wiki
    title: Wikipedia (February 2026)
    relative_path: old.zim
    download_url: https://example.invalid/old.zim
    mirror_url: https://mirror.invalid/old.zim
    tags: [keep]
  - id: unchanged
    title: Leave me
'''
        item={'id':'sample','filename':'wikipedia_en_all_maxi_2026-08.zim','url':'https://download.kiwix.org/new.zim','sha256':'a'*64}
        updated=replacement_manifest(original,[item])
        self.assertIn('Wikipedia (August 2026)',updated)
        self.assertIn('    tags: [keep]',updated)
        self.assertIn('  - id: unchanged\n    title: Leave me',updated)
        self.assertNotIn('mirror_url:',updated)
        self.assertIn('expected_hash: "'+'a'*64+'"',updated)
        self.assertIn('relative_path: '+item['filename'],updated)

    def test_rollback_restores_both_complete_and_partial_moves(self):
        for partial in (False,True):
            with self.subTest(partial=partial), tempfile.TemporaryDirectory() as d:
                root=Path(d);stage=root/'stage';previous=stage/'previous';previous.mkdir(parents=True)
                (root/'old.zim').write_bytes(b'old');(stage/'new.zim').write_bytes(b'new')
                records=[{'old':'old.zim','new':'new.zim'}]
                if partial:(root/'old.zim').rename(previous/'old.zim')
                else:switch_files(root,stage,previous,records)
                restore_files(root,stage,previous,records)
                self.assertEqual((root/'old.zim').read_bytes(),b'old')
                self.assertEqual((stage/'new.zim').read_bytes(),b'new')
                self.assertFalse((root/'new.zim').exists())

    def test_failed_publish_preserves_recovery_files_and_journal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);previous=root/'previous';previous.mkdir();old=previous/'old.zim';old.write_bytes(b'old')
            journal=root/'activation.json';journal.write_text('{}')
            with patch('tools.activate_content_updates.publish',side_effect=RuntimeError('publish failed')):
                with self.assertRaises(RuntimeError):finish(root,previous,journal,{'records':[{'old':'old.zim'}]})
            self.assertTrue(old.exists());self.assertTrue(journal.exists())
            with patch('tools.activate_content_updates.publish'),patch('tools.activate_content_updates.subprocess.run'):
                finish(root,previous,journal,{'records':[{'old':'old.zim'}]})
            self.assertFalse(old.exists());self.assertFalse(journal.exists())

    def test_catalog_matches_real_reader_links(self):
        xml='<feed xmlns="http://www.w3.org/2005/Atom"><entry><link type="image/png" href="/thumbnail"/><link type="text/html" href="/content/wikipedia_en_all_maxi_2026-08"/></entry></feed>'
        self.assertEqual(archive_names(xml),{'wikipedia_en_all_maxi_2026-08'})

    def test_paths_must_be_distinct_plain_archive_names(self):
        for records in [[{'old':'../bad.zim','new':'new.zim'}],[{'old':'same.zim','new':'same.zim'}]]:
            with self.assertRaises(ValueError):validate_records(records)
class ManifestIndentationTests(unittest.TestCase):
    def test_safe_dump_sequence_and_unrelated_section_are_preserved(self):
        import yaml
        original='assets:\n- id: khan-academy\n  repository_id: curriculum\n  relative_path: old.zim\n  download_url: https://example.invalid/old.zim\n  expected_hash: old\ndashboard:\n  title: Keep me\n'
        item={'id':'khan-academy','filename':'khanacademy_en_all_2023-03.zim','url':'https://download.kiwix.org/zim/other/khanacademy_en_all_2023-03.zim','sha256':'a'*64}
        result=yaml.safe_load(replacement_manifest(original,[item]))
        self.assertEqual(result['assets'][0]['expected_hash'],'a'*64)
        self.assertEqual(result['assets'][0]['relative_path'],item['filename'])
        self.assertEqual(result['dashboard'],{'title':'Keep me'})
