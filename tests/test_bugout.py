import asyncio
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock
import uuid

from app.services import bugout as b
from tools import bugout_worker as worker
from app.main import app


class BugoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.state = self.base/'state'; self.state.mkdir()
        (self.state/'credentials').mkdir(); (self.state/'gnupg').mkdir()
        self.runtime = self.base/'run'; self.runtime.mkdir()
        self.root = self.base/'ssd'; self.root.mkdir()
        self.task = {'id':'household','title':'Household documents','host':'nas.local','share':'Documents','credential':'nas'}
        self.cfg = {'tasks':[self.task], 'reserve_gib':2}
        for name, value in [('STATE',self.state),('RUNTIME',self.runtime),('SMB',sys.executable),('KEYS',self.base/'keys')]:
            mock = patch.object(b,name,value);mock.start();self.addCleanup(mock.stop)
        mock = patch.object(b,'configuration',return_value=(self.cfg,self.root));mock.start();self.addCleanup(mock.stop)
        self.integration = patch.object(b,'integration',return_value={}).start();self.addCleanup(patch.stopall)
        b.heartbeat()

    def ready(self):
        return {'ready':True,'reason':'Ready','tasks':[{'id':'household','title':'Household documents','ready':True,'reason':'Ready'}]}

    def start(self):
        with patch.object(b,'readiness',return_value=self.ready()):
            return b.start(str(uuid.uuid4()),'ark')

    def test_config_rejects_unsafe_sources_and_secret_inline(self):
        b.validate(self.cfg)
        for update in ({'host':'nas;rm'}, {'share':'../secret'}, {'path':'../secret'}, {'path':'x;put y'},
                       {'password':'secret'}, {'credential':'../secret'}, {'timeout_seconds':0},
                       {'encryption':{'method':'openpgp','public_key':'../key.asc'}}):
            task = dict(self.task,**update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                b.validate({'tasks':[task]})

    def test_empty_config_never_probes_or_exposes_button(self):
        with patch.object(b,'configuration',return_value=({'tasks':[]},self.root)), patch.object(b,'source_ready') as probe:
            self.assertFalse(b.readiness()['configured'])
            probe.assert_not_called()

    def test_readiness_gates_disk_worker_and_sources(self):
        with patch.object(b,'destination_ready',return_value=(False,'SSD not mounted')), patch.object(b,'source_ready') as probe:
            state = b.readiness()
            self.assertFalse(state['ready']);probe.assert_not_called()
        with patch.object(b,'destination_ready',return_value=(True,'Ready')), patch.object(b,'source_ready',return_value=(True,'Ready')):
            self.assertTrue(b.readiness()['ready'])
        (self.runtime/'heartbeat').unlink()
        with patch.object(b,'source_ready') as probe:
            self.assertFalse(b.readiness()['ready']);probe.assert_not_called()

    def test_source_check_timestamp_only_when_readiness_is_checked(self):
        stamp='2026-09-27T15:08:00+00:00'
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'now',return_value=stamp):
            for available in (True,False):
                with patch.object(b,'source_ready',return_value=(available,'Ready' if available else 'Share unavailable')):
                    task=b.readiness()['tasks'][0]
                    self.assertEqual(task['checked'],stamp)
                    self.assertEqual(task['ready'],available)
        with patch.object(b,'destination_ready',return_value=(False,'SSD unavailable')),patch.object(b,'source_ready') as probe:
            self.assertIsNone(b.readiness()['tasks'][0]['checked'])
            probe.assert_not_called()

    def test_credentials_private_and_use_once_expire(self):
        value={'username':'reader','password':'SECRET','domain':'HOME','remember':False}
        b.save_credential('household',value)
        self.assertFalse((self.state/'credentials/nas.json').exists())
        self.assertEqual(b.read_credential('nas')['password'],'SECRET')
        with b.smb_command(self.task) as args:
            self.assertNotIn('SECRET',' '.join(args))
            auth = Path(args[args.index('-A')+1]);self.assertIn('password = SECRET',auth.read_text())
        self.assertFalse(auth.exists())
        with patch.object(b.time,'time',return_value=time.time()+3601):
            self.assertIsNone(b.read_credential('nas'))
        b.save_credential('household',dict(value,remember=True))
        self.assertTrue((self.state/'credentials/nas.json').exists())
        with self.assertRaises(ValueError): b.save_credential('household',dict(value,password='bad\nusername=evil'))

    def test_readiness_reports_saved_credentials_without_secrets(self):
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')):
            self.assertFalse(b.readiness()['tasks'][0]['credentials_saved'])
            b.save_credential('household',{'username':'reader','password':'PRIVATE-SAVED','domain':'HOME','remember':True})
            state=b.readiness()
            self.assertTrue(state['tasks'][0]['credentials_saved'])
            self.assertNotIn('PRIVATE-SAVED',json.dumps(state))

    def test_credentials_cannot_change_mid_operation(self):
        self.start()
        with self.assertRaisesRegex(ValueError,'active backup'):
            b.save_credential('household',{'username':'x','password':'y','domain':'','remember':True})

    def test_authentication_and_source_error_classification(self):
        self.integration.return_value={'inbound_token_sha256':hashlib.sha256(b'secret').hexdigest()}
        self.assertTrue(b.ha_authorized('Bearer secret'))
        self.assertFalse(b.ha_authorized('Bearer wrong'))
        self.assertFalse(b.source_ready(self.task)[0])
        guest = dict(self.task);guest.pop('credential')
        with patch.object(b.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr=b'NT_STATUS_LOGON_FAILURE')):
            self.assertIn('Credentials rejected',b.source_ready(guest)[1])

    def test_idempotency_and_active_operation_alias_survive_completion(self):
        self.integration.return_value={'url':'http://ha.local:8123','token':'private'}
        first = self.start(); other=str(uuid.uuid4())
        with patch.object(b,'readiness',return_value=self.ready()):
            self.assertEqual(b.start(first['id'],'home_assistant')['id'],first['id'])
            self.assertEqual(b.start(other,'home_assistant')['id'],first['id'])
        first['state']='completed';b.update(first,'completed')
        with patch.object(b,'readiness') as probe:
            self.assertEqual(b.start(other,'home_assistant')['state'],'completed');probe.assert_not_called()
        with b.database() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM operations').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],2)

    def test_concurrent_triggers_queue_only_one_operation(self):
        from concurrent.futures import ThreadPoolExecutor
        with patch.object(b,'readiness',return_value=self.ready()), ThreadPoolExecutor(max_workers=3) as pool:
            values=list(pool.map(lambda _:b.start(str(uuid.uuid4()),'ark'),range(3)))
        self.assertEqual(len({v['id'] for v in values}),1)

    def test_not_ready_does_not_queue(self):
        with patch.object(b,'readiness',return_value={'ready':False,'reason':'No source'}):
            with self.assertRaisesRegex(ValueError,'No source'): b.start(str(uuid.uuid4()),'ark')
        with b.database() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM operations').fetchone()[0],0)

    def test_snapshot_success_and_failure_preserve_existing_files(self):
        producer = "import sys,tarfile,io; t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|'); i=tarfile.TarInfo('note.txt'); i.size=4; t.addfile(i,io.BytesIO(b'book')); t.close()"
        for fail in (False,True):
            op=self.start()
            cmd=[sys.executable,'-c','import sys; sys.exit(2)' if fail else producer]
            (self.root/'bugout-backups').mkdir(exist_ok=True)
            old=self.root/'bugout-backups/keep.txt';old.write_text('keep')
            # The temporary filesystem may be RAM-backed and smaller than the
            # production SSD reserve. Capacity is tested separately below.
            with patch.object(b,'source_ready',return_value=(True,'Ready')), patch.object(Path,'is_mount',return_value=True), patch.object(b.shutil,'disk_usage',return_value=SimpleNamespace(free=10 * 1024**3)), patch.object(b,'smb_command',return_value=nullcontext(cmd)):
                worker.run_operation(op)
            self.assertEqual(op['state'],'failed' if fail else 'completed',op.get('results'))
            self.assertEqual(old.read_text(),'keep')
            self.assertEqual(list((self.root/'.bugout-staging').iterdir()),[])
            if not fail:
                self.assertTrue((self.root/'bugout-backups'/op['results'][0]['file']).is_file())

    def test_low_space_rejects_snapshot_before_starting_producer(self):
        op=self.start()
        with patch.object(Path,'is_mount',return_value=True), patch.object(b.shutil,'disk_usage',return_value=SimpleNamespace(free=1024**3)), patch.object(worker.subprocess,'Popen') as producer:
            worker.run_operation(op)
        producer.assert_not_called()
        self.assertEqual(op['state'],'failed')
        self.assertEqual(op['results'][0]['message'],'SSD space is below the reserve')
        self.assertFalse((self.root/'.bugout-staging').exists())

    def test_copy_failure_reports_status_codes_not_stderr(self):
        op=self.start()
        producer=[sys.executable,'-c',"import sys;sys.stderr.write('private-filename secret NT_STATUS_ACCESS_DENIED');sys.exit(1)"]
        with patch.object(b,'source_ready',return_value=(True,'Ready')),patch.object(Path,'is_mount',return_value=True),patch.object(b.shutil,'disk_usage',return_value=SimpleNamespace(free=10*1024**3)),patch.object(worker,'producer_command',return_value=nullcontext(producer)):
            worker.run_operation(op)
        message=op['results'][0]['message']
        self.assertIn('exit 1',message)
        self.assertIn('NT_STATUS_ACCESS_DENIED',message)
        self.assertNotIn('secret',message)
        self.assertNotIn('private-filename',message)

    def test_timeout_cleans_only_the_partial_snapshot(self):
        op=self.start();result=op['results'][0]
        child=MagicMock();child.poll.return_value=None
        with patch.object(b,'destination_ready',return_value=(True,'Ready')), patch.object(b,'source_ready',return_value=(True,'Ready')), patch.object(b,'smb_command',return_value=nullcontext(['fake'])), patch.object(worker.subprocess,'Popen',return_value=child), patch.object(worker.time,'monotonic',side_effect=[0,2000]):
            with self.assertRaisesRegex(RuntimeError,'timed out'):
                worker.copy_task(self.task,self.root,self.cfg,op,result)
        child.terminate.assert_called_once()
        self.assertEqual(list((self.root/'.bugout-staging').iterdir()),[])

    def test_encryption_streams_to_gpg_without_plaintext_file(self):
        op=self.start();result=op['results'][0]
        task=dict(self.task,encryption={'method':'openpgp','public_key':'recipient.asc'})
        producer=MagicMock();producer.poll.return_value=0;producer.returncode=0
        consumer=MagicMock();consumer.poll.return_value=0;consumer.returncode=0
        calls=[]
        def spawn(args,**kwargs):
            calls.append((args,kwargs))
            if args[0]=='fake-smb':return producer
            kwargs['stdout'].write(b'encrypted-test-output')
            return consumer
        (self.root/'bugout-backups').mkdir()
        with patch.object(b,'destination_ready',return_value=(True,'Ready')), patch.object(b,'source_ready',return_value=(True,'Ready')), patch.object(b,'smb_command',return_value=nullcontext(['fake-smb'])),patch.object(worker.subprocess,'Popen',side_effect=spawn):
            worker.copy_task(task,self.root,self.cfg,op,result)
        self.assertEqual(calls[0][1]['stdout'],subprocess.PIPE)
        self.assertIs(calls[1][1]['stdin'],producer.stdout)
        self.assertIn('--recipient-file',calls[1][0])
        self.assertTrue(result['file'].endswith('.tar.gpg'))
        self.assertEqual(list((self.root/'.bugout-staging').iterdir()),[])

    def test_outbox_retries_in_order_without_credentials_in_payload(self):
        self.integration.return_value={'url':'http://ha.local:8123','token':'SECRET'}
        op=self.start();op['state']='completed';b.update(op,'completed')
        with patch.object(worker,'build_opener') as opener:
            opener.return_value.open.side_effect=OSError('not connected')
            worker.deliver_event()
            worker.deliver_event()
            self.assertEqual(opener.return_value.open.call_count,1)
        with b.database() as db:
            rows=list(db.execute('SELECT * FROM events ORDER BY rowid'))
            self.assertEqual(rows[0]['attempts'],1);self.assertEqual(rows[1]['attempts'],0)
            self.assertNotIn('SECRET',rows[0]['payload'])
            db.execute('UPDATE events SET next_try=0');db.commit()
        response=MagicMock();response.__enter__.return_value.status=200
        with patch.object(worker,'build_opener') as opener:
            opener.return_value.open.return_value=response;worker.deliver_event()
            req=opener.return_value.open.call_args.args[0]
            self.assertEqual(req.full_url,'http://ha.local:8123/api/events/dataark_bugout')
            self.assertEqual(json.loads(req.data)['kind'],'trigger')
        with b.database() as db:
            self.assertEqual(db.execute('SELECT sum(sent) FROM events').fetchone()[0],1)

    def test_normal_sync_and_bugout_are_independent(self):
        self.task.update(prefetch=True,include_in_bugout=False,normal_sync='manual')
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')):
            state=b.readiness()
            self.assertFalse(state['ready']);self.assertTrue(state['sync_ready'])
            with self.assertRaises(ValueError): b.start(str(uuid.uuid4()),'ark')
            op=b.start(str(uuid.uuid4()),'ark','prefetch')
            self.assertEqual(op['mode'],'prefetch')
        self.integration.return_value={'url':'http://ha','token':'secret'}
        b.update(op,'completed')
        with b.database() as db:self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],0)

    def test_scheduler_skips_manual_and_bugout_only(self):
        for values in ({'prefetch':False},{'prefetch':True,'normal_sync':'manual'}):
            self.task.update(values)
            with patch.object(b,'source_ready') as probe:
                worker.queue_prefetch();probe.assert_not_called()

    def test_prefetch_cache_preserved_on_failure_and_interval_respected(self):
        self.task.update(prefetch=True,prefetch_interval='365d')
        worker.record_prefetch(self.task,{'state':'completed','message':'Saved','file':'old.tar','bytes_written':25})
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready') as probe:
            worker.queue_prefetch();probe.assert_not_called()
        worker.record_prefetch(self.task,{'state':'failed','message':'Offline'})
        with b.database() as db:
            cache=json.loads(db.execute('SELECT payload FROM prefetch').fetchone()[0])
        self.assertEqual(cache['file'],'old.tar');self.assertIn('last_success',cache)

    def test_prefetch_never_uses_one_time_credentials(self):
        b.save_credential('household',{'username':'u','password':'p','domain':'','remember':False})
        self.assertIsNone(b.read_credential('nas',remembered_only=True))
        self.assertFalse(b.source_ready(self.task,remembered_only=True)[0])
        self.assertEqual(b.read_credential('nas')['username'],'u')

    def test_cancellation_handoff_is_single_and_silent(self):
        self.integration.return_value={'url':'http://ha','token':'secret'}
        op=self.start()
        b.cancel(op['id'],True);b.cancel(op['id'],False)
        with patch.object(worker,'copy_task') as copy:
            worker.run_operation(op);copy.assert_not_called()
        self.assertEqual(op['state'],'cancelled')
        self.assertIn('background_operation_id',op)
        with b.database() as db:
            events=[json.loads(row[0]) for row in db.execute('SELECT payload FROM events')]
            self.assertEqual(sum(v['kind']=='trigger' for v in events),1)
            self.assertEqual(sum(v['kind']=='cancelled' for v in events),1)
            jobs=list(db.execute("SELECT payload FROM operations WHERE state='queued'"))
        self.assertEqual(len(jobs),1)
        background=json.loads(jobs[0][0]);self.assertEqual(background['mode'],'prefetch')
        b.cancel(op['id'],True)
        with b.database() as db:self.assertEqual(db.execute('SELECT count(*) FROM operations').fetchone()[0],2)

    def test_cancel_without_handoff_preserves_completed_copy(self):
        op=self.start()
        def copy(task,root,cfg,operation,result):
            result['file']='saved.tar'
            b.cancel(operation['id'],False)
        with patch.object(worker,'copy_task',side_effect=copy):worker.run_operation(op)
        self.assertEqual(op['state'],'cancelled')
        self.assertEqual(op['results'][0]['state'],'completed')
        self.assertNotIn('background_operation_id',op)

    def test_time_budget_and_optional_estimate(self):
        op=self.start()
        job=json.loads((b.STATE/(op['id']+'.job.json')).read_text())
        job['config']['tasks'][0].update(optional=True,estimated_seconds=7200)
        b.atomic_json(b.STATE/(op['id']+'.job.json'),job)
        with patch.object(worker,'copy_task') as copy:
            worker.run_operation(op);copy.assert_not_called()
        self.assertEqual(op['results'][0]['state'],'skipped')
        op=self.start();op['deadline']=time.time()-1
        with self.assertRaises(worker.BudgetExpired):worker.check_control(op)

    def test_running_cancellation_terminates_child_and_removes_partial(self):
        op=self.start();child=MagicMock();child.poll.return_value=None
        (self.root/'bugout-backups').mkdir()
        checks=[None,None,worker.BugoutCancelled('Bugout cancelled')]
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')),patch.object(worker,'producer_command',return_value=nullcontext(['fake'])),patch.object(worker.subprocess,'Popen',return_value=child),patch.object(worker,'check_control',side_effect=checks):
            with self.assertRaises(worker.BugoutCancelled):worker.copy_task(self.task,self.root,self.cfg,op,op['results'][0])
        child.terminate.assert_called_once()
        self.assertEqual(list((self.root/'.bugout-staging').iterdir()),[])

    def test_bugout_preempts_background_and_priority_orders_sources(self):
        op=self.start()
        with self.assertRaises(worker.PrefetchYield):worker.check_control({'id':'background','mode':'prefetch'})
        second=dict(self.task,id='first',priority=1)
        job=json.loads((b.STATE/(op['id']+'.job.json')).read_text())
        job['config']['tasks'].append(second);job['ready_ids'].append('first')
        op['results'].append({'id':'first','title':'First','state':'pending'})
        b.atomic_json(b.STATE/(op['id']+'.job.json'),job)
        order=[]
        with patch.object(worker,'copy_task',side_effect=lambda t,*args:order.append(t['id'])):worker.run_operation(op)
        self.assertEqual(order,['first','household'])

    def test_new_source_validation_and_path_boundaries(self):
        b.validate({'tasks':[{'id':'web','title':'Web','kind':'http','url':'https://example.com/file','filename':'file.pdf','include_in_bugout':False}]})
        for url in ('file:///etc/passwd','https://user:pass@example.com/file'):
            with self.assertRaises(ValueError):b.validate({'tasks':[{'id':'web','title':'Web','kind':'http','url':url,'filename':'file.pdf'}]})
        with patch.object(Path,'is_mount',return_value=True):
            with self.assertRaises(ValueError):b.local_source({'mount':str(self.root),'path':'../private'})
        for values in ({'include_in_bugout':'false'},{'normal_sync':'weekly'},{'estimated_seconds':True}):
            with self.assertRaises(ValueError):b.validate({'tasks':[dict(self.task,**values)]})

    def test_when_available_refreshes_on_reconnection(self):
        self.task.update(prefetch=True,normal_sync='when_available',prefetch_interval='365d')
        worker.record_prefetch(self.task,{'state':'completed','message':'Saved','file':'old.tar'})
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(False,'Offline')):
            worker.queue_prefetch()
        with b.database() as db:db.execute('UPDATE availability SET checked=0');db.commit()
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')):
            worker.queue_prefetch()
        with b.database() as db:self.assertEqual(db.execute("SELECT count(*) FROM operations WHERE state='queued'").fetchone()[0],1)

    def test_all_optional_too_large_disables_bugout(self):
        self.task.update(optional=True,estimated_seconds=7200,prefetch=True)
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')):
            state=b.readiness()
            self.assertFalse(state['ready']);self.assertTrue(state['sync_ready'])
            with self.assertRaises(ValueError):b.start(str(uuid.uuid4()),'ark')

    def test_handoff_keeps_normal_schedule(self):
        worker.record_prefetch(self.task,{'state':'completed','message':'Saved','file':'old.tar'})
        with b.database() as db:
            attempted=db.execute('SELECT attempted FROM prefetch').fetchone()[0]
        worker.record_prefetch(self.task,{'state':'failed','message':'Offline'},preserve_schedule=True)
        with b.database() as db:
            row=db.execute('SELECT * FROM prefetch').fetchone()
        self.assertEqual(row['attempted'],attempted)
        self.assertEqual(json.loads(row['payload'])['schedule_state'],'completed')

    def test_preempted_manual_maintenance_stays_queued(self):
        self.task['prefetch']=True
        with patch.object(b,'readiness',return_value=dict(self.ready(),sync_ready=True)):
            op=b.start(str(uuid.uuid4()),'ark','prefetch')
        with patch.object(worker,'copy_task',side_effect=worker.PrefetchYield('Yield')):
            worker.run_operation(op)
        self.assertEqual(op['state'],'queued')
        self.assertTrue((b.STATE/(op['id']+'.job.json')).exists())
        with patch.object(worker,'copy_task',side_effect=lambda task,root,cfg,operation,result:result.update(file='saved.tar')) as copy:
            worker.run_operation(op);copy.assert_called_once()
        self.assertEqual(op['state'],'completed')

    def test_credential_probe_uses_entered_values_without_saving(self):
        saved={'username':'old','password':'OLD','domain':'HOME','remember':True}
        b.save_credential('household',saved)
        saved_file=self.state/'credentials/nas.json'
        before=saved_file.read_bytes()
        runtime_before=set(self.runtime.iterdir())
        entered={'username':'dave','password':'NEW-SECRET','domain':'WORKGROUP','remember':True}
        def probe(args,**kwargs):
            self.assertEqual(args[-2:],['-c','ls'])
            self.assertNotIn('NEW-SECRET',' '.join(args))
            auth=Path(args[args.index('-A')+1]).read_text()
            self.assertIn('password = NEW-SECRET',auth)
            self.assertIn('domain = WORKGROUP',auth)
            return SimpleNamespace(returncode=0,stderr=b'')
        with patch.object(b.subprocess,'run',side_effect=probe),patch.object(b,'atomic_json') as write:
            result=b.test_credential('household',entered)
            write.assert_not_called()
        self.assertTrue(result['ok'])
        self.assertIn('not been saved',result['message'])
        self.assertEqual(saved_file.read_bytes(),before)
        self.assertEqual(set(self.runtime.iterdir()),runtime_before)
        with b.database() as db:self.assertEqual(db.execute('SELECT count(*) FROM operations').fetchone()[0],0)

    def test_credential_probe_failure_and_timeout_clean_up(self):
        entered={'username':'dave','password':'SECRET','domain':'WORKGROUP','remember':False}
        before=set(self.runtime.iterdir())
        for outcome in (SimpleNamespace(returncode=1,stderr=b'NT_STATUS_LOGON_FAILURE SECRET'),subprocess.TimeoutExpired('smbclient',5)):
            with patch.object(b.subprocess,'run') as run:
                if isinstance(outcome,Exception):run.side_effect=outcome
                else:run.return_value=outcome
                result=b.test_credential('household',entered)
            self.assertFalse(result['ok'])
            self.assertNotIn('SECRET',result['message'])
            self.assertEqual(set(self.runtime.iterdir()),before)
        with patch.object(b.subprocess,'run') as run:
            with self.assertRaises(ValueError):b.test_credential('household',dict(entered,password='bad\nvalue'))
            with self.assertRaises(ValueError):b.test_credential('unknown',entered)
            run.assert_not_called()

    def test_exit_zero_with_access_denied_rejects_incomplete_archive(self):
        # Regression for the actual Manuals incident: smbclient reports success
        # at process level even when it skipped an unreadable source file.
        op=self.start()
        command=[sys.executable,'-c',"import sys;sys.stdout.buffer.write(b'incomplete archive');sys.stderr.write('NT_STATUS_ACCESS_DENIED opening remote file private-name')"]
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')),patch.object(worker,'producer_command',return_value=nullcontext(command)),patch.object(Path,'is_mount',return_value=True),patch.object(b.shutil,'disk_usage',return_value=SimpleNamespace(free=10*1024**3)):
            worker.run_operation(op)
        self.assertEqual(op['state'],'failed')
        self.assertIn('NT_STATUS_ACCESS_DENIED',op['results'][0]['message'])
        self.assertNotIn('private-name',json.dumps(op))
        self.assertNotIn('file',op['results'][0])
        self.assertEqual(list((self.root/'.bugout-staging').iterdir()),[])

    def test_snapshot_round_trip_preserves_binary_and_unicode_contents(self):
        import tarfile
        payload=bytes(range(256))*7
        code="import sys,tarfile,io; data=bytes(range(256))*7; t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|'); i=tarfile.TarInfo('documents/caf\u00e9.bin'); i.size=len(data); t.addfile(i,io.BytesIO(data)); t.close()"
        op=self.start()
        (self.root/'bugout-backups').mkdir()
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')),patch.object(Path,'is_mount',return_value=True),patch.object(b.shutil,'disk_usage',return_value=SimpleNamespace(free=10*1024**3)),patch.object(worker,'producer_command',return_value=nullcontext([sys.executable,'-c',code])):
            worker.run_operation(op)
        self.assertEqual(op['state'],'completed',op)
        with tarfile.open(self.root/'bugout-backups'/op['results'][0]['file']) as archive:
            restored=archive.extractfile('documents/caf\u00e9.bin').read()
        self.assertEqual(hashlib.sha256(restored).digest(),hashlib.sha256(payload).digest())

    def test_mid_copy_storage_failure_stops_child_and_preserves_previous_copy(self):
        for mounted,free in ((False,10*1024**3),(True,1024)):
            with self.subTest(mounted=mounted,free=free):
                op=self.start()
                folder=self.root/'bugout-backups';folder.mkdir(exist_ok=True)
                previous=folder/'previous.tar';previous.write_bytes(b'last good backup')
                child=MagicMock();child.poll.return_value=None
                with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')),patch.object(worker,'producer_command',return_value=nullcontext(['fake'])),patch.object(worker.subprocess,'Popen',return_value=child),patch.object(Path,'is_mount',return_value=mounted),patch.object(b.shutil,'disk_usage',return_value=SimpleNamespace(free=free)):
                    worker.run_operation(op)
                self.assertEqual(op['state'],'failed')
                child.terminate.assert_called_once()
                self.assertEqual(previous.read_bytes(),b'last good backup')
                self.assertEqual(list((self.root/'.bugout-staging').iterdir()),[])

    def test_corrupt_prefetch_does_not_replace_last_good_archive(self):
        self.task['prefetch']=True
        with patch.object(b,'readiness',return_value=dict(self.ready(),sync_ready=True)):
            op=b.start(str(uuid.uuid4()),'ark','prefetch')
        folder=self.root/'bugout-backups';folder.mkdir()
        filename=self.task['id']+'-prefetch-'+b.source_signature(self.task)[:16]+'.tar'
        previous=folder/filename;previous.write_bytes(b'previous verified archive')
        worker.record_prefetch(self.task,{'state':'completed','message':'Saved','file':filename})
        command=[sys.executable,'-c',"import sys;sys.stdout.buffer.write(b'not a tar file')"]
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')),patch.object(Path,'is_mount',return_value=True),patch.object(b.shutil,'disk_usage',return_value=SimpleNamespace(free=10*1024**3)),patch.object(worker,'producer_command',return_value=nullcontext(command)):
            worker.run_operation(op)
        self.assertEqual(op['state'],'failed')
        self.assertEqual(previous.read_bytes(),b'previous verified archive')
        with b.database() as db:
            cache=json.loads(db.execute('SELECT payload FROM prefetch').fetchone()[0])
        self.assertEqual(cache['file'],filename)
        self.assertEqual(cache['state'],'failed')
        self.assertIn('last_success',cache)

    def test_ha_lost_ack_retries_same_event_identity(self):
        self.integration.return_value={'url':'http://ha.local:8123','token':'PRIVATE'}
        self.start()
        with patch.object(worker,'build_opener') as opener:
            opener.return_value.open.side_effect=OSError('ack lost')
            worker.deliver_event()
            first=json.loads(opener.return_value.open.call_args.args[0].data)
        with b.database() as db:db.execute('UPDATE events SET next_try=0');db.commit()
        response=MagicMock();response.__enter__.return_value.status=200
        with patch.object(worker,'build_opener') as opener:
            opener.return_value.open.return_value=response
            worker.deliver_event()
            second=json.loads(opener.return_value.open.call_args.args[0].data)
        self.assertEqual(first['event_id'],second['event_id'])
        self.assertEqual(first['operation_id'],second['operation_id'])
        self.assertNotIn('PRIVATE',json.dumps(second))

    def test_reachable_source_does_not_erase_last_backup_failure(self):
        worker.record_prefetch(self.task,{'state':'failed','message':'Source copy failed; NT_STATUS_ACCESS_DENIED'})
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')):
            source=b.readiness()['tasks'][0]
        self.assertTrue(source['ready'])
        self.assertEqual(source['cache']['state'],'failed')
        self.assertIn('ACCESS_DENIED',source['cache']['message'])

    def test_retry_backoff_caps_and_success_restores_daily_schedule(self):
        self.task.update(prefetch=True,prefetch_interval='1d')
        delays=[]
        for attempt in range(10):
            worker.record_prefetch(self.task,{'state':'failed','message':'Copy denied'})
            with b.database() as db:cache=json.loads(db.execute('SELECT payload FROM prefetch').fetchone()[0])
            self.assertEqual(cache['failure_count'],attempt+1)
            delays.append(b.refresh_delay(self.task,cache))
        self.assertEqual(delays,[300,600,1200,2400,4800,9600,19200,21600,21600,21600])
        worker.record_prefetch(self.task,{'state':'completed','message':'Saved','file':'good.tar'})
        with b.database() as db:cache=json.loads(db.execute('SELECT payload FROM prefetch').fetchone()[0])
        self.assertEqual(cache['failure_count'],0)
        self.assertEqual(b.refresh_delay(self.task,cache),86400)

    def test_backoff_blocks_automatic_retry_but_not_manual_sync(self):
        self.task.update(prefetch=True)
        for _ in range(3):worker.record_prefetch(self.task,{'state':'failed','message':'Denied'})
        with b.database() as db:db.execute('UPDATE prefetch SET attempted=?',(time.time()-301,));db.commit()
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready') as probe:
            worker.queue_prefetch();probe.assert_not_called()
        with patch.object(b,'readiness',return_value=dict(self.ready(),sync_ready=True)):
            self.assertEqual(b.start(str(uuid.uuid4()),'ark','prefetch')['state'],'queued')

    def test_retry_metadata_and_missing_copy_remain_visible(self):
        self.task.update(prefetch=True)
        worker.record_prefetch(self.task,{'state':'completed','message':'Saved','file':'missing.tar'})
        with patch.object(b,'destination_ready',return_value=(True,'Ready')),patch.object(b,'source_ready',return_value=(True,'Ready')):
            cache=b.readiness()['tasks'][0]['cache']
        self.assertTrue(cache['missing_file'])
        self.assertNotIn('file',cache)
        self.assertIn('next_attempt',cache)

    def test_handoff_does_not_change_backoff_schedule(self):
        for _ in range(3):worker.record_prefetch(self.task,{'state':'failed','message':'Denied'})
        worker.record_prefetch(self.task,{'state':'completed','message':'Saved','file':'good.tar'},preserve_schedule=True)
        with b.database() as db:cache=json.loads(db.execute('SELECT payload FROM prefetch').fetchone()[0])
        self.assertEqual(cache['failure_count'],0)
        self.assertEqual(b.refresh_delay(self.task,cache),1200)


