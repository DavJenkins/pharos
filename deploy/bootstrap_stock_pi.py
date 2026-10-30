#!/usr/bin/python3
"""Experimental stock Raspberry Pi OS 64-bit / Debian 13 installer.
No formatting. Defaults to a read-only plan. Fresh-system acceptance pending.
"""
import argparse,fcntl,hashlib,json,os,platform,pwd,re,shutil,subprocess,tarfile,tempfile,time,uuid
from pathlib import Path
try:
 from . import bootstrap_platform as platforms
except ImportError:
 import sys
 sys.path.insert(0,str(Path(__file__).resolve().parent))
 import bootstrap_platform as platforms

def run(args,**kw):return subprocess.run(args,check=True,**kw)
def output(args):return subprocess.check_output(args,text=True).strip()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def atomic(path,text,mode=0o644):
 path.parent.mkdir(parents=True,exist_ok=True);p=path.with_suffix(path.suffix+'.dataark-new');p.write_text(text);p.chmod(mode);p.replace(path)
def validate(c):
 if c.get('schema')!=1 or c.get('admin_user')!='admin' or c.get('content_root')!='/mnt/storage':raise ValueError('First supported layout requires admin and /mnt/storage.')
 b=c['baseline'];platforms.validate(c)
 ap=c.get('hotspot',{})
 if platforms.selected(c)['network_mode']=='hotspot':
  if ap.get('interface')!='wlan0' or ap.get('connection')!='DataArk' or ap.get('subnet')!='192.168.4.1/24' or ap.get('security')!='open':raise ValueError('Existing portal helpers require the documented wlan0/open DataArk layout.')
  if not isinstance(ap.get('ssid'),str) or not 1<=len(ap['ssid'].encode())<=32 or any(ord(x)<32 for x in ap['ssid']):raise ValueError('Invalid SSID')
 if platforms.selected(c)['network_mode']=='hotspot' and not re.fullmatch('[A-Z]{2}',c.get('wifi_country','')):raise ValueError('Use a two-letter regulatory country.')
 if c.get('hostname') not in ('auto','keep') and not re.fullmatch('[a-z][a-z0-9-]{0,61}[a-z0-9]',c.get('hostname','')):raise ValueError('Invalid hostname')
 if not re.fullmatch(r'ghcr\.io/kiwix/kiwix-serve@sha256:[0-9a-f]{64}',c.get('kiwix_image','')):raise ValueError('Kiwix must have a pinned image digest.')
 if not c.get('packages') or any(not re.fullmatch('[a-z0-9][a-z0-9+.-]*',x) for x in c['packages']):raise ValueError('Invalid package list')
 for key in ['anonymous_ftp','restore_missing_content','automatic_archive_updates','automatic_map_updates']:
  if type(c.get(key)) is not bool:raise ValueError('Expected boolean '+key)
def extract_source(archive,target):
 with tarfile.open(archive) as t:
  members=t.getmembers()
  if sum(m.size for m in members)>1024**3:raise ValueError('Source archive exceeds 1 GiB')
  for m in members:
   p=Path(m.name)
   if p.is_absolute() or '..' in p.parts or not (m.isfile() or m.isdir()):raise ValueError('Unsafe source archive member')
  t.extractall(target,members=members,filter='data')
def os_info():
 return dict(line.split('=',1) for line in Path('/etc/os-release').read_text().replace('"','').splitlines() if '=' in line)
