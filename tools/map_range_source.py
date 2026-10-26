#!/usr/bin/python3
"""Loopback-only, resumable range cache for the pinned Protomaps source."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib,json,re,shutil,threading,time

ROOT=Path(__file__).resolve().parents[1]
CACHE=Path('/mnt/storage/.dataark-map-source-cache')
SOURCE=json.loads((ROOT/'deploy/reference/osm-usa.json').read_text())['source']
LOCKS={}; GUARD=threading.Lock(); META=None

def metadata():
    global META
    with GUARD:
        if META:return META
        if not re.fullmatch(r'https://build\.protomaps\.com/\d{8}\.pmtiles',SOURCE):raise ValueError('Only a pinned official Protomaps archive is supported')
        with urlopen(Request(SOURCE,method='HEAD',headers={'User-Agent':'DataArk/1.0 (offline map mirror)','Accept-Encoding':'identity'}),timeout=45) as r:
            meta={'url':SOURCE,'bytes':int(r.headers['Content-Length']),'etag':r.headers.get('ETag','')}
        CACHE.mkdir(parents=True,exist_ok=True)
        record=CACHE/'source.json'
        if record.exists() and json.loads(record.read_text())!=meta:raise ValueError('Cached source identity changed; inspect before replacing cache')
        record.write_text(json.dumps(meta)+'\n');META=meta;return meta

def fetch_range(start,end,opener=urlopen,retries=20,delay=time.sleep):
    meta=metadata();length=end-start+1
    if not 0<=start<=end<meta['bytes'] or length>8*1024**3:raise ValueError('Invalid or excessive range')
    target=CACHE/(str(start)+'-'+str(end)+'.bin');part=target.with_suffix('.part')
    with GUARD:lock=LOCKS.setdefault((start,end),threading.Lock())
    with lock:
        if target.is_file():
            if target.stat().st_size!=length:raise ValueError('Cached range has an unexpected size')
            return target
        for attempt in range(retries):
            written=part.stat().st_size if part.exists() else 0
            if written==length:part.replace(target);return target
            if written>length:raise ValueError('Partial range exceeds expected size')
            if shutil.disk_usage(CACHE).free<20*1024**3:raise RuntimeError('Map source cache storage reserve reached')
            cursor=start+written
            headers={'Range':f'bytes={cursor}-{end}','Accept-Encoding':'identity','User-Agent':'DataArk resumable map extraction'}
            if meta['etag'] and not meta['etag'].startswith('W/'):headers['If-Match']=meta['etag']
            try:
                with opener(Request(SOURCE,headers=headers),timeout=60) as response:
                    if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {cursor}-{end}/{meta["bytes"]}':raise ValueError('Publisher returned an unexpected range')
                    if meta['etag'] and response.headers.get('ETag')!=meta['etag']:raise ValueError('Publisher source version changed')
                    with part.open('ab',buffering=0) as stream:
                        remaining=length-written
                        while remaining:
                            chunk=response.read(min(1024**2,remaining))
                            if not chunk:raise EOFError('Publisher ended range early')
                            stream.write(chunk);remaining-=len(chunk)
                part.replace(target);print('Cached range',start,end,length,flush=True);return target
            except ValueError:raise
            except Exception as error:
                print('Retry range',start,end,'attempt',attempt+1,type(error).__name__,str(error)[:200],flush=True)
                if attempt+1==retries:raise
                delay(min(30,attempt+1))
        raise RuntimeError('Range retry limit reached')

class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        try:
            if self.path!='/source.pmtiles':self.send_error(404);return
            meta=metadata();self.send_response(200);self.send_header('Content-Length',str(meta['bytes']));self.send_header('Accept-Ranges','bytes');self.send_header('ETag',meta['etag']);self.end_headers()
        except Exception as error:self.send_error(502,str(error))
    def do_GET(self):
        try:
            if self.path!='/source.pmtiles':self.send_error(404);return
            match=re.fullmatch(r'bytes=(\d+)-(\d+)',self.headers.get('Range',''))
            if not match:self.send_error(416,'Explicit bounded range required');return
            start,end=map(int,match.groups());path=fetch_range(start,end);meta=metadata()
            self.send_response(206);self.send_header('Content-Length',str(end-start+1));self.send_header('Content-Range',f'bytes {start}-{end}/{meta["bytes"]}');self.send_header('ETag',meta['etag']);self.end_headers()
            with path.open('rb') as stream:shutil.copyfileobj(stream,self.wfile,1024**2)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as error:self.send_error(502,str(error))
    def log_message(self,*args):pass

if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8097),Handler).serve_forever()
