import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import library_helper as helper
from tools.update_worker import source_config
from tools.stage_content_updates import validate_plan
from app.routers.library import router

class LibraryTests(unittest.TestCase):
    def test_gutenberg_source(self):
        source_config({'relative_path':'gutenberg_en_all_2026-01.zim','update_source':{'kind':'kiwix_zim','directory':'https://download.kiwix.org/zim/gutenberg/','filename_prefix':'gutenberg_en_all_'}})

    def test_reject_arbitrary_source(self):
        with self.assertRaises(ValueError):
            source_config({'relative_path':'x_2026-01.zim','update_source':{'kind':'kiwix_zim','directory':'https://evil.example/','filename_prefix':'x_'}})

    def test_reject_invalid_request_before_side_effects(self):
        for payload in ({}, {'repository_id':'../../etc','release':'x','bytes':2}, {'repository_id':'project-gutenberg','release':'x','bytes':2,'url':'https://evil.example'}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                helper.register(payload)

    def test_reject_changed_release_without_writing(self):
        from contextlib import nullcontext
        data={'system':{'base_mount':'/mnt/storage'},'assets':[]}
        with patch('app.services.library_events.events.info'), tempfile.TemporaryDirectory() as tmp, patch.object(helper.Path,'open',return_value=open(Path(tmp)/'lock','a')), patch.object(helper,'load_manifest',return_value=data), patch('app.services.manifest.load_manifest',return_value=data), patch.object(helper.Path,'is_mount',return_value=True), patch.object(helper,'release_info',return_value={'filename':'new.zim','bytes':10}), patch.object(helper,'atomic_write') as write:
            with self.assertRaisesRegex(ValueError,'release changed'):
                helper.register({'repository_id':'project-gutenberg','release':'old.zim','bytes':10})
            write.assert_not_called()

    def test_route_exists(self):
        self.assertEqual({r.path for r in router.routes},{'/library','/library/catalogue','/library/install','/library/remove','/library/restore','/library/unlock','/library/changes','/library/prefer'})

    def test_catalogue_passes_identity_and_reports_release(self):
        from app.services import library
        def release(asset):
            self.assertEqual(asset['id'],'gutenberg-en')
            return {'filename':'gutenberg_en_all_2026-01.zim','bytes':123}
        with patch.object(library,'load_manifest',return_value={'assets':[]}), patch('tools.update_worker.release_info',side_effect=release):
            result=library.catalogue()[0]
            self.assertNotIn('error',result)
            self.assertEqual(result['bytes'],123)

    def test_catalogue_excludes_installed_pending_and_removed_registrations(self):
        from app.services import library
        for removed in (False,True):
            with self.subTest(removed=removed),patch.object(library,'load_manifest',return_value={'assets':[{'repository_id':'project-gutenberg','removed':removed}]}),patch('tools.update_worker.release_info') as release:
                self.assertEqual(library.catalogue(),[])
                release.assert_not_called()

    def test_schedule_last_check_and_next_daily_due(self):
        from app.services.library import update_schedule
        from datetime import datetime
        item=update_schedule({'id':'a','update_policy':'on_network_available','refresh_interval':'1d'}, {}, {'a':1000000}, now=1000010)
        self.assertFalse(item['due_now'])
        self.assertEqual((datetime.fromisoformat(item['next_due'])-datetime.fromisoformat(item['last_checked'])).total_seconds(),86400)
        self.assertTrue(update_schedule({'id':'a','update_policy':'auto','refresh_interval':'1d'}, {}, {'a':1000000}, now=1086400)['due_now'])

    def test_manual_removed_or_disabled_are_not_scheduled(self):
        from app.services.library import update_schedule
        for asset,repo in [({'id':'a','update_policy':'manual','refresh_interval':'never'},{}),({'id':'a','update_policy':'auto','refresh_interval':'1d','removed':True},{}),({'id':'a','update_policy':'auto','refresh_interval':'1d'},{'enabled':False})]:
            item=update_schedule(asset,repo,{'a':1000000},now=2000000)
            self.assertFalse(item['enabled'])
            self.assertIsNone(item['next_due'])
            self.assertFalse(item['due_now'])

    def test_missing_history_is_due_but_invalid_history_is_unknown(self):
        from app.services.library import update_schedule
        asset={'id':'a','update_policy':'auto','refresh_interval':'1d'}
        self.assertTrue(update_schedule(asset,{}, {})['due_now'])
        for value in [True,float('nan'),-1,'wrong',1e300]:
            with self.subTest(value=value):
                item=update_schedule(asset,{}, {'a':value})
                self.assertFalse(item['history_available'])
                self.assertFalse(item['due_now'])
        self.assertFalse(update_schedule(asset,{}, {},False)['history_available'])
