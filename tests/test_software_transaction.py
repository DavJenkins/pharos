import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from tools.software_update import Updater,allowed,digest,save
from tools.build_software_update import build

class Runtime:
    def __init__(self,health=(True,)):self.results=iter(health);self.calls=[]
    def preflight(self):self.calls.append('preflight')
    def stop(self):self.calls.append('stop')
    def start(self):self.calls.append('start')
    def healthy(self):return next(self.results)

class SoftwareTransactions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys=tempfile.TemporaryDirectory();cls.key=Path(cls.keys.name)/'private.pem';cls.pub=cls.key.with_name('public.pem')
        subprocess.run(['/usr/bin/openssl','genpkey','-algorithm','ED25519','-out',str(cls.key)],check=True,capture_output=True)
        subprocess.run(['/usr/bin/openssl','pkey','-in',str(cls.key),'-pubout','-out',str(cls.pub)],check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.keys.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.updater=Updater(self.root,Runtime());self.source=self.root/'opt/dataark'
        for name,raw in {'app/main.py':b'old source','requirements.txt':b'fixed dependencies','dataark.yaml':b'personal private config'}.items():
            p=self.source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        for name in ('var/lib/dataark/community.db','etc/dataark/network-admin.json','mnt/storage/library/book.zim'):
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'private state')
        self.updater.trust.mkdir(parents=True);shutil.copyfile(self.pub,self.updater.trust/'release.pem')
        self.updater.enroll('a'*40,'test-lan')
        self.payload=self.root/'payload';p=self.payload/'source/app/main.py';p.parent.mkdir(parents=True);p.write_bytes(b'new source')
        self.package=self.root/'package.tar.gz';self.build()
    def build(self,**kwargs):
        return build(self.payload,self.updater.receipt(),self.source/'requirements.txt',self.key,self.package,'test-1','b'*40,**kwargs)
    def stage(self):return self.updater.stage(self.package)['id']
    def preserved(self):
        self.assertEqual((self.source/'dataark.yaml').read_bytes(),b'personal private config')
        for name in ('var/lib/dataark/community.db','etc/dataark/network-admin.json','mnt/storage/library/book.zim'):self.assertEqual((self.root/name).read_bytes(),b'private state')
    def test_success_preserves_private_state(self):
        self.assertEqual(self.updater.apply(self.stage())['state'],'completed');self.preserved()
        self.assertEqual((self.source/'app/main.py').read_bytes(),b'new source');self.assertEqual(self.updater.receipt()['revision'],'b'*40)
        outcome=json.loads((self.updater.state/'transactions'/self.updater.journal()['id']/'result.json').read_text())
        self.assertEqual(outcome['state'],'completed');self.assertIn('updated_at',outcome)
    def test_failed_health_rolls_back_code_and_receipt(self):
        self.updater.runtime=Runtime((False,True))
        self.assertEqual(self.updater.apply(self.stage())['state'],'rolled_back');self.preserved()
        self.assertEqual((self.source/'app/main.py').read_bytes(),b'old source');self.assertEqual(self.updater.receipt()['revision'],'a'*40)
    def test_process_interruption_is_recovered_idempotently(self):
        identifier=self.stage()
        def crash(_):raise SystemExit('simulated power interruption')
        with self.assertRaises(SystemExit):self.updater.apply(identifier,crash)
        self.assertEqual(self.updater.journal()['state'],'applying')
        self.assertEqual(self.updater.recover()['state'],'rolled_back');self.assertEqual(self.updater.recover()['state'],'rolled_back');self.preserved()
    def test_failed_rollback_is_not_reported_success(self):
        self.updater.runtime=Runtime((False,False))
        with self.assertRaisesRegex(ValueError,'Rollback health'):self.updater.apply(self.stage())
        self.assertEqual(self.updater.journal()['state'],'rolling_back')
    def test_boot_restore_defers_service_and_health_until_after_startup(self):
        identifier=self.stage()
        with self.assertRaises(SystemExit):self.updater.apply(identifier,lambda _:(_ for _ in ()).throw(SystemExit()))
        self.updater.runtime.calls.clear()
        self.assertEqual(self.updater.recover(boot=True)['state'],'rollback_pending_health')
        self.assertEqual(self.updater.runtime.calls,[])
        self.assertEqual(self.updater.verify_recovery()['state'],'rolled_back')
    def test_dirty_baseline_and_staged_payload_tampering_refused(self):
        identifier=self.stage();(self.source/'app/main.py').write_bytes(b'local work')
        with self.assertRaisesRegex(ValueError,'Local software edits'):self.updater.apply(identifier)
        (self.source/'app/main.py').write_bytes(b'old source')
        (self.updater.stage_path(identifier)/'payload/source/app/main.py').write_bytes(b'tamper')
        with self.assertRaisesRegex(ValueError,'verification'):self.updater.apply(identifier)
    def test_untrusted_signature_rejected(self):
        (self.updater.trust/'release.pem').unlink()
        with self.assertRaisesRegex(ValueError,'signature'):self.stage()
    def test_schema_dependency_platform_and_downgrade_refused(self):
        identifier=self.stage();folder=self.updater.stage_path(identifier);original=json.loads((folder/'manifest.json').read_text())
        for key,value in [('configuration_schema',2),('migrations',['run.py']),('requirements_sha256','c'*64),('profiles',['other']),('sequence',0),('base_revision','c'*40)]:
            changed={**original,key:value};save(folder/'manifest.json',changed)
            with self.subTest(key=key),patch.object(self.updater,'signature'),self.assertRaises(ValueError):self.updater.validate(folder)
        self.assertNotIn('stop',self.updater.runtime.calls)
    def test_traversal_symlinks_duplicate_and_unlisted_entries_refused(self):
        for name,kind in [('../etc/passwd','file'),('payload/source/app/main.py','link'),('manifest.json','duplicate'),('payload/source/app/extra.py','file')]:
            bad=self.root/'bad.tar.gz'
            with tarfile.open(self.package,'r:gz') as src,tarfile.open(bad,'w:gz') as out:
                for item in src:out.addfile(item,src.extractfile(item))
                item=tarfile.TarInfo(name);item.size=1
                if kind=='link':item.type=tarfile.SYMTYPE;item.linkname='/etc/passwd';item.size=0
                out.addfile(item,io.BytesIO(b'x'))
            with self.subTest(name=name),self.assertRaises(ValueError):self.updater.stage(bad)
    def test_private_and_operating_system_paths_never_allowed(self):
        for name in ['source/dataark.yaml','source/tools/software_update.py','web/index.html','source/requirements.txt','web/../etc/passwd','source/app/../../etc/passwd','/source/app/a.py','source/app\\a.py']:
            self.assertFalse(allowed(name),name)
    def test_interrupted_staging_does_not_touch_live_files(self):
        with patch.object(self.updater,'validate',side_effect=SystemExit('staging interrupted')):
            with self.assertRaises(SystemExit):self.stage()
        self.assertEqual((self.source/'app/main.py').read_bytes(),b'old source');self.preserved()
        self.assertFalse(list((self.updater.state/'staged').iterdir()))
    def test_space_rechecked_before_service_stop(self):
        from types import SimpleNamespace
        identifier=self.stage()
        with patch('tools.software_update.shutil.disk_usage',return_value=SimpleNamespace(free=0)):
            with self.assertRaisesRegex(ValueError,'reserve'):self.updater.apply(identifier)
        self.assertNotIn('stop',self.updater.runtime.calls)
    def test_removal_and_new_file_rollback(self):
        (self.payload/'source/app/main.py').unlink();(self.payload/'source/app/new.py').write_text('new')
        self.build(removals=['source/app/main.py']);self.updater.runtime=Runtime((False,True))
        self.assertEqual(self.updater.apply(self.stage())['state'],'rolled_back')
        self.assertTrue((self.source/'app/main.py').is_file());self.assertFalse((self.source/'app/new.py').exists())

if __name__=='__main__':unittest.main()
