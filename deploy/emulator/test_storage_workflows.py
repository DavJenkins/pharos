"""Real ext4 adoption/replacement acceptance in a private mount namespace.

Formats only newly created sparse image files. No production disks or services.
"""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
from tools import external_library as x,storage_workflows as s,appliance_jobs

def main():
    assert os.geteuid()==0
    results=[]
    for mode,copy,fail in [('adopt',False,False),('adopt',False,True),('replace',False,False),('replace',True,False)]:
        with tempfile.TemporaryDirectory(prefix='dataark-storage-acceptance-') as folder:
            base=Path(folder);a=base/'source';b=base/'target';a.mkdir();b.mkdir();loops=[]
            real=x.run
            try:
                for number in range(2):
                    image=base/f'{number}.ext4'
                    with image.open('xb') as f:f.truncate(2*1024**3)
                    subprocess.run(['mkfs.ext4','-q','-F',str(image)],check=True)
                    loops.append(subprocess.check_output(['losetup','--find','--show',str(image)],text=True).strip())
                for loop,mount in zip(loops,[a,b]):subprocess.run(['mount',loop,str(mount)],check=True)
                (a/'sample.txt').write_text('Original content retained')
                if mode=='adopt':
                    (b/'existing.txt').write_text('Existing adopted content')
                    (b/'CLONE-REPORT.json').write_text(json.dumps({'files':[{'path':'existing.txt','sha256':hashlib.sha256((b/'existing.txt').read_bytes()).hexdigest()}]}))
                if mode=='replace' and not copy:subprocess.run(['umount',str(a)],check=True)
                identifier=real(['blkid','-s','UUID','-o','value',loops[1]])
                x.SOURCE=a;x.PRIVATE=base/'engine-private';x.PRIVATE.mkdir();x.LOCKS=[];x.FSTAB=base/'fstab'
                x.FSTAB.write_text(loops[0]+' '+str(a)+' ext4 defaults,nofail 0 0\n')
                x.devices=lambda:[{'uuid':identifier,'device':loops[1],'filesystem':'ext4','serial':'isolated-test','bytes':2*1024**3,'mounts':[str(b)]}]
                x.quiesce=lambda:([],False);x.resume=lambda *_:None
                fault=[fail]
                def run(args):
                    if args[:2]==['systemctl','daemon-reload'] or 'render_dashboard.py' in ' '.join(args):return ''
                    if args==['mount',str(a)]:
                        if fault[0] and 'UUID=' in x.FSTAB.read_text():fault[0]=False;raise ValueError('Injected mount failure')
                        return real(['mount',loops[1] if 'UUID=' in x.FSTAB.read_text() else loops[0],str(a)])
                    return real(args)
                x.run=run;s.engine=lambda:x;s.ROOT=base/'repo';(s.ROOT/'config').mkdir(parents=True)
                (s.ROOT/'dataark.yaml').write_text('assets: []\n')
                s.PRIVATE=base/'private';s.STATE=base/'state'
                # Profile parser has separate validation tests; isolate mount mechanics.
                s.public_profile=lambda _:({}, {'assets':[]}, {})
                appliance_jobs.emit=lambda *_:None
                plan=s.plan(identifier,mode,'keep',copy);s.save(s.PRIVATE/'job.json',json.loads((s.PRIVATE/'plan.json').read_text()))
                if fail:
                    try:s.worker();raise AssertionError('Injected failure was ignored')
                    except ValueError as e:assert 'Injected mount failure' in str(e)
                    assert (a/'sample.txt').read_text()=='Original content retained'
                    assert json.loads((s.PRIVATE/'journal.json').read_text())['phase']=='rolled_back'
                else:
                    s.worker();assert real(['findmnt','-n','-o','UUID','--mountpoint',str(a)])==identifier
                    if mode=='adopt':assert (a/'existing.txt').read_text()=='Existing adopted content'
                    if copy:assert (a/'sample.txt').read_text()=='Original content retained'
                    assert (s.ROOT/'dataark.yaml').read_text()=='assets: []\n'
                    assert json.loads((s.STATE/'status.json').read_text())['phase']=='ready'
                results.append({'mode':mode,'copy_existing':copy,'rollback':fail,'passed':True})
            finally:
                x.run=real
                for mount in [a,b]:subprocess.run(['umount',str(mount)],capture_output=True)
                for loop in loops:subprocess.run(['losetup','-d',loop],capture_output=True)
    print(json.dumps({'cases':results,'production_disks_changed':False}))

if __name__=='__main__':main()
