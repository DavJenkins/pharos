#!/usr/bin/python3
"""Install optional owner-controlled DNS HTTPS setup. Does not request a certificate."""
from pathlib import Path
import grp
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def install(path, content, mode=0o644):
    if path.is_symlink(): raise ValueError('Unexpected symlink: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as stream:
        temporary=Path(stream.name);stream.write(content.encode() if isinstance(content,str) else content)
    temporary.chmod(mode);os.chown(temporary,0,0);temporary.replace(path)

UNIT='''[Unit]
Description=Data Ark owner-controlled DNS certificate setup
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/dataark-https-worker
TimeoutStartSec=40min
TimeoutStopSec=10
KillMode=control-group
UMask=0077
Nice=10
MemoryMax=256M
StandardOutput=journal
StandardError=journal
'''
RECONCILE='''[Unit]
Description=Reconcile Data Ark optional HTTPS state after startup
After=local-fs.target
Before=dataark.service
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/dataark-https-reconcile
UMask=0077
[Install]
WantedBy=multi-user.target
'''

def main():
    if os.geteuid()!=0 or ROOT!=Path('/opt/dataark'): raise SystemExit('Run as root from /opt/dataark')
    for p in ['/usr/bin/certbot','/usr/bin/openssl','/usr/bin/curl','/usr/sbin/visudo','/usr/sbin/apache2ctl']:
        if not Path(p).is_file():raise SystemExit('Missing required program: '+p)
    if not Path('/etc/dataark/network-admin.json').is_file():raise SystemExit('Install caretaker authentication first')
    for folder,mode in [(Path('/etc/dataark/https'),0o700),(Path('/var/lib/dataark/https'),0o755)]:
        if folder.is_symlink():raise ValueError('Unexpected HTTPS state directory')
        folder.mkdir(parents=True,exist_ok=True);os.chown(folder,0,0);folder.chmod(mode)
    source=(ROOT/'tools/https_helper.py').read_bytes();compile(source,'https_helper.py','exec')
    rule='admin ALL=(root) NOPASSWD: /usr/local/libexec/dataark-https ""\n'
    with tempfile.NamedTemporaryFile(mode='w') as f:
        f.write(rule);f.flush();subprocess.run(['/usr/sbin/visudo','-cf',f.name],check=True)
    install(Path('/usr/local/lib/dataark_https.py'),source)
    for name,function in [('dataark-https','helper_main'),('dataark-https-worker','worker_main'),('dataark-https-auth','auth_main'),('dataark-https-reconcile','reconcile_main')]:
        install(Path('/usr/local/libexec')/name,"#!/usr/bin/python3\nimport sys\nsys.path.insert(0,'/usr/local/lib')\nfrom dataark_https import "+function+"\n"+function+"()\n",0o755)
    install(Path('/etc/sudoers.d/dataark-https'),rule,0o440)
    install(Path('/etc/systemd/system/dataark-https-setup.service'),UNIT)
    install(Path('/etc/systemd/system/dataark-https-reconcile.service'),RECONCILE)
    dns=Path('/etc/dataark/https/local-dns.conf')
    if not dns.exists():install(dns,'# Managed by Data Ark optional HTTPS\n')
    portal=Path('/etc/dataark/portal-dns.conf')
    include='conf-file=/etc/dataark/https/local-dns.conf\n'
    if portal.is_file() and include not in portal.read_text():
        previous=portal.read_bytes();install(portal,previous.decode()+include)
        try:subprocess.run(['/usr/sbin/dnsmasq','--test','--conf-file='+str(portal)],check=True)
        except Exception:install(portal,previous);raise
        subprocess.run(['/usr/bin/systemctl','try-restart','dataark-portal-dns.service'],check=True)
    subprocess.run(['/usr/bin/systemctl','daemon-reload'],check=True)
    subprocess.run(['/usr/bin/systemctl','enable','--now','dataark-https-reconcile.service'],check=True)
    print('Optional HTTPS setup installed. No certificate requested, no domain assigned, and HTTP remains available.')

if __name__=='__main__':main()
