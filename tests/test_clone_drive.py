import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import clone_drive as c


class CloneTests(unittest.TestCase):
    def unit(self, name, size, priority=1):
        return {'id': name, 'title': name, 'priority': priority, 'bytes': size,
                'files': [{'path': name, 'bytes': size, 'mtime_ns': 1}]}

    def test_fit_selects_complete_smaller_collections_and_keeps_reserve(self):
        units = [self.unit('huge', 900), self.unit('small', 100), self.unit('essential', 200, 0)]
        selected, skipped, fits = c.choose(units, 'fit', 1000, 100, 100, 1)
        self.assertTrue(fits)
        self.assertEqual([u['id'] for u in selected], ['essential', 'small'])
        self.assertEqual(skipped[0]['id'], 'huge')

    def test_all_content_refuses_insufficient_space_and_config_needs_allowance(self):
        self.assertFalse(c.choose([self.unit('large', 900)], 'populated', 1000, 100, 100, 1)[2])
        self.assertFalse(c.choose([], 'config', 100, 100, 100, 1)[2])
        self.assertEqual(c.choose([self.unit('large', 900)], 'config', 1000, 100, 100, 1)[0], [])

    def test_allocation_rounds_each_file(self):
        self.assertFalse(c.choose([self.unit('a', 1)], 'populated', 4095, 0, 0, 4096)[2])

    def test_inventory_includes_curriculum_and_excludes_private_and_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            root = source/'curriculum'; root.mkdir()
            for name in ['lesson.pdf', '.private', 'credentials.json', 'id_rsa', 'server.key']:
                (root/name).write_bytes(b'example')
            (source/'outside').write_bytes(b'private')
            (root/'link.pdf').symlink_to(source/'outside')
            manifest = {'repositories': [], 'assets': []}
            units = c.inventory(manifest, {'public_directories': [{'path':'curriculum', 'title':'Lessons','priority':1}]}, source)
            self.assertEqual([f['path'] for u in units for f in u['files']], ['curriculum/lesson.pdf'])

    def test_unsafe_and_overlapping_paths_refused(self):
        for path in ['../x', '/etc/passwd', 'a//b', 'a/./b', 'a\\b', '.']:
            with self.subTest(path=path), self.assertRaises(ValueError): c.safe_relative(path)

    def fixture(self, root):
        source=root/'source'; target=root/'target'; source.mkdir(); target.mkdir()
        path=source/'nested/file.bin'; path.parent.mkdir(); path.write_bytes(b'abcdefgh'*1000)
        item={'path':'nested/file.bin', 'bytes':path.stat().st_size, 'mtime_ns':path.stat().st_mtime_ns}
        marker=target/c.MARKER; marker.mkdir()
        return source,target,item,marker

    def test_copy_checksum_and_verified_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,target,item,marker=self.fixture(Path(tmp))
            result=c.copy_file(source,target,item,marker,0)
            self.assertEqual(result['sha256'], hashlib.sha256((source/item['path']).read_bytes()).hexdigest())
            self.assertEqual(c.copy_file(source,target,item,marker,0), result)
            (target/item['path']).write_bytes(b'changed')
            with self.assertRaises(ValueError): c.copy_file(source,target,item,marker,0)

    def test_matching_partial_resumes_and_bad_partial_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,target,item,marker=self.fixture(Path(tmp))
            partial=marker/'partial'/(hashlib.sha256(item['path'].encode()).hexdigest()+'.part')
            partial.parent.mkdir(); partial.write_bytes(b'bad')
            with self.assertRaises(ValueError): c.copy_file(source,target,item,marker,0)
            self.assertEqual(partial.read_bytes(), b'bad')
            partial.write_bytes((source/item['path']).read_bytes()[:1000])
            c.copy_file(source,target,item,marker,0)
            self.assertEqual((target/item['path']).read_bytes(), (source/item['path']).read_bytes())

    def test_unowned_file_and_changed_source_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,target,item,marker=self.fixture(Path(tmp))
            destination=target/item['path']; destination.parent.mkdir(); destination.write_bytes(b'keep')
            with self.assertRaises(ValueError): c.copy_file(source,target,item,marker,0)
            self.assertEqual(destination.read_bytes(), b'keep')
            (source/item['path']).write_bytes(b'new')
            with self.assertRaises(ValueError): c.copy_file(source,target,item,marker,0)

    def test_detachment_guard_stops_before_creating_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,target,item,marker=self.fixture(Path(tmp))
            with self.assertRaisesRegex(ValueError, 'disconnected'):
                c.copy_file(source,target,item,marker,0,guard=lambda: (_ for _ in ()).throw(ValueError('disconnected')))
            self.assertEqual(list(marker.iterdir()), [])

    def test_reserve_preserves_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,target,item,marker=self.fixture(Path(tmp))
            with patch.object(c.shutil, 'disk_usage', return_value=type('Usage',(),{'free':1})()):
                with self.assertRaisesRegex(ValueError, 'space changed'): c.copy_file(source,target,item,marker,100)
            self.assertFalse((target/item['path']).exists())

    def test_backing_disk_protects_other_partition_not_duplicate_serial(self):
        devices={'/dev/a':{'type':'disk','serial':'same'}, '/dev/a1':{'type':'part','parent':'/dev/a'},
                 '/dev/a2':{'type':'part','parent':'/dev/a'}, '/dev/b':{'type':'disk','serial':'same'},
                 '/dev/b1':{'type':'part','parent':'/dev/b'}}
        self.assertEqual(c.backing_disks('/dev/a1',devices), c.backing_disks('/dev/a2',devices))
        self.assertFalse(c.backing_disks('/dev/a1',devices) & c.backing_disks('/dev/b1',devices))

    def test_target_guards_readonly_nonempty_and_system_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'new'; source=Path(tmp)/'original'; target.mkdir(); source.mkdir()
            mounts={'/':{'source':'/dev/boot1','uuid':'boot'}, str(source):{'source':'/dev/a1','uuid':'original'},
                    str(target):{'source':'/dev/b1','uuid':'new','fstype':'ext4','options':'rw'}}
            devices={'/dev/boot':{'type':'disk'}, '/dev/boot1':{'type':'part','parent':'/dev/boot'},
                     '/dev/boot2':{'type':'part','parent':'/dev/boot'}, '/dev/a':{'type':'disk'},
                     '/dev/a1':{'type':'part','parent':'/dev/a'}, '/dev/b':{'type':'disk'},
                     '/dev/b1':{'type':'part','parent':'/dev/b'}}
            with patch.object(c,'SOURCE',source), patch.object(Path,'is_mount',return_value=True):
                self.assertTrue(c.inspect_target(target,mounts,devices)['eligible'])
                mounts[str(target)]['source']='/dev/boot2'
                self.assertIn('another partition', ' '.join(c.inspect_target(target,mounts,devices)['reasons']))
                mounts[str(target)]['source']='/dev/b1'; mounts[str(target)]['options']='ro'
                self.assertFalse(c.inspect_target(target,mounts,devices)['eligible'])
                mounts[str(target)]['options']='rw'; (target/'keep.txt').write_text('keep')
                self.assertFalse(c.inspect_target(target,mounts,devices)['eligible'])
            with patch.object(Path,'is_mount',return_value=False):
                self.assertFalse(c.inspect_target(target,mounts,devices)['eligible'])

    def test_saved_plan_tampering_changes_identity(self):
        plan={'target':{'uuid':'a','free_bytes':10},'fits':True,'selected':[self.unit('a',1)]}
        plan['plan_id']=c.plan_identity(plan)
        plan['target']['free_bytes']=9
        self.assertEqual(c.plan_identity(plan),plan['plan_id'])
        plan['selected'][0]['files'][0]['path']='different'
        self.assertNotEqual(c.plan_identity(plan),plan['plan_id'])

    def test_api_unknown_id_never_applies_and_only_has_get_routes(self):
        from app.routers import clone
        from fastapi import HTTPException
        self.assertTrue(all(route.methods == {'GET'} for route in clone.router.routes))
        with patch.object(c,'targets',return_value=[]), self.assertRaises(HTTPException) as raised:
            clone.plan('not-a-mounted-drive', 'config')
        self.assertEqual(raised.exception.status_code,404)

    def test_ntfs_bootstrap_records_uid_and_ntfs3g_fstab(self):
        from deploy import bootstrap_stock_pi as b
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fstab=root/'fstab'; fstab.write_text('# existing\n')
            config=json.loads((c.ROOT/'config/stock-pi.json').read_text())
            self.assertIn('ntfs-3g',config['packages'])
            installer=b.Installer(config,root/'kit',{},root/'journal')
            installer.root=root/'mounted'
            def path(value):
                if str(value)=='/etc/fstab':return fstab
                if str(value)=='/var/backups/dataark-bootstrap':return root/'backup'
                return Path(value)
            with patch.object(b,'output',side_effect=['/dev/test1','/dev/boot1','NTFS-UUID','ntfs',str(root/'mounted')]), patch.object(b,'Path',side_effect=path), patch.object(Path,'is_mount',return_value=True), patch.object(Path,'stat',return_value=SimpleNamespace(st_dev=1,st_uid=1000,st_mode=0o40755)), patch.object(b.shutil,'copy2'), patch.object(b.pwd,'getpwnam',return_value=SimpleNamespace(pw_gid=1000)), patch.object(b,'atomic') as written:
                installer.storage()
            self.assertIn(' /mnt/storage ntfs-3g ',written.call_args.args[1])
            self.assertIn('uid=1000,gid=1000,fmask=0133,dmask=0022',written.call_args.args[1])


if __name__ == '__main__': unittest.main()