def preflight(c,kit,journal):
 errors=[];info=os_info();b=c['baseline']
 if info.get('ID')!=b['os_id'] or info.get('VERSION_ID')!=b['version_id'] or platforms.architecture()!=b['architecture']:errors.append('Operating system or processor does not match the selected platform profile.')
 if b.get('require_raspberry_pi_os') and not Path('/etc/rpi-issue').exists():errors.append('Raspberry Pi OS image marker is missing.')
 try:
  account=pwd.getpwnam('admin')
  if account.pw_uid!=1000:errors.append('First supported image requires the admin account at UID 1000.')
 except KeyError:errors.append('Create the primary admin account with UID 1000 before setup.')
 if Path('/etc/systemd/system/dataark.service').exists() and not journal.exists():errors.append('An existing unmanaged Ark is present. This fresh-install coordinator will not overwrite it.')
 if Path('/opt/dataark').exists() and not journal.exists():errors.append('/opt/dataark already exists without this installer journal.')
 for name in ['dataark-source.tar.gz','kit.json','site.json','pmtiles']:
  if not (kit/name).is_file():errors.append('Missing kit file: '+name)
 if (kit/'kit.json').is_file() and (kit/'dataark-source.tar.gz').is_file():
  meta=json.loads((kit/'kit.json').read_text())
  if sha(kit/'dataark-source.tar.gz')!=meta.get('source_sha256'):errors.append('Source checkpoint checksum mismatch.')
 try:
  routes=json.loads(output(['ip','-j','route','show','default']))
  if not any(r.get('dev') and (platforms.selected(c)['network_mode']=='lan' or r['dev']!=c['hotspot']['interface']) for r in routes):errors.append('An existing upstream route separate from the proposed hotspot is required.')
 except (OSError,subprocess.CalledProcessError,ValueError):errors.append('Cannot verify an upstream route separate from wlan0.')
 if not journal.exists() and shutil.which('ss'):
  listeners=output(['ss','-H','-lunt'])
  if any(re.search(r':(?:80|8000|8080|8081|1053)\s',line) for line in listeners.splitlines()):errors.append('A required web/API/portal port is already in use. Use a fresh target or review conflicting services.')
 if (kit/'kit.json').is_file() and (kit/'pmtiles').is_file():
  if sha(kit/'pmtiles')!=json.loads((kit/'kit.json').read_text()).get('pmtiles_sha256'):errors.append('PMTiles binary checksum mismatch.')
 if (kit/'kit.json').is_file() and (kit/'bootstrap_stock_pi.py').is_file():
  if sha(kit/'bootstrap_stock_pi.py')!=json.loads((kit/'kit.json').read_text()).get('bootstrap_sha256'):errors.append('Bootstrap script checksum mismatch.')
 if (kit/'pmtiles').is_file() and platforms.elf_architecture(kit/'pmtiles')!=b['architecture']:errors.append('The kit PMTiles binary is for another processor architecture.')
 for name,expected in (json.loads((kit/'kit.json').read_text()).get('platform_files',{}) if (kit/'kit.json').is_file() else {}).items():
  if name.startswith('/') or '..' in Path(name).parts or not (kit/name).is_file() or sha(kit/name)!=expected:errors.append('Platform support file failed verification: '+name)
 return errors

