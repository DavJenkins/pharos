import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import wifi_role_manager as roles
from tools import wifi_interfaces
from tools import network_helper
from app.services import network

BUILTIN={'id':'02:00:00:00:00:01','interface':'wlan0','builtin':True,'ap_capable':True}
USB={'id':'02:00:00:00:00:02','interface':'wlan1','builtin':False,'ap_capable':True}

class SelectionTests(unittest.TestCase):
    def test_hardware_identity_survives_interface_renumbering(self):
        rows=[dict(BUILTIN,interface='wlan2'),dict(USB,interface='wlan0')]
        ap,upstream,fallback=roles.choose(rows,{'hotspot_adapter':USB['id']})
        self.assertEqual(ap['interface'],'wlan0')
        self.assertEqual(upstream['interface'],'wlan2')
        self.assertFalse(fallback)

    def test_missing_usb_uses_builtin_without_erasing_preference(self):
        preference={'hotspot_adapter':USB['id']}
        ap,upstream,fallback=roles.choose([BUILTIN],preference)
        self.assertEqual(ap,BUILTIN)
        self.assertIsNone(upstream)
        self.assertTrue(fallback)
        self.assertEqual(preference['hotspot_adapter'],USB['id'])

    def test_no_capable_adapter_fails_before_changes(self):
        with self.assertRaises(ValueError):
            roles.choose([dict(USB,ap_capable=False)],{})

    def test_runtime_assignment_rejects_command_and_duplicate_interfaces(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'runtime.json'
            with patch.object(wifi_interfaces,'RUNTIME',path):
                for data,expected in [({'hotspot':'wlan1','upstream':'wlan0'},('wlan1','wlan0')),
                                      ({'hotspot':'wlan2','upstream':''},('wlan2','')),
                                      ({'hotspot':'wlan1;id','upstream':'wlan0'},('wlan0','wlan1')),
                                      ({'hotspot':'wlan0','upstream':'wlan0'},('wlan0','wlan1'))]:
                    path.write_text(json.dumps(data))
                    self.assertEqual(wifi_interfaces.interfaces(),expected)

class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        for name in ('PENDING','PREFERENCE','RUNTIME'):
            p=patch.object(roles,name,self.base/(name+'.json'));p.start();self.addCleanup(p.stop)

    def test_rollback_timer_is_armed_before_switch(self):
        calls=[]
        saved={'profiles':[],'active':[],'files':{},'preference':{},'runtime':{},'deadline':100}
        with patch.object(roles,'inventory',return_value=[BUILTIN,USB]),patch.object(roles,'nm',return_value='wlan0'),patch.object(roles,'snapshot',return_value=saved),patch.object(roles,'run',side_effect=lambda *a,**kw:calls.append(a)),patch.object(roles,'switch',side_effect=lambda *a:calls.append(('switch',))),patch.object(roles,'status',return_value={'ok':True}):
            roles.apply(USB['id'])
        timer=next(i for i,c in enumerate(calls) if c[0]=='/usr/bin/systemd-run')
        switch=next(i for i,c in enumerate(calls) if c[0]=='switch')
        self.assertLess(timer,switch)
        self.assertEqual(json.loads(roles.PREFERENCE.read_text())['hotspot_adapter'],USB['id'])

    def test_activation_failure_restores_snapshot(self):
        with patch.object(roles,'inventory',return_value=[BUILTIN,USB]),patch.object(roles,'nm',return_value='wlan0'),patch.object(roles,'snapshot',return_value={'deadline':100}),patch.object(roles,'run'),patch.object(roles,'switch',side_effect=ValueError('AP failed')),patch.object(roles,'rollback') as rollback:
            with self.assertRaisesRegex(ValueError,'AP failed'):roles.apply(USB['id'])
            rollback.assert_called_once()

    def test_confirmation_after_deadline_rolls_back(self):
        roles.write(roles.PENDING,{'deadline':1})
        with patch.object(roles,'rollback') as rollback:
            with self.assertRaisesRegex(ValueError,'expired'):roles.confirm()
            rollback.assert_called_once()

    def test_confirmation_requires_active_hotspot(self):
        roles.write(roles.PENDING,{'deadline':10**12})
        with patch.object(roles,'nm',side_effect=['wlan1','30 (disconnected)']):
            with self.assertRaisesRegex(ValueError,'not active'):roles.confirm()
        self.assertTrue(roles.PENDING.exists())

    def test_rollback_restores_binding_rules_and_preference(self):
        firewall=self.base/'firewall';firewall.write_text('new')
        saved={'profiles':[{'uuid':'uuid','fields':{'connection.interface-name':'wlan0','802-11-wireless.mac-address':''}}],
               'active':[['uuid','wlan0']], 'files':{str(firewall):'old'},
               'preference':{'hotspot_adapter':BUILTIN['id']},'runtime':{'hotspot':'wlan0','upstream':'wlan1'}}
        roles.write(roles.PENDING,saved)
        with patch.object(roles,'inventory',return_value=[BUILTIN,USB]),patch.object(roles,'nm') as nm,patch.object(roles,'run'):
            roles.rollback()
        self.assertFalse(roles.PENDING.exists())
        self.assertEqual(firewall.read_text(),'old')
        nm.assert_any_call('connection','modify','uuid','uuid','connection.interface-name','wlan0','802-11-wireless.mac-address','')
        self.assertEqual(json.loads(roles.RUNTIME.read_text()),saved['runtime'])

    def test_default_status_and_guards_follow_swapped_roles(self):
        calls=[]
        with patch.object(network,'interfaces',return_value=('wlan1','wlan0')),patch.object(network,'run',side_effect=lambda args,**kw:calls.append(args) or ''):
            self.assertEqual(network.wifi()['interface'],'wlan0')
            self.assertEqual(network.access_point()['interface'],'wlan1')
        self.assertIn(['iw','dev','wlan0','link'],calls)
        self.assertIn(['iw','dev','wlan1','station','dump'],calls)
        with patch.object(network_helper,'interfaces',return_value=('wlan1','wlan0')),patch.object(network_helper,'ap_details'),patch.object(network_helper,'protect_access'),patch.object(network_helper,'nm') as nm:
            network_helper.execute({'action':'uplink','enabled':False})
            nm.assert_called_once_with('device','disconnect','wlan0',timeout=15)

    def test_untrusted_adapter_values_rejected(self):
        for adapter in ['wlan1',';reboot','AA:BB:CC:DD:EE:FF',None]:
            with self.assertRaises(ValueError):network_helper.validate({'action':'assign','adapter':adapter})

if __name__=='__main__':unittest.main()
