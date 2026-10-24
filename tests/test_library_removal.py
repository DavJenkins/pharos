import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from tools import library_removal as removal

class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.mount=self.root/'storage';self.mount.mkdir()
        self.state=self.root/'state';self.state.mkdir()
        self.archive=self.mount/'example_2026-01.zim';self.archive.write_bytes(b'archive')
        self.data={'system':{'base_mount':str(self.mount),'services':{'kiwix_port':8080}},
            'repositories':[{'id':'example-repo','enabled':True}],
            'assets':[{'id':'example','repository_id':'example-repo','relative_path':self.archive.name,'title':'Example',
                'category':'zim_archives','update_policy':'on_network_available','refresh_interval':'1d',
                'update_source':{'kind':'kiwix_zim','directory':'https://download.kiwix.org/zim/ifixit/','filename_prefix':'example_'}}]}
        (self.root/'dataark.yaml').write_text(yaml.safe_dump(self.data))
        self.payload={'action':'remove','asset_id':'example','relative_path':self.archive.name,'bytes':7}
        for name,value in [('ROOT',self.root),('MOUNT',self.mount),('JOURNAL',self.state/'removal.json')]:
            p=patch.object(removal,name,value);p.start();self.addCleanup(p.stop)
        for name in ('publish_library','docker','wait_for_library'):
            p=patch.object(removal,name);setattr(self,name,p.start());self.addCleanup(p.stop)
        p=patch.object(removal,'check_container',return_value=True);p.start();self.addCleanup(p.stop)
        p=patch.object(removal.Path,'is_mount',return_value=True);p.start();self.addCleanup(p.stop)
        p=patch.object(removal,'load_manifest',side_effect=lambda path:yaml.safe_load(path.read_text()));p.start();self.addCleanup(p.stop)
        # Never read or write the live updater history during reinstatement tests.
        p=patch.object(removal,'Path',side_effect=lambda *args: self.state/'checked.json' if str(Path(*args))=='/var/lib/dataark/updates/checked.json' else Path(*args));p.start();self.addCleanup(p.stop)
        # Route the fixed worker lock into this disposable fixture only.
        self.original_open=Path.open
        def opening(path,*args,**kwargs):
            if str(path)=='/var/lib/dataark/updates/worker.lock':
                path=self.state/'worker.lock'
            return self.original_open(path,*args,**kwargs)
        p=patch.object(Path,'open',opening);p.start();self.addCleanup(p.stop)

    def test_remove_retains_source_disables_updates_and_frees_file(self):
        removal.remove(self.payload)
        data=yaml.safe_load((self.root/'dataark.yaml').read_text())
        self.assertFalse(self.archive.exists())
        self.assertTrue(data['assets'][0]['removed'])
        self.assertEqual(data['assets'][0]['update_policy'],'manual')
        self.assertIn('update_source',data['assets'][0])
        self.assertFalse(data['repositories'][0]['enabled'])
        self.assertFalse(removal.JOURNAL.exists())
        self.wait_for_library.assert_called_once_with([], [self.archive.name],8080)

    def test_reader_failure_rolls_back_file_and_manifest(self):
        self.wait_for_library.side_effect=[RuntimeError('reader failed'),None]
        with self.assertRaises(RuntimeError):
            removal.remove(self.payload)
        self.assertEqual(self.archive.read_bytes(),b'archive')
        self.assertEqual(yaml.safe_load((self.root/'dataark.yaml').read_text()),self.data)
        self.assertFalse(removal.JOURNAL.exists())

    def test_stale_size_rejected(self):
        with self.assertRaisesRegex(ValueError,'size changed'):
            removal.remove({**self.payload,'bytes':8})
        self.assertTrue(self.archive.exists())

    def test_traversal_and_unregistered_paths_rejected(self):
        for path in ('../secret', '/etc/passwd','other.zim'):
            with self.subTest(path=path),self.assertRaises(ValueError):
                removal.remove({**self.payload,'relative_path':path})
        self.assertTrue(self.archive.exists())

    def test_symlink_rejected(self):
        self.archive.unlink();self.archive.symlink_to(self.root/'secret')
        with self.assertRaises(ValueError):
            removal.remove(self.payload)

    def test_shared_file_rejected(self):
        data=copy.deepcopy(self.data);data['assets'].append({**data['assets'][0],'id':'other'})
        (self.root/'dataark.yaml').write_text(yaml.safe_dump(data))
        with self.assertRaisesRegex(ValueError,'shared'):
            removal.remove(self.payload)

    def test_prepared_removal_recovers_on_next_worker(self):
        stage=self.mount/'.dataark-updates';stage.mkdir()
        original=(self.root/'dataark.yaml').read_text()
        self.archive.rename(stage/'removed-file')
        removal.JOURNAL.write_text(json.dumps({'phase':'prepared','relative_path':self.archive.name,'original':original,'zim':True,'port':8080}))
        removal.recover()
        self.assertTrue(self.archive.exists())
        self.assertFalse(removal.JOURNAL.exists())

    def test_reinstate_preseeded_archive(self):
        removal.remove(self.payload)
        from collections import namedtuple
        usage=namedtuple('Usage','total used free')(10000000000,0,10000000000)
        with patch('tools.update_worker.release_info',return_value={'filename':'example_2026-01.zim','bytes':7}),patch('shutil.disk_usage',return_value=usage),patch.object(removal.subprocess,'run') as run:
            removal.restore({'action':'restore','asset_id':'example'})
        data=yaml.safe_load((self.root/'dataark.yaml').read_text())
        self.assertNotIn('removed',data['assets'][0])
        self.assertEqual(data['assets'][0]['update_policy'],'on_network_available')
        self.assertTrue(data['repositories'][0]['enabled'])
        run.assert_called_once()

    def test_serialized_layout_supported_by_activation(self):
        from tools.activate_content_updates import replacement_manifest
        text=removal.serialize(self.data)
        # A future replacement must still find the retained asset block.
        text=text.replace('    update_source:', '    download_url: https://download.kiwix.org/old.zim\n    update_source:')
        result=replacement_manifest(text,[{'id':'example','filename':'example_2026-02.zim','url':'https://download.kiwix.org/new.zim','sha256':'0'*64}])
        self.assertIn('relative_path: example_2026-02.zim',result)
