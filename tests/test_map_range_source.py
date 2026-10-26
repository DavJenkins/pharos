import importlib.util,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import map_range_source as source

class Response(io.BytesIO):
    status=206
    def __init__(self,data,start,end,total):super().__init__(data);self.headers={'Content-Range':f'bytes {start}-{end}/{total}','ETag':'v1'}

class RangeTests(unittest.TestCase):
    def test_short_response_resumes_only_missing_bytes_then_reuses_cache(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(source,'CACHE',Path(directory)),patch.object(source,'metadata',return_value={'bytes':6,'etag':'v1'}),patch.object(source.shutil,'disk_usage',return_value=type('Disk',(),{'free':100*1024**3})()):
            requests=[]
            def opener(request,**kwargs):
                value=request.get_header('Range');requests.append(value)
                return Response(b'abc',0,5,6) if len(requests)==1 else Response(b'def',3,5,6)
            path=source.fetch_range(0,5,opener=opener,delay=lambda _:None)
            self.assertEqual(path.read_bytes(),b'abcdef');self.assertEqual(requests,['bytes=0-5','bytes=3-5'])
            source.fetch_range(0,5,opener=lambda *a,**k:self.fail('Complete cached range must not be downloaded again'))

    def test_ignored_range_is_rejected_without_accepting_planet_file(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(source,'CACHE',Path(directory)),patch.object(source,'metadata',return_value={'bytes':6,'etag':'v1'}),patch.object(source.shutil,'disk_usage',return_value=type('Disk',(),{'free':100*1024**3})()):
            response=Response(b'abcdef',0,5,6);response.status=200
            with self.assertRaises(ValueError):source.fetch_range(0,5,opener=lambda *a,**k:response)

if __name__=='__main__':unittest.main()
