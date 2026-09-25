import unittest
from unittest.mock import patch
from app.services import network
from app.models.network import Network

def output(cmd, **kwargs):
    if cmd == ['iw','dev','wlan1','link']:
        return 'Connected to aa:bb:cc:dd:ee:ff\n\tSSID: Uplink\n\tsignal: -50 dBm'
    if cmd == ['iw','dev','wlan0','info']:
        return 'Interface wlan0\n\tssid DataArk\n\ttype AP'
    if cmd == ['nmcli','-g','GENERAL.STATE','device','show','wlan0']:
        return '100 (connected)'
    if cmd[:4] == ['ip','-4','-o','addr']:
        device = cmd[-1]
        address = {'eth0':'192.168.40.10','wlan1':'192.168.40.123','wlan0':'192.168.4.1'}[device]
        return f'2: {device} inet {address}/24 scope global {device}'
    if cmd[:4] == ['ip','route','show','default']:
        return 'default via 192.168.40.1 dev ' + cmd[-1]
    return ''

class ConcurrentNetworkTests(unittest.TestCase):
    def test_all_three_interfaces_active_without_ap_clients(self):
        with patch.object(network, 'run', side_effect=output), patch.object(network.Path,'read_text', return_value='up'):
            data = Network.model_validate(network.collect()).model_dump()
        self.assertTrue(data['ethernet']['connected'])
        self.assertTrue(data['wifi']['connected'])
        self.assertTrue(data['access_point']['active'])
        self.assertEqual(data['access_point']['client_count'],0)
        self.assertEqual(data['access_point']['ip'],'192.168.4.1')
        self.assertNotEqual(data['ethernet']['ip'],data['wifi']['ip'])

    def test_missing_ethernet_does_not_hide_wireless(self):
        with patch.object(network,'run',side_effect=output), patch.object(network.Path,'read_text',side_effect=FileNotFoundError):
            data=Network.model_validate(network.collect()).model_dump()
        self.assertIsNone(data['ethernet']['connected'])
        self.assertTrue(data['wifi']['connected'])
        self.assertTrue(data['access_point']['active'])

    def test_ap_configuration_is_not_proof_of_activity(self):
        def inactive(cmd, **kwargs):
            if cmd == ['nmcli','-g','GENERAL.STATE','device','show','wlan0']:
                return '30 (disconnected)'
            return output(cmd)
        with patch.object(network,'run',side_effect=inactive):
            self.assertFalse(network.access_point()['active'])

    def test_failed_wireless_probes_are_unknown(self):
        with patch.object(network,'run',return_value=''):
            self.assertIsNone(network.wifi()['connected'])
            self.assertIsNone(network.access_point()['active'])

    def test_disconnected_uplink_does_not_hide_ap(self):
        def disconnected(cmd, **kwargs):
            if cmd == ['iw','dev','wlan1','link']:
                return 'Not connected.'
            return output(cmd)
        with patch.object(network,'run',side_effect=disconnected), patch.object(network.Path,'read_text',return_value='up'):
            data=network.collect()
        self.assertTrue(data['ethernet']['connected'])
        self.assertFalse(data['wifi']['connected'])
        self.assertTrue(data['access_point']['active'])

if __name__ == '__main__':
    unittest.main()
