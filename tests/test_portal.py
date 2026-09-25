import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from app.main import app
from app.routers import portal
from deploy import install_portal as installer

class TestClient:
    """Minimal ASGI client: exercise routing without adding httpx to Pi dependencies."""
    def __init__(self, application, **kwargs):
        self.app = application

    def request(self, method, path, headers):
        async def execute():
            messages = []
            scope = {'type':'http','asgi':{'version':'3.0'},'http_version':'1.1',
                     'method':method,'scheme':'http','path':path,'raw_path':path.encode(),
                     'root_path':'','query_string':b'', 'server':('testserver',80),
                     'client':('127.0.0.1',12345),
                     'headers':[(key.lower().encode(),value.encode()) for key,value in headers.items()]}
            async def receive(): return {'type':'http.request','body':b'','more_body':False}
            async def send(message): messages.append(message)
            await self.app(scope,receive,send)
            start = next(item for item in messages if item['type']=='http.response.start')
            body = b''.join(item.get('body',b'') for item in messages if item['type']=='http.response.body')
            return SimpleNamespace(status_code=start['status'],
                headers={key.decode():value.decode() for key,value in start['headers']},
                json=lambda:json.loads(body))
        return asyncio.run(execute())

    def get(self,path,headers): return self.request('GET',path,headers)
    def post(self,path,headers): return self.request('POST',path,headers)


AP = {'X-DataArk-Peer': '192.168.4.22'}

class PortalTests(unittest.TestCase):
    def setUp(self):
        self.allowed = {}
        def control(address, enabled=None):
            if enabled is not None: self.allowed[address] = enabled
            return self.allowed.get(address,False)
        control_patch = patch.object(portal,'control',side_effect=control)
        online_patch = patch.object(portal,'upstream_available',return_value=True)
        control_patch.start(); online_patch.start()
        self.addCleanup(control_patch.stop); self.addCleanup(online_patch.stop)
        self.client = TestClient(app, follow_redirects=False)

    def test_upstream_status_available_without_ap_membership(self):
        for online in (True, False):
            with patch.object(portal,'upstream_available',return_value=online):
                result=self.client.get('/portal/upstream',headers={})
            self.assertEqual(result.status_code,200)
            self.assertEqual(result.json(),{'online':online})
            self.assertEqual(result.headers['cache-control'],'no-store')

    def test_new_client_redirects_without_upstream_request(self):
        with patch.object(portal, 'upstream_probe') as upstream:
            response = self.client.get('/portal/probe/generate_204', headers=AP)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['location'], 'http://192.168.4.1/?portal=1')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        upstream.assert_not_called()

    def test_lan_and_missing_trusted_headers_are_rejected(self):
        for headers in ({}, dict(AP, **{'X-DataArk-Peer':'192.168.40.22'}),
                        {'X-DataArk-Server':'192.168.4.1', 'X-Forwarded-For':'192.168.4.22'},
                        dict(AP, **{'X-DataArk-Peer':'garbage'})):
            self.assertEqual(self.client.get('/portal/state',headers=headers).status_code,404)

    def test_continue_requires_same_origin_and_is_client_specific(self):
        self.assertEqual(self.client.post('/portal/continue',headers=AP).status_code,403)
        self.assertEqual(self.client.get('/portal/continue',headers=AP).status_code,405)
        headers = dict(AP, Origin='http://192.168.4.1')
        self.assertEqual(self.client.post('/portal/continue',headers=headers).status_code,204)
        self.assertTrue(self.client.get('/portal/state',headers=AP).json()['enabled'])
        self.assertFalse(self.client.get('/portal/state',headers=dict(AP, **{'X-DataArk-Peer':'192.168.4.23'})).json()['enabled'])

    def test_acknowledged_client_checks_actual_upstream(self):
        self.client.post('/portal/continue',headers=dict(AP, Origin='http://192.168.4.1'))
        with patch.object(portal,'upstream_probe',return_value=(204,b'','text/plain')):
            self.assertEqual(self.client.get('/portal/probe/generate_204',headers=AP).status_code,204)
        with patch.object(portal,'upstream_probe',side_effect=OSError('offline')):
            self.assertEqual(self.client.get('/portal/probe/generate_204',headers=AP).status_code,302)
        self.assertEqual(self.client.get('/portal/probe/http://evil.example',headers=AP).status_code,404)

    def test_control_failure_is_not_reported_as_off(self):
        with patch.object(portal,'control',side_effect=RuntimeError('unavailable')):
            self.assertEqual(self.client.get('/portal/state',headers=AP).status_code,503)
            self.assertEqual(self.client.get('/portal/probe/generate_204',headers=AP).status_code,302)

    def test_toggle_off_and_offline_enable_rejection(self):
        headers=dict(AP,Origin='http://192.168.4.1')
        self.assertEqual(self.client.post('/portal/pass-through/on',headers=headers).status_code,204)
        self.assertTrue(self.client.get('/portal/state',headers=AP).json()['enabled'])
        with patch.object(portal,'upstream_available',return_value=False):
            self.assertEqual(self.client.post('/portal/pass-through/off',headers=headers).status_code,204)
            self.assertEqual(self.client.post('/portal/pass-through/on',headers=headers).status_code,409)
        self.assertFalse(self.client.get('/portal/state',headers=AP).json()['enabled'])

    def test_probe_forwards_only_bounded_expected_response(self):
        class Result:
            status = 200
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,limit):
                self.limit = limit
                return b'Microsoft Connect Test'
        result = Result()
        with patch.object(portal,'build_opener') as opener:
            opener.return_value.open.return_value = result
            self.assertEqual(portal.upstream_probe('connecttest.txt')[1], b'Microsoft Connect Test')
            self.assertEqual(result.limit,4097)
            self.assertEqual(opener.return_value.open.call_args.args[0],portal.PROBES['connecttest.txt'][0])
            result.status = 302
            with self.assertRaises(ValueError): portal.upstream_probe('connecttest.txt')

