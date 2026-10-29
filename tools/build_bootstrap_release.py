#!/usr/bin/env python3
"""Build a public bootstrap download from a verified kit and committed source.
Does not install, format media, publish a release or copy appliance credentials.
"""
from pathlib import Path
import argparse,hashlib,io,json,subprocess,tarfile,tempfile,gzip,re
import yaml
ROOT=Path(__file__).resolve().parents[1]

def sha(data):return hashlib.sha256(data).hexdigest()
def archive_bytes(files):
 stream=io.BytesIO()
 with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as zipped:
  with tarfile.open(fileobj=zipped,mode='w') as tar:
   for name,(data,mode) in sorted(files.items()):
    item=tarfile.TarInfo(name);item.size=len(data);item.mode=mode;item.mtime=0;tar.addfile(item,io.BytesIO(data))
 return stream.getvalue()
def inspect_config(value):
 if isinstance(value,dict):
  for key,item in value.items():
   if str(key).lower() in {'password','token','secret','private_key','integration_token','ha_token'} and item:raise ValueError('Credential field in public configuration: '+str(key))
   inspect_config(item)
 elif isinstance(value,list):
  for item in value:inspect_config(item)
 elif isinstance(value,str) and value.startswith(('https://','http://')):
  from urllib.parse import urlsplit
  if urlsplit(value).username or urlsplit(value).password:raise ValueError('Credentials in configuration URL')

