import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.services import collection_changes as changes
from app.services import library_events


class CollectionChangeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.override = patch.object(changes, 'STATE', Path(self.directory.name)/'feed')
        self.override.start()
        self.addCleanup(self.override.stop)

    def test_phase_changes_are_events_but_percent_updates_are_not(self):
        for percent in [0, 10, 25, 50]:
            changes.from_library('update_progress', {'phase':'downloading', 'title':'Books', 'percent':percent})
        first = changes.snapshot()
        self.assertEqual(len(first['events']), 1)
        self.assertEqual(first['activity']['updater']['percent'], 50)
        changes.from_library('update_progress', {'phase':'verifying', 'title':'Books'})
        self.assertEqual(len(changes.snapshot()['events']), 2)

    def test_debug_disabled_still_records_lifecycle(self):
        with patch.object(library_events, 'DEBUG_FLAG', Path(self.directory.name)/'absent'), patch.object(library_events.events, 'info') as log:
            library_events.emit('update_progress', detailed=True, phase='downloading', title='Books')
            log.assert_not_called()
        self.assertEqual(changes.snapshot()['events'][0]['kind'], 'downloading')

    def test_restart_has_stable_journal_and_ordered_unique_event_ids(self):
        changes.record('suggested', operation_id='request1', title='Books')
        first = changes.snapshot()
        changes.record('approved', operation_id='request1')
        second = changes.snapshot()
        self.assertEqual(first['journal_id'], second['journal_id'])
        self.assertEqual([r['sequence'] for r in second['events']], [1, 2])
        self.assertNotEqual(second['events'][0]['event_id'], second['events'][1]['event_id'])

    def test_retention_is_bounded_without_reusing_sequences(self):
        with patch.object(changes, 'KEEP', 3):
            for n in range(6): changes.record('queued', operation_id=str(n))
            feed = changes.snapshot()
        self.assertEqual([r['sequence'] for r in feed['events']], [4, 5, 6])
        self.assertEqual(feed['oldest_sequence'], 4)

    def test_private_fields_and_error_bodies_never_exported(self):
        changes.from_library('operation_failed', {'title':'Books', 'action':'download', 'error_type':'ValueError',
                             'reason':'password=secret https://private-source', 'token':'secret', 'source_url':'private'})
        exported = json.dumps(changes.snapshot())
        self.assertNotIn('secret', exported)
        self.assertNotIn('private', exported)
        self.assertIn('ValueError', exported)

    def test_successful_remove_and_install_have_distinct_events(self):
        changes.from_library('operation_completed', {'outcome':'removed', 'action':'remove', 'asset_id':'books'})
        changes.from_library('archive_activated', {'asset_id':'books'})
        self.assertEqual([e['kind'] for e in changes.snapshot()['events']], ['removed', 'installed'])

    def test_idle_is_status_not_a_completion_claim(self):
        changes.from_library('update_progress', {'phase':'idle'})
        feed = changes.snapshot()
        self.assertEqual(feed['events'], [])
        self.assertEqual(feed['activity']['updater']['kind'], 'idle')

    def test_notification_failure_does_not_interrupt_content(self):
        with patch.object(changes, 'record', side_effect=OSError('disk full')):
            changes.safe_record('installed')

    def test_invalid_events_and_percentages(self):
        with self.assertRaises(ValueError): changes.record('arbitrary')
        changes.record('downloading', percent=float('nan'))
        self.assertNotIn('percent', changes.snapshot()['events'][0])

    def test_failure_keeps_current_collection_without_exporting_exception_text(self):
        changes.from_library('update_progress', {'phase':'downloading', 'title':'Books'})
        changes.from_library('update_progress', {'phase':'error', 'reason':'private failure text'})
        event = changes.snapshot()['events'][-1]
        self.assertEqual(event['title'], 'Books')
        self.assertEqual(event['error_type'], 'UpdateError')

    def test_successful_download_reports_approval_and_queue(self):
        changes.from_library('operation_completed', {'outcome':'queued', 'action':'download', 'operation':'request'})
        self.assertEqual([e['kind'] for e in changes.snapshot()['events']], ['approved', 'queued'])

    def test_ha_event_actions_use_mapping_payloads(self):
        # HA rejects a template for the whole event_data dictionary at setup.
        import yaml
        root = Path(__file__).resolve().parents[1]
        package = yaml.safe_load((root/'deploy/home-assistant-collections.example.yaml').read_text(encoding='utf-8'))
        def check(node):
            if isinstance(node, dict):
                if 'event' in node and 'event_data' in node:
                    self.assertIsInstance(node['event_data'], dict)
                for value in node.values(): check(value)
            elif isinstance(node, list):
                for value in node: check(value)
        check(package['automation'])


if __name__ == '__main__':
    unittest.main()
