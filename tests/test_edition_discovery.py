import hashlib,io,json
from datetime import date
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from urllib.error import HTTPError
from tools import edition_discovery as d
from app.services import reference_checks as view

class Response(io.BytesIO):
 def __init__(self,url,data):super().__init__(data);self.url=url;self.headers={}

class EditionTests(unittest.TestCase):
 def setUp(self):
  self.rule={'kind':'dated_template','directory_template':'https://publisher.example/editions/{year}/','filename_template':'guide-{year}.pdf','period':'year','current_edition':'2024','lookback':2,'lookahead':1,'max_probes':4,'edition_text_pattern':r'\b{year}\b'}
  self.asset={'id':'guide','download_url':'https://publisher.example/editions/2024/guide-2024.pdf'}
 def fake(self,available,calls):
  def open(request,**kwargs):
   calls.append(request.full_url)
   if request.full_url not in available:raise HTTPError(request.full_url,404,'missing',{},None)
   return Response(request.full_url,available[request.full_url])
  return open
 def test_newest_valid_edition_is_detected_without_installing(self):
  url='https://publisher.example/editions/2025/guide-2025.pdf';calls=[]
  r=d.discover(self.rule,self.asset,date(2025,10,27),self.fake({url:b'%PDF-new'},calls),lambda *a:'a'*64)
  self.assertEqual(r['status'],'available');self.assertEqual(r['candidate']['edition'],'2025');self.assertEqual(r['candidate']['sha256'],'a'*64);self.assertLessEqual(len(calls),4)
 def test_missing_future_editions_are_not_errors(self):
  r=d.discover(self.rule,self.asset,date(2025,10,27),self.fake({},[]),lambda *a:'x')
  self.assertEqual(r['status'],'no_new_edition');self.assertIsNone(r['candidate'])
 def test_installed_url_advances_the_baseline(self):
  self.asset['download_url']='https://publisher.example/editions/2025/guide-2025.pdf';calls=[]
  d.discover(self.rule,self.asset,date(2025,10,27),self.fake({},calls),lambda *a:'x')
  self.assertTrue(all('/2026/' in u for u in calls))
 def test_index_filters_unlisted_and_external_links(self):
  self.rule.update(kind='index',index_url='https://publisher.example/catalogue')
  url='https://publisher.example/editions/2025/guide-2025.pdf';calls=[]
  sources={self.rule['index_url']:b'<a href="/editions/2025/guide-2025.pdf">Guide</a><a href="https://evil.example/x.pdf">other</a>',url:b'%PDF-new'}
  r=d.discover(self.rule,self.asset,date(2025,10,27),self.fake(sources,calls),lambda *a:'x')
  self.assertEqual(r['status'],'available');self.assertEqual(calls,[self.rule['index_url'],url])
 def test_year_month_and_day_windows_cross_boundaries(self):
  rule={**self.rule,'period':'month','directory_template':'https://publisher.example/{year}/{month:02d}/'}
  self.assertEqual(d.window(rule,date(2026,1,1))[0],date(2026,2,1));self.assertIn(date(2025,12,1),d.window(rule,date(2026,1,1)))
  rule['period']='day';self.assertIn(date(2025,12,31),d.window(rule,date(2026,1,1)))
 def test_templates_must_be_bounded_and_public(self):
  for changes in [{'directory_template':'http://publisher.example/{year}/'},{'directory_template':'https://127.0.0.1/{year}/'},{'filename_template':'{unknown}.pdf'},{'lookback':100},{'action':'automatic'},{'lookback':10,'max_probes':2}]:
   with self.subTest(changes=changes),self.assertRaises(ValueError):d.validate({**self.rule,**changes})
 def test_redirect_cannot_leave_configured_publisher(self):
  with self.assertRaises(ValueError):d.PublisherRedirect({'publisher.example'}).redirect_request(None,None,302,'',{},'https://evil.example/file.pdf')
 def test_html_and_wrong_edition_pdf_are_rejected(self):
  with self.assertRaises(ValueError):d.pdf_edition(b'<html>not a PDF</html>',self.rule,date(2025,1,1))
  with patch.object(d.subprocess,'run'),patch.object(d.subprocess,'check_output',return_value='Guide edition 2024'):
   with self.assertRaises(ValueError):d.pdf_edition(b'%PDF-test',self.rule,date(2025,1,1))
  with patch.object(d.subprocess,'run'),patch.object(d.subprocess,'check_output',return_value='Guide edition 2025 DRAFT'):
   with self.assertRaises(ValueError):d.pdf_edition(b'%PDF-test',self.rule,date(2025,1,1))
 def test_valid_pdf_edition_gets_content_checksum(self):
  with patch.object(d.subprocess,'run'),patch.object(d.subprocess,'check_output',return_value='Guide edition 2025'):
   self.assertEqual(d.pdf_edition(b'%PDF-test',self.rule,date(2025,1,1)),hashlib.sha256(b'%PDF-test').hexdigest())
 def test_response_size_and_host_are_checked(self):
  with self.assertRaises(ValueError):d.fetch('https://publisher.example/a',{'publisher.example'},2,lambda *a,**k:Response('https://publisher.example/a',b'large'))
  with self.assertRaises(ValueError):d.fetch('https://publisher.example/a',{'publisher.example'},20,lambda *a,**k:Response('https://other.example/a',b'data'))
 def test_rate_limit_stops_probing(self):
  calls=[]
  def limited(request,**kwargs):calls.append(request.full_url);raise HTTPError(request.full_url,429,'wait',{},None)
  r=d.discover(self.rule,self.asset,date(2025,1,1),limited)
  self.assertEqual(len(calls),1);self.assertEqual(r['status'],'error')
 def test_inventory_projection_keeps_new_edition_distinct(self):
  asset={**self.asset,'relative_path':'guide.pdf','repository_id':'docs'}
  candidate={'edition':'2025','url':'https://publisher.example/editions/2025/guide-2025.pdf','bytes':10,'sha256':'a'*64}
  state={'sources':{asset['download_url']:{'status':'unchanged','edition_discovery':{'status':'available','candidate':candidate,'detail':'New edition available'}}}}
  result=view.projection(asset,{'enabled':True},{'enabled':True,'interval':'7d'},state,0)
  self.assertEqual(result['result'],'edition_available');self.assertEqual(result['available_edition'],candidate);self.assertTrue(result['pending_change']);self.assertEqual(result['source_url'],asset['download_url'])
 def test_configured_rules_validate_against_real_saved_sources(self):
  from tools.check_reference_sources import ROOT
  config=json.loads((ROOT/'deploy/reference/edition-discovery.json').read_text())
  self.assertGreater(len(config['rules']),1)
  for rule in config['rules'].values():d.validate(rule)

