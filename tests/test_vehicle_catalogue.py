import copy
import json
from pathlib import Path
import ssl
import tempfile
import unittest

from tools.vehicle_catalogue import load, validate_document, render_index
from tools.source_tls import extra_ca, context


class VehicleCatalogueTests(unittest.TestCase):
    def test_other_make_year_and_explicit_notices(self):
        source = load(Path(__file__).resolve().parents[1] / 'deploy/reference/vehicle-manuals.json')
        item = copy.deepcopy(source['documents'][0])
        item.update(id='example-2022', title='Example <guide>', model='Example Model',
                    year=2022, publisher='Example Motors', rights_notice='Explicit notice')
        validate_document(item, '2022 EXAMPLE MODEL owner guide')
        with self.assertRaises(ValueError):
            validate_document(item, '2017 Example Model owner guide')
        page = render_index([{**item, 'path': 'vehicles/example.pdf'}])
        self.assertIn('Example &lt;guide&gt;', page)
        self.assertIn('Explicit notice', page)
        self.assertNotIn('Honda', page)

    def test_defaults_and_duplicate_ids(self):
        source = json.loads((Path(__file__).resolve().parents[1] / 'deploy/reference/vehicle-manuals.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalogue.json'
            path.write_text(json.dumps(source), encoding='utf-8')
            self.assertEqual(load(path)['documents'][0]['scope'], source['defaults']['scope'])
            source['documents'].append(source['documents'][0])
            path.write_text(json.dumps(source), encoding='utf-8')
            with self.assertRaises(ValueError):
                load(path)

    def test_tls_scope_and_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = root / 'deploy/reference/source-tls.json'
            policy.parent.mkdir(parents=True)
            policy.write_text(json.dumps({'schema': 1, 'hosts': {'publisher.example': {'ca_bundle': '../outside.pem'}}}), encoding='utf-8')
            self.assertIsNone(extra_ca('https://other.example/file.pdf', root))
            with self.assertRaises(ValueError):
                extra_ca('https://publisher.example/file.pdf', root)
            tls = context('https://other.example/file.pdf', root)
            self.assertTrue(tls.check_hostname)
            self.assertEqual(tls.verify_mode, ssl.CERT_REQUIRED)


if __name__ == '__main__':
    unittest.main()
