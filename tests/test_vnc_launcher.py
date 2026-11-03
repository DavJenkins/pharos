import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

LAUNCHER=Path(__file__).resolve().parents[1]/'deploy/vnc/launch_vnc.py'

class VncLauncherTests(unittest.TestCase):
    def test_launcher_waits_without_starting_a_desktop_or_changing_login(self):
        with patch('subprocess.check_output',return_value='[]'),patch('os.execv'):
            with self.assertRaises(SystemExit):namespace=runpy.run_path(str(LAUNCHER))
        # Load the helper while supplying an interface so the module completes.
        interface=[{'ifname':'eth0','addr_info':[{'family':'inet','local':'192.168.4.1'}]}]
        with patch('subprocess.check_output',return_value=json.dumps(interface)),patch('os.execv'):
            namespace=runpy.run_path(str(LAUNCHER))
        with patch('pathlib.Path.is_socket',side_effect=[False,False,True]),patch('time.sleep') as sleep:
            namespace['wait_for_desktop']('/run/user/1000','wayland-0')
        sleep.assert_called_once_with(5)

    def test_only_private_addresses_on_physical_interfaces_are_bound(self):
        interfaces=[
            {'ifname':'wlan0','addr_info':[{'family':'inet','local':'192.168.4.1'}]},
            {'ifname':'eth0','addr_info':[{'family':'inet','local':'10.1.2.3'},{'family':'inet','local':'8.8.8.8'}]},
            {'ifname':'docker0','addr_info':[{'family':'inet','local':'172.17.0.1'}]},
            {'ifname':'lo','addr_info':[{'family':'inet','local':'127.0.0.1'}]},
        ]
        with patch('subprocess.check_output',return_value=json.dumps(interfaces)),patch('os.execv') as launch:
            runpy.run_path(str(LAUNCHER))
        executable,args=launch.call_args.args
        self.assertEqual(executable,'/usr/bin/wayvnc')
        self.assertEqual(args[-2:],['10.1.2.3','192.168.4.1'])
        self.assertNotIn('0.0.0.0',args)
        self.assertNotIn('8.8.8.8',args)
        self.assertNotIn('172.17.0.1',args)

    def test_no_private_interface_does_not_expose_fallback_listener(self):
        with patch('subprocess.check_output',return_value='[]'),patch('os.execv') as launch:
            with self.assertRaises(SystemExit): runpy.run_path(str(LAUNCHER))
        launch.assert_not_called()
