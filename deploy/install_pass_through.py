#!/usr/bin/env python3
"""Install default-off AP forwarding, without restarting network connections."""
import json
import os
from pathlib import Path
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from deploy.install_portal import run, atomic

MARKER = '# Managed by Data Ark pass-through v1'
RULES = MARKER + '''
add table inet dataark_forward
flush table inet dataark_forward
add set inet dataark_forward clients { type ether_addr; flags timeout; timeout 6h; }
add set inet dataark_forward addresses { type ipv4_addr; flags timeout; timeout 6h; }
add chain inet dataark_forward gate { type filter hook forward priority -10; policy accept; }
# Preserve published local Kiwix (Docker DNAT) and its replies.
add rule inet dataark_forward gate iifname "wlan0" ct status dnat tcp dport 8080 return
add rule inet dataark_forward gate oifname "wlan0" ct status dnat tcp sport 8080 return
add rule inet dataark_forward gate iifname "wlan0" ether saddr @clients ip saddr @addresses return
add rule inet dataark_forward gate oifname "wlan0" ip daddr @addresses return
# IPv6 forwarding is blocked too; enabling this control permits IPv4 internet.
add rule inet dataark_forward gate iifname "wlan0" reject with icmpx type admin-prohibited
add rule inet dataark_forward gate oifname "wlan0" reject with icmpx type admin-prohibited
'''
UNIT = 'dataark-pass-through.service'
SERVICE = MARKER + '''
[Unit]
Description=Data Ark default-off AP internet forwarding
After=nftables.service netfilter-persistent.service
Before=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/usr/sbin/nft -f /etc/dataark/pass-through.nft
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
'''
FILES = {
    Path('/etc/dataark/pass-through.nft'):(RULES.encode(),0o644),
    Path('/etc/systemd/system')/UNIT:(SERVICE.encode(),0o644),
    Path('/etc/sudoers.d/dataark-pass-through'):(b'admin ALL=(root) NOPASSWD: /usr/local/libexec/dataark-pass-through ""\n',0o440),
    Path('/usr/local/libexec/dataark-pass-through'):((ROOT/'tools/pass_through_helper.py').read_bytes(),0o755),
}

def restore(backup):
    meta=json.loads((backup/'state.json').read_text())
    run(['systemctl','disable','--now',UNIT],check=False)
    current=run(['nft','list','table','inet','dataark_forward'],check=False)
    script=('delete table inet dataark_forward\n' if current.returncode==0 else '')+meta['table']
    if script: run(['nft','-f','-'],input=script)
    for path,item in meta['files'].items():
        if item is None: Path(path).unlink(missing_ok=True)
        else: atomic(Path(path),(backup/item['name']).read_bytes(),item['mode'])
    run(['systemctl','daemon-reload'])
    if meta['enabled']: run(['systemctl','enable',UNIT])
    # Do not restart the old unit: that would erase the restored allowlist.
    print('Restored previous forwarding configuration.')

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rollback',type=Path)
    args=parser.parse_args()
    if os.geteuid()!=0 or ROOT!=Path('/opt/dataark'):
        raise SystemExit('Run with sudo python3 deploy/install_pass_through.py on the Pi.')
    if args.rollback:
        backup=args.rollback.resolve()
        if backup.parent!=Path('/var/backups/dataark-pass-through') or backup.stat().st_uid!=0:
            raise SystemExit('Use the root-owned backup printed by this installer.')
        restore(backup); return
    run(['systemctl','is-active','--quiet','dataark-portal-dns.service'])
    if run(['systemctl','show','dataark.service','-p','User','--value']).stdout.strip()!='admin':
        raise SystemExit('Expected API account admin.')
    profile=run(['nmcli','-g','connection.interface-name,ipv4.method,ipv4.addresses','connection','show','DataArk']).stdout.splitlines()
    if profile!=['wlan0','shared','192.168.4.1/24']:
        raise SystemExit('Unexpected AP profile; no changes made.')
    compile(FILES[Path('/usr/local/libexec/dataark-pass-through')][0],'<helper>','exec')
    unit_path = Path('/etc/systemd/system')/UNIT
    if unit_path.exists() and not unit_path.read_text().startswith(MARKER):
        raise SystemExit('Refusing an unmanaged forwarding service.')
    for path in FILES:
        if path.is_symlink(): raise SystemExit('Unexpected symlink: '+str(path))
        if path.exists() and not (Path('/etc/systemd/system')/UNIT).exists():
            raise SystemExit('Refusing pre-existing unmanaged file: '+str(path))
    previous=run(['nft','list','table','inet','dataark_forward'],check=False)
    if previous.returncode==0 and not (Path('/etc/systemd/system')/UNIT).exists():
        raise SystemExit('Unmanaged forwarding table already exists.')
    run(['nft','-c','-f','-'],input=RULES)
    with tempfile.NamedTemporaryFile() as check:
        check.write(FILES[Path('/etc/sudoers.d/dataark-pass-through')][0]);check.flush()
        run(['visudo','-cf',check.name])
    parent=Path('/var/backups/dataark-pass-through');parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    backup=Path(tempfile.mkdtemp(dir=parent))
    meta={'files':{},'table':previous.stdout if previous.returncode==0 else '',
          'enabled':run(['systemctl','is-enabled','--quiet',UNIT],check=False).returncode==0}
    for i,path in enumerate(FILES):
        meta['files'][str(path)]=None
        if path.exists():
            (backup/str(i)).write_bytes(path.read_bytes())
            meta['files'][str(path)]={'name':str(i),'mode':path.stat().st_mode & 0o777}
    (backup/'state.json').write_text(json.dumps(meta))
    print(f'Configuration backup: {backup}',flush=True)
    try:
        for path,(data,mode) in FILES.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            atomic(path,data,mode)
        run(['systemctl','daemon-reload'])
        run(['systemctl','enable',UNIT])
        run(['systemctl','restart',UNIT])
        run(['nft','list','table','inet','dataark_forward'])
    except Exception:
        restore(backup); raise
    print('AP internet forwarding is OFF by default. Local Ark services remain available.')
    print('Deploy/restart the API and use the upper-right per-device toggle.')
    print('Opt-ins expire after six hours and reset on reboot or firewall-service restart.')
    print(f'Undo: sudo python3 deploy/install_pass_through.py --rollback {backup}')

if __name__=='__main__': main()
