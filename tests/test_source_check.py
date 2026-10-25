import asyncio
import fcntl
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.services import source_check as checks
from app.services import upstream
from app.routers import source_check as routes

ASSET={'id':'book','download_url':'https://example.org/book.pdf'}

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patches=[patch.object(checks,'CACHE',self.root/'cache.json'),patch.object(checks,'LOCK_FILE',self.root/'check.lock'),patch.object(checks,'STATE',{'state':'idle','completed':0,'total':0,'message':''}),patch.object(checks,'LAST_REQUEST',0.0),patch.object(checks,'load_manifest',return_value={'assets':[ASSET]})]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def test_one_job_and_cooldown(self):
        with patch.object(checks.threading,'Thread') as thread:
            self.assertEqual(checks.start()['state'],'checking')
            self.assertEqual(checks.start()['state'],'checking')
            self.assertEqual(thread.call_count,1)
            thread.call_args.kwargs['args'][0].close()
            checks.STATE['state']='complete'
            with self.assertRaises(checks.CheckError) as caught:checks.start()
            self.assertEqual(caught.exception.status,429)
    def test_shared_lock_prevents_overlapping_cli_job(self):
        with checks.LOCK_FILE.open('a') as file:
            fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(checks.CheckError) as caught:checks.start()
            self.assertEqual(caught.exception.status,409)
    def test_failure_keeps_last_result(self):
        checks.CACHE.write_text('{"previous":"preserved"}')
        with patch.object(checks,'check_assets',side_effect=OSError('test failure')),patch('logging.Logger.exception'):
            checks.run(checks.LOCK_FILE.open('a'))
        self.assertEqual(checks.STATE['state'],'failed')
        self.assertEqual(json.loads(checks.CACHE.read_text()),{'previous':'preserved'})
    def test_success_updates_timestamp_and_validates_current_urls(self):
        result={'version':1,'batch_started_at':'2026-10-25T00:00:00+00:00','batch_finished_at':'2026-10-25T00:00:01+00:00','assets':{'book':{'status':'available','sources':[ASSET['download_url']],'checked_at':'2026-10-25T00:00:01+00:00'}}}
        with patch.object(checks,'check_assets',return_value=result):checks.run(checks.LOCK_FILE.open('a'))
        status=checks.current()
        self.assertEqual(status['state'],'complete');self.assertEqual(status['checked_at'],result['batch_finished_at'])
        self.assertEqual(status['assets']['book']['status'],'available')
        with patch.object(checks,'load_manifest',return_value={'assets':[{**ASSET,'download_url':'https://other.example/book.pdf'}]}):
            self.assertIsNone(checks.current()['assets']['book']['checked_at'])

class ProbeTests(unittest.TestCase):
    def test_at_most_four_parallel_probes_and_progress(self):
        lock=threading.Lock();barrier=threading.Barrier(4,timeout=5)
        active=0;peak=0;progress=[]
        def probe(url):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active)
            barrier.wait()
            with lock:active-=1
            return {'url':url,'status':'available'}
        with patch.object(upstream,'probe',side_effect=probe):
            result=upstream.check_assets([{'id':str(i),'download_url':'https://example.org/'+str(i)} for i in range(8)],progress=lambda a,b:progress.append((a,b)))
        self.assertLessEqual(peak,4);self.assertEqual(len(result['assets']),8)
        self.assertEqual(progress[0],(0,8));self.assertEqual(progress[-1],(8,8))

class Request:
    def __init__(self,body=b'{}',headers=None):
        self.body=body;self.headers={'host':'dataark','origin':'http://dataark','content-type':'application/json',**(headers or {})}
    async def stream(self):yield self.body

class RouteTests(unittest.TestCase):
    def test_only_same_origin_empty_json_can_start(self):
        for request,status in [(Request(headers={'origin':'http://evil.example'}),403),(Request(headers={'content-type':'text/plain'}),415),(Request(b'{"url":"https://other.example"}'),400),(Request(b'x'*33),413)]:
            with patch.object(checks,'start') as start,self.assertRaises(HTTPException) as caught:asyncio.run(routes.start(request))
            self.assertEqual(caught.exception.status_code,status);start.assert_not_called()
        with patch.object(checks,'start',return_value={'state':'checking'}):
            self.assertEqual(asyncio.run(routes.start(Request()))['state'],'checking')

if __name__=='__main__':unittest.main()
