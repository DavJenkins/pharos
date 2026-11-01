"""Post-install demo verification; run before and after the guest reboot."""
from pathlib import Path
import os,json,subprocess,hashlib,urllib.request,urllib.error,base64,time,sys,re
from urllib.parse import urljoin,urlsplit
root=Path('/opt/dataark');base=Path('/var/lib/dataark/acceptance/clean-demo-20261101');sys.path.insert(0,str(root))
assert os.geteuid()==0 and Path('/etc/dataark-clean-bootstrap-test').is_file()
r={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'checks':{},'http':{}}
def run(a):return subprocess.check_output(a,text=True).strip()
def get(url):
 with urllib.request.urlopen(url,timeout=30) as response:
  data=response.read(16*1024**2);r['http'][url]={'status':response.status,'bytes':len(data)};return data
state=json.loads(Path('/var/lib/dataark/bootstrap.json').read_text());assert state['completed']==['packages','source','storage','python','platform_settings','base_services','content_access','network','content','finish'];r['checks']['ten_phases_completed']=True
profile=root/'config/content/content.yaml';original=Path('/home/admin/demo-candidate/DATA-ARK-CONFIG/config/content/content.yaml')
assert profile.read_bytes()==original.read_bytes()
r['checks']['desired_source_profile_preserved']=True
for unit in ['dataark','apache2','docker','smbd','avahi-daemon']:assert run(['systemctl','is-active',unit])=='active'
for path in ['/','/api/','/docs/','/library.html','/community.html','/recovery.html','/api/docs']:get('http://127.0.0.1'+path)
status=json.loads(get('http://127.0.0.1/api/status'));r['health']=status['status'];assert status['network']['capabilities']['network_mode']=='lan'
inv=json.loads(get('http://127.0.0.1/api/library'));assert 'Demo library' in inv['storage_label'];assert inv['storage_ready'];r['inventory']={k:inv[k] for k in ['storage_label','storage_ready','total_bytes','used_bytes']}
assert inv['total_bytes']<4*1024**3
assert Path('/mnt/storage').is_mount();loop=run(['findmnt','-n','-o','SOURCE','--mountpoint','/mnt/storage']);assert loop.startswith('/dev/loop');assert Path(run(['losetup','-n','-O','BACK-FILE',loop])).resolve()==Path('/var/lib/dataark/demo-library.ext4');assert Path('/var/lib/dataark/demo-library.ext4').stat().st_size==4*1024**3
r['checks']['capped_system_card_mount']=True
from deploy import demo_library
image=Path('/var/lib/dataark/demo-library.ext4');identity=(image.stat().st_ino,image.stat().st_size)
demo_library.create(4)
assert identity==(image.stat().st_ino,image.stat().st_size)
r['checks']['existing_demo_image_reused']=True
config=json.loads((root/'config/demo-library.json').read_text());samples={}
for item in config['samples']:
 p=Path('/mnt/storage')/item['path'];digest=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
 if 'sha256' in item:assert digest==item['sha256'] and p.stat().st_size==item['bytes']
 else:assert digest==hashlib.file_digest((root/item['source']).open('rb'),'sha256').hexdigest()
 samples[item['id']]={'sha256':digest,'bytes':p.stat().st_size}
r['samples']=samples
page=get('http://127.0.0.1/').decode();assert 'Demo library on the system card' in page
from app.services.manifest import load_manifest
manifest=load_manifest(root/'dataark.yaml');assert len(manifest['repositories'])>20;r['repository_count']=len(manifest['repositories'])
for item in config['samples']:
 if item.get('source'):assert get('http://127.0.0.1/library-files/'+item['path']).startswith(b'%PDF-')
archive='http://127.0.0.1:8080/content/wikipedia_en_100_2026-08';article=get(archive).decode();assert '<html' in article.lower()
# Follow one real article link and one archive image, rather than only its welcome page.
links=re.findall(r'href=[\"\x27]([^\"\x27]+)',article)
for link in links:
 target=urljoin(archive+'/',link)
 if urlsplit(target).netloc=='127.0.0.1:8080' and '/content/' in target and not target.endswith(('.css','.js')) and not link.startswith('#'):
  try:article=get(target).decode();r['article_url']=target;break
  except (OSError,UnicodeError):continue
images=re.findall(r'<img[^>]+src=[\"\x27]([^\"\x27]+)',article)
for image in images:
 target=urljoin(r.get('article_url',archive+'/'),image)
 if urlsplit(target).netloc=='127.0.0.1:8080':
  data=get(target)
  if len(data)>100:r['image_url']=target;break
assert r.get('image_url'),'No archive image was verified'
password=Path('/root/demo-test-caretaker').read_text();auth='Basic '+base64.b64encode(('admin:'+password).encode()).decode();url='http://127.0.0.1/api/library/unlock'
req=urllib.request.Request(url,data=b'{}',headers={'Authorization':auth,'Content-Type':'application/json'},method='POST');assert json.load(urllib.request.urlopen(req))['message']
try:urllib.request.urlopen(urllib.request.Request(url,data=b'{}',method='POST'));raise AssertionError('Anonymous unlock accepted')
except urllib.error.HTTPError as e:assert e.code==401
r['checks']['caretaker_authentication']=True
r['checks']['reader_article_and_image']=True;r['status']='passed'
name='post-reboot.json' if (base/'pre-reboot.json').exists() else 'pre-reboot.json';(base/name).write_text(json.dumps(r,indent=2));print(json.dumps({'status':r['status'],'evidence':name,'samples':samples,'repositories':r['repository_count'],'health':r['health']},indent=2))
