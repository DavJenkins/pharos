import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from deploy import bootstrap_platform as p, bootstrap_stock_pi as b
from tools import wifi_interfaces as roles
from tools import platform_tools


class PlatformTests(unittest.TestCase):
    def config(self,name='debian13-amd64-lan'):
        c=json.loads((Path(__file__).resolve().parents[1]/'config/stock-pi.json').read_text())
        return p.configure(c,name)

    def facts(self,arch='x86_64'):
        return {'architecture':arch,'os':{'id':'debian','version':'13'},'raspberry_pi_os':False,
                'systemd':True,'network_manager':True,'machine_id_sha256':'a'*64,
                'tools':{k:True for k in ('ip','nmcli','ethtool','iw')},
                'interfaces':[{'name':'enp3s0','kind':'ethernet','permanent_mac':'aa:bb:cc:dd:ee:01','hotspot_capable':None,'state':'UP','addresses':['192.0.2.10']}],
                'default_routes':[{'interface':'enp3s0','metric':100}]}

    def test_three_profiles_and_architecture_correct_container_pins(self):
        for name in (p.DEFAULT,'debian13-arm64-lan','debian13-amd64-lan'):
            c=self.config(name);b.validate(c)
            self.assertEqual(c['kiwix_image'],p.profile(name)['kiwix_image'])
        self.assertNotEqual(self.config()['kiwix_image'],self.config(p.DEFAULT)['kiwix_image'])
        bad=self.config();bad['baseline']['architecture']='aarch64'
        with self.assertRaises(ValueError):b.validate(bad)
        bad=self.config();bad['kiwix_image']=self.config(p.DEFAULT)['kiwix_image']
        with self.assertRaises(ValueError):b.validate(bad)
        with self.assertRaises(ValueError):p.profile('../escape')

    def test_lan_proposes_real_names_without_assuming_eth0_or_wlan0(self):
        plan=p.proposal(self.config(),self.facts())
        self.assertEqual(plan['issues'],[])
        self.assertEqual(plan['roles']['ethernet'],'enp3s0')
        self.assertEqual(plan['roles']['identities']['ethernet'],'aa:bb:cc:dd:ee:01')
        self.assertIsNone(plan['roles']['hotspot'])

    def test_dhcp_and_link_state_do_not_invalidate_hardware_review(self):
        facts=self.facts();initial=p.proposal(self.config(),facts)['plan_id']
        facts['interfaces'][0].update(state='DOWN',addresses=['192.0.2.20'])
        self.assertEqual(initial,p.proposal(self.config(),facts)['plan_id'])
        facts['interfaces'][0]['permanent_mac']='aa:bb:cc:dd:ee:02'
        self.assertNotEqual(initial,p.proposal(self.config(),facts)['plan_id'])
        facts=self.facts();facts['machine_id_sha256']='b'*64
        self.assertNotEqual(initial,p.proposal(self.config(),facts)['plan_id'])

    def test_unsupported_baseline_and_missing_discovery_dependencies_block(self):
        facts=self.facts();facts['os']['id']='ubuntu'
        self.assertTrue(p.proposal(self.config(),facts)['issues'])
        facts=self.facts();facts['tools']['ethtool']=False
        self.assertTrue(p.proposal(self.config(),facts)['issues'])
        facts=self.facts();facts['network_manager']=False
        self.assertTrue(p.proposal(self.config(),facts)['issues'])

    def test_hotspot_requires_capability_identity_and_separate_upstream(self):
        c=self.config(p.DEFAULT);facts=self.facts('aarch64');facts['raspberry_pi_os']=True
        radio={'name':'wlan0','kind':'wifi','permanent_mac':'aa:bb:cc:dd:ee:02','hotspot_capable':True,'state':'UP','addresses':[]}
        facts['interfaces'].append(radio)
        self.assertFalse(p.proposal(c,facts)['issues'])
        radio['hotspot_capable']=None
        self.assertTrue(p.proposal(c,facts)['issues'])
        radio['hotspot_capable']=True;facts['default_routes'].append({'interface':'wlan0','metric':50})
        self.assertTrue(any('default route' in issue for issue in p.proposal(c,facts)['issues']))

    def test_generic_network_phase_performs_no_network_commands(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(b,'run') as run:
            i=b.Installer(self.config(),Path(tmp),{},Path(tmp)/'state.json')
            with patch.object(i,'script') as script:i.network();script.assert_not_called()
            run.assert_not_called()

    def test_lan_without_radios_is_valid_public_network_response(self):
        from app.services import network
        from app.models.network import Network
        with patch.object(network,'interfaces',return_value=('','')),patch.object(network,'ethernet_interface',return_value=''),patch.object(network,'run') as run:
            response=Network.model_validate(network.collect())
            self.assertEqual(response.access_point.state,'not_configured')
            self.assertEqual(response.wifi.state,'not_configured')
            run.assert_not_called()

    def test_permanent_identity_resolves_renamed_ethernet_interface(self):
        from types import SimpleNamespace
        settings={'roles':{'ethernet':'old0','identities':{'ethernet':'aa:bb:cc:dd:ee:01'}}}
        def query(args,**kwargs):
            return SimpleNamespace(returncode=0 if args[-1]=='enp3s0' else 1,stdout='Permanent address: aa:bb:cc:dd:ee:01')
        with patch.object(roles.Path,'iterdir',return_value=iter([Path('/sys/class/net/enp3s0')])),patch.object(roles.subprocess,'run',side_effect=query):
            self.assertEqual(roles.role_interface(settings,'ethernet'),'enp3s0')

    def test_foreign_elf_is_identified_without_running_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'pmtiles';data=bytearray(20);data[:6]=b'\x7fELF\x02\x01'
            for machine,expected in [(62,'x86_64'),(183,'aarch64'),(3,'unsupported')]:
                data[18:20]=machine.to_bytes(2,'little');binary.write_bytes(data)
                self.assertEqual(p.elf_architecture(binary),expected)

    def test_verified_native_cache_needs_no_network_or_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'pmtiles-x86_64';data=bytearray(20);data[:6]=b'\x7fELF\x02\x01';data[18:20]=(62).to_bytes(2,'little');binary.write_bytes(data)
            spec=p.profile('debian13-amd64-lan');spec['pmtiles']['binary_sha256']=hashlib.sha256(data).hexdigest()
            with patch.object(platform_tools,'urlopen') as download:
                self.assertEqual(platform_tools.pmtiles(spec,Path(tmp),Path(tmp)/'absent'),binary)
                download.assert_not_called()

    def test_corrupt_platform_state_disables_network_mutations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'platform.json';path.write_text('{broken')
            with patch.object(roles,'PLATFORM',path):
                self.assertTrue(roles.platform_settings()['configuration_error'])
                self.assertEqual(roles.ethernet_interface(),'')
                self.assertEqual(roles.interfaces(),('',''))

    def test_lan_control_rejects_mutation_before_any_nmcli_call(self):
        from tools import network_helper
        with patch.object(network_helper,'platform_settings',return_value={'network_mode':'lan'}),patch.object(network_helper,'nm') as nm:
            with self.assertRaisesRegex(network_helper.NetworkError,'preserves'):
                network_helper.execute({'action':'ethernet','enabled':False})
            nm.assert_not_called()

    def test_aliases_and_profile_data_cannot_select_shell_commands(self):
        self.assertEqual(p.architecture('AMD64'),'x86_64')
        self.assertEqual(p.architecture('arm64'),'aarch64')
        self.assertEqual(p.architecture('armv7l'),'unsupported')
        commands=[];adapter=p.DebianAdapter(lambda args:commands.append(args))
        adapter.packages(['python3'])
        self.assertEqual(commands,[['apt-get','update'],['apt-get','install','-y','--no-install-recommends','python3']])


if __name__=='__main__':unittest.main()
