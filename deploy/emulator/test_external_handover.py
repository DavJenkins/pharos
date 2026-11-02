"""Isolated real-filesystem acceptance; requires root in a private mount namespace.

Only newly created sparse image files are formatted. No host drive, fstab,
service, configuration or production library is changed.
"""
import importlib.util,json,os,subprocess,tempfile,hashlib
from pathlib import Path
import sys

def main(module_path):
    assert os.geteuid()==0
    spec=importlib.util.spec_from_file_location('handover',module_path);x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x)
    with tempfile.TemporaryDirectory(prefix='dataark-handover-') as folder:
        base=Path(folder);a=base/'source';b=base/'target';a.mkdir();b.mkdir()
        images=[base/'demo.ext4',base/'external.ext4'];loops=[]
        try:
            for image in images:
                with image.open('xb') as f:f.truncate(2*1024**3)
                subprocess.run(['mkfs.ext4','-q','-F',str(image)],check=True)
                loops.append(subprocess.check_output(['losetup','--find','--show',str(image)],text=True).strip())
            for loop,mount in zip(loops,[a,b]):subprocess.run(['mount',loop,str(mount)],check=True)
            (a/'DEMO-LIBRARY.json').write_text('{}');(a/'books').mkdir();(a/'books/sample.pdf').write_bytes(b'verified offline library\n'*250000)
            before=hashlib.sha256((a/'books/sample.pdf').read_bytes()).hexdigest()
            uuid=subprocess.check_output(['blkid','-s','UUID','-o','value',loops[1]],text=True).strip()
            x.SOURCE=a;x.IMAGE=images[0];x.PRIVATE=base/'private';x.PRIVATE.mkdir();x.STATE=base/'state';x.LOCKS=[];x.REPO=base/'repo';(x.REPO/'config').mkdir(parents=True);(x.REPO/'config/installed-site.json').write_text('{"demo_library":{}}')
            x.FSTAB=base/'fstab';x.FSTAB.write_text(str(images[0])+' '+str(a)+' ext4 loop,nofail 0 0\n')
            x.devices=lambda:[{'uuid':uuid,'device':loops[1],'filesystem':'ext4','serial':'isolated-test','size':2*1024**3,'mounts':[str(b)]}]
            x.quiesce=lambda:([],False);x.resume=lambda *_:None
            x.status=lambda phase,**fields:x.save(x.STATE/'status.json',dict(phase=phase,**fields),0o644)
            real=x.run
            def run(args):
                if args[:2]==['systemctl','daemon-reload']:return ''
                if args==['mount',str(a)]:return real(['mount',loops[1] if 'UUID=' in x.FSTAB.read_text() else loops[0],str(a)])
                if 'render_dashboard.py' in ' '.join(args):return ''
                return real(args)
            x.run=run
            p=x.plan(uuid);x.save(x.PRIVATE/'job.json',{'plan_id':p['plan_id']});x.worker()
            assert json.loads((x.STATE/'status.json').read_text())['phase']=='verified'
            assert hashlib.sha256((b/'books/sample.pdf').read_bytes()).hexdigest()==before
            old_fstab=x.FSTAB.read_text();fault=[True]
            def broken_mount(args):
                if args==['mount',str(a)] and 'UUID=' in x.FSTAB.read_text() and fault[0]:
                    fault[0]=False;raise ValueError('Injected external mount failure')
                return run(args)
            x.run=broken_mount
            try:x.switch();raise AssertionError('Injected failure did not happen')
            except ValueError as e:assert 'Injected external mount failure' in str(e)
            assert x.FSTAB.read_text()==old_fstab
            assert hashlib.sha256((a/'books/sample.pdf').read_bytes()).hexdigest()==before
            # Re-present the verified destination after rollback, then retry.
            real(['mount',loops[1],str(b)]);x.run=run
            x.status('verified',plan_id=p['plan_id'])
            x.switch();assert json.loads((x.STATE/'status.json').read_text())['phase']=='ready'
            assert real(['findmnt','-n','-o','UUID','--mountpoint',str(a)])==uuid
            assert hashlib.sha256((a/'books/sample.pdf').read_bytes()).hexdigest()==before
            # Simulate the next mount using the persisted UUID selection.
            real(['umount',str(a)]);run(['mount',str(a)])
            assert hashlib.sha256((a/'books/sample.pdf').read_bytes()).hexdigest()==before
            # The retained system-card image is independently usable.
            real(['mount',loops[0],str(b)])
            assert hashlib.sha256((b/'books/sample.pdf').read_bytes()).hexdigest()==before
            print(json.dumps({'copy_verified':True,'switch_verified':True,'failed_switch_rollback_verified':True,'persisted_mount_verified':True,'original_image_retained':True,'production_drives_changed':False}))
        finally:
            for mount in [a,b]:subprocess.run(['umount',str(mount)],capture_output=True)
            for loop in loops:subprocess.run(['losetup','-d',loop],capture_output=True)

if __name__=='__main__':main(sys.argv[1])
