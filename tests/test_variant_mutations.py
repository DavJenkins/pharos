import unittest,yaml
from unittest.mock import patch
from tests.test_library_removal import RemovalTests
from tools import library_removal as removal
class VariantMutations(unittest.TestCase):
 setUp=RemovalTests.setUp
 def configure(self):
  repo=self.data['repositories'][0];repo.update(preferred_variant='first',variants=[{'id':'first','title':'Original','asset_id':'example'},{'id':'second','title':'Alternative','asset_id':'alternative'}])
  second={**self.data['assets'][0],'id':'alternative','relative_path':'alternative.zim','removed':True};self.data['assets'].append(second)
  (self.root/'dataark.yaml').write_text(yaml.safe_dump(self.data))
 def test_download_alternative_preserves_original_and_records_desired_variant(self):
  self.configure()
  with patch('tools.update_worker.release_info',return_value={'bytes':7}),patch('shutil.disk_usage',return_value=type('Usage',(),{'free':10**10})()),patch.object(removal.subprocess,'run'):
   removal.restore({'action':'restore','asset_id':'alternative'})
  data=yaml.safe_load((self.root/'dataark.yaml').read_text());self.assertEqual(data['repositories'][0]['preferred_variant'],'second');self.assertTrue(self.archive.exists());self.assertFalse(data['assets'][0].get('removed'));self.assertFalse((self.mount/'alternative.zim').exists())
 def test_cannot_prefer_uninstalled_alternative(self):
  self.configure()
  with self.assertRaisesRegex(ValueError,'activate'):removal.prefer_variant({'action':'prefer','repository_id':'example-repo','variant_id':'second'})
  self.assertTrue(self.archive.exists())
 def test_preference_does_not_remove_either_installed_copy(self):
  self.configure();self.data['assets'][1].pop('removed');(self.mount/'alternative.zim').write_bytes(b'other');(self.root/'dataark.yaml').write_text(yaml.safe_dump(self.data))
  with patch.object(removal.subprocess,'run'):removal.prefer_variant({'action':'prefer','repository_id':'example-repo','variant_id':'second'})
  self.assertTrue(self.archive.exists());self.assertTrue((self.mount/'alternative.zim').exists());self.assertEqual(yaml.safe_load((self.root/'dataark.yaml').read_text())['repositories'][0]['preferred_variant'],'second')