class BugoutRouteTests(unittest.TestCase):
    def request(self,path,value=None,header=''):
        async def call():
            messages=[]
            payload=json.dumps(value).encode()
            scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'POST','scheme':'http',
                   'path':path,'raw_path':path.encode(),'root_path':'','query_string':b'',
                   'server':('testserver',80),'client':('127.0.0.1',1),
                   'headers':[(b'authorization',header.encode()),(b'content-type',b'application/json')]}
            async def receive():return {'type':'http.request','body':payload,'more_body':False}
            async def send(message):messages.append(message)
            await app(scope,receive,send)
            return next(m['status'] for m in messages if m['type']=='http.response.start')
        return asyncio.run(call())

    def test_auth_before_work_and_ha_cannot_set_credentials(self):
        with patch('app.routers.bugout.authorized',return_value=False),patch.object(b,'ha_authorized',return_value=False),patch.object(b,'start') as start:
            self.assertEqual(self.request('/bugout/trigger',{'operation_id':str(uuid.uuid4())}),401);start.assert_not_called()
        with patch('app.routers.bugout.authorized',return_value=False),patch.object(b,'ha_authorized',return_value=True),patch.object(b,'save_credential') as save:
            self.assertEqual(self.request('/bugout/credentials/household',{}),401);save.assert_not_called()

    def test_ha_origin_and_no_caller_supplied_sources(self):
        with patch('app.routers.bugout.authorized',return_value=False),patch.object(b,'ha_authorized',return_value=True),patch.object(b,'start',return_value={'state':'queued'}) as start:
            key=str(uuid.uuid4())
            self.assertEqual(self.request('/bugout/trigger',{'operation_id':key}),200)
            start.assert_called_once_with(key,'home_assistant')
            self.assertEqual(self.request('/bugout/trigger',{'operation_id':key,'host':'evil'}),400)

    def test_cancel_and_sync_require_authorization(self):
        with patch('app.routers.bugout.authorized',return_value=False),patch.object(b,'ha_authorized',return_value=False),patch.object(b,'cancel') as cancel:
            self.assertEqual(self.request('/bugout/cancel',{'operation_id':'x','continue_updates':True}),401)
            cancel.assert_not_called()
        with patch('app.routers.bugout.authorized',return_value=False),patch.object(b,'ha_authorized',return_value=True),patch.object(b,'cancel',return_value={'state':'cancelling'}) as cancel:
            self.assertEqual(self.request('/bugout/cancel',{'operation_id':'operation-id','continue_updates':True}),200)
            cancel.assert_called_once_with('operation-id',True)
            self.assertEqual(self.request('/bugout/sync',{'operation_id':'operation-id'}),401)

    def test_credential_test_is_admin_only(self):
        payload={'username':'dave','password':'private','domain':'WORKGROUP','remember':False}
        with patch('app.routers.bugout.authorized',return_value=False),patch.object(b,'ha_authorized',return_value=True),patch.object(b,'test_credential') as probe:
            self.assertEqual(self.request('/bugout/credentials/household/test',payload),401)
            probe.assert_not_called()
        with patch('app.routers.bugout.authorized',return_value=True),patch.object(b,'test_credential',return_value={'ok':True,'message':'Readable'}) as probe:
            self.assertEqual(self.request('/bugout/credentials/household/test',payload),200)
            probe.assert_called_once_with('household',payload)


if __name__ == '__main__': unittest.main()
