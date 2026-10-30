import json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from app.services import browser_reviews as reviews,integration_health as health

class ReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.record={'id':'doc','title':'Saved document','url':'https://publisher.test/doc.pdf','filename':'doc.pdf','status':'installed','sha256':'abc','checked_at':'2026-10-24T20:00:00+00:00','acquisition':{'method':'browser'}}
  self.now=datetime(2026,10,30,tzinfo=timezone.utc)
 def test_deadline_is_dynamic_and_equal_bytes_reset_it(self):
  early=reviews.review(self.record,{},90,self.now)
  self.assertFalse(early['review_due']);self.assertEqual(early['next_due'],'2027-01-22T20:00:00+00:00')
  late=reviews.review(self.record,{},90,self.now+timedelta(days=100));self.assertTrue(late['review_due'])
  fresh={'state':'current','installed_sha256':'abc','checked_at':'2027-02-01T00:00:00+00:00'}
  self.assertFalse(reviews.review(self.record,fresh,90,datetime(2027,2,2,tzinfo=timezone.utc))['review_due'])
 def test_changed_copy_due_and_stale_comparison_ignored(self):
  self.assertTrue(reviews.review(self.record,{'state':'changed','installed_sha256':'abc'},365,self.now)['review_due'])
  self.assertFalse(reviews.review(self.record,{'state':'changed','installed_sha256':'old'},365,self.now)['review_due'])
 def test_missing_timestamp_is_due(self):
  self.assertTrue(reviews.review({**self.record,'checked_at':'invalid'}, {},365,self.now)['review_due'])
 def test_snapshot_only_configured_existing_installed_files(self):
  folder=self.root/'docs';folder.mkdir();(folder/'doc.pdf').write_bytes(b'file')
  (folder/'sources.json').write_text(json.dumps([self.record,{**self.record,'id':'not-configured'}]))
  policy=self.root/'policy.json';policy.write_text(json.dumps({'collections':['docs'],'review_intervals_days':{'doc':90}}))
  with patch.object(reviews,'MOUNT',self.root),patch.object(reviews,'POLICY',policy),patch.object(reviews,'CAPTURES',self.root/'missing'):
   result=reviews.snapshot(self.now);self.assertEqual(result['required'],1);self.assertEqual(result['overdue'],0)
   reference=self.root/'publisher.json';reference.write_text(json.dumps({'sources':{self.record['url']:{'status':'unchanged'}}}))
   with patch.object(reviews,'REFERENCE',reference):self.assertEqual(reviews.snapshot(self.now)['required'],0)
   (folder/'doc.pdf').unlink();self.assertEqual(reviews.snapshot(self.now)['required'],0)
 def test_health_separates_expected_block_and_records_review_transitions(self):
  source=self.root/'source.json';source.write_text(json.dumps({'sources':{self.record['url']:{'status':'error','detail':'HTTP 403'}}}))
  manual={'required':1,'overdue':0,'changed':0,'reviews':[{'id':'doc','source_url':self.record['url'],'last_verified':'date'}],'review_url':'/capture.html'}
  with patch.object(health,'REFERENCE',source),patch.object(health,'get_status',return_value={'status':{'issues':[]},'services':{}}),patch.object(health,'failed_units',return_value=[]),patch.object(health,'public_status',return_value={}),patch('app.services.software_installation.status',return_value={}),patch.object(reviews,'snapshot',return_value=manual):
   first=health.collect();self.assertEqual(first['state'],'ok');self.assertEqual(first['source_checks']['errors'],0)
   stable=health.collect();self.assertEqual(first['fingerprint'],stable['fingerprint'])
   manual['overdue']=1;due=health.collect();self.assertEqual(due['state'],'warning');self.assertNotEqual(first['fingerprint'],due['fingerprint'])
   manual['overdue']=0;manual['reviews'][0]['last_verified']='newdate';verified=health.collect();self.assertEqual(verified['state'],'ok');self.assertNotEqual(first['fingerprint'],verified['fingerprint'])
   source.write_text(json.dumps({'sources':{self.record['url']:{'status':'error','detail':'HTTP 404'}}}))
   self.assertEqual(health.collect()['source_checks']['errors'],1)

if __name__=='__main__':unittest.main()
