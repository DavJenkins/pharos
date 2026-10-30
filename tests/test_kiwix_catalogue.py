import unittest
from tools.configure_kiwix_catalogue import render
class CatalogueTests(unittest.TestCase):
 def test_customization_is_idempotent_and_preserves_upstream_assets(self):
  page='<html><head><script src="/skin/index.js"></script></head><body><input id="searchFilter"><input id="searchButton"></body></html>'
  result=render(page);self.assertEqual(render(result),result);self.assertIn('/skin/index.js',result);self.assertEqual(result.count('DATAARK CATALOGUE FILTER BEGIN'),1);self.assertIn('not their contents',result)
 def test_unknown_page_is_not_overwritten(self):
  with self.assertRaises(ValueError):render('<html><body>Service unavailable</body></html>')
