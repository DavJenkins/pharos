from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.services import configuration_project as p
from app.services.manifest import build,load_manifest


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.data={'system':{'version':'1.4','project_name':'Test Ark','base_mount':'/mnt/storage'},
            'categories':[{'id':'reference','title':'Reference'}],
            'repositories':[{'id':key,'title':key,'category':'reference','enabled':True,'links':[]} for key in ['one','two']],
            'assets':[{'id':key,'title':key,'repository_id':repo,'category':'reference','relative_path':key+'.pdf','expected_hash':'a'*64,'download_url':'https://example.org/'+key+'.pdf','removed':key=='a'} for key,repo in [('a','one'),('b','two'),('c','one')]],
            'personalization':{'version':1,'vehicles':[]},'community':{'enabled':True},'private_household':{'password':'not portable'}}

    def test_round_trip_preserves_every_definition_and_cross_collection_order(self):
        files=p.split(self.data);result,names=p.assemble(files.__getitem__)
        self.assertEqual(result,p.public(self.data));self.assertEqual([a['id'] for a in result['assets']],['a','b','c'])
        self.assertNotIn('assets:',files['ark.yaml']);self.assertNotIn('password',''.join(files.values()))
        self.assertNotIn('expected_hash',files['catalogues/one.yaml']);self.assertIn('a'*64,files['state/versions/one.yaml'])

    def test_safe_paths_duplicates_and_yaml_tags(self):
        for path in ['../dataark.yaml','/etc/passwd','collections/../../escape.yaml','collections\\one.yaml']:
            with self.assertRaises(ValueError):p.inside(self.root,path)
        for source in ['a: 1\na: 2','a: &loop [*loop]','!!python/object/apply:os.system [id]']:
            with self.assertRaises((ValueError,p.yaml.YAMLError)):p.parse(source)

    def test_missing_refs_duplicate_assets_and_wrong_repository_fail(self):
        for change in ['missing','duplicate','repository']:
            files=p.split(self.data)
            if change=='missing':del files['catalogues/one.yaml']
            else:
                value=p.parse(files['catalogues/two.yaml'])
                if change=='duplicate':value['assets'][0]['id']='a'
                else:value['assets'][0]['repository_id']='one'
                files['catalogues/two.yaml']=p.dump(value)
            with self.assertRaises((ValueError,KeyError)):p.assemble(files.__getitem__)

    def test_manual_disk_edits_are_not_overwritten(self):
        root=self.root/'config/library';p.write(root,self.data)
        path=root/'ark.yaml';path.write_text(path.read_text()+'# handwritten note\n')
        with self.assertRaisesRegex(ValueError,'manual edits'):p.write(root,self.data)
        self.assertIn('handwritten note',path.read_text())

    def test_loader_and_rendered_dashboard_match_legacy(self):
        main=self.root/'dataark.yaml';main.write_text(p.dump(p.public(self.data)))
        root=self.root/'config/library';p.write(root,self.data)
        self.assertEqual(load_manifest(main),load_manifest(root/'ark.yaml'))
        content=self.root/'content';content.mkdir();(content/'b.pdf').write_text('fixture')
        template=self.root/'template.html';template.write_text('{{PROJECT_NAME}}{{BACKGROUND_STYLE}}{{MANIFEST_CARDS}}')
        a=self.root/'first/index.html';b=self.root/'second/index.html'
        build(main,template,a,content_root=content);build(root/'ark.yaml',template,b,content_root=content)
        self.assertEqual(a.read_text(),b.read_text())

    def test_comments_in_edited_file_survive_publication_projection(self):
        root=self.root/'config/library';files=p.split(self.data)
        edited=files['ark.yaml']+'# keep this explanation\n'
        p.write(root,self.data,{'ark.yaml':edited})
        self.assertEqual((root/'ark.yaml').read_text(),edited)
        self.assertEqual(p.load(root/'ark.yaml'),p.public(self.data))
        self.assertEqual(p.view_files(root,self.data)['ark.yaml'],edited)
        p.write(root,self.data)
        self.assertEqual((root/'ark.yaml').read_text(),edited)
        changed=deepcopy(self.data);changed['repositories'][0]['title']='Edited collection'
        p.write(root,changed)
        self.assertEqual((root/'ark.yaml').read_text(),edited)

    def test_file_write_failure_restores_all_touched_files(self):
        root=self.root/'config/library';p.write(root,self.data);original=p.disk_files(root)
        data=deepcopy(self.data);data['repositories'][0]['title']='Changed'
        real=p.atomic_write;failed=False
        def broken(path,value):
            nonlocal failed
            if not failed and path.name=='order.yaml':failed=True;raise OSError('fixture write failure')
            return real(path,value)
        with patch.object(p,'atomic_write',side_effect=broken),self.assertRaises(OSError):p.write(root,data)
        self.assertEqual(p.disk_files(root),original);p.ensure_clean(root)

    def test_generated_records_are_marked_read_only(self):
        files=p.split(self.data)
        self.assertTrue(all(row['read_only']==row['path'].startswith('state/') for row in p.metadata(files)))

    def test_catalogue_order_can_be_edited_without_changing_generated_state(self):
        files=p.split(self.data);catalogue=p.parse(files['catalogues/one.yaml'])
        catalogue['assets'].reverse();files['catalogues/one.yaml']=p.dump(catalogue)
        assembled,_=p.assemble(files.__getitem__)
        self.assertEqual([a['id'] for a in assembled['assets']],['c','b','a'])

    def test_relative_destination_stays_within_project(self):
        import os
        root=self.root/'relative-project'
        p.write(Path(os.path.relpath(root)),self.data)
        self.assertEqual(p.load(root/'ark.yaml'),p.public(self.data))

    def test_restoration_jobs_and_capacity_match_for_both_manifest_formats(self):
        from tools import content_profile as content,recovery_queue as queue
        (self.root/'public-manifest.yaml').write_text(p.dump(p.public(self.data)))
        p.write(self.root/'project',self.data)
        profile={'schema':1,'manifest':'public-manifest.yaml','reserve_gib':10,'content_root':str(self.root),
                 'direct_files':[{'id':'book','path':'preparedness/book.pdf','url':'https://example.org/book.pdf','bytes':10}]}
        path=self.root/'content.yaml';path.write_text(p.dump(profile))
        first=queue.build_plan(path,'full',free_bytes=10**12)
        profile['manifest']='project/ark.yaml';path.write_text(p.dump(profile))
        second=queue.build_plan(path,'full',free_bytes=10**12)
        self.assertEqual(first['jobs'],second['jobs']);self.assertEqual(first['capacity'],second['capacity'])
        portable={name for _,name in content.portable_files(profile,self.root)}
        self.assertIn('config/content/project/catalogues/one.yaml',portable)
        self.assertIn('config/library/ark.yaml',portable)


if __name__=='__main__':unittest.main()
