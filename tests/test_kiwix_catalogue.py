import unittest
from tools.configure_kiwix_catalogue import render
class CatalogueTests(unittest.TestCase):
 def test_customization_is_idempotent_and_preserves_upstream_assets(self):
  page='<html><head><script src="/skin/index.js"></script></head><body><input id="searchFilter"><input id="searchButton"></body></html>'
  result=render(page);self.assertEqual(render(result),result);self.assertIn('/skin/index.js',result);self.assertEqual(result.count('DATAARK CATALOGUE FILTER BEGIN'),1);self.assertIn('not their contents',result)
 def test_unknown_page_is_not_overwritten(self):
  with self.assertRaises(ValueError):render('<html><body>Service unavailable</body></html>')

class ReadinessTests(unittest.TestCase):
 def test_cold_reader_can_take_longer_than_thirty_attempts(self):
  from unittest.mock import patch,MagicMock
  from tools.configure_kiwix_catalogue import fetch_catalogue
  response=MagicMock();response.__enter__.return_value.read.return_value=b'<html>ready</html>'
  with patch('tools.configure_kiwix_catalogue.urllib.request.urlopen',side_effect=[ConnectionResetError('starting')]*31+[response]) as request,patch('tools.configure_kiwix_catalogue.time.sleep'),patch('tools.configure_kiwix_catalogue.time.monotonic',return_value=0):
   self.assertEqual(fetch_catalogue(),'<html>ready</html>');self.assertEqual(request.call_count,32)
 def test_readiness_deadline_propagates_failure(self):
  from unittest.mock import patch
  from tools.configure_kiwix_catalogue import fetch_catalogue
  with patch('tools.configure_kiwix_catalogue.urllib.request.urlopen',side_effect=ConnectionResetError('starting')),patch('tools.configure_kiwix_catalogue.time.monotonic',side_effect=[0,0,2]):
   with self.assertRaises(ConnectionResetError):fetch_catalogue(startup_timeout=1)
