import tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from tools.collect_usage import classify,collect,sample
NOW=datetime(2026,10,27,16,0,tzinfo=timezone.utc)
def line(path,status=200,address='192.168.4.5'):
 return f'{address} - - [27/Oct/2026:16:00:00 +0000] "GET {path} HTTP/1.1" {status} 123 "-" "browser"\n'
class UsageTests(unittest.TestCase):
 def test_excludes_polling_and_bad_requests(self):
  for path in ['/api/status','/assets/js/main.js','/library-files/usage.json','/favicon.ico']:
   self.assertIsNone(classify(line(path)))
  self.assertIsNone(classify(line('/a.pdf',404)));self.assertIsNone(classify(line('/',address='127.0.0.1')))
  self.assertIsNone(classify('bad request'));self.assertIsNone(classify(line('http://[')))
 def test_aggregates_without_personal_details(self):
  item=classify(line('/library-files/forms/a.pdf?private=secret'));self.assertEqual(item[1:],(123,'forms'))
  self.assertEqual(classify(line('/library-files/unknown-person/private.pdf'))[2],'Other files')
 def test_resume_rotation_retention_and_first_start(self):
  with tempfile.TemporaryDirectory() as temp:
   log=Path(temp)/'access.log';log.write_text(line('/'))
   state={'started_at':(NOW-timedelta(seconds=1)).isoformat(),'daily':{},'hourly':{}}
   current={'hotspot_devices':2}
   collect(state,log,NOW,current);self.assertEqual(state['daily']['2026-10-27']['opens'],0)
   with log.open('a') as f:f.write(line('/library-files/forms/a.pdf?private=secret'))
   public=collect(state,log,NOW,current);self.assertEqual(public['daily']['2026-10-27']['opens'],1);self.assertNotIn('log',public)
   collect(state,log,NOW,current);self.assertEqual(state['daily']['2026-10-27']['opens'],1)
   with log.open('a') as f:f.write(line('/docs/a.html'))
   log.rename(log.with_name('access.log.1'));log.write_text(line('/index.html'))
   collect(state,log,NOW,current);self.assertEqual(state['daily']['2026-10-27']['opens'],3)
   self.assertEqual(state['daily']['2026-10-27']['hotspot_peak'],2)
   state['daily']['2020-01-01']={};collect(state,log,NOW,current);self.assertNotIn('2020-01-01',state['daily'])
   self.assertNotIn('private',str(public));self.assertNotIn('192.168',str(public))
 def test_unique_visitors_deduplicate_and_remain_private(self):
  with tempfile.TemporaryDirectory() as temp:
   log=Path(temp)/'access.log';log.write_text('')
   state={'started_at':(NOW-timedelta(seconds=1)).isoformat(),'daily':{},'hourly':{}}
   collect(state,log,NOW,{'hotspot_devices':0})
   log.write_text(line('/')+line('/docs/a.html')+line('/index.html',address='192.168.4.6')+line('/api/status',address='192.168.4.7'))
   public=collect(state,log,NOW,{'hotspot_devices':0})
   self.assertEqual(public['daily']['2026-10-27']['unique_visitors'],2)
   self.assertNotIn('_visitors',public);self.assertNotIn('192.168',str(state))
   self.assertNotIn('salt',str(public));self.assertNotIn('hashes',str(public))
   collect(state,log,NOW,{'hotspot_devices':0});self.assertEqual(state['daily']['2026-10-27']['unique_visitors'],2)
   collect(state,log,NOW+timedelta(days=4),{'hotspot_devices':0});self.assertEqual(state['_visitors'],{})
 def test_connection_samples_are_not_sessions(self):
  with patch('tools.collect_usage.command',side_effect=['Station aa\nStation bb\n','0 0 192.168.4.1:5901 192.168.4.5:44321\n0 0 127.0.0.1:4200 127.0.0.1:12345\n0 0 192.168.4.1:22 192.168.4.5:45678']):
   result=sample();self.assertEqual(result['hotspot_devices'],2);self.assertEqual(result['desktop_connections'],1);self.assertEqual(result['terminal_connections'],0);self.assertEqual(result['ssh_connections'],1)
if __name__=='__main__':unittest.main()
