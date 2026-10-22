import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
from app.services import library_events as events

class LibraryEventTests(unittest.TestCase):
    def test_only_approved_fields_are_logged(self):
        with patch.object(events.events,'info') as log:
            events.emit('sample',action='remove',password='secret',authorization='secret',body={'password':'secret'})
        fields=log.call_args.kwargs
        self.assertEqual(fields,{'source':'library','action':'remove'})

    def test_debug_controls_detailed_stages(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(events,'DEBUG_FLAG',Path(tmp)/'debug'),patch.object(events.events,'info') as log:
            events.phase('checking file')
            log.assert_not_called()
            events.DEBUG_FLAG.touch()
            events.phase('checking file')
            self.assertEqual(log.call_args.args[0],'library_stage')

    def test_success_records_bytes_elapsed_and_correlation(self):
        @events.tracked('remove')
        def operation(payload):
            events.emit('sample')
            return {'ok':True}
        with patch.object(events.events,'info') as log:
            self.assertEqual(operation({'bytes':100,'password':'not logged'}),{'ok':True})
        records=[(c.args[0],c.kwargs) for c in log.call_args_list]
        completed=records[-1][1]
        self.assertEqual(completed['bytes_freed'],100)
        self.assertGreaterEqual(completed['elapsed_seconds'],0)
        self.assertEqual(len({v['operation'] for _,v in records}),1)
        self.assertNotIn('not logged',str(records))

    def test_failure_records_reason_and_reraises(self):
        @events.tracked('remove')
        def operation(payload):
            raise ValueError('File size changed')
        with patch.object(events.events,'info') as log,self.assertRaises(ValueError):
            operation({})
        self.assertEqual(log.call_args.args[0],'library_operation_failed')
        self.assertEqual(log.call_args.kwargs['reason'],'File size changed')

    def test_log_failure_does_not_interrupt_operation(self):
        with patch.object(events.events,'info',side_effect=OSError('disk full')):
            events.emit('sample')
