import asyncio
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.services import software_downloads as service
from app.routers import software_updates as routes

TAG='software-2026.11.03'
URL='https://github.com/DavJenkins/pharos/releases/download/'+TAG+'/data-ark-'+TAG+'.tar.gz'


class Response(io.BytesIO):
    url=URL
    def __init__(self,raw,length=None):
        super().__init__(raw);self.headers={'Content-Length':str(length if length is not None else len(raw))}


class Request:
    def __init__(self,body,headers=None):self.body=body;self.headers=headers or {'content-type':'application/json'}
    async def stream(self):yield self.body


class SoftwareDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for p in [patch.object(service.installation,'INBOX',self.root),patch('tools.update_notifications.download')]:
            p.start();self.addCleanup(p.stop)
        self.job={'id':'a'*32,'tag':TAG,'preview':False,'state':'queued'}

    def run_download(self,raw=b'signed bytes',expected=None,declared=None,staged=None):
        lock=io.BytesIO()
        with patch.object(service,'package',return_value=(URL,len(raw) if declared is None else declared,expected)),patch.object(service.installation,'invoke',return_value=staged or {'ok':True,'id':'b'*32,'release':TAG,'files':1,'removals':0}) as invoke:
            service.run(self.job,lock,lambda *a,**k:Response(raw))
        self.assertTrue(lock.closed)
        self.assertFalse((self.root/(self.job['id']+'.tar.gz')).exists())
        return service.read(),invoke

    def test_download_only_stages_and_persists_verified_result(self):
        result,invoke=self.run_download(expected=hashlib.sha256(b'signed bytes').hexdigest())
        self.assertEqual(result['state'],'verified');self.assertEqual(result['percent'],100)
        self.assertEqual(result['staged']['id'],'b'*32)
        invoke.assert_called_once_with({'action':'stage','id':self.job['id']})
        self.assertEqual(service.status()['state'],'verified')

    def test_checksum_truncation_and_signature_failures_never_install(self):
        result,invoke=self.run_download(expected='0'*64)
        self.assertEqual(result['state'],'failed');invoke.assert_not_called()
        result,invoke=self.run_download(declared=100)
        self.assertEqual(result['state'],'failed');invoke.assert_not_called()
        result,invoke=self.run_download(staged={'ok':False,'error':'Signature rejected'})
        self.assertEqual(result['state'],'failed');self.assertIn('Signature rejected',result['message'])
        self.assertEqual(invoke.call_args.args[0]['action'],'stage')

    def test_wrong_signed_release_is_not_offered_for_installation(self):
        result,_=self.run_download(staged={'ok':True,'id':'b'*32,'release':'software-2025.01.01'})
        self.assertEqual(result['state'],'failed');self.assertNotIn('staged',result)

    def test_growth_beyond_metadata_is_rejected(self):
        with patch.object(service,'package',return_value=(URL,3,None)),patch.object(service.installation,'invoke') as invoke:
            response=Response(b'oversized');response.headers={}
            service.run(self.job,io.BytesIO(),lambda *a,**k:response)
        self.assertEqual(service.read()['state'],'failed');invoke.assert_not_called()

    def test_network_failure_is_actionable_and_preserves_running_software(self):
        with patch.object(service,'package',side_effect=OSError('offline')),patch.object(service.installation,'invoke') as invoke:
            service.run(self.job,io.BytesIO())
        self.assertEqual(service.read()['state'],'failed');self.assertIn('running software was not changed',service.read()['message']);invoke.assert_not_called()

    def test_restart_marks_partial_download_interrupted_and_removes_it(self):
        service.save(self.job);(self.root/(self.job['id']+'.tar.gz')).write_bytes(b'partial')
        self.assertEqual(service.status()['state'],'interrupted')
        self.assertFalse((self.root/(self.job['id']+'.tar.gz')).exists())

    def test_concurrent_download_is_rejected_and_refresh_keeps_progress(self):
        from types import SimpleNamespace
        args=[]
        def thread(**kwargs):args.append(kwargs['args']);return SimpleNamespace(start=lambda:None)
        with patch.object(service.installation,'status',return_value={'configured':True,'state':'idle'}),patch.object(service.threading,'Thread',side_effect=thread):
            service.start(TAG)
            try:
                self.assertEqual(service.status()['state'],'queued')
                with self.assertRaises(service.DownloadError) as e:service.start(TAG)
                self.assertEqual(e.exception.status,409)
            finally:args[0][1].close()

    def test_bootstrap_preview_and_unconfigured_updater_are_refused(self):
        for tag,preview in [('bootstrap-2026.11.03',False),(TAG+'-preview.1',False),('../evil',False)]:
            with self.assertRaises(service.DownloadError):service.start(tag,preview)
        with patch.object(service.installation,'status',return_value={'configured':False}):
            with self.assertRaises(service.DownloadError):service.start(TAG)

    def test_only_official_https_redirects_are_allowed(self):
        for url in ['http://github.com/file','https://github.com.evil.test/file','https://127.0.0.1/file','https://github.com:444/file','https://user@github.com/file']:
            with self.subTest(url=url),self.assertRaises(service.DownloadError):service.validate_url(url)
        service.validate_url(URL);service.validate_url('https://release-assets.githubusercontent.com/asset?token=temporary')

    def test_release_metadata_is_rechecked_and_not_a_client_url(self):
        item={'tag_name':TAG,'target_commitish':'b'*40,'assets':[{'name':'data-ark-'+TAG+'.tar.gz','state':'uploaded','size':10,'browser_download_url':URL}]}
        with patch.object(service.releases,'read_releases',return_value=[item]),patch.object(service.releases,'relationship',return_value='uncompared'),patch.object(service.releases,'installed',return_value={}):
            self.assertEqual(service.package(TAG,False),(URL,10,None))
            item['assets'][0]['browser_download_url']='https://evil.test/archive'
            with self.assertRaises(service.DownloadError):service.package(TAG,False)

    def test_endpoint_requires_caretaker_and_exact_request(self):
        body=json.dumps({'tag':TAG,'preview':False}).encode()
        with patch.object(routes,'authorized',return_value=False),patch.object(service,'start') as start:
            with self.assertRaises(HTTPException) as e:asyncio.run(routes.download(Request(body)))
            self.assertEqual(e.exception.status_code,401);start.assert_not_called()
        with patch.object(routes,'authorized',return_value=True),patch.object(service,'start',return_value=self.job) as start:
            self.assertEqual(asyncio.run(routes.download(Request(body))),self.job)
            start.assert_called_once_with(TAG,False)
            for value in [{'url':'https://evil.test'}, {'tag':TAG,'preview':False,'url':URL},[]]:
                with self.assertRaises(HTTPException):asyncio.run(routes.download(Request(json.dumps(value).encode())))


if __name__=='__main__':unittest.main()
