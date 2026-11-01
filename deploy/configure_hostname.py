"""Keep Debian local hostname resolution and cloud-init ownership consistent."""
import re,shutil
from pathlib import Path

def configure(name,root=Path('/')):
 if not re.fullmatch(r'[a-z][a-z0-9-]{0,61}[a-z0-9]',name):raise ValueError('Invalid hostname')
 hosts=root/'etc/hosts';text=hosts.read_text()
 lines=text.splitlines();replacement='127.0.1.1 '+name
 found=False;result=[]
 for line in lines:
  if line.split()[:1]==['127.0.1.1']:
   if not found:result.append(replacement);found=True
  else:result.append(line)
 if not found:result.append(replacement)
 backup=root/'var/backups/dataark-bootstrap';backup.mkdir(parents=True,exist_ok=True)
 if not (backup/'hosts.before-hostname').exists():shutil.copy2(hosts,backup/'hosts.before-hostname')
 hosts.write_text('\n'.join(result)+'\n')
 cloud=root/'etc/cloud/cloud.cfg.d'
 if cloud.is_dir():(cloud/'99-dataark-hostname.cfg').write_text('# Data Ark owns hostname and its local hosts entry.\npreserve_hostname: true\nmanage_etc_hosts: false\n')
 return name

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('hostname');a=p.parse_args();print(configure(a.hostname))
