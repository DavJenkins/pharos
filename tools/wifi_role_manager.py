#!/usr/bin/python3 -I
"""Root-owned Wi-Fi role transaction, boot reconciliation and timed rollback."""
import fcntl
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time

BASE = Path('/var/lib/dataark/wifi-roles')
PENDING = BASE / 'pending.json'
PREFERENCE = Path('/etc/dataark/wifi-roles.json')
RUNTIME = Path('/run/dataark-wifi-roles.json')
SELF = '/usr/local/libexec/dataark-wifi-roles'
FIELDS = ('connection.interface-name', '802-11-wireless.mac-address')
FILES = ('/etc/dataark/portal-dns.conf', '/etc/dataark/portal.nft', '/etc/dataark/pass-through.nft')

def run(*args, check=True, timeout=40):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                            env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LC_ALL':'C'})
    if check and result.returncode:
        raise ValueError('A network operation failed. The previous assignment will be restored.')
    return result.stdout.strip()

def nm(*args, **kwargs):
    return run('/usr/bin/nmcli', '--wait', '30', *args, **kwargs)

def write(path, value, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.new')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.chmod(mode)
    os.replace(temp, path)

def inventory():
    rows = []
    for path in sorted(Path('/sys/class/net').glob('wlan*')):
        if not re.fullmatch(r'wlan[0-9]+', path.name):
            continue
        device = (path/'device').resolve()
        # Permanent address is independent of connection MAC randomization.
        address = run('/usr/sbin/ethtool', '-P', path.name).split()[-1].lower()
        if not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', address):
            raise ValueError('Cannot identify a Wi-Fi adapter by its permanent address.')
        builtin = '/usb' not in str(device)
        driver = (path/'device/driver').resolve().name
        phy = (path/'phy80211').resolve().name
        info = run('/usr/sbin/iw', 'phy', phy, 'info')
        modes = info.split('Supported interface modes:',1)[-1].split('Band ',1)[0]
        rows.append({'id': address, 'interface': path.name, 'builtin': builtin,
                     'label': ('Built-in Wi-Fi' if builtin else 'USB Wi-Fi') + ' (' + driver + ')',
                     'ap_capable': bool(re.search(r'^\s*\* AP\s*$', modes, re.M))})
    return rows

def choose(rows, preference):
    capable = [r for r in rows if r['ap_capable']]
    ap = next((r for r in capable if r['id'] == preference.get('hotspot_adapter')), None)
    fallback = ap is None
    ap = ap or next((r for r in capable if r['builtin']), None) or next(iter(capable), None)
    if ap is None:
        raise ValueError('No access-point-capable Wi-Fi adapter is available.')
    other = next((r for r in rows if r['id'] != ap['id']), None)
    return ap, other, fallback

def preference():
    try:
        return json.loads(PREFERENCE.read_text())
    except FileNotFoundError:
        return {}

def status():
    rows = inventory()
    ap = nm('-g','connection.interface-name','connection','show','id','DataArk')
    pending = json.loads(PENDING.read_text()) if PENDING.exists() else None
    saved = preference()
    return {'ok':True, 'adapters':rows, 'hotspot':ap,
            'preferred':saved.get('hotspot_adapter'),
            'pending':bool(pending), 'deadline':pending['deadline'] if pending else None,
            'message':'Reconnect and confirm before the countdown expires.' if pending else 'Assignment saved.'}

def snapshot():
    profiles = []
    for uid in nm('-g','UUID','connection','show').splitlines():
        kind = nm('-g','connection.type','connection','show','uuid',uid)
        if kind != '802-11-wireless':
            continue
        profiles.append({'uuid':uid, 'fields':{k:nm('-g',k,'connection','show','uuid',uid) for k in FIELDS}})
    active = []
    for line in nm('-t','-f','UUID,DEVICE','connection','show','--active').splitlines():
        uid, dev = line.split(':',1)
        if dev.startswith('wlan'):
            active.append([uid,dev])
    return {'profiles':profiles, 'active':active,
            'files':{name:Path(name).read_text() for name in FILES},
            'preference':preference(),
            'runtime':json.loads(RUNTIME.read_text()) if RUNTIME.exists() else {'hotspot':'wlan0','upstream':'wlan1'},
            'deadline':time.time()+240}

def publish(ap, other, fallback=False):
    write(RUNTIME, {'hotspot':ap['interface'], 'upstream':other['interface'] if other else '',
                    'fallback':fallback}, 0o644)

def bind(profile, dev):
    nm('connection','modify','uuid',profile, 'connection.interface-name',dev,
       '802-11-wireless.mac-address','')

def policy(ap):
    for name in FILES:
        path = Path(name)
        text = path.read_text()
        text = re.sub(r'\bwlan[0-9]+\b', ap, text)
        temp = path.with_suffix(path.suffix+'.new')
        temp.write_text(text)
        temp.chmod(0o644)
        os.replace(temp,path)
    # Forwarding is reset to OFF; an opt-in on the old adapter is not transferable.
    run('/usr/bin/systemctl','restart','dataark-pass-through.service','dataark-portal-dns.service')
    run('/usr/bin/systemctl','try-restart','dataark-portal-monitor.service',check=False)

def switch(ap, other):
    logging.info('Applying hotspot adapter %s (%s)',ap['interface'],ap['id'])
    old_ap = nm('-g','connection.interface-name','connection','show','id','DataArk')
    ap_uuid = nm('-g','connection.uuid','connection','show','id','DataArk')
    # Move only upstream profiles bound to either participating adapter; retain SSIDs and secrets.
    for uid in nm('-g','UUID','connection','show').splitlines():
        if uid == ap_uuid or nm('-g','connection.type','connection','show','uuid',uid) != '802-11-wireless':
            continue
        dev = nm('-g','connection.interface-name','connection','show','uuid',uid)
        mac = nm('-g','802-11-wireless.mac-address','connection','show','uuid',uid).lower()
        if other and (dev in (old_ap,ap['interface'],other['interface']) or mac in (ap['id'],other['id'])):
            bind(uid,other['interface'])
    for dev in {old_ap,ap['interface'],other['interface'] if other else old_ap}:
        nm('device','disconnect',dev,check=False)
    bind(ap_uuid,ap['interface'])
    publish(ap,other)
    policy(ap['interface'])
    nm('connection','up','uuid',ap_uuid,'ifname',ap['interface'])
    if other:
        # Restore an upstream only if one was active before the role change.
        pending = json.loads(PENDING.read_text()) if PENDING.exists() else {}
        for uid, _ in pending.get('active',[]):
            if uid != ap_uuid:
                nm('connection','up','uuid',uid,'ifname',other['interface'],check=False)

def rollback():
    if not PENDING.exists():
        return
    saved = json.loads(PENDING.read_text())
    logging.warning('Restoring the previous Wi-Fi adapter assignment')
    for dev in [r['interface'] for r in inventory()]:
        nm('device','disconnect',dev,check=False)
    for row in saved['profiles']:
        args = [v for pair in row['fields'].items() for v in pair]
        nm('connection','modify','uuid',row['uuid'],*args)
    for name,text in saved['files'].items():
        Path(name).write_text(text)
    write(PREFERENCE,saved['preference'],0o644)
    write(RUNTIME,saved['runtime'],0o644)
    for uid,dev in saved['active']:
        nm('connection','up','uuid',uid,'ifname',dev,check=False)
    run('/usr/bin/systemctl','restart','dataark-pass-through.service','dataark-portal-dns.service')
    run('/usr/bin/systemctl','try-restart','dataark-portal-monitor.service',check=False)
    PENDING.unlink()

def apply(adapter):
    if PENDING.exists():
        raise ValueError('Confirm or revert the pending assignment first.')
    rows = inventory()
    ap = next((r for r in rows if r['id']==adapter and r['ap_capable']),None)
    if ap is None:
        raise ValueError('Select a present adapter that supports access-point mode.')
    if ap['interface'] == nm('-g','connection.interface-name','connection','show','id','DataArk'):
        write(PREFERENCE,{'schema':1,'hotspot_adapter':ap['id'],'fallback':'builtin'},0o644)
        mirror_preference()
        return status()
    other = next((r for r in rows if r['id']!=ap['id']),None)
    write(PENDING,snapshot())
    # Timer is independent of the web request and survives a disconnected browser.
    run('/usr/bin/systemctl','stop','dataark-wifi-rollback.timer',check=False)
    run('/usr/bin/systemctl','reset-failed','dataark-wifi-rollback.service',check=False)
    run('/usr/bin/systemd-run','--collect','--unit=dataark-wifi-rollback','--on-active=240s',SELF,'--rollback')
    try:
        write(PREFERENCE,{'schema':1,'hotspot_adapter':ap['id'],'fallback':'builtin'},0o644)
        switch(ap,other)
    except Exception:
        rollback()
        raise
    return status()

def mirror_preference():
    kit=Path("/mnt/storage/DATA-ARK-RECOVERY")
    if os.path.ismount("/mnt/storage") and kit.is_dir():
        try:
            write(kit/"wifi-roles.json",preference(),0o644)
        except OSError:
            logging.warning('Assignment saved, but recovery-kit preference could not be refreshed')

def confirm():
    if not PENDING.exists():
        raise ValueError('No adapter change is awaiting confirmation.')
    if time.time() >= json.loads(PENDING.read_text())['deadline']:
        rollback()
        raise ValueError('Confirmation expired. The previous assignment was restored.')
    ap = nm('-g','connection.interface-name','connection','show','id','DataArk')
    if nm('-g','GENERAL.STATE','device','show',ap).split()[0] != '100':
        raise ValueError('The hotspot is not active; the change cannot be confirmed.')
    PENDING.unlink()
    mirror_preference()
    run('/usr/bin/systemctl','stop','dataark-wifi-rollback.timer',check=False)
    return status()

def boot():
    if PENDING.exists():
        rollback()
    rows = inventory()
    ap,other,fallback = choose(rows,preference())
    old = nm('-g','connection.interface-name','connection','show','id','DataArk')
    if old != ap['interface']:
        # Boot reconciliation is also recoverable after a power loss.
        write(PENDING,snapshot())
        try:
            switch(ap,other)
            PENDING.unlink()
        except Exception:
            rollback()
            raise
    publish(ap,other,fallback)
    if old == ap['interface']:
        policy(ap['interface'])
    # A saved upstream profile can have won autoconnect on the fallback radio.
    # Matching the profile's interface alone does not prove the hotspot is up.
    active = nm('-g','GENERAL.CON-UUID','device','show',ap['interface'])
    expected = nm('-g','connection.uuid','connection','show','id','DataArk')
    if active != expected:
        nm('connection','up','id','DataArk','ifname',ap['interface'])

def main():
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    if os.geteuid()!=0:
        raise SystemExit('Root-owned network helper only.')
    BASE.mkdir(mode=0o700,parents=True,exist_ok=True)
    BASE.chmod(0o700)
    with (BASE/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            if sys.argv[1:]==['--rollback']:
                rollback(); return
            if sys.argv[1:]==['--boot']:
                boot(); return
            if len(sys.argv)!=1:
                raise ValueError('Unsupported operation.')
            data=json.loads(sys.stdin.buffer.read(2049))
            action=data.get('action')
            if set(data)-{'action','adapter'}:
                raise ValueError('Unsupported request.')
            if action=='adapters': result=status()
            elif action=='assign': result=apply(data.get('adapter'))
            elif action=='confirm-roles': result=confirm()
            elif action=='revert-roles': rollback(); result=status()
            else: raise ValueError('Unsupported operation.')
        except Exception as error:
            logging.exception('Wi-Fi adapter operation failed')
            result={'ok':False,'error':str(error) if isinstance(error,ValueError) else 'Adapter operation failed; inspect the local system log.'}
        print(json.dumps(result))

if __name__=='__main__':
    main()