class Installer:
 def __init__(self,c,kit,state,journal):self.c=c;self.kit=kit;self.state=state;self.journal=journal;self.repo=Path('/opt/dataark');self.root=Path('/mnt/storage');self.adapter=platforms.DebianAdapter(lambda *args,**kwargs:run(*args,**kwargs))
 def save(self):atomic(self.journal,json.dumps(self.state,indent=2)+'\n',0o600)
 def phase(self,name,fn):
  if name in self.state['completed']:print('Already completed:',name,flush=True);return
  self.state['running']=name;self.save();print('Installing:',name,flush=True)
  try:fn()
  except BaseException as e:self.state['error']=str(e);self.save();raise
  self.state['completed'].append(name);self.state.pop('error',None);self.state['running']=None;self.save()
 def script(self,name,*args):run(['/usr/bin/python3',str(self.repo/'deploy'/name)]+list(args))
 def source(self):
  expected=json.loads((self.kit/'kit.json').read_text())['source_sha256']
  marker=self.repo/'.dataark-bootstrap-source'
  if self.repo.exists():
   if not marker.is_file() or marker.read_text().strip()!=expected:raise RuntimeError('Existing source does not match this interrupted install.')
  else:
   stage=Path(tempfile.mkdtemp(prefix='.dataark-setup-',dir='/opt'))
   try:
    extract_source(self.kit/'dataark-source.tar.gz',stage);(stage/'.dataark-bootstrap-source').write_text(expected+'\n');stage.rename(self.repo)
   finally:
    if stage.exists():shutil.rmtree(stage)
  # Restore public selections and editable source catalogues from the inserted kit.
  mirror=self.kit.parent/'DATA-ARK-CONFIG'
  if not (mirror/'config/content/content.yaml').is_file():raise RuntimeError('The drive has no readable content profile.')
  for relative in ['config/content','deploy/reference']:
   for p in (mirror/relative).rglob('*'):
    if p.is_symlink():raise RuntimeError('Unexpected configuration symlink')
    if p.is_file():target=self.repo/relative/p.relative_to(mirror/relative);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  atomic(self.repo/'config/installed-site.json',json.dumps(self.c,indent=2)+'\n')
  atomic(self.repo/'config/installed-software.json',json.dumps({'revision':json.loads((self.kit/'kit.json').read_text())['source_revision'],'source_sha256':expected},indent=2)+'\n')
  run(['chown','-R','admin:admin',str(self.repo)])
  if not (self.repo/'.git').exists():
   run(['runuser','-u','admin','--','git','-C',str(self.repo),'init','-b','ark-local'])
   run(['runuser','-u','admin','--','git','-C',str(self.repo),'config','user.name','Data Ark local setup'])
   run(['runuser','-u','admin','--','git','-C',str(self.repo),'config','user.email','dataark@localhost'])
   (self.repo/'.git/info/exclude').write_text('.dataark-bootstrap-source\n')
   run(['runuser','-u','admin','--','git','-C',str(self.repo),'add','.'])
   run(['runuser','-u','admin','--','git','-C',str(self.repo),'commit','-m','Initialize from verified Data Ark installation kit'])
   run(['runuser','-u','admin','--','git','-C',str(self.repo),'remote','add','origin','https://github.com/DavJenkins/pharos.git'])

 def packages(self):
  self.adapter.packages(self.c['packages'])
  if platforms.selected(self.c)['network_mode']=='lan':return
  try:pwd.getpwnam('dnsmasq')
  except KeyError:run(['useradd','--system','--home-dir','/var/lib/misc','--no-create-home','--shell','/usr/sbin/nologin','dnsmasq'])
 def storage(self):
  # The kit must be on a distinct, already formatted local content volume.
  device=output(['findmnt','-n','-o','SOURCE','--target',str(self.kit)])
  if not device.startswith('/dev/') or device==output(['findmnt','-n','-o','SOURCE','/']):raise RuntimeError('Kit must be on a separate local content volume, not the system disk.')
  uuid=output(['blkid','-s','UUID','-o','value',device]);fs=output(['blkid','-s','TYPE','-o','value',device])
  if not re.fullmatch('[A-Za-z0-9-]+',uuid) or fs not in ['exfat','ext4','ntfs']:raise RuntimeError('Only existing exFAT, ext4 or NTFS content filesystems are supported.')
  mounted=Path(output(['findmnt','-n','-o','TARGET','--target',str(self.kit)]))
  if self.root.is_mount():
   if self.root.stat().st_dev!=self.kit.stat().st_dev:raise RuntimeError('/mnt/storage is occupied by another filesystem.')
  else:self.root.mkdir(parents=True,exist_ok=True);run(['mount','--bind',str(mounted),str(self.root)])
  if self.root.stat().st_uid!=1000:raise RuntimeError('Content mount must be owned by admin UID 1000. Correct its mount options before continuing.')
  fstab=Path('/etc/fstab');text=fstab.read_text();rows=[x.split() for x in text.splitlines() if x.strip() and not x.lstrip().startswith('#')]
  for row in rows:
   if len(row)>1 and (row[0]=='UUID='+uuid or row[1]=='/mnt/storage') and row[:2]!=['UUID='+uuid,'/mnt/storage']:raise RuntimeError('Existing fstab entry conflicts with the selected content mount; review it manually.')
  if not any(row[:2]==['UUID='+uuid,'/mnt/storage'] for row in rows):
   backup=Path('/var/backups/dataark-bootstrap');backup.mkdir(parents=True,mode=0o700,exist_ok=True);shutil.copy2(fstab,backup/'fstab')
   opts='defaults,nofail,x-systemd.device-timeout=10'
   if fs in ['exfat','ntfs']:opts+=',uid=1000,gid='+str(pwd.getpwnam('admin').pw_gid)+',fmask=0133,dmask=0022'
   if fs=='ntfs':fs='ntfs-3g'
   atomic(fstab,text.rstrip()+'\n# Data Ark content volume\nUUID='+uuid+' /mnt/storage '+fs+' '+opts+' 0 0\n')
  self.kit=self.root/'DATA-ARK-RECOVERY'
 def python(self):
  target=Path('/usr/local/bin/pmtiles')
  if target.exists() and sha(target)!=sha(self.kit/'pmtiles'):raise RuntimeError('Different PMTiles CLI already installed; inspect it before replacement.')
  shutil.copyfile(self.kit/'pmtiles',target);target.chmod(0o755)
  run(['runuser','-u','admin','--','python3','-m','venv',str(self.repo/'venv')]);run(['runuser','-u','admin','--',str(self.repo/'venv/bin/python'),'-m','pip','install','-r',str(self.repo/'requirements.txt')])
  for d in ['updates','maps','library']:
   p=Path('/var/lib/dataark')/d;p.mkdir(parents=True,exist_ok=True);shutil.chown(p,user='admin',group='admin')
 def base_services(self):
  shutil.copyfile(self.repo/'config/content/public-manifest.yaml',self.repo/'dataark.yaml');shutil.chown(self.repo/'dataark.yaml',user='admin',group='admin')
  unit=(self.repo/'deploy/reference/dataark.service').read_text();unit=unit.replace('After=network.target','After=network.target\nRequiresMountsFor=/mnt/storage')
  atomic(Path('/etc/systemd/system/dataark.service'),unit)
  run(['a2enmod','proxy','proxy_http','headers','alias','autoindex','mime','dir'])
  atomic(Path('/etc/apache2/sites-available/000-default.conf'),(self.repo/'deploy/reference/apache-vhost.conf').read_text())
  run(['apache2ctl','configtest']);run(['systemctl','daemon-reload']);run(['systemctl','enable','--now','apache2','docker','smbd','avahi-daemon'])
  run(['systemctl','reload','apache2'])
  run(['docker','pull',self.c['kiwix_image']])
  reader_state=self.root/'.dataark-reader'
  if reader_state.is_symlink():raise RuntimeError('Unexpected reader-state symlink')
  reader_state.mkdir(exist_ok=True)
  atomic(reader_state/'empty.xml','<?xml version="1.0" encoding="UTF-8"?><library version="20110515"></library>\n')
  if subprocess.run(['docker','inspect','kiwix-serve'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
   label=output(['docker','inspect','kiwix-serve','--format','{{index .Config.Labels "org.dataark.bootstrap"}}'])
   if label!=self.state['configuration_sha256']:raise RuntimeError('Unmanaged kiwix-serve container exists.')
   run(['docker','rm','-f','kiwix-serve'])
  run(['docker','run','-d','--name','kiwix-serve','--label','org.dataark.bootstrap='+self.state['configuration_sha256'],'--restart','unless-stopped','-p','8080:8080','-v','/mnt/storage:/data','-v',str(self.repo/'deploy/reference/kiwix-start.sh')+':/usr/local/bin/dataark-start:ro','--entrypoint','/bin/sh',self.c['kiwix_image'],'/usr/local/bin/dataark-start'])
  self.script('install_reliability_logging.py');self.script('install_network_admin.py','--defer-wifi-roles',*(['--read-only-network'] if platforms.selected(self.c)['network_mode']=='lan' else []));self.script('install_library.py');run(['install','-m','644',str(self.repo/'deploy/dataark-recovery.service'),'/etc/systemd/system/dataark-recovery.service']);run(['systemctl','daemon-reload']);self.script('install_usage.py');self.script('install_shell_welcome.py');self.script('install_community.py');self.script('install_https.py')
  run(['bash',str(self.repo/'deploy/deploy-web.sh')]);run(['systemctl','enable','--now','dataark'])
 def content_access(self):
  # Public distribution does not depend on a radio or an AP profile.
  smb=Path('/etc/samba/smb.conf');text=smb.read_text()
  defaults={'Offline-Archives':'path = /mnt/storage\nread only = yes\nguest ok = yes\nbrowseable = yes',
            'Bugout-Staging':'path = /mnt/storage/bugout-drop\nread only = yes\nguest ok = no\nvalid users = admin\nbrowseable = no'}
  for name,body in defaults.items():
   if not re.search(r'^\s*\['+re.escape(name)+r'\]\s*$',text,re.M|re.I):text+='\n['+name+']\n'+body+'\n'
  if text!=smb.read_text():
   backup=Path('/var/backups/dataark-bootstrap');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(smb,backup/'smb.conf.before-share-creation');atomic(smb,text)
  self.script('install_content_access.py')
  if self.c['anonymous_ftp']:self.script('install_ftp.py')
 def platform_settings(self):
  spec=platforms.selected(self.c);roles=self.state.get('network_roles',{})
  atomic(Path('/etc/dataark/platform.json'),json.dumps({'schema':1,'profile':spec['id'],'network_mode':spec['network_mode'],'roles':roles},indent=2)+'\n')
  if spec['network_mode']=='lan':
   atomic(Path('/run/dataark-wifi-roles.json'),json.dumps({'hotspot':'','upstream':roles.get('wifi') or ''})+'\n')
 def network(self):
  if platforms.selected(self.c)['network_mode']=='lan':
   print('Existing LAN connections, interface names, addresses and host name retained. No hotspot or forwarding configuration installed.')
   return
  if 'wlan0' not in output(['nmcli','-g','DEVICE','device']).splitlines():raise RuntimeError('wlan0 is missing.')
  profiles=output(['nmcli','-g','NAME','connection','show']).splitlines()
  if 'DataArk' in profiles:
   if output(['nmcli','-g','connection.uuid','connection','show','DataArk'])!=self.state.get('ap_uuid'):raise RuntimeError('Unmanaged DataArk network profile exists.')
  elif not self.state.get('ap_uuid'):self.state['ap_uuid']=str(uuid.uuid4());self.save()
  self.adapter.country(self.c['wifi_country'],self.c['baseline'].get('require_raspberry_pi_os',False))
  host=self.c['hostname']
  if host=='auto':host='dataark-'+Path('/etc/machine-id').read_text().strip()[:6]
  self.adapter.hostname(host)
  if 'DataArk' not in profiles:run(['nmcli','connection','add','type','wifi','ifname','wlan0','con-name','DataArk','connection.uuid',self.state['ap_uuid'],'ssid',self.c['hotspot']['ssid'],'802-11-wireless.mode','ap','ipv4.method','shared','ipv4.addresses','192.168.4.1/24','ipv6.method','disabled','connection.autoconnect','yes'])
  run(['nmcli','connection','up','DataArk'])
  self.script('install_wifi_roles.py')
  self.script('install_portal.py');self.script('install_pass_through.py');self.script('install_portal_monitor.py')
  role_config=self.kit/'wifi-roles.json'
  if role_config.is_file():
   preference=json.loads(role_config.read_text())
   adapter=preference.get('hotspot_adapter')
   if adapter is not None and not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',adapter):raise ValueError('Invalid saved Wi-Fi adapter identity')
   atomic(Path('/etc/dataark/wifi-roles.json'),json.dumps({'schema':1,'hotspot_adapter':adapter,'fallback':'builtin'})+'\n')
  run(['/usr/local/libexec/dataark-wifi-roles','--boot'])
 def content(self):
  # Device setup approval does not authorize optional content downloads.
  print('Base services are ready. Choose optional content separately at /recovery.html or use tools/recovery_queue.py plan.')
  print('None starts no downloads. Minimal/Recommended/Full require explicit plan acceptance.')
  if self.c['restore_missing_content']:
   print('Legacy restore_missing_content=true is ignored; an approved recovery queue is required.')
 def finish(self):
  print('Automatic download timers remain off until content selection is approved; enable them separately after restoration.')
  run(['systemctl','is-active','--quiet','dataark','apache2','docker'])
  run(['curl','--fail','--retry','10','--retry-connrefused','--retry-delay','1','--max-time','15','--output','/dev/null','http://127.0.0.1/api/'])
  run(['curl','--fail','--retry','10','--retry-connrefused','--retry-delay','1','--max-time','15','--output','/dev/null','http://127.0.0.1/'])
  self.script('install_software_updater.py','--revision',json.loads((self.kit/'kit.json').read_text())['source_revision'],'--profile',self.c.get('platform_profile',platforms.DEFAULT))
  atomic(Path('/var/lib/dataark/bootstrap-readiness.json'),json.dumps({'status':'software_phases_completed_client_acceptance_required','checks_remaining':['Reboot and confirm mount']+(['Hotspot client and captive detection'] if platforms.selected(self.c)['network_mode']=='hotspot' else ['Existing LAN connectivity retained'])+['Offline article and image','Maps/forms/radio tools','Management authentication','Independent fresh-media recovery'],'finished_at':time.time()},indent=2)+'\n')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kit',type=Path);p.add_argument('--site',type=Path);p.add_argument('--profile');p.add_argument('--list-profiles',action='store_true');p.add_argument('--discover',action='store_true');p.add_argument('--accept-plan');p.add_argument('--apply',action='store_true');a=p.parse_args()
 if a.list_profiles:
  print(json.dumps([platforms.profile(p.stem) for p in sorted(platforms.PROFILES.glob('*.json'))],indent=2));return
 if a.discover:print(json.dumps(platforms.discover(),indent=2));return
 if not a.kit:p.error('--kit is required except with --discover')
 kit=a.kit.resolve();site=a.site or kit/'site.json';c=json.loads(site.read_text())
 if a.profile:c=platforms.configure(c,a.profile)
 validate(c)
 journal=Path('/var/lib/dataark/bootstrap.json');plan=platforms.proposal(c,platforms.discover());errors=preflight(c,kit,journal)+plan['issues']
 print(json.dumps(plan,indent=2))
 print('Stages: packages -> source -> existing storage -> Python -> platform settings -> services -> public distribution -> reviewed network -> optional content -> verification.')
 print('No formatting or content removal. Public services use the existing networks. Software downloads require internet.')
 for error in errors:print('BLOCKED:',error)
 if not a.apply:
  import shlex
  args=['sudo','python3',str(Path(__file__).resolve()),'--kit',str(kit)]
  if a.site:args+=['--site',str(a.site)]
  if a.profile:args+=['--profile',a.profile]
  print('Preview only. Reviewed apply command:',shlex.join(args+['--accept-plan',plan['plan_id'],'--apply']));return
 if errors:raise SystemExit('Preflight failed; no installation changes made.')
 if a.accept_plan!=plan['plan_id']:raise SystemExit('Accept the exact current discovery plan with --accept-plan before applying.')
 if os.geteuid()!=0 or not os.isatty(0):raise SystemExit('Run with sudo from a local interactive terminal.')
 if os.environ.get('SSH_CONNECTION') and plan['network_mode']=='hotspot':raise SystemExit('Use the local console for initial hotspot setup.')
 if input('Type INSTALL to apply this reviewed plan: ')!='INSTALL':raise SystemExit('Cancelled.')
 journal.parent.mkdir(parents=True,exist_ok=True);lock=(journal.parent/'bootstrap.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 fingerprint=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest();state=json.loads(journal.read_text()) if journal.exists() else {'completed':[],'configuration_sha256':fingerprint,'kit_source_sha256':json.loads((kit/'kit.json').read_text())['source_sha256'],'network_plan_id':plan['plan_id'],'network_roles':plan['roles']}
 if state.get('configuration_sha256')!=fingerprint:raise SystemExit('Site settings changed since the previous run; review the journal before resuming.')
 if state.get('kit_source_sha256')!=json.loads((kit/'kit.json').read_text())['source_sha256']:raise SystemExit('Installation source changed; use the original kit or review the journal.')
 if state.get('network_plan_id',plan['plan_id'])!=plan['plan_id']:raise SystemExit('Hardware or network assignments changed since setup; review before resuming.')
 state.setdefault('network_roles',plan['roles'])
 installer=Installer(c,kit,state,journal)
 for name in ['packages','source','storage','python','platform_settings','base_services','content_access','network','content','finish']:installer.phase(name,getattr(installer,name))
 print('Software setup completed. Reboot and perform the client acceptance checks for this platform.')
if __name__=='__main__':main()
