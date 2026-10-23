#!/usr/bin/env python3
"""Install encrypted Wayland VNC using existing Linux PAM login; no password migration."""
from pathlib import Path
import os,pwd,subprocess
ROOT=Path(__file__).resolve().parents[1]
def run(*args,**kw):return subprocess.run(args,check=True,**kw)
def main():
    if os.geteuid()!=0:raise SystemExit('Run as root')
    owner=pwd.getpwnam('admin');config=Path('/home/admin/.config/dataark-vnc');config.mkdir(parents=True,exist_ok=True)
    os.chown(config,owner.pw_uid,owner.pw_gid);config.chmod(0o700)
    key=config/'tls.key';cert=config/'tls.crt'
    if not key.exists() and not cert.exists():
        run('openssl','req','-x509','-newkey','rsa:3072','-sha256','-nodes','-days','365','-keyout',str(key),'-out',str(cert),'-subj','/CN=dataark','-addext','subjectAltName=DNS:dataark,DNS:dataark.local,IP:192.168.4.1',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if not key.is_file() or not cert.is_file():raise SystemExit('Incomplete VNC identity; inspect instead of replacing it')
    (config/'config').write_text('port=5901\nenable_auth=true\nenable_pam=true\nrelax_encryption=false\nallow_broken_crypto=false\nprivate_key_file='+str(key)+'\ncertificate_file='+str(cert)+'\n')
    for p in config.iterdir():os.chown(p,owner.pw_uid,owner.pw_gid);p.chmod(0o600)
    helper=Path('/usr/local/libexec/dataark-vnc');helper.write_bytes((ROOT/'deploy/vnc/launch_vnc.py').read_bytes());helper.chmod(0o755)
    run('systemctl','disable','--now','x11vnc.service','wayvnc.service','wayvnc-control.service')
    run('systemctl','mask','wayvnc.service','wayvnc-control.service')
    Path('/etc/systemd/system/dataark-vnc.service').write_bytes((ROOT/'deploy/vnc/dataark-vnc.service').read_bytes())
    run('systemctl','daemon-reload');run('systemctl','enable','dataark-vnc.service');run('systemctl','restart','dataark-vnc.service')
    public=ROOT/'app/static/legal/vnc-certificate.crt';public.write_bytes(cert.read_bytes());public.chmod(0o644)
    run('openssl','x509','-in',str(cert),'-noout','-fingerprint','-sha256','-enddate')
if __name__=='__main__':main()
