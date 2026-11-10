import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from app.services import welcome_guides as g,bugout as b
class WelcomeGuideTests(unittest.TestCase):
 def test_all_channels_have_the_same_branding_and_no_real_code(self):
  for key in g.channels():
   with self.subTest(channel=key):
    text=g.render(key);self.assertIn('PHAROS DATA ARK',text);self.assertIn('DEJ Software',text);self.assertNotIn('0007',text);self.assertIn(g.channels()[key]['title'],text)
 def test_only_prepared_distributions_accept_a_private_code(self):
  for key,item in g.channels().items():
   if item['pairing']:self.assertIn('0007',g.render(key,code='0007'))
   else:
    with self.assertRaises(ValueError):g.render(key,code='0007')
 def test_private_custom_values_are_escaped_and_network_specific(self):
  text=g.render('appliance',code='0007',hostname='example',network_mode='lan',title='<script>x</script>');self.assertIn('Ethernet',text);self.assertIn('&lt;script&gt;',text);self.assertNotIn('<script>x',text)
  text=g.render('microsd',code='0007',ssid='My Ark');self.assertIn('My Ark',text);self.assertIn('width="70mm"',text);self.assertTrue('scale(1 -1)' in text)
class BugoutRetentionTests(unittest.TestCase):
 def test_unconfigured_destination_still_queues_and_expires_after_thirty_days(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(b,'STATE',Path(tmp)),patch.object(b,'integration',return_value={}),patch.object(b.time,'time',return_value=10000000) as clock:
   with b.database() as db:b.event(db,{'id':'op','state':'completed','origin':'local'},'completed');db.commit()
   with b.database() as db:self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],1)
   clock.return_value=10000000+30*86400-1
   with b.database() as db:self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],1)
   clock.return_value+=1
   with b.database() as db:self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],0)

