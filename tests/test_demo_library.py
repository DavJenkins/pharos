import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from deploy import demo_library as d


class DemoLibraryTests(unittest.TestCase):
    def test_capacity_is_explicit_and_preserves_system_headroom(self):
        self.assertEqual(d.plan(4, 20*d.GIB)['system_free_after_bytes'],16*d.GIB)
        for size in [0,1,17,True,1.5]:
            with self.subTest(size=size),self.assertRaises(ValueError):d.plan(size,100*d.GIB)
        with self.assertRaises(ValueError):d.plan(4,13*d.GIB)

    def paths(self,root):
        image=root/'demo.ext4';state=root/'state.json';mount=root/'content';fstab=root/'fstab'
        fstab.write_text('# fixture\n');mount.mkdir()
        return image,state,mount,fstab

    def test_existing_mounted_volume_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=self.paths(Path(tmp))
            runner=lambda *args,**kw:SimpleNamespace(returncode=0,stdout='/dev/test\n')
            with patch.object(d.shutil,'disk_usage',return_value=SimpleNamespace(free=100*d.GIB)),self.assertRaises(ValueError):d.create(4,*paths,runner=runner)
            self.assertFalse(paths[0].exists())

    def test_unowned_image_is_never_formatted(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=self.paths(Path(tmp));paths[0].write_bytes(b'existing content')
            with self.assertRaises(ValueError):d.create(4,*paths)
            self.assertEqual(paths[0].read_bytes(),b'existing content')

    def test_interrupted_allocation_is_not_reformatted(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=self.paths(Path(tmp));image,state,_,_=paths
            with image.open('wb') as f:f.truncate(d.GIB)
            info=image.stat();state.write_text(json.dumps({'image':str(image),'inode':info.st_ino,'device':info.st_dev,'capacity_bytes':d.GIB,'stage':'allocated'}))
            with self.assertRaisesRegex(ValueError,'Interrupted'):d.create(1,*paths)

    def test_fstab_and_mount_directory_conflicts_block_before_allocation(self):
        for conflict in ['fstab','files']:
            with tempfile.TemporaryDirectory() as tmp:
                paths=self.paths(Path(tmp));image,state,mount,fstab=paths
                if conflict=='fstab':fstab.write_text('UUID=original '+str(mount)+' ext4 defaults 0 0\n')
                else:(mount/'keep').write_text('content')
                with patch.object(d.shutil,'disk_usage',return_value=SimpleNamespace(free=100*d.GIB)),self.assertRaises(ValueError):
                    d.create(4,*paths,runner=lambda *a,**kw:SimpleNamespace(returncode=1,stdout=''))
                self.assertFalse(image.exists())

    def test_symlink_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=self.paths(root);other=root/'other';other.write_text('keep')
            try:paths[0].symlink_to(other)
            except OSError:self.skipTest('Symlinks unavailable')
            with self.assertRaises(ValueError):d.create(4,*paths)
            self.assertEqual(other.read_text(),'keep')

    def test_registration_preserves_original_sources(self):
        import yaml
        from deploy.install_demo_samples import register
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config/content').mkdir(parents=True)
            data={'system':{'project_name':'Ark','version':'1.4','base_mount':'/mnt/storage','services':{'kiwix_port':8080}},'categories':[{'id':'content_sources','title':'Sources'},{'id':'zim_archives','title':'Archives'}],'repositories':[{'id':'original','title':'Original collection','category':'content_sources','update_policy':'manual','refresh_interval':'never','links':[]}],'assets':[]}
            (root/'dataark.yaml').write_text(yaml.safe_dump(data))
            config={'label':'Demo library on the system card','notice':'Small offline sample.','repository':{'id':'demo','title':'Demo','category':'content_sources','links':[],'update_policy':'manual','refresh_interval':'never'},'samples':[{'id':'sample','title':'Sample archive','path':'sample.zim','category':'zim_archives','url':'https://example.org/sample.zim','sha256':'a'*64}]}
            result=register(root,config)
            self.assertIn(data['repositories'][0],result['repositories'])
            self.assertEqual(result['assets'][0]['expected_hash'],'a'*64)
            self.assertFalse(result['system']['hide_missing'])
            self.assertEqual(yaml.safe_load((root/'dataark.yaml').read_text()),data)
            removed=dict(result['assets'][0],removed=True);result['assets'][0]=removed
            from app.services.demo_library import overlay
            self.assertTrue(overlay(result,config)['assets'][0]['removed'])