if __name__=='__main__':unittest.main()

class EditionStateTests(unittest.TestCase):
 def test_old_file_under_new_url_is_not_a_new_edition(self):
  rule={'kind':'dated_template','url_template':'https://publisher.example/{year}/guide.pdf','current_edition':'2024','edition_text_pattern':r'\b{year}\b'}
  asset={'download_url':'https://publisher.example/2024/guide.pdf','expected_hash':'a'*64}
  result=d.discover(rule,asset,date(2025,1,1),lambda request,**kwargs:Response(request.full_url,b'%PDF-old'),lambda *args:'a'*64)
  self.assertIsNone(result['candidate']);self.assertEqual(result['status'],'error')
 def test_fixed_source_refresh_preserves_discovered_edition(self):
  from tools import check_reference_sources as worker
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'guide.pdf').write_bytes(b'original');url='https://publisher.example/old.pdf';statepath=root/'state.json'
   candidate={'edition':'2025','url':'https://publisher.example/new.pdf','sha256':'b'*64,'bytes':20}
   saved={'status':'available','candidate':candidate,'detail':'New edition available'}
   statepath.write_text(json.dumps({'sources':{url:{'edition_discovery':saved}}}))
   manifest={'system':{'base_mount':folder},'repositories':[{'id':'docs'}],'assets':[{'id':'fixture','repository_id':'docs','relative_path':'guide.pdf','download_url':url}]}
   with patch.object(worker,'STATE',statepath),patch.object(worker,'settings',return_value={'enabled':True,'interval':'7d','request_delay_seconds':0}),patch.object(worker,'load_manifest',return_value=manifest),patch.object(worker.Path,'is_mount',return_value=True),patch.object(worker,'check',return_value={'status':'unchanged'}):worker.run()
   self.assertEqual(json.loads(statepath.read_text())['sources'][url]['edition_discovery'],saved)
 def test_failed_discovery_keeps_previous_candidate(self):
  from tools import check_reference_sources as worker
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'guide.pdf').write_bytes(b'original');url='https://publisher.example/old.pdf'
   candidate={'edition':'2025','url':'https://publisher.example/new.pdf'}
   state={'sources':{url:{'edition_discovery':{'candidate':candidate}}}}
   manifest={'repositories':[{'id':'docs'}],'assets':[{'id':'fixture','repository_id':'docs','relative_path':'guide.pdf','download_url':url}]}
   with patch.object(worker,'STATE',root/'state.json'),patch.object(worker,'read',return_value={'schema':1,'enabled':True,'rules':{'fixture':{}|{'kind':'dated_template'}}}),patch('tools.edition_discovery.discover',return_value={'status':'error','candidate':None,'issues':['HTTP 429']}):worker.discover_editions(manifest,root,state,{'request_delay_seconds':0})
   self.assertEqual(state['sources'][url]['edition_discovery']['candidate'],candidate)

class PublisherSoft404Tests(unittest.TestCase):
 def test_explicit_publisher_not_found_title_is_absence_not_failure(self):
  rule={'kind':'dated_template','url_template':'https://publisher.example/{year}/guide.pdf','current_edition':'2024','edition_text_pattern':r'\b{year}\b','not_found_title_pattern':r'Page Not Found \| GovInfo'}
  result=d.discover(rule,{'download_url':'https://publisher.example/2024/guide.pdf'},date(2025,1,1),lambda req,**kwargs:Response(req.full_url,b'<html><title>Page Not Found | GovInfo</title></html>'))
  self.assertEqual(result['status'],'no_new_edition')
 def test_other_html_is_not_mistaken_for_a_missing_edition(self):
  rule={'kind':'dated_template','url_template':'https://publisher.example/{year}/guide.pdf','current_edition':'2024','edition_text_pattern':r'\b{year}\b','not_found_title_pattern':r'Page Not Found \| GovInfo'}
  result=d.discover(rule,{'download_url':'https://publisher.example/2024/guide.pdf'},date(2025,1,1),lambda req,**kwargs:Response(req.full_url,b'<html><title>Access denied</title></html>'))
  self.assertEqual(result['status'],'error')
