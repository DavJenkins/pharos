#!/usr/bin/python3
"""Build a signed software-only package from an explicit payload directory."""
import argparse
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from software_update import allowed,digest,MAX_BYTES,REV,ID


def build(payload,baseline,requirements,signing_key,output,release,revision,removals=()):
    if not ID.fullmatch(release) or not REV.fullmatch(revision):raise ValueError('Invalid release identity')
    files={}
    for path in sorted(payload.rglob('*')):
        if path.is_symlink():raise ValueError('Payload symlinks are forbidden')
        if not path.is_file():continue
        name=path.relative_to(payload).as_posix()
        if not allowed(name):raise ValueError('Unsupported software payload path: '+name)
        files[name]={'sha256':digest(path),'bytes':path.stat().st_size}
    if not files or sum(v['bytes'] for v in files.values())>MAX_BYTES:raise ValueError('Invalid payload size')
    if any(not allowed(name) for name in removals):raise ValueError('Invalid removal path')
    manifest={'schema':1,'release':release,'sequence':baseline['sequence']+1,'source_revision':revision,
        'base_revision':baseline['revision'],'profiles':[baseline['profile']],'requirements_sha256':digest(requirements),
        'configuration_schema':1,'migrations':[],'files':files,'removals':list(removals)}
    raw=(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n').encode()
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp);(folder/'manifest.json').write_bytes(raw)
        subprocess.run(['/usr/bin/openssl','pkeyutl','-sign','-inkey',str(signing_key),'-rawin','-in',str(folder/'manifest.json'),'-out',str(folder/'manifest.sig')],check=True,capture_output=True)
        with tarfile.open(output,'w:gz',format=tarfile.USTAR_FORMAT) as archive:
            for name,value in [('manifest.json',raw),('manifest.sig',(folder/'manifest.sig').read_bytes())]:
                info=tarfile.TarInfo(name);info.size=len(value);info.mode=0o600;archive.addfile(info,io.BytesIO(value))
            for name in files:archive.add(payload/name,arcname='payload/'+name,recursive=False)
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('payload','baseline','requirements','signing-key','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--release',required=True);p.add_argument('--revision',required=True);p.add_argument('--remove',action='append',default=[])
    a=p.parse_args();build(a.payload,json.loads(a.baseline.read_text()),a.requirements,a.signing_key,a.output,a.release,a.revision,a.remove)
    print(a.output)
