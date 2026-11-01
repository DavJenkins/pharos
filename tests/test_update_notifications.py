from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.services import collection_changes as feed
from tools import update_notifications as events


class UpdateNotifications(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        state=patch.object(feed,'STATE',Path(tmp.name)/'feed');state.start();self.addCleanup(state.stop)

    def test_pending_is_durable_and_deduplicated(self):
        value={'state':'newer_release','installation_supported':True,'channel':'stable','release':{'tag':'software-2026.11.01'}}
        events.available(value);events.available(value)
        snapshot=feed.snapshot();self.assertEqual(len(snapshot['events']),1)
        self.assertEqual(snapshot['events'][0]['action'],'software_update')
        self.assertEqual(snapshot['events'][0]['kind'],'suggested')
        events.available({'state':'unavailable'})
        self.assertEqual(feed.snapshot()['activity']['software_updates:stable']['kind'],'suggested')
        events.available({'state':'same','channel':'stable'})
        self.assertEqual(feed.snapshot()['activity']['software_updates:stable']['kind'],'idle')

    def test_bootstrap_is_not_an_installable_update(self):
        events.available({'state':'newer_release','installation_supported':False,'release':{'tag':'bootstrap-2026.11.01'}})
        self.assertEqual(feed.snapshot()['events'],[])

    def test_completed_and_rollback_outcomes(self):
        record={'id':'operation','release':'software-test','from_revision':'a'*40,'to_revision':'b'*40}
        for state in ['preparing','completed','completed','rolled_back']:
            events.transaction({**record,'state':state})
        changes=feed.snapshot()['events']
        self.assertEqual([c['kind'] for c in changes],['request_started','installed','failed'])
        self.assertIn('aaaaaaaaaaaa → bbbbbbbbbbbb',changes[1]['title'])
        self.assertEqual(changes[-1]['error_type'],'rolled_back')

    def test_notification_failure_does_not_break_transaction(self):
        with patch.object(feed,'safe_record',side_effect=OSError('offline storage')):
            events.transaction({'state':'completed','release':'test','id':'one'})

    def test_content_changes_and_new_editions_notify_once(self):
        asset={'id':'books','title':'Books'}
        result={'status':'changed','pending_change':True,'fingerprint':'one'}
        events.content(asset,result);events.content(asset,result)
        self.assertEqual(len(feed.snapshot()['events']),1)
        events.content(asset,{'status':'unchanged','pending_change':False,'edition_discovery':{'status':'available','candidate':{'edition':'2027','sha256':'new'}}})
        records=feed.snapshot()['events']
        self.assertEqual(len(records),2)
        self.assertEqual(records[-1]['action'],'content_update')
        self.assertIn('2027',records[-1]['title'])
