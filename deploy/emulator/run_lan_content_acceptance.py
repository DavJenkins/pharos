"""Minimal real-queue content and replacement-volume acceptance in the marked LAN VM."""
from pathlib import Path
import os,sys,json,time,hashlib,subprocess,urllib.request,urllib.error,base64,shutil
assert os.geteuid()==0 and Path('/etc/dataark-lan-acceptance-test').is_file()
assert 'QEMU' in Path('/sys/class/dmi/id/product_name').read_text()
root=Path('/opt/dataark');sys.path.insert(0,str(root))
import yaml
from tools import content_profile as c,recovery_queue as q
from app.services.manifest import load_manifest
from tools.library_removal import serialize
state=Path('/var/lib/dataark-lan-acceptance');report=json.loads((state/'result.json').read_text());assert report['status']=='installed',report
assert set(json.loads(Path('/var/lib/dataark/bootstrap.json').read_text())['completed'])=={'packages','source','storage','python','platform_settings','base_services','content_access','network','content','finish'}
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True,cwd=root).stdout
checks={}
subprocess.run(['systemctl','reset-failed','dataark-lan-acceptance','dataark-lan-install','dataark-lan-content-proof','dataark-lan-minimal-proof','dataark-lan-paired-proof','dataark-lan-replacement-proof','dataark-lan-recovery-proof','dataark-lan-final-recovery-proof','dataark-lan-empty-volume-proof'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def save(phase):report.update(phase=phase,checks=checks);(state/'result.json').write_text(json.dumps(report,indent=2))
def get(path):
 for attempt in range(20):
  try:return urllib.request.urlopen('http://127.0.0.1'+path,timeout=30).read()
  except (OSError,urllib.error.HTTPError):
   if attempt==19:raise
   time.sleep(.5)
for name in ['dataark','apache2','docker','smbd','avahi-daemon','systemd-networkd']:run(['systemctl','is-active','--quiet',name])
for path in ['/','/api/','/docs/SUMMARY.html','/library.html','/community.html','/api/docs']:assert get(path),path
net=json.loads(get('/api/status'))['network'];assert net['capabilities']['network_mode']=='lan';assert net['capabilities']['hotspot'] is False;assert not net['access_point']['interface']
checks['core_services_and_pages']=True;checks['no_hotspot_capability']=True
assert not Path('/etc/NetworkManager/system-connections/DataArk.nmconnection').exists()
assert run(['systemctl','is-active','systemd-networkd']).strip()=='active'
assert subprocess.run(['systemctl','is-active','--quiet','NetworkManager']).returncode!=0
checks['existing_network_manager_retained']=True
password=Path('/root/lan-acceptance-caretaker').read_text();auth='Basic '+base64.b64encode(('admin:'+password).encode()).decode()
req=urllib.request.Request('http://127.0.0.1/api/library/unlock',data=b'{}',headers={'Authorization':auth,'Content-Type':'application/json'},method='POST');assert json.load(urllib.request.urlopen(req))['message']
try:urllib.request.urlopen(urllib.request.Request('http://127.0.0.1/api/library/unlock',data=b'{}',method='POST'));raise AssertionError('Anonymous caretaker unlock accepted')
except urllib.error.HTTPError as e:assert e.code==401
checks['caretaker_authentication']=True
save('preparing_minimal_selection')
folder=root/'config/lan-proof';folder.mkdir(exist_ok=True);manifest=load_manifest(root/'dataark.yaml');repo=next(r for r in manifest['repositories'] if r['id']=='resilience');repo['links']=[{'title':'Read the Forest Service checklist','url':'/library-files/preparedness/forest-service-checklist.pdf'}]
url='https://www.fs.usda.gov/media/21573';sha='b05af6b1db2612070a16636372ae70bebd119e9943e8b2f48cd17937b96b77e6';size=1152413
asset={'id':'lan-proof-checklist','repository_id':'resilience','category':'pdf_reference','title':'Forest Service recreation checklist (2021)','relative_path':'preparedness/forest-service-checklist.pdf','service_endpoint':'/library-files/preparedness/forest-service-checklist.pdf','download_url':url,'expected_hash':sha,'update_policy':'manual','refresh_interval':'never'}
manifest.pop('personalization',None);manifest.pop('dashboard',None)
for collection in manifest['repositories']:
 collection.pop('variants',None);collection.pop('preferred_variant',None)
manifest['assets']=[asset];(folder/'public-manifest.yaml').write_text(serialize(manifest))
profile={'schema':1,'name':'LAN acceptance minimal proof','content_root':'/mnt/storage','manifest':'public-manifest.yaml','reserve_gib':10,'archives':[],'map_files':[],'variant_groups':[],'direct_files':[{'id':asset['id'],'title':asset['title'],'path':asset['relative_path'],'url':url,'bytes':size,'sha256':sha},{'id':'disabled-proof','enabled':False,'path':'preparedness/disabled.pdf','url':url,'bytes':size,'sha256':sha}],'recipes':[{'id':'indexes','enabled':True,'installed_bytes':0,'temporary_bytes':0,'update_headroom_bytes':0}]}
(folder/'content.yaml').write_text(yaml.safe_dump(profile,sort_keys=False));profile_path=folder/'content.yaml'
def restore(directory):
 plan=q.build_plan(profile_path,'minimal');assert plan['capacity']['fits'];assert [j['id'] for j in plan['jobs']]==['lan-proof-checklist','indexes'];
 if not (directory/'queue.json').exists():q.create(plan,plan['plan_id'],directory)
 run([str(root/'venv/bin/python'),'-m','tools.recovery_queue','resume','--state',str(directory)])
 result=q.snapshot(directory);assert result['status']=='complete',result
 data=(Path('/mnt/storage')/asset['relative_path']).read_bytes();assert hashlib.sha256(data).hexdigest()==sha;assert get(asset['service_endpoint'])==data;assert not Path('/mnt/storage/preparedness/disabled.pdf').exists()
 return result
first=restore(state/'initial-queue-v2');checks['minimal_real_download_verified_and_served']=True;checks['disabled_choice_not_downloaded']=True;save('minimal_ready')
c.mirror(profile,folder,Path('/mnt/storage/DATA-ARK-CONFIG'))
# Only a newly hot-plugged, specifically serialized blank test disk may be formatted.
device=Path('/dev/disk/by-id/virtio-DATAARK-LAN-EMPTY');assert device.is_symlink();disk=device.resolve()
boot_source=run(['findmnt','-n','-o','SOURCE','/']).strip();boot_chain=run(['lsblk','-sno','KNAME',boot_source]).split();assert disk.name not in boot_chain
assert run(['findmnt','-n','-o','SOURCE','/mnt/storage']).strip()!=str(disk)
assert int((Path('/sys/class/block')/disk.name/'size').read_text())*512==16*1024**3
if subprocess.run(['blkid',str(disk)],stdout=subprocess.DEVNULL).returncode!=0:
 run(['mkfs.ext4','-q','-L','ARK-LAN-SPARE',str(disk)])
else:
 assert run(['blkid','-s','LABEL','-o','value',str(disk)]).strip() in {'ARK-LAN-SPARE','ARK-LAN-REPLACEMENT'[:16]}
 inspect=Path('/mnt/dataark-lan-empty-inspect');inspect.mkdir(exist_ok=True);run(['mount','-o','ro',str(disk),str(inspect)])
 try:assert not any(p.name!='lost+found' for p in inspect.iterdir())
 finally:run(['umount',str(inspect)])
run(['systemctl','stop','dataark']);run(['docker','stop','kiwix-serve']);original=Path('/mnt/dataark-lan-original');original.mkdir(exist_ok=True);run(['mount','--bind','/mnt/storage',str(original)]);run(['umount','/mnt/storage']);run(['mount',str(disk),'/mnt/storage']);os.chown('/mnt/storage',1000,1000)
assert not any(p.name!='lost+found' for p in Path('/mnt/storage').iterdir());checks['replacement_started_empty']=True
uuid=run(['blkid','-s','UUID','-o','value',str(disk)]).strip();fstab=Path('/etc/fstab');old=fstab.read_text();(state/'fstab-before-replacement').write_text(old);lines=[line for line in old.splitlines() if len(line.split())<2 or line.split()[1]!='/mnt/storage'];fstab.write_text('\n'.join(lines)+'\nUUID='+uuid+' /mnt/storage ext4 defaults,nofail 0 0\n')
second=restore(state/'replacement-queue-v2');checks['system_half_rebuilt_empty_content_volume']=True
from tools.replicate_drive import kit_files
meta=kit_files(Path('/mnt/storage'),profile=profile_path,platform_profile='debian13-arm64-lan');assert meta['platform_profile']=='debian13-arm64-lan';checks['replacement_content_has_regenerated_bootstrap_kit']=True
run(['docker','restart','kiwix-serve']);run(['systemctl','start','dataark'])
for attempt in range(30):
 try:get('/api/');break
 except Exception:time.sleep(1)
else:raise RuntimeError('API did not restart')
checks['restored_services_returned']=True;report.update(status='paired_minimal_passed',completed_at=time.time(),minimal_bytes=size,sha256=sha,original_content_mount=str(original),replacement_device=str(disk),remaining_acceptance=['Reboot and offline client checks']);save('paired_minimal_complete');print(json.dumps({'status':report['status'],'checks':checks},indent=2))
