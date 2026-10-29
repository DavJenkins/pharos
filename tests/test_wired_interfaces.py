import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from tools import wired_interfaces as wired, network_helper as helper
from app.services import network


class WiredTests(unittest.TestCase):
    def test_inventory_keeps_both_adapters_and_prefers_lower_route_metric(self):
        def item(name):return {'interface':name,'enabled':True,'connected':True,'carrier':True,'state':'up','ip':'192.0.2.1','gateway':'192.0.2.254'}
        routes=[{'dev':'enp1s0','metric':200},{'dev':'enp2s0','metric':100}]
        def run(args):
            return json.dumps(routes) if args==['ip','-j','route','show','default'] else '2: enp1s0 inet 192.0.2.1/24 scope global'
        with patch.object(network,'wired_devices',return_value=['enp1s0','enp2s0']),patch.object(network,'ethernet',side_effect=item),patch.object(network,'run',side_effect=run),patch.object(network,'wifi',return_value={}),patch.object(network,'access_point',return_value={}):
            result=network.collect()
        self.assertEqual(len(result['ethernet_interfaces']),2)
        self.assertEqual(result['ethernet']['interface'],'enp2s0')
        self.assertEqual(result['ethernet_interfaces'][0]['addresses'],['192.0.2.1/24'])

    def test_ambiguous_legacy_request_never_changes_a_port(self):
        with patch.object(helper,'wired_devices',return_value=['eth0','enx123']),patch.object(helper,'platform_settings',return_value={}),patch.object(helper,'ap_details'),patch.object(helper,'nm') as nm:
            with self.assertRaisesRegex(helper.NetworkError,'ambiguous'):helper.execute({'action':'ethernet','enabled':False})
            nm.assert_not_called()

    def test_selected_adapter_is_bound_to_current_permanent_mac(self):
        request={'action':'ethernet','enabled':False,'interface':'enx123','expected_mac':'aa:bb:cc:dd:ee:02'}
        with patch.object(helper,'wired_devices',return_value=['eth0','enx123']),patch.object(helper,'platform_settings',return_value={}),patch.object(helper,'ap_details'),patch.object(helper,'permanent_mac',return_value=request['expected_mac']),patch.object(helper,'protect_access') as guard,patch.object(helper,'nm') as nm:
            helper.execute(request)
            guard.assert_called_once_with(request,'enx123')
            nm.assert_called_once_with('device','disconnect','enx123',timeout=15)
        with patch.object(helper,'wired_devices',return_value=['eth0','enx123']),patch.object(helper,'platform_settings',return_value={}),patch.object(helper,'ap_details'),patch.object(helper,'permanent_mac',return_value='aa:bb:cc:dd:ee:03'),patch.object(helper,'nm') as nm:
            with self.assertRaisesRegex(helper.NetworkError,'hardware changed'):helper.execute(request)
            nm.assert_not_called()

    def test_interface_injection_or_missing_identity_is_rejected(self):
        for name in ['eth0;reboot','../eth0','--help','wlan0']:
            request={'action':'ethernet','enabled':False,'interface':name}
            with self.subTest(name=name),self.assertRaises(ValueError):helper.validate(request)

    def test_bridge_and_bond_dependencies_are_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'br0/brif').mkdir(parents=True);(root/'br0/brif/bond0').touch()
            (root/'bond0').mkdir();(root/'bond0/lower/enp1s0').parent.mkdir(parents=True)
            (root/'bond0/lower_enp1s0').touch();(root/'bond0/lower_enp2s0').touch()
            with patch.object(wired,'NET',root):
                self.assertEqual(wired.dependencies('br0'),{'br0','bond0','enp1s0','enp2s0'})

    def test_receiving_and_return_ports_both_protected(self):
        def nm(*args,**kwargs):return {'wlan0':'192.168.4.1/24','wlan1':'','enp1s0':'192.0.2.1/24','enp2s0':'192.0.2.2/24'}[args[-1]]
        sockets=SimpleNamespace(stdout='0 0 192.0.2.1:443 192.0.2.10:50000')
        route=SimpleNamespace(stdout='[{"dev":"enp2s0"}]')
        with patch.object(helper,'wired_devices',return_value=['enp1s0','enp2s0']),patch.object(helper,'nm',side_effect=nm),patch.object(helper.subprocess,'run',side_effect=[sockets,route]):
            self.assertEqual(helper.access_interfaces({'peer':'192.0.2.10'}),['enp1s0','enp2s0'])


if __name__=='__main__':unittest.main()
