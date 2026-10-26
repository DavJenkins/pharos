import collections,copy,unittest
from app.services.dashboard_cards import compose,validate
from app.services.manifest import load_manifest,ManifestError,url
class DashboardCardTests(unittest.TestCase):
 def fixture(self):
  return {'repositories':[{'id':'family','title':'Family'},{'id':'other','title':'Other'}],'assets':[{'id':'learn','repository_id':'family'},{'id':'play','repository_id':'family'},{'id':'paper','repository_id':'other'}],'dashboard':{'cards':[{'id':'learning','anchor':'family','title':'Learning','repository_ids':[],'asset_ids':['learn']},{'id':'games','anchor':'family','title':'Games','repository_ids':['family'],'asset_ids':[]}]}}
 def test_split_preserves_ownership_and_keeps_each_asset_once(self):
  data=self.fixture();original=copy.deepcopy(data);rows={'family':data['assets'][:2],'other':data['assets'][2:]}
  validate(data,ManifestError,url);repos,out=compose(data,rows)
  self.assertEqual([r['id'] for r in repos],['learning','games','other'])
  self.assertEqual([a['id'] for a in out['learning']],['learn']);self.assertEqual([a['id'] for a in out['games']],['play'])
  self.assertEqual(data,original)
 def test_duplicate_assignment_and_bad_links_are_rejected(self):
  data=self.fixture();data['dashboard']['cards'][1]['asset_ids']=['learn']
  with self.assertRaises(ManifestError):validate(data,ManifestError,url)
  data=self.fixture();data['dashboard']['cards'][0]['links']=[{'title':'bad','url':'javascript:bad'}]
  with self.assertRaises(ManifestError):validate(data,ManifestError,url)
 def test_unknown_references_are_rejected(self):
  data=self.fixture();data['dashboard']['cards'][0]['asset_ids']=['missing']
  with self.assertRaises(ManifestError):validate(data,ManifestError,url)
 def test_live_selection_is_lossless_and_readiness_topics_stay_visible(self):
  data=load_manifest('/opt/dataark/dataark.yaml');rows={}
  for asset in data['assets']:
   if not asset.get('removed'):rows.setdefault(asset['repository_id'],[]).append(asset)
  repos,out=compose(data,rows);counts=collections.Counter(a['id'] for group in out.values() for a in group)
  self.assertEqual(set(counts),{a['id'] for group in rows.values() for a in group});self.assertTrue(all(n==1 for n in counts.values()))
  titles={r['title'] for r in repos}
  for title in ['Drinking Water','Food Preservation & Cooking','Shelter & Winter Readiness','First Aid & Caregiving','Disability Preparedness','Pets & Livestock']:self.assertIn(title,titles)
 def test_without_customization_original_layout_is_retained(self):
  data=self.fixture();data.pop('dashboard');rows={'family':data['assets'][:2]}
  repos,out=compose(data,rows);self.assertIs(out,rows);self.assertEqual(repos,data['repositories'])
