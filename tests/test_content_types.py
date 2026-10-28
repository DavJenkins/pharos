import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

from tools import content_types as types
from tools import content_profile as profile
from tools.check_content_types import check


class ContentTypeTests(unittest.TestCase):
    def test_all_registered_handlers_conform(self):
        names = check()
        self.assertIn('family', names)
        self.assertIn('example-text', names)
        self.assertIn('archives', names)

    def test_example_full_round_trip_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            phases = []
            context = types.Context(root, {}, root, progress=phases.append)
            item = {'id': 'welcome', 'path': 'example/welcome.txt', 'text': 'Welcome to the Ark'}
            self.assertEqual(types.dispatch('example-text', 'inspect', item, context)['status'], 'missing')
            self.assertEqual(types.dispatch('example-text', 'restore', item, context)['status'], 'complete')
            self.assertEqual(types.dispatch('example-text', 'restore', item, context)['status'], 'present')
            types.dispatch('example-text', 'verify', item, context)
            self.assertIn('publishing', phases)
            (root/item['path']).write_text('damaged')
            with self.assertRaises(ValueError):
                types.dispatch('example-text', 'verify', item, context)

    def test_cancel_before_code_runs(self):
        context = types.Context(Path('.'), {}, Path('.'), cancelled=lambda: True)
        with patch.object(types, 'load_handler') as load:
            with self.assertRaises(InterruptedError):
                types.dispatch('example-text', 'restore', {}, context)
            load.assert_not_called()

    def test_unsupported_operation_and_unknown_type_fail_closed(self):
        context = types.Context(Path('.'), {}, Path('.'))
        for name, operation in [('missing', 'restore'), ('family', 'remove')]:
            with patch.object(types, 'load_handler') as load:
                with self.assertRaises(ValueError):
                    types.dispatch(name, operation, {}, context)
                load.assert_not_called()

    def test_path_escape_rejected(self):
        for name in ['../escape.py', '/absolute.py', 'plugins\\escape.py']:
            with self.assertRaises(ValueError):
                types.source_path(types.ROOT, name)

    def test_registry_duplicate_keys_and_future_api_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'types.yaml'
            path.write_text('schema: 1\nschema: 1\ntypes: {}\n')
            with self.assertRaises(ValueError):
                types.read_registry(path)
            data = types.read_registry()
            data['types']['family']['api'] = 2
            path.write_text(yaml.safe_dump(data))
            with self.assertRaises(ValueError):
                types.read_registry(path)

    def test_existing_recipe_uses_registered_adapter(self):
        with patch.object(profile, '_legacy_recipe') as legacy:
            profile.recipe({'id': 'family'}, {}, Path('.'), Path('.'))
            legacy.assert_called_once()

    def test_custom_type_can_have_different_collection_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = {'id': 'local-welcome', 'type': 'example-text', 'path': 'hello.txt', 'text': 'Hello'}
            profile.validate({'schema': 1, 'reserve_gib': 1, 'recipes': [item]})
            profile.recipe(item, {}, root, root)
            self.assertEqual((root/'hello.txt').read_text(), 'Hello')

    def test_portable_registry_and_handlers_without_import(self):
        with patch.object(types, 'load_handler', side_effect=AssertionError('must not import')):
            names = [name for _, name in types.portable_sources()]
        self.assertIn('config/content-types.yaml', names)
        self.assertIn('plugins/example_text.py', names)
        self.assertEqual(len(names), len(set(names)))

    def test_invalid_result_fails_worker(self):
        class Handler:
            def validate(self, item, context): pass
            def restore(self, item, context): return None
        with patch.object(types, 'load_handler', return_value=Handler()):
            with self.assertRaises(ValueError):
                types.dispatch('example-text', 'restore', {}, types.Context(Path('.'), {}, Path('.')))

    def test_changed_plugin_invalidates_queue_fingerprint(self):
        from tools.recovery_queue import fingerprint
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = root/'content.yaml'
            recipe.write_text('schema: 1\n')
            handler = root/'handler.py'
            handler.write_text('API_VERSION = 1\n')
            with patch.object(profile, 'portable_files', return_value=[(handler, 'plugins/custom.py')]):
                before = fingerprint(recipe, {})
                handler.write_text('API_VERSION = 1\n# Changed implementation\n')
                self.assertNotEqual(before, fingerprint(recipe, {}))


if __name__ == '__main__':
    unittest.main()
