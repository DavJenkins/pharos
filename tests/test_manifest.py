import base64
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
import yaml
from PIL import Image
from app.services.manifest import build, load_manifest, ManifestError, prepare_artwork
from app.services.upstream import probe, check_assets, asset_state


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'dataark.yaml'
        self.template = self.root / 'template.html'
        self.template.write_text('<title>{{PROJECT_NAME}}</title>{{BACKGROUND_STYLE}}<main>{{MANIFEST_CARDS}}</main>')
        self.output = self.root / 'web/index.html'
        self.content = self.root / 'content'
        self.content.mkdir()
        self.data = {'system': {'version': '1.4', 'project_name': 'Test Ark', 'base_mount': '/mnt/storage'},
            'categories': [{'id': 'reference', 'title': 'Reference'}],
            'repositories': [{'id': 'source', 'title': 'Source', 'category': 'reference', 'links': [
                {'title': 'Online reference', 'url': 'https://example.invalid', 'requires_internet': True}]}],
            'assets': [{'id': 'book', 'title': 'Book', 'repository_id': 'source', 'category': 'reference',
                'relative_path': 'book.pdf', 'download_url': 'https://example.invalid/book.pdf'}]}
        image = Image.new('RGB', (2, 2))
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        self.png = buffer.getvalue()

    def write(self):
        self.manifest.write_text(yaml.safe_dump(self.data), encoding='utf-8')

    def render(self):
        self.write()
        result = build(self.manifest, self.template, self.output, content_root=self.content)
        return result, self.output.read_text(encoding='utf-8')

    def test_grouped_actions_share_standard_link_navigation(self):
        self.data['repositories'][0]['link_groups']=[{'title':'Radio tools','links':[{'title':'Practice','url':'/radio-study.html'},{'title':'Callsign search','url':'/callsigns.html'}]}]
        _,page=self.render()
        self.assertIn('<h4>Radio tools</h4><nav class="manifest-links" aria-label="Radio tools">',page)
        self.assertIn('href="/radio-study.html"',page)
        self.assertIn('href="/callsigns.html"',page)
        self.assertNotIn('</a> · <a',page)

    def test_collapsed_collection_keeps_files_and_primary_link(self):
        (self.content/'book.pdf').write_bytes(b'pdf')
        self.data['repositories'][0]['collapse_assets']=True
        self.data['repositories'][0]['links'].append({'title':'Browse collection','url':'/library-files/forms/index.html'})
        _, page=self.render()
        self.assertIn('<details class="manifest-file-details"><summary>1 of 1 assets available</summary>',page)
        self.assertEqual(page.count('1 of 1 assets available'),1)
        self.assertIn('href="/library-files/book.pdf"',page)
        self.assertIn('href="/library-files/forms/index.html"',page)
        self.data['repositories'][0]['collapse_assets']='yes'
        self.write()
        with self.assertRaises(ManifestError): load_manifest(self.manifest)

    def test_geographic_coverage_survives_rendering(self):
        coverage = {'country':'US','state':{'code':'MA','name':'Massachusetts'},
                    'counties':[{'name':'Worcester','focus':'Northern Worcester County'}, {'name':'Middlesex'}]}
        self.data['geography'] = coverage
        result, _ = self.render()
        self.assertEqual(result['geography'], coverage)
        self.assertEqual(json.loads((self.output.parent/'manifest.json').read_text())['geography'], coverage)
        for invalid in (None, {}, dict(coverage,counties=[{'name':'Worcester'},{'name':'worcester'}]),
                        dict(coverage,counties=[{'name':'Worcester','focus':False}]),
                        dict(coverage,state={'code':'mass','name':'Massachusetts'})):
            self.data['geography'] = invalid
            self.write()
            with self.subTest(invalid=invalid), self.assertRaises(ManifestError):
                load_manifest(self.manifest)

    def test_nested_resources_and_connectivity(self):
        self.template.write_text('{{PROJECT_NAME}}{{BACKGROUND_STYLE}}{{MANIFEST_CARDS}}{{RESOURCE_SECTIONS}}')
        (self.content / 'Manuals').mkdir()
        (self.content / 'Manuals' / 'my guide.pdf').write_bytes(b'pdf')
        self.data['resource_sections'] = [{'title':'Personal <resources>', 'items':[
            {'title':'Folder', 'path':'Manuals'},
            {'title':'Absent', 'path':'missing.pdf'},
            {'title':'Online', 'url':'https://example.invalid/reference'},
            {'title':'LAN', 'url':'http://192.168.4.2/', 'requires_internet':False}],
            'sections':[{'title':'Guides', 'items':[{'title':'Guide', 'path':'Manuals/my guide.pdf'}]}]}]
        _, page = self.render()
        self.assertIn('Personal &lt;resources&gt;', page)
        self.assertIn('href="/library-files/Manuals/"', page)
        self.assertIn('href="/library-files/Manuals/my%20guide.pdf"', page)
        self.assertIn('href="https://example.invalid/reference" data-requires-internet="true"', page)
        self.assertIn('href="http://192.168.4.2/">LAN', page)
        self.assertIn('<h3>Guides</h3>', page)
        self.assertIn('Unavailable locally', page)
        self.data['system']['hide_missing'] = True
        self.assertNotIn('Absent', self.render()[1])

    def test_invalid_resources_rejected(self):
        for item in ({'title':'Bad','path':'../secret'}, {'title':'Bad','url':'javascript:alert(1)'},
                     {'title':'Bad','path':'file','url':'/file'}, {'title':'Bad','url':'/file','requires_internet':'yes'}):
            self.data['resource_sections'] = [{'title':'Section', 'items':[item]}]
            self.write()
            with self.assertRaises(ManifestError): load_manifest(self.manifest)
        nested = {'title':'Deep'}
        self.data['resource_sections'] = [nested]
        for _ in range(6):
            nested['sections'] = [{'title':'Deep'}]
            nested = nested['sections'][0]
        self.write()
        with self.assertRaises(ManifestError): load_manifest(self.manifest)

    def test_empty_and_configuration_drives_cards(self):
        result, page = self.render()
        self.assertFalse(result['assets'][0]['available'])
        self.assertIn('Unavailable / Pending Download', page)
        self.assertIn('https://example.invalid', page)
        self.data['repositories'].append({'id': 'another', 'title': 'Another', 'category': 'reference'})
        _, page = self.render()
        self.assertEqual(page.count('data-repository-id='), 2)
        self.data['repositories'] = []
        self.data['assets'] = []
        _, page = self.render()
        self.assertNotIn('data-repository-id=', page)
        self.assertIn('No repositories configured', page)

    def test_local_copy_survives_source_loss_and_hide_missing(self):
        (self.content / 'book.pdf').write_bytes(b'payload')
        self.data['system']['hide_missing'] = True
        cache = self.root / '.cache'
        cache.mkdir()
        (cache / 'manifest-upstream.json').write_text(json.dumps({'version': 1, 'assets': {'book': {
            'status': 'unavailable', 'sources': ['https://example.invalid/book.pdf'],
            'checked_at': '2026-09-24T19:00:00+00:00'}}}))
        result, page = self.render()
        self.assertTrue(result['assets'][0]['available'])
        self.assertIn('Preserved locally', page)
        self.assertIn('href="/library-files/book.pdf"', page)
        self.assertEqual((self.content / 'book.pdf').read_bytes(), b'payload')
        (self.content / 'book.pdf').unlink()
        _, page = self.render()
        self.assertNotIn('data-repository-id=', page)

    def test_escape_content_and_encode_file_url(self):
        self.data['assets'][0]['title'] = '<script>alert(1)</script>'
        self.data['assets'][0]['relative_path'] = 'space & name.pdf'
        (self.content / 'space & name.pdf').touch()
        _, page = self.render()
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('/library-files/space%20%26%20name.pdf', page)

    def test_archive_titles_open_reader_and_external_icons_open_pages(self):
        asset = self.data['assets'][0]
        asset.update(relative_path='wikipedia_2026.zim', download_url='https://example.invalid/huge.zim',
                     online_url='https://example.invalid/read')
        (self.content/'wikipedia_2026.zim').touch()
        _, page = self.render()
        self.assertIn('data-manifest-kiwix-path="/content/wikipedia_2026"',page)
        self.assertIn('href="https://example.invalid/read"',page)
        self.assertNotIn('href="/library-files/wikipedia_2026.zim"',page)
        self.assertNotIn('href="https://example.invalid/huge.zim"',page)
        del asset['online_url']
        _, page = self.render()
        self.assertNotIn('class="asset-external"',page)

    def test_shared_sweep_time_preserves_older_and_unknown_observations(self):
        self.data['categories'][0]['title']='Content sources'
        cache = self.root / '.cache'
        cache.mkdir()
        records = {}
        for key, status, checked in [
                ('book', 'available', '2026-10-24T08:30:00+00:00'),
                ('older', 'available', '2026-10-23T08:30:00+00:00'),
                ('uncertain', 'unknown', '2026-10-24T08:30:01+00:00')]:
            asset = deepcopy(self.data['assets'][0])
            asset.update(id=key, title=key, relative_path=key+'.pdf',
                         download_url='https://example.invalid/'+key+'.pdf')
            if key == 'book': self.data['assets'][0] = asset
            else: self.data['assets'].append(asset)
            (self.content/(key+'.pdf')).touch()
            records[key] = {'status':status, 'sources':[asset['download_url']], 'checked_at':checked}
        (cache/'manifest-upstream.json').write_text(json.dumps({
            'version':1, 'batch_started_at':'2026-10-24T08:29:00+00:00',
            'batch_finished_at':'2026-10-24T08:31:00+00:00', 'assets':records}))
        _, page = self.render()
        self.assertEqual(page.count('Last checked:'), 1)
        self.assertEqual(page.count('id="source-check-now"'),1)
        self.assertEqual(page.count('<time data-local-time'), 2)  # Sweep and genuinely older check.
        self.assertIn('Older check · Source OK', page)
        self.assertIn('Source unknown</span>', page)
        self.assertNotIn('2026-10-24T08:30:00+00:00', page)
        self.assertNotIn('2026-10-24T08:30:01+00:00', page)

    def test_invalid_manifest_preserves_previous_page(self):
        self.render()
        previous = self.output.read_bytes()
        original = deepcopy(self.data)
        for field, bad in [('repository_id', 'unknown'), ('relative_path', '../escape'), ('download_url', 'javascript:alert(1)'), ('online_url', 'javascript:alert(1)'), ('expected_hash', 'bad')]:
            self.data = deepcopy(original)
            self.data['assets'][0][field] = bad
            self.write()
            with self.assertRaises(ManifestError):
                build(self.manifest, self.template, self.output, content_root=self.content)
            self.assertEqual(self.output.read_bytes(), previous)
        self.manifest.write_text('system: {}\nsystem: {}')
        with self.assertRaises(ManifestError):
            load_manifest(self.manifest)

    def test_pin_requires_version_and_metadata_never_downloads(self):
        self.data['repositories'][0]['update_policy'] = 'pin_version'
        self.write()
        with self.assertRaises(ManifestError):
            load_manifest(self.manifest)
        self.data['repositories'][0]['version_pin'] = '2026-02'
        with patch('app.services.upstream.urlopen') as fetch:
            self.render()
            fetch.assert_not_called()

    def test_artwork_local_inline_cache_and_failed_refresh(self):
        (self.root / 'art.png').write_bytes(self.png)
        cache, dest = self.root / 'cache', self.root / 'web'
        local = prepare_artwork({'path': 'art.png'}, self.root, dest, cache)
        inline = prepare_artwork({'inline': 'data:image/png;base64,' + base64.b64encode(self.png).decode()}, self.root, dest, cache)
        self.assertEqual(local, inline)
        spec = {'url': 'https://example.invalid/art.png'}
        with patch('app.services.manifest.download_artwork', return_value=self.png) as fetch:
            remote = prepare_artwork(spec, self.root, dest, cache)
            prepare_artwork(spec, self.root, dest, cache)
            fetch.assert_called_once()
        with patch('app.services.manifest.download_artwork', side_effect=OSError):
            with self.assertWarns(UserWarning):
                self.assertEqual(remote, prepare_artwork(spec, self.root, dest, cache, refresh=True))
            with self.assertRaises(ManifestError):
                prepare_artwork({'url': 'https://example.invalid/new.png'}, self.root, dest, cache)


