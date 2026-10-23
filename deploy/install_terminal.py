#!/usr/bin/env python3
"""Install the reviewed terminal-only HTTPS configuration after caretaker approval."""
from pathlib import Path
import argparse, ipaddress, json, os, pwd, subprocess
ROOT=Path(__file__).resolve().parents[1]
def run(*args,**kwargs): return subprocess.run(args,check=True,**kwargs)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enable',action='store_true',help='Enable approved admin shell access on hotspot/private LAN')
    args=parser.parse_args()
    if not args.enable: raise SystemExit('Review deploy/terminal/dataark-terminal.service, then explicitly use --enable.')
    if os.geteuid()!=0: raise SystemExit('Run as root.')
    account=pwd.getpwnam('shellinabox');pwd.getpwnam('admin')
    directory=Path('/etc/dataark-terminal');directory.mkdir(exist_ok=True);os.chown(directory,0,0);directory.chmod(0o700)
    key=directory/'private.key';cert=directory/'certificate.crt';bundle=directory/'certificate.pem'
    if not key.exists() and not cert.exists():
        ips={'127.0.0.1','192.168.4.1'}
        interfaces=json.loads(subprocess.check_output(['ip','-j','address'],text=True))
        for interface in interfaces:
            for address in interface.get('addr_info',[]):
                value=ipaddress.ip_address(address['local'])
                if value.version==4 and value.is_private: ips.add(str(value))
        san='DNS:dataark,DNS:dataark.local,'+','.join('IP:'+value for value in sorted(ips))
        run('openssl','req','-x509','-newkey','rsa:3072','-sha256','-nodes','-days','365','-keyout',str(key),'-out',str(cert),'-subj','/CN=dataark','-addext','subjectAltName='+san,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if not key.is_file() or not cert.is_file(): raise SystemExit('Incomplete existing certificate; inspect it rather than silently replacing identity.')
    key.chmod(0o600);cert.chmod(0o644)
    if bundle.exists(): bundle.unlink()  # Obsolete duplicate; Apache uses the root-only original key.
    known=Path('/var/lib/shellinabox/known_hosts');known.parent.mkdir(exist_ok=True)
    known.write_text(''.join('127.0.0.1 '+p.read_text().strip()+'\n' for p in Path('/etc/ssh').glob('ssh_host_*_key.pub')));known.chmod(0o644)
    run('systemctl','mask','--now','shellinabox.service')
    source=ROOT/'deploy/terminal/dataark-terminal.service'
    run('systemd-analyze','verify',str(source))
    target=Path('/etc/systemd/system/dataark-terminal.service');target.write_bytes(source.read_bytes());target.chmod(0o644)
    Path('/etc/apache2/conf-available/dataark-terminal-listen.conf').write_text('Listen 4200\n')
    Path('/etc/apache2/sites-available/dataark-terminal.conf').write_bytes((ROOT/'deploy/terminal/apache-terminal.conf').read_bytes())
    run('a2enmod','ssl','proxy','proxy_http','headers')
    run('a2enconf','dataark-terminal-listen');run('a2ensite','dataark-terminal')
    run('apache2ctl','configtest')
    run('systemctl','daemon-reload');run('systemctl','enable','dataark-terminal.service')
    run('systemctl','restart','dataark-terminal.service');run('systemctl','reload','apache2')
    run('openssl','x509','-in',str(cert),'-noout','-fingerprint','-sha256','-enddate')
if __name__=='__main__': main()
