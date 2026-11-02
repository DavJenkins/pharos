import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.routers import software_updates as routes
from tools import software_update_control as control

class Request:
    def __init__(self,body=b'',headers=None):self.body=body;self.headers=headers or {'authorization':'test','content-type':'application/gzip'}
    async def stream(self):yield self.body

class SoftwareInstallationTests(unittest.TestCase):
    def test_fresh_event_feed_is_writable_by_its_service_account(self):
        import os
        from types import SimpleNamespace
        from deploy.install_software_updater import prepare_collection_feed
        with tempfile.TemporaryDirectory() as directory:
            account=SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())
            path=prepare_collection_feed(Path(directory),account)
            self.assertEqual(path.stat().st_uid,account.pw_uid)
            self.assertEqual(path.stat().st_mode&0o7777,0o2770)
            (path/'write-proof').write_text('service can write')
            self.assertEqual(prepare_collection_feed(Path(directory),account),path)

    def test_no_password_no_upload_or_root_call(self):
        with patch.object(routes,'authorized',return_value=False),patch.object(routes.installation,'invoke') as invoke:
            with self.assertRaises(HTTPException) as caught:asyncio.run(routes.stage(Request(b'archive')))
            self.assertEqual(caught.exception.status_code,401);invoke.assert_not_called()
    def test_upload_is_bounded_private_and_removed(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(routes,'authorized',return_value=True),patch.object(routes.installation,'INBOX',Path(tmp)),patch.object(routes.installation,'invoke',return_value={'ok':True,'id':'b'*32,'release':'v1'}) as invoke:
            self.assertEqual(asyncio.run(routes.stage(Request(b'archive')))['release'],'v1')
            self.assertEqual(invoke.call_args.args[0]['action'],'stage');self.assertFalse(list(Path(tmp).iterdir()))
    def test_empty_or_wrong_type_upload_refused(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(routes,'authorized',return_value=True),patch.object(routes.installation,'INBOX',Path(tmp)),patch.object(routes.installation,'invoke') as invoke:
            for request in [Request(),Request(b'archive',{'content-type':'text/plain'})]:
                with self.assertRaises(HTTPException):asyncio.run(routes.stage(request))
            invoke.assert_not_called()
    def test_install_requires_exact_id_request(self):
        with patch.object(routes,'authorized',return_value=True),patch.object(routes.installation,'invoke',return_value={'ok':True,'state':'queued'}) as invoke:
            asyncio.run(routes.install(Request(json.dumps({'id':'a'*32}).encode())))
            invoke.assert_called_once_with({'action':'apply','id':'a'*32})
            for body in [{'path':'/tmp/x'},[],{'id':'x','command':'reboot'}]:
                with self.assertRaises(HTTPException):asyncio.run(routes.install(Request(json.dumps(body).encode())))
    def test_helper_rejects_unknown_fields_before_any_privileged_work(self):
        for data in [{'action':'exec','command':'sh'},{'action':'status','id':'a'*32},{'action':'stage','id':'../etc/passwd'},[]]:
            with patch.object(control,'Updater') as updater,self.subTest(data=data),self.assertRaises(ValueError):control.control(data)

if __name__=='__main__':unittest.main()
