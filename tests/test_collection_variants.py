import copy,unittest
from app.services.collection_variants import groups,recovery_archives
class VariantTests(unittest.TestCase):
 def setUp(self):
  self.data={'repositories':[{'id':'encyclopedia','title':'Encyclopedia','preferred_variant':'illustrated','variants':[{'id':'illustrated','title':'Images','asset_id':'large'},{'id':'text','title':'Text','asset_id':'small'}]}],'assets':[{'id':'large','repository_id':'encyclopedia','relative_path':'large.zim'},{'id':'small','repository_id':'encyclopedia','relative_path':'small.zim'}]}
  self.profile={'archives':[{'id':'large'},{'id':'small'}],'variant_groups':groups(self.data)}
 def test_preferred_chooses_one(self):self.assertEqual(recovery_archives(self.profile,{}),{'small'})
 def test_policy_can_choose_other_enabled_variant(self):self.assertEqual(recovery_archives(self.profile,{'variant_preferences':{'encyclopedia':'text'}}),{'large'})
 def test_disabled_is_never_resurrected(self):
  self.profile['archives'][0]['enabled']=False
  self.assertEqual(recovery_archives(self.profile,{}),{'large'})
  with self.assertRaises(ValueError):recovery_archives(self.profile,{'variant_preferences':{'encyclopedia':'illustrated'}})
 def test_both_disabled_restore_neither(self):
  for a in self.profile['archives']:a['enabled']=False
  self.assertEqual(recovery_archives(self.profile,{}),{'large','small'})
 def test_invalid_membership_and_preference_rejected(self):
  self.data['repositories'][0]['variants'][1]['asset_id']='large'
  with self.assertRaises(ValueError):groups(self.data)
  with self.assertRaises(ValueError):recovery_archives(self.profile,{'variant_preferences':{'typo':'text'}})
 def test_recovery_packages_select_one_enabled_archive(self):
  from tools.recovery_queue import packages
  policy={'recipe_tiers':{},'recommended_archives':[],'minimal_file_max_bytes':1}
  self.assertEqual([p['id'] for p in packages(self.profile,policy)],['large'])
  policy['variant_preferences']={'encyclopedia':'text'}
  self.assertEqual([p['id'] for p in packages(self.profile,policy)],['small'])
 def test_legacy_profiles_unchanged(self):self.assertEqual(recovery_archives({'archives':[{'id':'a'},{'id':'b'}]},{}),set())
if __name__=='__main__':unittest.main()
