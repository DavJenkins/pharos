from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.services import collection_changes as feed
from tools.check_os_updates import pending_packages,completed_transactions,report


class OSUpdateNotifications(unittest.TestCase):
    def test_cached_package_list(self):
        self.assertEqual(pending_packages('Listing...\nopenssl/stable 3.5 arm64 [upgradable from: 3.4]\n'),['openssl/stable 3.5'])

    def test_only_finished_transactions_and_no_commands_in_events(self):
        history='Start-Date: 2026-11-01  09:00:00\nCommandline: apt secret-command\nUpgrade: one:arm64 (1, 2), two:arm64 (1, 2)\nEnd-Date: 2026-11-01 09:01:00\n\nStart-Date: 2026-11-01 10:00:00\nInstall: pending:arm64 (1)\n'
        values=completed_transactions(history);self.assertEqual(len(values),1)
        self.assertIn('2 upgraded',values[0]['title']);self.assertNotIn('secret',str(values))
        with tempfile.TemporaryDirectory() as tmp,patch.object(feed,'STATE',Path(tmp)/'feed'):
            state=Path(tmp)/'monitor.json';report(['one 2'],values,state)
            self.assertEqual(len(feed.snapshot()['events']),1)
            later=[*values,{'id':'next','title':'OS packages updated: 1 upgraded'}]
            report([],later,state);report([],later,state)
            events=feed.snapshot()['events'];self.assertEqual([e['kind'] for e in events],['suggested','installed'])
