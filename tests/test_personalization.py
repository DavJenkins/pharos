import unittest
from copy import deepcopy
from app.services.personalization import validate
from app.services.manifest import ManifestError, url, load_manifest
from tools.content_profile import PUBLIC_KEYS

class PersonalizationTests(unittest.TestCase):
    def setUp(self):
        self.data = {'assets': [{'id': 'manual'}], 'personalization': {'version': 1,
            'vehicles': [{'id': 'car', 'year': 2017, 'make': 'Honda', 'model': 'Accord', 'asset_ids': ['manual']}],
            'destinations': [{'id': 'island', 'name': 'Sint Maarten', 'viewer_url': '/maps.html?collection=caribbean'}]}}
    def check(self, data):
        validate(data, ManifestError, url)
    def test_optional_and_valid_profile(self):
        self.check({'assets': []})
        self.check(self.data)
        self.check({'personalization': {'version': 1}})
    def test_unknown_assets_and_duplicate_ids_rejected(self):
        bad = deepcopy(self.data)
        bad['personalization']['vehicles'][0]['asset_ids'] = ['typo']
        with self.assertRaises(ManifestError): self.check(bad)
        bad = deepcopy(self.data)
        bad['personalization']['vehicles'] *= 2
        with self.assertRaises(ManifestError): self.check(bad)
    def test_bad_year_and_external_viewer_rejected(self):
        for value in [True, '2017', 100]:
            bad = deepcopy(self.data)
            bad['personalization']['vehicles'][0]['year'] = value
            with self.assertRaises(ManifestError): self.check(bad)
        for value in ['https://example.org/', '//example.org/', 'javascript:alert(1)']:
            bad = deepcopy(self.data)
            bad['personalization']['destinations'][0]['viewer_url'] = value
            with self.assertRaises(ManifestError): self.check(bad)
    def test_live_profile_is_valid_and_portable(self):
        data = load_manifest('/opt/dataark/dataark.yaml')
        self.assertIn('personalization', PUBLIC_KEYS)
        public = {key: data[key] for key in PUBLIC_KEYS if key in data}
        self.assertEqual(public['personalization'], data['personalization'])
        self.assertEqual(len(public['personalization']['vehicles']), 2)