class UpstreamTests(unittest.TestCase):
    def test_http_results_and_no_body_read(self):
        for code, expected in [(200, 'available'), (206, 'available'), (404, 'unavailable'), (410, 'unavailable'), (403, 'unknown'), (503, 'unknown')]:
            response = MagicMock()
            response.__enter__.return_value.status = code
            with patch('app.services.upstream.urlopen', return_value=response):
                self.assertEqual(probe('https://example.invalid')['status'], expected)
                response.__enter__.return_value.read.assert_not_called()
        with patch('app.services.upstream.urlopen', side_effect=TimeoutError):
            self.assertEqual(probe('https://example.invalid')['status'], 'unknown')

    def test_head_fallback_and_mirror(self):
        error = HTTPError('https://example.invalid', 405, 'Method not allowed', {}, None)
        response = MagicMock()
        response.__enter__.return_value.status = 206
        with patch('app.services.upstream.urlopen', side_effect=[error, response]) as fetch:
            self.assertEqual(probe('https://example.invalid')['status'], 'available')
            self.assertEqual(fetch.call_args[0][0].method, 'GET')
            self.assertEqual(fetch.call_args[0][0].get_header('Range'), 'bytes=0-0')
        asset = {'id': 'book', 'download_url': 'https://example.invalid/book', 'mirror_url': 'https://mirror.example.invalid/book'}
        with patch('app.services.upstream.probe', side_effect=[{'status': 'unavailable'}, {'status': 'available'}]):
            state = check_assets([asset])['assets']
        self.assertEqual(asset_state(asset, state)['status'], 'available')
        asset['download_url'] += '-new'
        self.assertEqual(asset_state(asset, state)['status'], 'unknown')

    def test_unknown_mirror_prevents_false_removal(self):
        asset = {'id': 'book', 'download_url': 'https://example.invalid/book', 'mirror_url': 'https://mirror.example.invalid/book'}
        with patch('app.services.upstream.probe', side_effect=[{'status': 'unavailable'}, {'status': 'unknown'}]):
            self.assertEqual(check_assets([asset])['assets']['book']['status'], 'unknown')

if __name__ == '__main__':
    unittest.main()
