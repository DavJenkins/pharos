import json
import subprocess
import unittest
from unittest.mock import patch
from tools import pass_through_helper as helper
from deploy import install_pass_through as installer
from app.services import pass_through

MAC='aa:bb:cc:dd:ee:02'
ADDRESS='192.168.4.22'
def table(enabled=False):
    return json.dumps({'nftables':[{'set':{'name':'clients','elem':[{'elem':{'val':MAC,'timeout':21600}}] if enabled else []}},
                                 {'set':{'name':'addresses','elem':[ADDRESS] if enabled else []}}]})
NEIGHBORS=json.dumps([{'dst':ADDRESS,'dev':'wlan0','lladdr':MAC}])

class PassThroughTests(unittest.TestCase):
    def test_invalid_input_cannot_reach_commands(self):
        for data in ({'address':'192.168.40.2'},{'address':'192.168.4.1'},
                     {'address':'192.168.4.22; flush ruleset'},
                     {'address':ADDRESS,'enabled':'yes'}, {'address':ADDRESS,'command':'flush'}):
            with self.subTest(data=data),patch.object(helper,'run') as run:
                with self.assertRaises(ValueError): helper.execute(data)
                run.assert_not_called()

    def test_off_default_and_atomic_enable(self):
        with patch.object(helper,'run',side_effect=[table(),NEIGHBORS]) as run:
            self.assertFalse(helper.execute({'address':ADDRESS})['enabled'])
            self.assertEqual(run.call_count,2)
        with patch.object(helper,'run',side_effect=[table(),NEIGHBORS,'']) as run:
            self.assertTrue(helper.execute({'address':ADDRESS,'enabled':True})['enabled'])
            script=run.call_args.kwargs['input']
            self.assertIn('add element inet dataark_forward clients { '+MAC+' }',script)
            self.assertIn('add element inet dataark_forward addresses { '+ADDRESS+' }',script)
            self.assertEqual(run.call_args.args[0],[helper.NFT,'-f','-'])

    def test_disable_and_repeated_enable(self):
        with patch.object(helper,'run',side_effect=[table(True),NEIGHBORS,'']) as run:
            self.assertFalse(helper.execute({'address':ADDRESS,'enabled':False})['enabled'])
            self.assertEqual(run.call_args.kwargs['input'].count('delete element'),2)
        with patch.object(helper,'run',side_effect=[table(True),NEIGHBORS]) as run:
            self.assertTrue(helper.execute({'address':ADDRESS,'enabled':True})['enabled'])
            self.assertEqual(run.call_count,2)

    def test_different_device_at_same_ip_is_not_enabled(self):
        neighbors=NEIGHBORS.replace(MAC,'aa:bb:cc:dd:ee:03')
        with patch.object(helper,'run',side_effect=[table(True),neighbors]):
            self.assertFalse(helper.execute({'address':ADDRESS})['enabled'])
        with patch.object(helper,'run',side_effect=[table(),'[]']):
            with self.assertRaises(ValueError): helper.execute({'address':ADDRESS,'enabled':True})

    def test_helper_failure_is_not_false_success(self):
        with patch.object(pass_through.subprocess,'run',side_effect=subprocess.TimeoutExpired('sudo',12)):
            with self.assertRaises(RuntimeError): pass_through.control(ADDRESS,True)

    def test_policy_blocks_both_directions_and_preserves_local_kiwix(self):
        self.assertIn('type filter hook forward priority -10',installer.RULES)
        self.assertNotIn('hook input',installer.RULES)
        self.assertNotIn('hook output',installer.RULES)
        self.assertIn('iifname "wlan0" reject',installer.RULES)
        self.assertIn('oifname "wlan0" reject',installer.RULES)
        self.assertIn('ct status dnat tcp dport 8080 return',installer.RULES)
        self.assertIn('ct status dnat tcp sport 8080 return',installer.RULES)
        self.assertIn('timeout 6h',installer.RULES)
        self.assertNotIn('elements =',installer.RULES)

if __name__=='__main__': unittest.main()
