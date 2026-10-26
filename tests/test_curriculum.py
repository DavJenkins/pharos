import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from tools import install_curriculum as m
from tools.discover_curriculum import describe

class CurriculumTests(unittest.TestCase):
    def item(self):
        return {'id':'ck-'+'a'*16,'relative_path':'curriculum/core-knowledge/ck-'+'a'*16+'.pdf','url':'https://www.coreknowledge.org/wp-content/uploads/book.pdf','publisher':'Core Knowledge Foundation','contexts':[{'unit_id':1,'unit':'Unit one','grades':['1'],'subject':'Mathematics','roles':['Teacher guide']}]}
    def test_paths_and_hosts_are_restricted(self):
        item=self.item();m.validate_item(item)
        for key,value in [('relative_path','../escape.pdf'),('url','https://example.org/book.pdf'),('url','https://name:secret@www.coreknowledge.org/book.pdf'),('id','../../escape')]:
            changed={**item,key:value}
            with self.assertRaises(ValueError):m.validate_item(changed)
    def test_unit_completeness_does_not_confuse_teacher_and_student(self):
        teacher={**self.item(),'status':'installed'}
        student=deepcopy(teacher);student['id']='other';student['contexts'][0]['roles']=['Student material'];student['status']='needs_review'
        unit=m.coverage([teacher,student])[0]
        self.assertFalse(unit['all_discovered_files_installed']);self.assertFalse(unit['teacher_and_student'])
        student['status']='installed';unit=m.coverage([teacher,student])[0]
        self.assertTrue(unit['all_discovered_files_installed']);self.assertTrue(unit['teacher_and_student'])
    def test_publisher_grade_labels_are_preserved(self):
        title,grades,subject=describe({'title':{'rendered':'Grade one math'},'class_list':['grade-grade1-03','subject-subject-06-math']})
        self.assertEqual(grades,['1']);self.assertEqual(subject,'Mathematics')
        self.assertEqual(describe({'title':{'rendered':'Kindergarten science'},'class_list':['grade-kindergarten-02','subject-science']})[1],['K'])
    def test_license_must_be_explicit(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'book.pdf';path.write_bytes(b'%PDF-fixture')
            with patch.object(m.subprocess,'check_output',side_effect=['Pages: 2','Copyright. All rights reserved.']):
                with self.assertRaisesRegex(ValueError,'Open license'):m.inspect_pdf(path,'publisher')
            with patch.object(m.subprocess,'check_output',side_effect=['Pages: 2','This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 license.']):
                self.assertIn('noncommercial',m.inspect_pdf(path,'publisher')[1])
    def test_hash_verified_original_is_reused_without_network(self):
        item=self.item()
        with TemporaryDirectory() as directory:
            root=Path(directory);target=root/item['relative_path'];target.parent.mkdir(parents=True);target.write_bytes(b'original')
            previous={'sha256':m.checksum(target),'bytes':8,'pages':1,'license':'CC BY','header':'Book'}
            with patch.object(m,'CONTENT',root),patch.object(m,'urlopen') as opener:
                result=m.acquire(item,previous,{})
                opener.assert_not_called();self.assertEqual(result['status'],'installed');self.assertEqual(target.read_bytes(),b'original')

    def test_curriculum_check_never_downloads_the_book_body(self):
        from tools.check_reference_sources import check
        class Response:
            url='https://assets.openstax.org/book.pdf'
            headers={'Content-Length':'100000000','ETag':'edition-one','Content-Type':'application/pdf'}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,*args): raise AssertionError('Must not download textbook body')
        calls=[]
        def opener(request,**kwargs):
            calls.append(request.get_method());return Response()
        result=check(Response.url,[{'repository_id':'curriculum','relative_path':'curriculum/book.pdf'}],{}, {},Path('/tmp'),opener=opener)
        self.assertEqual(calls,['HEAD']);self.assertEqual(result['status'],'baseline')

class KhanArchiveTests(unittest.TestCase):
    def test_khan_archive_uses_verified_supported_pipeline(self):
        from tools.update_worker import source_config
        from tools.stage_content_updates import validate_plan
        asset={'relative_path':'khanacademy_en_all_2023-03.zim','update_source':{'kind':'kiwix_zim','directory':'https://download.kiwix.org/zim/other/','filename_prefix':'khanacademy_en_all_'}}
        self.assertEqual(source_config(asset)[1],'khanacademy_en_all_')
        item={'id':'khan-academy','filename':asset['relative_path'],'url':'https://download.kiwix.org/zim/other/'+asset['relative_path'],'bytes':180007047736,'sha256':'3b8f4d286c6206a1c00c2252ac33187d30d4e146b8666ae2039d00f0d91eee3a'}
        self.assertEqual(validate_plan({'archives':[item]}),[item])
        with self.assertRaises(ValueError):validate_plan({'archives':[{**item,'url':'https://example.com/'+item['filename']}]})
