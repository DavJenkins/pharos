import asyncio
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from app.services import network_admin
from app.routers import network_admin as routes
from tools import network_helper as helper

class Request:
    def __init__(self, body=b'{}', headers=None):
        self.headers = headers if headers is not None else {'authorization': 'Basic test', 'content-type': 'application/json'}
        self.body = body
    async def stream(self):
        yield self.body

class AuthenticationTests(unittest.TestCase):
    def test_password_and_fail_closed(self):
        password = 'sample-admin-password'
        salt = b'0123456789abcdef'
        record = json.dumps({'salt': salt.hex(), 'hash': hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 300000).hex()})
        def header(value):
            return 'Basic ' + base64.b64encode(('admin:' + value).encode()).decode()
        with patch.object(Path, 'read_text', return_value=record):
            self.assertTrue(network_admin.authorized(header(password)))
            self.assertFalse(network_admin.authorized(header('wrong')))
            self.assertFalse(network_admin.authorized('not-basic'))
        with patch.object(Path, 'read_text', side_effect=FileNotFoundError):
            self.assertFalse(network_admin.authorized(header(password)))

    def test_secret_uses_stdin_only(self):
        with patch.object(network_admin.subprocess, 'run', return_value=SimpleNamespace(stdout='{"ok":true}')) as run:
            self.assertTrue(network_admin.invoke({'action': 'connect', 'password': 'private-value'})['ok'])
        self.assertNotIn('private-value', str(run.call_args.args))
        self.assertIn('private-value', run.call_args.kwargs['input'])
        self.assertEqual(run.call_args.args[0], ['/usr/bin/sudo', '-n', '--', '/usr/local/libexec/dataark-network'])

class RouteTests(unittest.TestCase):
    def test_unauthenticated_requests_never_invoke_helper(self):
        with patch.object(routes, 'authorized', return_value=False), patch.object(routes, 'invoke') as invoke:
            with self.assertRaises(HTTPException) as error:
                asyncio.run(routes.network_action('connect', Request()))
            self.assertEqual(error.exception.status_code, 401)
            invoke.assert_not_called()

    def test_authenticated_dispatch(self):
        with patch.object(routes, 'authorized', return_value=True), patch.object(routes, 'invoke', return_value={'ok': True, 'networks': ['one']}) as invoke:
            self.assertTrue(asyncio.run(routes.network_action('scan', Request()))['ok'])
            invoke.assert_called_once_with({'action': 'scan'})

    def test_rejects_bad_and_oversize_requests(self):
        for body, expected in [(b'[]', 400), (b'{', 400), (b'{"action":"rename"}', 400), (b' ' * 4097, 413)]:
            with self.subTest(body=body[:30]), patch.object(routes, 'authorized', return_value=True), patch.object(routes, 'invoke') as invoke:
                with self.assertRaises(HTTPException) as error:
                    asyncio.run(routes.network_action('connect', Request(body)))
                self.assertEqual(error.exception.status_code, expected)
                invoke.assert_not_called()
        with patch.object(routes, 'authorized', return_value=True):
            with self.assertRaises(HTTPException) as error:
                asyncio.run(routes.network_action('rename', Request(headers={'content-type': 'application/x-www-form-urlencoded'})))
            self.assertEqual(error.exception.status_code, 415)

class HelperTests(unittest.TestCase):
    def test_invalid_input_never_reaches_nmcli(self):
        for data in [
            {'action':'other'}, {'action':'scan','command':'id'},
            {'action':'rename','ssid':'é' * 17}, {'action':'rename','ssid':'bad\nssid'},
            {'action':'connect','ssid':'x','security':'wpa-psk','password':'short'},
            {'action':'connect','ssid':'x','security':'enterprise','password':'12345678'},
        ]:
            with self.subTest(data=data), patch.object(helper, 'nm') as nm:
                with self.assertRaises(ValueError):
                    helper.execute(data)
                nm.assert_not_called()

    def test_scan_uses_wlan1_and_preserves_names(self):
        with patch.object(helper, 'ap_details', return_value='DataArk'), patch.object(helper, 'nm', return_value='DataArk\nA:B\\C\nA:B\\C\nOther\n') as nm:
            result = helper.execute({'action':'scan'})
        self.assertEqual(result['networks'], ['A:B\\C', 'Other'])
        self.assertIn('wlan1', nm.call_args.args)
        self.assertNotIn('wlan0', nm.call_args.args)

    def test_ap_profile_must_match_device_and_mode(self):
        with patch.object(helper, 'nm', side_effect=['infrastructure', 'wlan0']):
            with self.assertRaises(helper.NetworkError):
                helper.ap_details()

    def test_ap_rollback(self):
        calls = []
        def nm(*args, **kwargs):
            calls.append(args)
            if len(calls) == 2:
                raise helper.NetworkError('failure')
            return ''
        with patch.object(helper, 'ap_details', return_value='Old AP'), patch.object(helper, 'nm', side_effect=nm):
            with self.assertRaisesRegex(helper.NetworkError, 'restored'):
                helper.execute({'action':'rename','ssid':'New AP'})
        self.assertEqual(calls[2], ('connection', 'modify', 'id', 'DataArk', '802-11-wireless.ssid', 'Old AP'))
        self.assertEqual(calls[3][-2:], ('ifname','wlan0'))

    def test_connect_uses_private_file_and_fixed_interface(self):
        calls = []
        password = 'never-in-process-args'
        def nm(*args, **kwargs):
            calls.append(args)
            self.assertNotIn(password, args)
            if 'passwd-file' in args:
                path = Path(args[args.index('passwd-file') + 1])
                self.assertIn(password, path.read_text())
            return ''
        temporary = tempfile.TemporaryDirectory
        with patch.object(helper, 'ap_details', return_value='DataArk'), patch.object(helper, 'nm', side_effect=nm), patch.object(helper.tempfile, 'TemporaryDirectory', side_effect=lambda **kw: temporary()):
            result = helper.execute({'action':'connect','ssid':'Cafe; $(touch x)', 'security':'wpa-psk','password':password})
        self.assertTrue(result['ok'])
        activate = next(call for call in calls if call[:2] == ('connection','up'))
        self.assertEqual(activate[4:6], ('ifname','wlan1'))
        self.assertFalse(Path(activate[-1]).exists())

    def test_connect_failure_restores_previous_uuid(self):
        previous = '11111111-1111-1111-1111-111111111111'
        calls = []
        def nm(*args, **kwargs):
            calls.append(args)
            if args[:2] == ('-g', 'GENERAL.CON-UUID'):
                return previous
            if args[:2] == ('connection', 'up') and previous not in args:
                raise helper.NetworkError('failure')
            return ''
        temporary = tempfile.TemporaryDirectory
        with patch.object(helper, 'ap_details', return_value='DataArk'), patch.object(helper, 'nm', side_effect=nm), patch.object(helper.tempfile, 'TemporaryDirectory', side_effect=lambda **kw: temporary()):
            with self.assertRaisesRegex(helper.NetworkError, 'restored'):
                helper.execute({'action':'connect','ssid':'Other','security':'open','password':''})
        self.assertIn(('connection','up','uuid',previous,'ifname','wlan1'), calls)
        self.assertTrue(any(call[:2] == ('connection','delete') for call in calls))

if __name__ == '__main__':
    unittest.main()