def build(input_kit,version,output,source_ref='HEAD'):
 if not re.fullmatch(r'[0-9A-Za-z][0-9A-Za-z._-]*',version):raise ValueError('Use a filename-safe release version')
 output=Path(output);output.mkdir(parents=True,exist_ok=True)
 with tarfile.open(input_kit) as incoming:
  files={}
  for item in incoming.getmembers():
   if item.isdir():continue
   if not item.isfile() or item.name.startswith('/') or '..' in Path(item.name).parts:raise ValueError('Unsafe input kit member')
   files[item.name]=incoming.extractfile(item).read()
 old=json.loads(files['DATA-ARK-RECOVERY/kit.json'])
 for name,key in [('dataark-source.tar.gz','source_sha256'),('bootstrap_stock_pi.py','bootstrap_sha256'),('pmtiles','pmtiles_sha256')]:
  if sha(files['DATA-ARK-RECOVERY/'+name])!=old[key]:raise ValueError('Input checksum mismatch: '+name)
 public=yaml.safe_load(files['DATA-ARK-CONFIG/config/content/public-manifest.yaml']);assert 'bugout' not in public;inspect_config(public)
 git=['git','-c','safe.directory='+str(ROOT),'-c','core.autocrlf=false','-C',str(ROOT)]
 revision=subprocess.check_output(git+['rev-parse',source_ref],text=True).strip()
 current=subprocess.check_output(git+['archive','--format=tar',revision])
 with tarfile.open(fileobj=io.BytesIO(current)) as archive:
  source={m.name:(archive.extractfile(m).read(),m.mode) for m in archive.getmembers() if m.isfile()}
 with tarfile.open(fileobj=io.BytesIO(files['DATA-ARK-RECOVERY/dataark-source.tar.gz'])) as frozen:
  compared=0
  for item in frozen.getmembers():
   if item.isfile() and (item.name.endswith(('.py','.sh')) or item.name=='requirements.txt'):
    if source.get(item.name,(None,))[0]!=frozen.extractfile(item).read():raise ValueError('Tested executable source changed: '+item.name)
    compared+=1
 # The combined authoring manifest can contain private household tasks. Public
 # downloads use the already exported public manifest in both locations.
 source['dataark.yaml']=(yaml.safe_dump(public,sort_keys=False,allow_unicode=True).encode(),0o644)
 payload={name:(data,0o644) for name,data in files.items() if name.startswith('DATA-ARK-CONFIG/')}
 for name,(data,_) in payload.items():
  if name.endswith(('.yaml','.yml','.json')):inspect_config(json.loads(data) if name.endswith('.json') else yaml.safe_load(data))
 source_zip=archive_bytes(source)
 payload['DATA-ARK-RECOVERY/dataark-source.tar.gz']=(source_zip,0o644)
 coordinator=source['deploy/bootstrap_stock_pi.py'][0]
 payload['DATA-ARK-RECOVERY/bootstrap_stock_pi.py']=(coordinator,0o644)
 site=json.loads(source['config/stock-pi.json'][0]);inspect_config(site)
 payload['DATA-ARK-RECOVERY/site.json']=(json.dumps(site,indent=2).encode()+b'\n',0o644)
 for name in ['pmtiles','PMTILES-LICENSE.txt','PMTILES-NOTICE.txt']:
  payload['DATA-ARK-RECOVERY/'+name]=(files['DATA-ARK-RECOVERY/'+name],0o755 if name=='pmtiles' else 0o644)
 metadata={'schema':1,'version':version,'source_revision':revision,'source_sha256':sha(source_zip),'bootstrap_sha256':sha(coordinator),'pmtiles_sha256':sha(files['DATA-ARK-RECOVERY/pmtiles']),'status':'experimental_preview','credentials_included':False,'device_identity_included':False,'public_manifest_only':True,'validated_runtime_source':old['source_revision'],'validated_executable_files_unchanged':compared}
 payload['DATA-ARK-RECOVERY/kit.json']=(json.dumps(metadata,indent=2).encode()+b'\n',0o644)
 payload['START-ARK.sh']=(b'#!/bin/sh\nset -eu\nHERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec python3 "$HERE/DATA-ARK-RECOVERY/bootstrap_stock_pi.py" --kit "$HERE/DATA-ARK-RECOVERY" "$@"\n',0o755)
 readme=f'''# Data Ark bootstrap {version}\n\nA public configuration and software kit for building a Data Ark. Clean Debian 13 ARM64 installation, authentication, public file serving and reboot have passed a single uninterrupted software-phase replay, plus 43 regression tests.\n\n## Start\n\n1. Start with Raspberry Pi OS 64-bit based on Debian 13, primary account admin (UID 1000), and internet via Ethernet or a second Wi-Fi adapter.\n2. This download is a .tar.gz archive, not a disk image. Extract its files onto a separate drive already formatted as ext4, exFAT or NTFS. Ensure it is mounted and owned by admin. The installer does not format drives.\n3. In a local terminal, run `sudo bash START-ARK.sh` to preview, then `sudo bash START-ARK.sh --apply` to install. Review the plan and enter INSTALL. A separate caretaker password is requested privately.\n\nContent is chosen separately after setup: None, Minimal, Recommended or Full. Downloads use the Ark's network and free space.\n\nThe download includes public source, readable configuration, the PMTiles CLI and its license. OS images, system packages, Python/container dependencies and library content are acquired separately; installation needs internet. Every appliance establishes its own private identity.\n\nPreview release: physical Pi validation is the next step.\n\nSource: https://github.com/DavJenkins/pharos/tree/{revision}\nGuide: https://www.dejsoftware.com/data-ark/installation/\nResults: https://github.com/DavJenkins/pharos/blob/2506c8215dd079799a5f29ce27d278a6ca92d444/docs/20-Administration/FrozenBootstrapReplay.md\n'''
 payload['README.md']=(readme.encode(),0o644)
 manifest={**metadata,'files':{name:{'bytes':len(data),'sha256':sha(data)} for name,(data,_) in sorted(payload.items())}}
 payload['MANIFEST.json']=(json.dumps(manifest,indent=2).encode()+b'\n',0o644)
 body=archive_bytes(payload);name='data-ark-bootstrap-'+version+'.tar.gz';path=output/name;path.write_bytes(body)
 (output/'SHA256SUMS').write_text(sha(body)+'  '+name+'\n',encoding='utf-8')
 (output/'release-manifest.json').write_text(json.dumps({'version':version,'source_revision':revision,'asset':name,'bytes':len(body),'sha256':sha(body),'channel':'preview','validated_executable_files_unchanged':compared},indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'asset':str(path),'bytes':len(body),'sha256':sha(body),'validated_executable_files_unchanged':compared},indent=2))
 return path
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-kit',type=Path,required=True);p.add_argument('--version',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-ref',default='HEAD');a=p.parse_args();build(a.input_kit,a.version,a.output,a.source_ref)
