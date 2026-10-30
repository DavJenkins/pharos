from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from tools.update_worker import eligible, choose_filename, source_config, release_info, download
from tools.activate_content_updates import switch_files, restore_files, validate_records
from app.services.update_status import progress


class AutomaticUpdateTests(unittest.TestCase):
    def asset(self):
        return {'id':'wiki', 'relative_path':'wikipedia_en_all_maxi_2026-02.zim',
            'update_policy':'on_network_available', 'refresh_interval':'1d',
            'update_source':{'kind':'kiwix_zim','directory':'https://download.kiwix.org/zim/wikipedia/',
                'filename_prefix':'wikipedia_en_all_maxi_'}}

    def test_policies_and_refresh_intervals(self):
        a=self.asset()
        self.assertTrue(eligible(a,0,100000))
        self.assertFalse(eligible(a,99999,100000))
        a['update_policy']='manual'
        self.assertFalse(eligible(a,0,100000))
        a['update_policy']='auto';a['refresh_interval']='never'
        self.assertFalse(eligible(a,0,100000))

    def test_scheduled_bootstrap_and_other_non_archives_do_not_enter_zim_worker(self):
        for path in ['data-ark-bootstrap.tar.gz','forms/tax.pdf','maps/region.pmtiles']:
            asset={'id':'non-archive','relative_path':path,'update_policy':'pin_version','refresh_interval':'7d','version_pin':'2026.10.29'}
            self.assertFalse(eligible(asset,0,1000000),path)
        # The valid archive following an unrelated pinned kit still gets work.
        mixed=[asset,self.asset()]
        self.assertEqual([item['id'] for item in mixed if eligible(item,0,1000000)],['wiki'])

    def test_missing_or_bad_zim_recipe_is_still_a_configuration_error(self):
        for spec in [None,{'kind':'unsupported'}]:
            asset=self.asset();asset['update_source']=spec
            self.assertTrue(eligible(asset,0,100000))
            with self.assertRaisesRegex(ValueError,'explicit supported'):source_config(asset)

    def test_discovery_keeps_series_and_honors_pin(self):
        html=''.join('<a href="'+name+'">x</a>' for name in [
            'wikipedia_en_all_maxi_2026-02.zim','wikipedia_en_all_maxi_2026-08.zim',
            'wikipedia_en_all_nopic_2026-09.zim','../wikipedia_en_all_maxi_2027-01.zim',
            'wikipedia_en_all_maxi_2026-99.zim'])
        self.assertEqual(choose_filename(html,'wikipedia_en_all_maxi_'),'wikipedia_en_all_maxi_2026-08.zim')
        self.assertEqual(choose_filename(html,'wikipedia_en_all_maxi_','2026-02'),'wikipedia_en_all_maxi_2026-02.zim')
        with self.assertRaises(ValueError):choose_filename(html,'wikipedia_en_all_maxi_','2025-01')

    def test_source_scope_and_no_unintentional_downgrade(self):
        a=self.asset();a['update_source']['directory']='https://example.invalid/'
        with self.assertRaises(ValueError):source_config(a)
        a=self.asset();a['relative_path']='../escape.zim'
        with self.assertRaises(ValueError):source_config(a)
        a=self.asset()
        with patch('tools.update_worker.fetch_small',return_value=b'<a href="wikipedia_en_all_maxi_2026-01.zim">old</a>') as fetch:
            self.assertIsNone(release_info(a));self.assertEqual(fetch.call_count,1)

    def test_ifixit_source_uses_its_exact_release_series(self):
        asset = self.asset()
        asset['relative_path'] = 'ifixit_en_all_2025-12.zim'
        asset['update_source'] = {'kind':'kiwix_zim', 'directory':'https://download.kiwix.org/zim/ifixit/', 'filename_prefix':'ifixit_en_all_'}
        self.assertEqual(source_config(asset), ('https://download.kiwix.org/zim/ifixit/', 'ifixit_en_all_'))
        asset['update_source']['directory'] = 'https://download.kiwix.org/zim/ifixit-untrusted/'
        with self.assertRaises(ValueError): source_config(asset)

    def test_publisher_metadata_must_match_release(self):
        a=self.asset();name='wikipedia_en_all_maxi_2026-08.zim'
        listing=f'<a href="{name}">new</a>'.encode()
        metadata=('<metalink xmlns="urn:ietf:params:xml:ns:metalink"><file name="'+name+'"><size>8</size><hash type="sha-256">'+'a'*64+'</hash></file></metalink>').encode()
        with patch('tools.update_worker.fetch_small',side_effect=[listing,metadata]):
            result=release_info(a);self.assertEqual(result['bytes'],8);self.assertEqual(result['sha256'],'a'*64)
        with patch('tools.update_worker.fetch_small',side_effect=[listing,metadata.replace(name.encode(),b'wrong.zim')]):
            with self.assertRaises(ValueError):release_info(a)

    def test_first_download_can_activate_and_rollback_without_old_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);stage=root/'stage';previous=stage/'previous';previous.mkdir(parents=True)
            (stage/'new.zim').write_bytes(b'new')
            records=[{'old':None,'new':'new.zim'}];validate_records(records)
            switch_files(root,stage,previous,records)
            self.assertTrue((root/'new.zim').is_file())
            restore_files(root,stage,previous,records)
            self.assertEqual((stage/'new.zim').read_bytes(),b'new')

    def test_disk_shortage_does_not_start_download_or_remove_partial(self):
        with tempfile.TemporaryDirectory() as d:
            stage=Path(d);part=stage/'new.zim.part';part.write_bytes(b'ZIM')
            with patch('tools.update_worker.shutil.disk_usage',return_value=MagicMock(free=1)),patch('tools.update_worker.subprocess.Popen') as start:
                with self.assertRaises(RuntimeError):download({'filename':'new.zim','bytes':100},stage,'Title')
                start.assert_not_called()
            self.assertEqual(part.read_bytes(),b'ZIM')

    def test_missing_stale_and_live_worker_status(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'status.json';self.assertIsNone(progress(path))
            now=datetime.now(timezone.utc)
            path.write_text(json.dumps({'state':'downloading','asset':'Wikipedia','percent':25,'updated':now.isoformat()}))
            self.assertEqual(progress(path)['label'],'Downloading 25%: Wikipedia')
            path.write_text(json.dumps({'state':'downloading','updated':(now-timedelta(minutes=10)).isoformat()}))
            self.assertEqual(progress(path)['label'],'Update status stale')
            for percent in (0, 45, 100):
                path.write_text(json.dumps({'state':'verifying','asset':'Wikipedia with a long archive title',
                    'percent':percent,'updated':now.isoformat()}))
                self.assertTrue(progress(path)['label'].startswith(f'Verifying {percent}%:'))
            path.write_text('not json');self.assertEqual(progress(path)['label'],'Update status unavailable')

class WorkerStartupRegression(unittest.TestCase):
    def test_startup_does_not_reference_loop_asset(self):
        from tools import update_worker as worker
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'dataark.yaml').write_text('example')
            with patch.object(worker,'ROOT',root),patch.object(worker,'STATE',root/'state'),patch.object(worker,'run') as run,patch.object(worker,'report') as report:
                self.assertEqual(worker.main(),0)
                run.assert_called_once()
                report.assert_not_called()
