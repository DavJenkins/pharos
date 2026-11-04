"""Isolated review transactions: never touch actual library files or services."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import publisher_review as review


class PublisherReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.mount=self.root/'media';self.mount.mkdir()
        self.stage=self.root/'stage';self.stage.mkdir();self.back=self.mount/'.publisher-review-backups'
        self.installed=self.mount/'forms/schedule-2025.pdf';self.installed.parent.mkdir();self.installed.write_bytes(b'old 2025')
        (self.stage/'candidate.pdf').write_bytes(b'new 2026')
        self.asset={'id':'schedule','title':'Schedule C 2025','relative_path':'forms/schedule-2025.pdf','repository_id':'forms','download_url':'https://www.irs.gov/2025.pdf'}
        self.manifest={'assets':[self.asset],'system':{'base_mount':str(self.mount)},'repositories':[]}
        (self.root/'dataark.yaml').write_text('original manifest')
        (self.root/'config/content').mkdir(parents=True);(self.root/'config/content/profile.json').write_text('original profile')
        self.source=self.asset['download_url'];self.record={'fingerprint':'checked','baseline':'original','pending_change':False,'edition_discovery':{'current_edition':'2025','candidate':{'edition':'2026','url':'https://www.irs.gov/2026.pdf','sha256':review.digest(self.stage/'candidate.pdf')}}}
        self.state=self.root/'reference.json';self.state.write_text(json.dumps({'sources':{self.source:self.record}}))
        self.value={'job':'f'*32,'asset_id':'schedule','title':'Schedule C','kind':'document','state':'installing','decision':'install','edition':self.record['edition_discovery']['candidate'],'revision':review.revision(self.record),'checked':{'fingerprint':'checked','fingerprint_kind':'bytes'},'files':[{'file':'candidate.pdf','relative_path':self.asset['relative_path'],'sha256':review.digest(self.stage/'candidate.pdf'),'bytes':8}]}
        self.patches=[patch.object(review,'ROOT',self.root),patch.object(review.checks,'STATE',self.state),patch.object(review,'save'),patch('tools.library_removal.serialize',side_effect=lambda d:json.dumps(d)),patch('tools.library_removal.publish_library'),patch.object(review.subprocess,'run'),patch('tools.update_notifications.content')]
        self.mocks=[p.start() for p in self.patches]
        for p in self.patches:self.addCleanup(p.stop)
        for patcher in (patch.object(review,'STATE',self.root/'jobs'),patch.object(review,'UPDATES_LOCK',self.root/'updates.lock'),patch.object(review,'notify')):
            patcher.start();self.addCleanup(patcher.stop)

    def apply(self):review.apply(self.value,self.manifest,self.asset,self.mount,self.installed,self.source,self.record,self.stage)

    def test_new_edition_retains_old_file_and_registers_both_distinct_links(self):
        self.apply()
        data=json.loads((self.root/'dataark.yaml').read_text())
        self.assertEqual(self.installed.read_bytes(),b'old 2025')
        self.assertEqual(len(data['assets']),2)
        self.assertEqual(data['assets'][0]['title'],'Schedule C 2025')
        new=data['assets'][1]
        self.assertEqual(new['title'],'Schedule C 2026')
        self.assertEqual(new['service_endpoint'],'/library-files/forms/schedule-2026.pdf')
        self.assertEqual((self.mount/new['relative_path']).read_bytes(),b'new 2026')
        self.assertFalse((self.back/self.value['job']/'dataark.yaml').exists())
        self.assertTrue((self.root/'jobs/configuration-backups'/self.value['job']/'dataark.yaml').exists())

    def test_keep_does_not_modify_content_and_acknowledges_only_exact_edition(self):
        self.value['decision']='keep';self.apply()
        self.assertEqual(self.installed.read_bytes(),b'old 2025')
        self.assertEqual((self.root/'dataark.yaml').read_text(),'original manifest')
        record=json.loads(self.state.read_text())['sources'][self.source]
        self.assertIsNone(record['edition_discovery']['candidate'])
        self.assertEqual(record['edition_discovery']['reviewed_candidate']['edition'],'2026')
        self.assertFalse(record['pending_change'])

    def test_replacement_retains_each_previous_file_once(self):
        self.value.pop('edition');self.record['edition_discovery']={}
        self.value['revision']=review.revision(self.record)
        self.state.write_text(json.dumps({'sources':{self.source:self.record}}))
        original=review.shutil.copyfile
        with patch.object(review.shutil,'copyfile',wraps=original) as copied:self.apply()
        retained=[c for c in copied.call_args_list if c.args[0]==self.installed and c.args[1]==self.back/self.value['job']/'candidate.pdf']
        self.assertEqual(len(retained),1)
        self.assertEqual((self.back/self.value['job']/'candidate.pdf').read_bytes(),b'old 2025')

    def test_checksum_progress_reports_the_actual_bytes_and_phase(self):
        expected=review.digest(self.installed)
        self.assertEqual(review.installed_digest(self.installed,self.value,'Checking installed file checksum'),expected)
        telemetry=self.value['install_telemetry']
        self.assertEqual(telemetry['bytes_processed'],len(b'old 2025'))
        self.assertEqual(telemetry['percent'],100)
        self.assertEqual(telemetry['phase'],'Checking installed file checksum')

    def test_observed_progress_is_bound_to_the_current_job_and_fresh(self):
        import time
        from app.services import publisher_review as public
        folder=self.root/'public-progress';folder.mkdir();(folder/'progress').mkdir()
        job='f'*32
        (folder/'schedule.json').write_text(json.dumps({'state':'installing','job':job,'updated_at':time.time()}))
        sidecar=folder/'progress'/(job+'.json')
        with patch.object(public,'STATE',folder):
            sidecar.write_text(json.dumps({'job':job,'observed_at':time.time(),'telemetry':{'phase':'Checking checksum','percent':50}}))
            self.assertEqual(public.status('schedule')['install_telemetry']['percent'],50)
            sidecar.write_text(json.dumps({'job':'different','observed_at':time.time(),'telemetry':{'percent':100}}))
            self.assertNotIn('install_telemetry',public.status('schedule'))
            sidecar.write_text(json.dumps({'job':job,'observed_at':time.time()-60,'telemetry':{'percent':100}}))
            self.assertNotIn('install_telemetry',public.status('schedule'))

    def test_dashboard_progress_preserves_asset_identity_and_measured_percentage(self):
        from app.services import publisher_review as public
        folder=self.root/'dashboard-progress';folder.mkdir()
        (folder/'map.json').write_text(json.dumps({'asset_id':'map','updated_at':1}))
        current={'asset_id':'map','job':'f'*32,'state':'installing','title':'Map','install_telemetry':{'percent':42.5,'phase':'Backing up map'}}
        with patch.object(public,'STATE',folder),patch.object(public,'status',return_value=current):
            result=public.active_progress()
        self.assertEqual(result['asset_id'],'map')
        self.assertEqual(result['percent'],42.5)
        self.assertEqual(result['phase'],'Backing up map')

    def test_tampered_staging_file_is_not_installed(self):
        (self.stage/'candidate.pdf').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'verification'):self.apply()
        self.assertEqual(self.installed.read_bytes(),b'old 2025')

    def test_publication_failure_rolls_back_new_file_and_manifest(self):
        self.mocks[4].side_effect=[RuntimeError('publication failed'),None]
        self.value.pop('edition');self.record['edition_discovery']={}
        self.value['revision']=review.revision(self.record)
        self.state.write_text(json.dumps({'sources':{self.source:self.record}}))
        with patch.object(Path,'is_mount',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'publication failed'):self.apply()
        self.assertEqual(self.installed.read_bytes(),b'old 2025')
        self.assertEqual((self.root/'dataark.yaml').read_text(),'original manifest')

    def test_revision_detects_different_candidate(self):
        changed=copy.deepcopy(self.record);changed['edition_discovery']['candidate']['sha256']='different'
        self.assertNotEqual(review.revision(changed),review.revision(self.record))

    def test_repeated_check_timestamps_do_not_invalidate_the_same_candidate(self):
        changed=copy.deepcopy(self.record)
        changed['edition_discovery']['attempted_at']=123456
        changed['edition_discovery']['detail']='Same candidate checked again'
        changed['checked_at']=123456
        self.assertEqual(review.revision(changed),review.revision(self.record))

    def test_file_version_ignores_exfat_inode_reallocation_but_detects_size(self):
        from types import SimpleNamespace
        a=SimpleNamespace(st_dev=1,st_ino=10,st_size=20,st_mtime_ns=30)
        b=SimpleNamespace(st_dev=1,st_ino=99,st_size=20,st_mtime_ns=30)
        with patch.object(Path,'stat',return_value=a):first=review.file_version(self.installed)
        with patch.object(Path,'stat',return_value=b):self.assertEqual(first,review.file_version(self.installed))
        b.st_size=21
        with patch.object(Path,'stat',return_value=b):self.assertNotEqual(first,review.file_version(self.installed))

    def test_html_comparison_excludes_ark_wrapper_and_virginia_banner_clock(self):
        a=self.root/'old.html';b=self.root/'new.html'
        a.write_text('<h1>Old wrapper</h1><p><a>Publisher source</a></p><main>Constitution of Virginia10/24/2026 10/24/2026<p>Real provisions</p></main>')
        b.write_text('<h1>Different wrapper</h1><div><a>Original publisher page (internet)</a></div><main>Constitution of Virginia11/3/2026 11/3/2026<p>Real provisions</p></main>')
        self.assertTrue(review.comparison(a,b)['identical'])
        b.write_text(b.read_text().replace('Real provisions','Amended provisions'))
        self.assertFalse(review.comparison(a,b)['identical'])

    def test_new_year_appends_provenance_without_rewriting_last_year(self):
        index=self.installed.parent/'sources.json'
        original={'id':'schedule','filename':self.installed.name,'title':'2025 Schedule C','sha256':review.digest(self.installed),'url':self.source}
        index.write_text(json.dumps([original]))
        self.apply()
        records=json.loads(index.read_text())
        self.assertEqual(records[0],original)
        self.assertEqual(records[1]['filename'],'schedule-2026.pdf')
        self.assertEqual(records[1]['url'],'https://www.irs.gov/2026.pdf')

    def test_interrupted_transaction_restores_files_and_configuration(self):
        backup=self.back/self.value['job'];backup.mkdir(parents=True)
        (backup/'candidate.pdf').write_bytes(b'old 2025')
        private=self.root/'jobs/configuration-backups'/self.value['job'];private.mkdir(parents=True)
        (private/'dataark.yaml').write_text('original manifest')
        self.installed.write_bytes(b'partially replaced')
        self.value['transaction']={'mount':str(self.mount),'files':[{'file':'candidate.pdf','relative_path':self.asset['relative_path'],'existed':True}]}
        with patch.object(Path,'is_mount',return_value=True):review.recover(self.value)
        self.assertEqual(self.installed.read_bytes(),b'old 2025')
        self.assertNotIn('transaction',self.value)

    def test_invalid_decision_and_traversal_refused(self):
        for payload in [{'action':'publisher_review','asset_id':'../bad','decision':'prepare','job':''}, {'action':'publisher_review','asset_id':'good','decision':'execute','job':''}]:
            with self.assertRaises(ValueError):review.submit(payload)

    def test_submit_queues_only_fixed_worker_and_registered_identity(self):
        args=(self.manifest,self.asset,self.mount,self.installed,self.source,self.record)
        with patch('app.services.publisher_review.status',return_value={'state':'idle'}),patch.object(review,'asset_record',return_value=args):
            result=review.submit({'action':'publisher_review','asset_id':'schedule','decision':'prepare','job':''})
        self.assertEqual(result['state'],'queued')
        command=self.mocks[5].call_args.args[0]
        self.assertIn(str(self.root/'tools/publisher_review.py'),command)
        self.assertEqual(command[-2],'schedule')
        self.assertRegex(command[-1],r'^[0-9a-f]{32}$')
        self.assertFalse(any('https://' in word for word in command))

    def test_decision_rejects_stale_source_revision(self):
        old=dict(self.value,state='ready',installed_version=review.file_version(self.installed))
        changed=copy.deepcopy(self.record);changed['fingerprint']='newer-publisher-version'
        args=(self.manifest,self.asset,self.mount,self.installed,self.source,changed)
        with patch('app.services.publisher_review.status',return_value=old),patch.object(review,'asset_record',return_value=args):
            with self.assertRaisesRegex(ValueError,'changed'):
                review.submit({'action':'publisher_review','asset_id':'schedule','decision':'install','job':old['job']})
        self.assertEqual(self.installed.read_bytes(),b'old 2025')

    def test_worker_prepares_without_installing(self):
        value=dict(self.value,state='queued',installed_version=review.file_version(self.installed))
        args=(self.manifest,self.asset,self.mount,self.installed,self.source,self.record)
        with patch('app.services.publisher_review.status',return_value=value),patch.object(review,'asset_record',return_value=args),patch.object(review,'prepare') as prepare:
            review.worker('schedule',value['job'])
        self.assertEqual(value['state'],'ready');prepare.assert_called_once()
        self.assertEqual(self.installed.read_bytes(),b'old 2025')

    def test_worker_failed_fetch_does_not_install_or_acknowledge(self):
        value=dict(self.value,state='queued',installed_version=review.file_version(self.installed))
        args=(self.manifest,self.asset,self.mount,self.installed,self.source,self.record)
        before=self.state.read_bytes()
        with patch('app.services.publisher_review.status',return_value=value),patch.object(review,'asset_record',return_value=args),patch.object(review,'prepare',side_effect=ValueError('Publisher unavailable')):
            with self.assertRaisesRegex(ValueError,'Publisher unavailable'):review.worker('schedule',value['job'])
        self.assertEqual(value['state'],'failed')
        self.assertEqual(self.state.read_bytes(),before)
        self.assertEqual(self.installed.read_bytes(),b'old 2025')


if __name__=='__main__':unittest.main()
