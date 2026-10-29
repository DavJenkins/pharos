import unittest
from unittest.mock import patch
from starlette.requests import Request
from starlette.responses import JSONResponse
from deploy.emulator.asgi import protect_test_media, ark_app

class EmulatorProfileTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, method, path, marked=True):
        request=Request({'type':'http','method':method,'path':path,'headers':[]})
        async def next_handler(_):return JSONResponse({'ok':True})
        with patch('deploy.emulator.asgi.Path.is_file',return_value=marked):
            return await protect_test_media(request,next_handler)
    async def test_hardware_media_and_household_writes_are_blocked(self):
        for path in ['/bugout/trigger','/network/admin','/library/remove','/configuration/save','/recovery/approve']:
            self.assertEqual((await self.request('POST',path)).status_code,409,path)
    async def test_read_and_local_preview_community_remain_available(self):
        for method,path in [('GET','/status'),('POST','/configuration/validate'),('POST','/community/notice'),('POST','/library/unlock')]:
            self.assertEqual((await self.request(method,path)).status_code,200,path)
    async def test_profile_cannot_run_without_guest_marker(self):
        self.assertEqual((await self.request('GET','/status',False)).status_code,503)

    def test_import_does_not_attach_emulator_guard_to_the_production_app(self):
        self.assertFalse(any(m.kwargs.get('dispatch') is protect_test_media for m in ark_app.user_middleware))
