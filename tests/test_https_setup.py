import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from starlette.requests import Request
from fastapi import HTTPException
from tools import https_helper as h
from app.services import https_setup
from app.routers import https_setup as routes

class HTTPSSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.private=self.root/'private';self.private.mkdir()
        self.public=self.root/'public';self.public.mkdir()
        self.site=self.root/'site.conf';self.enabled=self.root/'enabled.conf'
        self.patches=[patch.object(h,'PRIVATE',self.private),patch.object(h,'PUBLIC',self.public),
            patch.object(h,'IDENTITY',self.root/'identity.json'),patch.object(h,'SITE',self.site),
            patch.object(h,'ENABLED',self.enabled),patch.object(h,'DNS',self.private/'local-dns.conf')]
        for p in self.patches:p.start()
        self.addCleanup(lambda:[p.stop() for p in self.patches]);self.addCleanup(self.temp.cleanup)

    def test_domain_is_a_hostname_not_a_command_url_or_private_address(self):
        self.assertEqual(h.domain_name('Ark.Owner-Domain.org.'),'ark.owner-domain.org')
        for domain in ['192.168.4.1','dataark','dataark.lan','a.local','example.org','ark.example.org','*.owner.org','https://owner.org/','owner.org:443','owner.org\nServerName bad','--server=bad','../secret','[::1]']:
            with self.subTest(domain=domain),self.assertRaises(ValueError):h.domain_name(domain)

    def test_private_identity_is_stable_and_fresh_rebuild_gets_a_new_one(self):
        original=h.identity();self.assertEqual(h.identity(),original)
        with patch.object(h,'IDENTITY',self.root/'fresh-system-identity.json'):
            self.assertNotEqual(h.identity(),original)

    def test_terms_are_required_before_any_request_or_state_change(self):
        with patch.object(h,'command') as command,self.assertRaises(ValueError):
            h.helper_action({'action':'start','domain':'ark.owner-domain.org','email':'owner@owner-domain.org','agree_terms':False})
        command.assert_not_called();self.assertFalse((self.private/'job.json').exists())

    def test_start_records_contact_privately_and_only_launches_fixed_service(self):
        with patch.object(h,'running',return_value=False),patch.object(h,'command') as command:
            h.helper_action({'action':'start','domain':'ark.owner-domain.org','email':'owner@owner-domain.org','agree_terms':True})
        self.assertEqual(command.call_args.args[0],['/usr/bin/systemctl','start','--no-block',h.UNIT])
        self.assertIn('owner@owner-domain.org',(self.private/'job.json').read_text())
        self.assertNotIn('owner@owner-domain.org',(self.public/'status.json').read_text())
        if os.name!='nt':self.assertEqual((self.private/'job.json').stat().st_mode&0o777,0o600)

    def test_external_servers_paths_and_extra_fields_are_rejected(self):
        for request in [{'action':'start','domain':'ark.owner.org','email':'a@owner.org','agree_terms':True,'server':'http://evil'}, {'action':'details','path':'/etc/shadow'}, {'action':'shell','command':'id'}]:
            with self.assertRaises(ValueError):h.helper_action(request)

    def test_challenge_approval_is_bound_to_current_job_and_nonce(self):
        h.save(self.private/'challenge.json',{'job_id':'a','challenge_id':'b','expires_at':time.time()+100})
        h.save(self.public/'status.json',{'phase':'waiting_dns'})
        with patch.object(h,'running',return_value=True):
            with self.assertRaises(ValueError):h.helper_action({'action':'verify','job_id':'old','challenge_id':'b'})
            self.assertFalse((self.private/'approval.json').exists())
            h.helper_action({'action':'verify','job_id':'a','challenge_id':'b'})
        self.assertEqual(h.read(self.private/'approval.json'),{'job_id':'a','challenge_id':'b'})

    def test_manual_hook_waits_for_explicit_dns_approval(self):
        h.save(self.private/'job.json',{'domain':'ark.owner-domain.org','job_id':'job1'})
        def approve(_):
            challenge=h.read(self.private/'challenge.json')
            self.assertEqual(h.read(self.public/'status.json')['phase'],'waiting_dns')
            h.save(self.private/'approval.json',{k:challenge[k] for k in ('job_id','challenge_id')})
        with patch.dict(os.environ,{'CERTBOT_DOMAIN':'ark.owner-domain.org','CERTBOT_VALIDATION':'a'*43}),patch.object(h.time,'sleep',side_effect=approve):h.auth_main()
        self.assertEqual(h.read(self.public/'status.json')['phase'],'verifying')

    def test_details_do_not_write_over_worker_phase(self):
        h.save(self.public/'status.json',{'phase':'waiting_dns'})
        with patch.object(h,'status',side_effect=AssertionError('Polling must not write state')):
            self.assertEqual(h.helper_action({'action':'details'})['phase'],'waiting_dns')

    def test_failed_apache_validation_restores_previous_site_and_dns(self):
        old=h.MARKER+'\nold configuration\n';self.site.write_text(old);self.enabled.symlink_to(self.site)
        dns=self.private/'local-dns.conf';dns.write_text('old DNS')
        http=self.root/'http.conf';http.write_text('original HTTP')
        def command(args,**kwargs):
            if args[:2]==['/usr/sbin/apache2ctl','configtest']:raise RuntimeError('bad config')
            return ''
        with patch.object(h,'command',side_effect=command),patch.object(h.subprocess,'run'):
            with self.assertRaises(RuntimeError):h.activate('ark.owner-domain.org',self.private/'new-certificate',{})
        self.assertEqual(self.site.read_text(),old);self.assertEqual(dns.read_text(),'old DNS')
        self.assertTrue(self.enabled.is_symlink());self.assertEqual(http.read_text(),'original HTTP')

    def test_acme_command_is_pinned_dns_only_and_uses_private_paths(self):
        command=h.certbot_command({'domain':'ark.owner-domain.org','email':'owner@owner-domain.org'})
        self.assertIn(h.ACME,command);self.assertIn('--manual-auth-hook',command)
        self.assertIn('--keep-until-expiring',command);self.assertNotIn('--apache',command)
        self.assertNotIn('--force-renewal',command)
        self.assertNotIn('/mnt/storage',' '.join(command))
        config=h.apache_config('ark.owner-domain.org',self.private/'installed')
        self.assertNotIn('Redirect',config);self.assertNotIn('Strict-Transport-Security',config)

    def test_public_health_reports_expiry_without_root_or_network(self):
        p=self.public/'health.json';h.save(p,{'certificate':{'expires_at':'2000-01-01T00:00:00+00:00'}})
        with patch.object(https_setup,'STATUS',p):
            result=https_setup.public_status()
        self.assertEqual(result['certificate_health'],'expired');self.assertEqual(result['days_remaining'],0)

    def test_certificate_key_mismatch_is_rejected(self):
        def command(args,**kwargs):
            if '-pubkey' in args:return 'certificate key'
            if 'pkey' in args:return 'different private key'
            return ''
        with patch.object(h,'command',side_effect=command),self.assertRaisesRegex(ValueError,'private key'):
            h.validate_certificate('ark.owner-domain.org',self.private/'live')

class HTTPSAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    def request(self,headers):return Request({'type':'http','headers':[(k.encode(),v.encode()) for k,v in headers.items()]})
    async def test_wrong_password_rejected_before_privileged_helper(self):
        with patch.object(routes,'authorized',return_value=False),patch.object(routes,'invoke') as invoke:
            with self.assertRaises(HTTPException) as error:await routes.details(self.request({'host':'dataark','authorization':'Basic bad'}))
            self.assertEqual(error.exception.status_code,401);invoke.assert_not_called()
    async def test_cross_origin_management_rejected(self):
        with patch.object(routes,'authorized') as auth:
            with self.assertRaises(HTTPException) as error:await routes.authenticate(self.request({'host':'dataark','origin':'https://elsewhere.org'}))
            self.assertEqual(error.exception.status_code,403);auth.assert_not_called()

if __name__=='__main__':unittest.main()
