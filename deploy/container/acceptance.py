"""Isolated Docker acceptance. Uses new fixture media and named test volumes.

An optional real ZIM is mounted read-only; no production content is modified.
"""
import argparse,base64,hashlib,json,os,secrets,subprocess,tempfile,time,urllib.request,urllib.error
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',default='dataark:container-candidate');p.add_argument('--zim',type=Path);p.add_argument('--port',type=int,default=18089);p.add_argument('--keep',action='store_true');a=p.parse_args()
    token=secrets.token_hex(4);name='dataark-verification-'+token;base=Path(tempfile.mkdtemp(prefix='dataark-container-verification-'));media=base/'media';config=base/'config';(media/'forms').mkdir(parents=True);config.mkdir();os.chown(config,1000,1000)
    sample=b'%PDF-1.7\nPublic range-request fixture\n';(media/'forms/sample.pdf').write_bytes(sample)
    (media/'bugout-drop').mkdir();(media/'bugout-drop/private.txt').write_text('Not public')
    volumes=[name+'-state',name+'-private'];url=f'http://127.0.0.1:{a.port}';password=secrets.token_urlsafe(24);auth='Basic '+base64.b64encode(('admin:'+password).encode()).decode()
    report={'image':a.image,'production_content_modified':False,'checks':{},'container':name,'fixture':str(base),'volumes':volumes,'port':a.port}
    def request(path,body=None,headers=None):
        req=urllib.request.Request(url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with urllib.request.urlopen(req,timeout=30) as r:return r.status,r.read(),dict(r.headers)
        except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
    def start():
        args=['docker','run','-d','--name',name,'--label','dataark.acceptance=container','--cap-drop=ALL','--security-opt','no-new-privileges:true','-p',f'{a.port}:8088']
        for source,target,kind,ro in [(str(media),'/mnt/storage','bind',True),(str(config),'/config','bind',False),(volumes[0],'/var/lib/dataark','volume',False),(volumes[1],'/etc/dataark','volume',False)]:args+=['--mount',f'type={kind},src={source},dst={target}'+(',readonly' if ro else '')]
        if a.zim:
            assert a.zim.is_file() and a.zim.suffix=='.zim';(media/a.zim.name).touch()
            args+=['--mount',f'type=bind,src={a.zim},dst=/mnt/storage/{a.zim.name},readonly']
        subprocess.run(args+[a.image],check=True,capture_output=True)
        end=time.monotonic()+180
        while True:
            try:
                if request('/api/container/health')[0]==200:return
            except OSError:pass
            if time.monotonic()>end:raise RuntimeError('Container did not start; inspect docker logs '+name)
            time.sleep(2)
    success=False
    try:
        start();report['checks']['startup']=True
        for path in ['/','/library.html','/container.html','/docs/20-Administration/Container.html','/api/status','/api/network','/api/configuration','/api/library','/api/integration/health']:
            assert request(path)[0]==200,path
        report['checks']['web_api_and_docs']=True
        assert request('/library-files/forms/sample.pdf',headers={'Range':'bytes=0-7'})[:2]==(206,sample[:8])
        assert request('/library-files/bugout-drop/private.txt')[0]==404
        report['checks']['range_requests_and_private_file_exclusion']=True
        inspected=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
        assert inspected['Config']['User']=='1000:1000' and inspected['HostConfig']['CapDrop']==['ALL'] and not inspected['HostConfig']['Privileged']
        write=subprocess.run(['docker','exec',name,'python','-c',"from pathlib import Path;Path('/mnt/storage/should-not-exist').write_text('no')"],capture_output=True)
        assert write.returncode!=0 and not (media/'should-not-exist').exists()
        assert request('/api/library/remove',{})[0]==501
        report['checks']['unprivileged_readonly_and_no_host_mutations']=True
        code="import sys,json;from tools.prepare_recipient import password_record;from pathlib import Path;Path('/etc/dataark/network-admin.json').write_text(json.dumps(password_record(sys.stdin.read())))"
        subprocess.run(['docker','exec','-i',name,'python','-c',code],input=password,text=True,check=True)
        assert request('/api/container/reload',{})[0]==401
        assert request('/api/container/reload',{},headers={'Authorization':auth})[0]==200
        board={'name':'Test','title':'Persistent container '+token,'category':'general','body':'**Offline** community message'}
        assert request('/api/community/threads',board)[0]==201
        assert request('/api/community/notice',{'text':'Test banner'},headers={'Authorization':auth})[0]==200
        report['checks']['caretaker_and_community']=True
        if a.zim:
            end=time.monotonic()+90
            while request('/kiwix/')[0]!=200:
                if time.monotonic()>end:raise RuntimeError('Reader did not become ready')
                time.sleep(2)
            assert b'Kiwix' in request('/kiwix/')[1]
            assert request('/library-files/'+a.zim.name,headers={'Range':'bytes=0-7'})[0]==206
            report['checks']['real_zim_reader_and_download']=True
        subprocess.run(['docker','stop',name],check=True,capture_output=True);subprocess.run(['docker','rm',name],check=True,capture_output=True)
        start()
        assert board['title'].encode() in request('/api/community/threads')[1]
        assert b'Test banner' in request('/api/community/notice')[1]
        assert request('/api/library/unlock',{},headers={'Authorization':auth})[0]==200
        report['checks']['recreation_preserves_board_banner_and_caretaker']=True
        report['state']='passed';success=True
    finally:
        evidence=Path('/var/lib/dataark/acceptance/container-20261102');evidence.mkdir(parents=True,exist_ok=True)
        log=subprocess.run(['docker','logs',name],capture_output=True,text=True)
        (evidence/(token+'.log')).write_text(log.stdout+log.stderr)
        report['kept_running']=bool(a.keep and success)
        if not report['kept_running']:
            subprocess.run(['docker','rm','-f',name],capture_output=True)
        (evidence/(token+'.json')).write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))

if __name__=='__main__':main()
