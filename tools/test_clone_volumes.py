"""Isolated file-backed-volume acceptance of the clone copy worker, not Pi recovery."""
from pathlib import Path
import json, os, shutil, subprocess, sys, tarfile, tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if os.geteuid()!=0 or '--apply' not in sys.argv:
    raise SystemExit('Run with sudo and --apply to create, mount and remove two temporary image files. No physical drives are changed.')
from tools import clone_drive as c, content_profile
from tools import replicate_drive

base=Path(tempfile.mkdtemp(prefix='dataark-clone-volume-proof-',dir='/var/tmp'))
mounts=[]
def run(args): subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
try:
    for name,size in [('source',128*1024**2),('destination',3*1024**3)]:
        image=base/(name+'.img')
        with image.open('wb') as stream: stream.truncate(size)
        run(['mkfs.ext4','-q','-F',str(image)])
        point=base/name; point.mkdir()
        run(['mount','-o','loop',str(image),str(point)]);mounts.append(point)
    source=base/'source'; target=base/'destination'
    for name in ['communication/demo.txt','preparedness/example.pdf','radio-study/questions.json']:
        path=source/name;path.parent.mkdir(exist_ok=True);path.write_bytes((name+'\n').encode()*1000)
    snapshot=content_profile.read(ROOT/'config/content/public-manifest.yaml')
    def export(folder):
        shutil.copytree(ROOT/'config/content',folder,dirs_exist_ok=True)
    with patch.object(c,'SOURCE',source), patch.object(c,'STATUS',base/'status'), patch.object(c,'public_manifest',return_value=snapshot), patch.object(content_profile,'export',side_effect=export):
        plan=c.build_plan(target,'fit')
        assert sum(len(u['files']) for u in plan['selected'])==3
        original=c.copy_file
        calls=[0]
        def interrupted(*args,**kwargs):
            calls[0]+=1
            if calls[0]==2: raise InterruptedError('simulated power interruption between files')
            return original(*args,**kwargs)
        with patch.object(c,'copy_file',side_effect=interrupted):
            try:c.apply(plan,plan['plan_id'])
            except InterruptedError:pass
            else:raise AssertionError('interruption was not injected')
        assert c.status()['state']=='interrupted'
        resumed=c.build_plan(target,'fit')
        assert resumed['plan_id']==plan['plan_id']
        result=c.apply(resumed,resumed['plan_id'],True)
        assert result['state']=='ready' and result['files_complete']==3
        report=json.loads((target/'CLONE-REPORT.json').read_text())
        for item in report['files']:
            assert c.digest(target/item['path'])==c.digest(source/item['path'])==item['sha256']
        assert not (target/'DATA-ARK-RECOVERY/wifi-roles.json').exists()
        with tarfile.open(target/'DATA-ARK-RECOVERY/dataark-source.tar.gz') as archive:
            import yaml
            public=yaml.safe_load(archive.extractfile('dataark.yaml'))
            assert 'bugout' not in public
            assert archive.getmember('tools/clone_drive.py').isfile()
        assert not c.inspect_target(target)['eligible']
        run(['sync'])
        run(['umount',str(target)]);mounts.remove(target)
        run(['mount','-o','loop,ro',str(base/'destination.img'),str(target)]);mounts.append(target)
        for item in report['files']:assert c.digest(target/item['path'])==item['sha256']
        evidence={'state':'passed','files':3,'bytes':report['files'] and sum(x['bytes'] for x in report['files']),
                  'interrupted_and_resumed':True,'sha256_after_readonly_remount':True,
                  'public_source_archive_checked':True,'real_media_untouched':True,'plan_id':plan['plan_id']}
        Path('/var/tmp/dataark-clone-proof-result.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps(evidence,indent=2))
finally:
    for point in reversed(mounts):
        subprocess.run(['umount',str(point)],check=True)
    shutil.rmtree(base)