class PortalInstallerTests(unittest.TestCase):
    def test_waits_for_api_startup(self):
        ready = SimpleNamespace(stdout='LISTEN 0 2048 127.0.0.1:8000 0.0.0.0:*')
        with patch.object(installer,'run',side_effect=[SimpleNamespace(stdout=''),ready]) as run, patch.object(installer.time,'sleep') as sleep:
            installer.wait_for_api()
            self.assertEqual(run.call_count,2)
            sleep.assert_called_once_with(.5)

    def test_rejects_non_loopback_listener_without_waiting(self):
        for output in ('LISTEN 0 2048 0.0.0.0:8000 0.0.0.0:*',
                       'LISTEN 0 2048 [::]:8000 [::]:*', 'unexpected'):
            with self.subTest(output=output), patch.object(installer,'run',return_value=SimpleNamespace(stdout=output)), patch.object(installer.time,'sleep') as sleep:
                with self.assertRaisesRegex(SystemExit,'Found:'):
                    installer.wait_for_api()
                sleep.assert_not_called()

    def test_missing_api_has_bounded_wait_and_specific_error(self):
        with patch.object(installer,'run',return_value=SimpleNamespace(stdout='')) as run, patch.object(installer.time,'sleep') as sleep:
            with self.assertRaisesRegex(SystemExit,'No API listener appeared'):
                installer.wait_for_api()
            self.assertEqual(run.call_count,21)
            self.assertEqual(sleep.call_count,20)

    def test_removes_only_exact_legacy_nat_rules(self):
        legacy = ' '.join(installer.LEGACY)+'\n'
        docker = '-A PREROUTING -m addrtype --dst-type LOCAL -j DOCKER\n'
        other = legacy.replace('wlan0','wlan1')
        source = '*filter\n'+legacy+'COMMIT\n*nat\n'+legacy*3+docker+other+'COMMIT\n'
        expected = '*filter\n'+legacy+'COMMIT\n*nat\n'+docker+other+'COMMIT\n'
        self.assertEqual(installer.clean_saved(source),expected)
        self.assertEqual(installer.clean_saved(expected),expected)
        self.assertEqual(installer.live_legacy_positions('-P PREROUTING ACCEPT\n'+legacy+docker+legacy),[1,3])

    def test_rollback_restores_files_and_exact_rules_without_flushing(self):
        with tempfile.TemporaryDirectory() as directory:
            backup = Path(directory)
            target = backup/'config'
            target.write_bytes(b'new')
            (backup/'old').write_bytes(b'previous')
            meta = {'files': {str(target): {'backup':'old','mode':0o644}},
                    'enabled':False,'active':False,'apache_enabled':False,
                    'headers_enabled':True,'legacy_positions':[1,2,3]}
            (backup/'state.json').write_text(json.dumps(meta))
            with patch.object(installer,'ENABLED',backup/'enabled'), patch.object(installer,'run') as run:
                run.return_value = SimpleNamespace(stdout='-A PREROUTING -m addrtype --dst-type LOCAL -j DOCKER',returncode=0)
                installer.rollback(backup)
                self.assertEqual(target.read_bytes(),b'previous')
                commands = [call.args[0] for call in run.call_args_list]
                inserts = [cmd for cmd in commands if '-I' in cmd]
                self.assertEqual(len(inserts),3)
                self.assertFalse(any('-F' in cmd or 'flush' in cmd for cmd in commands))
                self.assertFalse(any('DOCKER' in cmd for cmd in commands))
                self.assertEqual([cmd[7] for cmd in inserts],['1','2','3'])

    def test_dns_rules_do_not_capture_http_or_upstream_interface(self):
        rules = [line for line in installer.NFT.splitlines() if line.startswith('add rule')]
        self.assertEqual(len(rules),2)
        for line in rules:
            self.assertIn('iifname "wlan0"',line)
            self.assertIn('ip daddr 192.168.4.1',line)
            self.assertIn('dport 53',line)
        self.assertNotIn('www.gstatic.com',installer.HOSTS)
        self.assertNotIn('address=/#/',installer.DNS)
        for host in installer.HOSTS:
            self.assertNotIn('address=/' + host + '/',installer.DNS)
        self.assertIn('address=/dataark/192.168.4.1',installer.DNS)
        self.assertIn('Require ip 192.168.4.0/24',installer.APACHE)
        self.assertIn('ProxyPass / !',installer.APACHE)
        self.assertIn('RedirectMatch 302',installer.APACHE)
        self.assertIn('server=192.168.4.1#53',installer.DNS)

if __name__ == '__main__':
    unittest.main()
