import asyncio,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yaml
import subprocess
from types import SimpleNamespace
from fastapi import HTTPException
from app.services import configuration as c
from app.routers import configuration as routes
from app.services.manifest import build,load_manifest
from tools import publish_configuration as publisher

class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.data={'system':{'version':'1.4','project_name':'Test Ark','base_mount':'/mnt/storage'},'categories':[],'repositories':[],'assets':[],'private_household':{'keep':'unchanged'}}
        (self.root/'dataark.yaml').write_text(yaml.safe_dump(self.data));(self.root/'state').mkdir()
        for name,value in [('ROOT',self.root),('STATE',self.root/'state')]:
            mocked=patch.object(c,name,value);mocked.start();self.addCleanup(mocked.stop)
    def test_editor_omits_private_sections_and_save_preserves_them(self):
        value=c.read();self.assertNotIn('private_household',value['text'])
        public=c.public(self.data);public['community']={'enabled':False}
        merged=c.checked(c.dump(public),self.data)
        self.assertEqual(merged['private_household'],self.data['private_household'])
        self.assertFalse(merged['community']['enabled'])
    def test_invalid_yaml_duplicate_keys_private_fields_and_paths_rejected(self):
        for text in ['!!python/object/apply:os.system [id]','system: [','system: {}\nsystem: {}',c.dump(c.public(self.data))+'private_household: {}\n']:
            with self.subTest(text=text[:30]),self.assertRaises(ValueError):c.checked(text,self.data)
        data=c.public(self.data);data['system']={**data['system'],'base_mount':'/etc'}
        with self.assertRaisesRegex(ValueError,'read-only'):c.checked(c.dump(data),self.data)
    def test_recursive_aliases_rejected(self):
        text=c.dump(c.public(self.data)).replace('categories: []','categories: &loop [*loop]')
        with self.assertRaisesRegex(ValueError,'nested|recursive'):c.checked(text,self.data)
    def test_queue_requires_current_revision_and_does_not_change_live_file(self):
        original=(self.root/'dataark.yaml').read_bytes();text=c.dump(c.public(self.data))
        with self.assertRaisesRegex(ValueError,'changed'):c.queue(text,'old-revision')
        result=c.queue(text,c.revision(original));self.assertEqual(result['state'],'queued')
        self.assertEqual((self.root/'dataark.yaml').read_bytes(),original)
        with self.assertRaisesRegex(ValueError,'already in progress'):c.queue(text,c.revision(original))
    def test_community_boolean_validated(self):
        for enabled in ['false',None,0]:
            data=c.public(self.data);data['community']={'enabled':enabled}
            with self.subTest(enabled=enabled),self.assertRaises(ValueError):c.checked(c.dump(data),self.data)
    def test_rendered_community_card_and_navigation_follow_configuration(self):
        template=self.root/'template.html';template.write_text('{{PROJECT_NAME}}{{BACKGROUND_STYLE}}{{MANIFEST_CARDS}}{{COMMUNITY_NAV}}{{COMMUNITY_CARD}}')
        for enabled in [True,False]:
            self.data['community']={'enabled':enabled};source=self.root/'dataark.yaml';source.write_text(c.dump(self.data))
            output=self.root/'web/index.html';build(source,template,output,content_root=self.root)
            self.assertEqual('id="community-board"' in output.read_text(),enabled)
            self.assertEqual('href="/community.html"' in output.read_text(),enabled)
    def test_history_rejects_arbitrary_paths(self):
        for identifier in ['../dataark.yaml','/etc/shadow','x']:
            with self.assertRaises(ValueError):c.history(identifier)
    def test_read_requires_caretaker_authorization(self):
        class Request:headers={}
        with patch.object(routes,'authorized',return_value=False),patch.object(c,'read') as read:
            with self.assertRaises(HTTPException) as result:asyncio.run(routes.read(Request()))
            self.assertEqual(result.exception.status_code,401);read.assert_not_called()

    def publisher_setup(self):
        folder=self.root/'config/content';folder.mkdir(parents=True)
        (folder/'public-manifest.yaml').write_text(c.dump(c.public(self.data)))
        for name,value in [('ROOT',self.root),('WORKER_LOCK',self.root/'worker.lock'),('BACKUPS',self.root/'backups'),('CONTENT_ROOT',self.root/'unmounted-content')]:
            mocked=patch.object(publisher,name,value);mocked.start();self.addCleanup(mocked.stop)
        value=c.public(self.data);value['community']={'enabled':False}
        return c.queue(c.dump(value),c.revision((self.root/'dataark.yaml').read_bytes()))

    def test_successful_publication_keeps_history_and_private_settings(self):
        self.publisher_setup()
        with patch.object(publisher.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
            publisher.main()
        current=load_manifest(self.root/'dataark.yaml')
        self.assertFalse(current['community']['enabled'])
        self.assertEqual(current['private_household'],self.data['private_household'])
        self.assertEqual(c.status()['state'],'ready')
        history=c.read()['history'];self.assertEqual(len(history),1)
        self.assertTrue(yaml.safe_load(c.history(history[0]['id'])['text'])['community']['enabled'])
        self.assertFalse((c.STATE/'pending.json').exists())
        self.assertEqual(run.call_count,1)

    def test_failed_publication_restores_previous_manifest_and_profile(self):
        self.publisher_setup();original=(self.root/'dataark.yaml').read_bytes();profile=(self.root/'config/content/public-manifest.yaml').read_bytes()
        with patch.object(publisher.subprocess,'run',side_effect=[subprocess.CalledProcessError(1,['deploy']),SimpleNamespace(returncode=0)]):
            publisher.main()
        self.assertEqual((self.root/'dataark.yaml').read_bytes(),original)
        self.assertEqual((self.root/'config/content/public-manifest.yaml').read_bytes(),profile)
        self.assertEqual(c.status()['state'],'error')

    def test_publication_rejects_conflicting_updater_edit(self):
        self.publisher_setup();self.data['private_household']['keep']='new updater state';(self.root/'dataark.yaml').write_text(c.dump(self.data));expected=(self.root/'dataark.yaml').read_bytes()
        with patch.object(publisher.subprocess,'run') as run:publisher.main()
        self.assertEqual((self.root/'dataark.yaml').read_bytes(),expected)
        self.assertEqual(c.status()['state'],'error');run.assert_not_called()

    def test_profile_write_failure_also_restores_live_manifest(self):
        self.publisher_setup();original=(self.root/'dataark.yaml').read_bytes();profile=self.root/'config/content/public-manifest.yaml';previous=profile.read_bytes();atomic=publisher.atomic_write
        def write(path,data):
            if path==profile and data!=previous:raise OSError('Simulated profile write failure')
            return atomic(path,data)
        with patch.object(publisher,'atomic_write',side_effect=write),patch.object(publisher.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
            publisher.main()
        self.assertEqual((self.root/'dataark.yaml').read_bytes(),original)
        self.assertEqual(profile.read_bytes(),previous)
        self.assertEqual(c.status()['state'],'error')

if __name__=='__main__':unittest.main()
