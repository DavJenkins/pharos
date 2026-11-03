import hashlib
import io
import json
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from tools import check_reference_sources as worker
from app.services import reference_checks as view

class Response(io.BytesIO):
    def __init__(self, data=b'', headers=None):
        super().__init__(data); self.headers = headers or {}; self.url = 'https://publisher.test/file'

class ReferenceChecksTests(unittest.TestCase):
    def test_retired_map_discovers_bounded_header_without_touching_map(self):
        url='https://build.protomaps.com/20261022.pmtiles'
        asset=dict(self.asset,relative_path='maps/usa.pmtiles')
        requests=[]
        class HeaderResponse(Response):
            status=206
            def read(self,size=-1):
                self.asserted_size=size
                if size != 127:raise AssertionError('Unbounded map read')
                return b'PMTiles\x03'+bytes(119)
        def opener(request,**kwargs):
            requests.append(request)
            if request.full_url.endswith('20261103.pmtiles'):raise HTTPError(request.full_url,404,'',{},None)
            response=HeaderResponse(headers={'Content-Range':'bytes 0-126/139000000000','ETag':'v2'})
            response.url=request.full_url
            return response
        with tempfile.TemporaryDirectory() as folder:
            saved=Path(folder)/'map.pmtiles';saved.write_bytes(b'original')
            result=worker.retired_map_edition(url,[asset],{'baseline':'old'},self.cfg,opener,date(2026,11,3))
            self.assertEqual(saved.read_bytes(),b'original')
        self.assertEqual(len(requests),2)
        self.assertEqual(requests[1].get_header('Range'),'bytes=0-126')
        self.assertEqual(result['edition_discovery']['candidate']['edition'],'2026-11-02')
        self.assertTrue(result['pending_change'])

    def test_retired_map_discovery_is_bounded_and_rejects_html(self):
        url='https://build.protomaps.com/20261022.pmtiles';asset=dict(self.asset,relative_path='maps/usa.pmtiles');calls=[]
        def absent(request,**kwargs):
            calls.append(request);raise HTTPError(request.full_url,404,'',{},None)
        with self.assertRaisesRegex(ValueError,'four-day'):
            worker.retired_map_edition(url,[asset],{},self.cfg,absent,date(2026,11,3))
        self.assertEqual(len(calls),4)
        response=Response(b'Not a map',{'Content-Range':'bytes 0-126/1000'});response.status=206;response.url='https://build.protomaps.com/20261103.pmtiles'
        with self.assertRaisesRegex(ValueError,'invalid PMTiles'):
            worker.retired_map_edition(url,[asset],{},self.cfg,lambda *a,**k:response,date(2026,11,3))
    @staticmethod
    def constitution_page(clause='The constitutional provision', furniture='Navigation'):
        values = [None, {'data': 2}, {'useConstitutionEntriesAllsnapshot': 3}, list(range(4, 14))]
        values += [{'clause': 14, 'title': 15} for _ in range(10)]
        values += [clause, 'Article']
        return ('<html><p>'+furniture+'</p><script id="__NUXT_DATA__">'+json.dumps(values)+'</script></html>').encode()

    def test_constitution_checks_embedded_provisions_not_page_furniture(self):
        url='https://50constitutions.org/ma/constitution'
        first=worker.body_fingerprint(self.constitution_page(), 'text/html', url)
        self.assertEqual(first, worker.body_fingerprint(self.constitution_page(furniture='New navigation'), 'text/html', url))
        self.assertNotEqual(first, worker.body_fingerprint(self.constitution_page(clause='Amended constitutional provision'), 'text/html', url))

    def test_constitution_baseline_migration_requires_exact_installed_match(self):
        data=self.constitution_page()
        from tools.install_jurisdictions import university_body
        body=university_body(data.decode())[0]
        asset=dict(self.asset,relative_path='constitution.html')
        previous={'baseline':'old-page-furniture','pending_change':True,'etag':'old'}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/asset['relative_path']
            path.write_text('<html><h1>Saved snapshot</h1>'+body+'</html>')
            def opener(request,**kwargs):
                self.assertIsNone(request.get_header('If-none-match'))
                return Response(data,{'Content-Type':'text/html'})
            result=worker.check('https://50constitutions.org/ma/constitution',[asset],previous,self.cfg,root,opener)
            self.assertEqual(result['status'],'unchanged')
            self.assertFalse(result['pending_change'])
            path.write_text('<html>'+body.replace('The constitutional provision','Older text')+'</html>')
            changed=worker.check('https://50constitutions.org/ma/constitution',[asset],previous,self.cfg,root,opener)
            self.assertTrue(changed['pending_change'])
            path.unlink()
            missing=worker.check('https://50constitutions.org/ma/constitution',[asset],previous,self.cfg,root,opener)
            self.assertTrue(missing['pending_change'])

    def test_publisher_body_migration_does_not_ignore_substantive_changes(self):
        url='https://www.energy.gov/guide'
        body='<p>'+('Useful wind guidance. '*30)+'</p>'
        data=('<html><nav>New navigation</nav><main>'+body+'</main></html>').encode()
        asset=dict(self.asset,relative_path='guide.html')
        previous={'baseline':'old-whole-page','pending_change':True}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'guide.html'
            path.write_text('<html><h1>Local title</h1><div class="source"><a>Original publisher page (internet)</a></div>'+body+'</html>')
            result=worker.check(url,[asset],previous,self.cfg,root,lambda *a,**k:Response(data,{'Content-Type':'text/html'}))
            self.assertFalse(result['pending_change'])
            changed=data.replace(b'Useful wind guidance.',b'Changed wind guidance.')
            result=worker.check(url,[asset],result,self.cfg,root,lambda *a,**k:Response(changed,{'Content-Type':'text/html'}))
            self.assertTrue(result['pending_change'])

    def setUp(self):
        self.asset = {'id': 'doc', 'relative_path': 'docs/file.pdf', 'repository_id': 'docs', 'download_url': 'https://publisher.test/file.pdf'}
        self.cfg = {'enabled': True, 'interval': '7d', 'max_bytes': 10000}

    def test_direct_pdf_matches_installed_hash_and_checks_structure(self):
        data = b'%PDF-1.4\ninstalled document'
        self.asset['expected_hash'] = hashlib.sha256(data).hexdigest()
        with patch.object(worker.subprocess, 'run') as validate:
            result = worker.check(self.asset['download_url'], [self.asset], {}, self.cfg, Path('/tmp'), opener=lambda *a, **k: Response(data))
        self.assertEqual(result['status'], 'unchanged')
        self.assertFalse(result['pending_change'])
        validate.assert_called_once()

    def test_changed_file_is_reported_without_touching_installed_file(self):
        self.asset['expected_hash'] = 'a' * 64
        with tempfile.TemporaryDirectory() as folder, patch.object(worker.subprocess, 'run'):
            installed = Path(folder) / 'installed.pdf'; installed.write_bytes(b'original')
            result = worker.check(self.asset['download_url'], [self.asset], {}, self.cfg, Path(folder), opener=lambda *a, **k: Response(b'%PDF-1.4\nreplacement'))
            self.assertEqual(installed.read_bytes(), b'original')
            self.assertEqual(list(Path(folder).iterdir()), [installed])
        self.assertTrue(result['pending_change'])
        self.assertEqual(result['status'], 'changed')

    def test_conditional_304_preserves_pending_change(self):
        def opener(request, **kwargs):
            self.assertEqual(request.get_header('If-none-match'), 'v2')
            raise HTTPError(request.full_url, 304, '', {}, None)
        result = worker.check(self.asset['download_url'], [self.asset], {'etag': 'v2', 'baseline': 'v1', 'pending_change': True}, self.cfg, Path('/tmp'), opener)
        self.assertTrue(result['pending_change'])
        self.assertEqual(result['status'], 'changed')

    def test_unicode_publisher_filename_is_encoded_without_double_escaping(self):
        url = 'https://publisher.test/Gu\u0308ero%20book.pdf?edition=2&name=\u00e9'
        def opener(request, **kwargs):
            self.assertEqual(request.full_url, 'https://publisher.test/Gu%CC%88ero%20book.pdf?edition=2&name=%C3%A9')
            request.full_url.encode('ascii')
            return Response(b'%PDF-1.4\nbook')
        with patch.object(worker.subprocess, 'run'):
            self.assertEqual(worker.check(url, [self.asset], {}, self.cfg, Path('/tmp'), opener)['status'], 'baseline')

    def test_pdf_challenge_page_is_never_an_update(self):
        with self.assertRaisesRegex(ValueError, 'PDF'):
            worker.check(self.asset['download_url'], [self.asset], {}, self.cfg, Path('/tmp'), lambda *a, **k: Response(b'<html>Access denied</html>', {'Content-Type': 'text/html'}))

    def test_size_limit_checked_before_and_during_read(self):
        for response in [Response(b'', {'Content-Length': '10001'}), Response(b'x' * 10001)]:
            with self.assertRaisesRegex(ValueError, 'size'):
                worker.check(self.asset['download_url'], [self.asset], {}, self.cfg, Path('/tmp'), lambda *a, **k: response)

    def test_package_metadata_and_word_challenge_pages_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'HTML'):
            worker.check('https://publisher.test/code.zip', [self.asset], {}, self.cfg, Path('/tmp'), lambda *a, **k: Response(headers={'Content-Type': 'text/html', 'ETag': 'challenge'}))
        self.asset['relative_path'] = 'docs/file.docx'
        with self.assertRaises(Exception):
            worker.check('https://publisher.test/download', [self.asset], {}, self.cfg, Path('/tmp'), lambda *a, **k: Response(b'<html>challenge</html>'))

    def test_shared_package_uses_head_and_detects_metadata_change(self):
        def opener(request, **kwargs):
            self.assertEqual(request.method, 'HEAD')
            return Response(headers={'ETag': 'new'})
        result = worker.check('https://publisher.test/code.zip', [self.asset], {'baseline': 'old||'}, self.cfg, Path('/tmp'), opener)
        self.assertTrue(result['pending_change'])

    def test_head_refusal_falls_back_to_one_byte_range_and_uses_total_size(self):
        methods = []
        def opener(request, **kwargs):
            methods.append(request.method)
            if request.method == 'HEAD': raise HTTPError(request.full_url, 403, '', {}, None)
            self.assertEqual(request.get_header('Range'), 'bytes=0-0')
            return Response(headers={'ETag': 'v1', 'Content-Length': '1', 'Content-Range': 'bytes 0-0/200000000'})
        result = worker.check('https://publisher.test/code.zip', [self.asset], {'baseline': 'v1||200000000'}, self.cfg, Path('/tmp'), opener)
        self.assertEqual(methods, ['HEAD', 'GET'])
        self.assertEqual(result['status'], 'unchanged')

    def test_first_html_baseline_does_not_claim_installed_freshness(self):
        data = ('<html><script>random tracking</script><p>' + 'Useful content ' * 20 + '</p></html>').encode()
        self.asset['relative_path'] = 'docs/page.html'
        result = worker.check('https://publisher.test/page', [self.asset], {}, self.cfg, Path('/tmp'), lambda *a, **k: Response(data, {'Content-Type': 'text/html'}))
        self.assertEqual(result['status'], 'baseline')
        self.assertIn('not established', result['detail'])
        other = data.replace(b'random tracking', b'a changed script')
        self.assertEqual(worker.body_fingerprint(data, 'text/html', ''), worker.body_fingerprint(other, 'text/html', ''))

    def test_weekly_schedule_and_failed_attempt_does_not_erase_last_success(self):
        state = {'sources': {self.asset['download_url']: {'attempted_at': 1000000, 'checked_at': 900000, 'status': 'error', 'pending_change': True}}}
        result = view.projection(self.asset, {}, self.cfg, state, 1000010)
        self.assertEqual(result['interval'], '7d')
        self.assertFalse(result['due_now'])
        self.assertTrue(result['pending_change'])
        self.assertNotEqual(result['last_success'], result['last_checked'])

    def test_removed_and_generated_items_have_truthful_labels(self):
        self.assertIn('paused', view.projection(dict(self.asset, removed=True), {}, self.cfg, {}, 0)['summary'])
        self.assertIn('Generated locally', view.projection({'id': 'generated'}, {}, self.cfg, {}, 0)['summary'])
        self.assertIsNone(view.projection(dict(self.asset, update_source={'kind': 'kiwix_zim'}), {}, self.cfg, {}, 0))

    def test_release_notice_checks_do_not_compare_metadata_with_package_hash(self):
        asset=dict(self.asset, relative_path='software/kit.tar.gz', expected_hash='a'*64,
                   source_check_url='https://publisher.test/release.json')
        url=view.source(asset)
        self.assertEqual(url,asset['source_check_url'])
        first=worker.check(url,[asset],{},self.cfg,Path('/tmp'),lambda *a,**k:Response(b'{"version":"1"}'))
        self.assertEqual(first['status'],'baseline')
        next_check=worker.check(url,[asset],first,self.cfg,Path('/tmp'),lambda *a,**k:Response(b'{"version":"2"}'))
        self.assertTrue(next_check['pending_change'])
        projected=view.projection(asset,{},self.cfg,{'sources':{url:next_check}},0)
        self.assertTrue(projected['pending_change'])

    def test_shared_sources_checked_once_and_removed_files_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'docs').mkdir(); (root / 'docs/file.pdf').write_bytes(b'original')
            assets = [self.asset, dict(self.asset, id='same-source'), dict(self.asset, id='removed', removed=True)]
            manifest = {'system': {'base_mount': folder}, 'repositories': [{'id': 'docs'}], 'assets': assets}
            with patch.object(worker, 'STATE', root / 'state.json'), patch.object(worker, 'settings', return_value=self.cfg), patch.object(worker, 'load_manifest', return_value=manifest), patch.object(worker.Path, 'is_mount', return_value=True), patch.object(worker, 'check', return_value={'status': 'baseline'}) as check, patch.object(worker.time, 'sleep'):
                worker.run()
                check.assert_called_once()
                self.assertEqual([a['id'] for a in check.call_args.args[1]], ['doc', 'same-source'])

if __name__ == '__main__': unittest.main()
