"""Standard-library platform discovery and reviewed, bounded installation profiles.

This file and platforms/*.json also travel beside the standalone coordinator.
Discovery never changes connections and does not record passwords or SSIDs.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

PROFILES = Path(__file__).resolve().parent/'platforms'
DEFAULT = 'raspberry-pi-debian13-arm64'
INTERFACE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,14}')
ARCHITECTURES = {'aarch64':'aarch64', 'arm64':'aarch64', 'x86_64':'x86_64', 'amd64':'x86_64'}
TOOL_PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'


def architecture(value=None):
    return ARCHITECTURES.get((value or platform.machine()).lower(), 'unsupported')


def profile(name=DEFAULT, directory=PROFILES):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',name):
        raise ValueError('Invalid platform profile name')
    value=json.loads((Path(directory)/(name+'.json')).read_text())
    if value.get('schema')!=1 or value.get('id')!=name or value.get('adapter')!='debian-systemd-networkmanager':
        raise ValueError('Unsupported platform profile or command adapter')
    if value['baseline']['architecture'] not in {'aarch64','x86_64'} or value['baseline']['os_id']!='debian' or value['baseline']['version_id']!='13':
        raise ValueError('Unreviewed operating-system baseline')
    if value.get('network_mode') not in {'hotspot','lan'}:
        raise ValueError('Unsupported network mode')
    if not re.fullmatch(r'ghcr.io/kiwix/kiwix-serve@sha256:[0-9a-f]{64}',value.get('kiwix_image','')):
        raise ValueError('A pinned architecture-specific Kiwix image is required')
    return value


def selected(config):
    return profile(config.get('platform_profile',DEFAULT))


def configure(config, name):
    result=copy.deepcopy(config);spec=profile(name)
    result['platform_profile']=name;result['baseline']=copy.deepcopy(spec['baseline'])
    result['network']={'mode':spec['network_mode']}
    result['kiwix_image']=spec['kiwix_image']
    if spec['network_mode']=='lan':result['hostname']='keep'
    return result


def validate(config):
    spec=selected(config)
    if config['baseline'] != spec['baseline']:
        # The existing disposable ARM64 harness explicitly removes only the Pi marker.
        legacy=dict(config['baseline'],require_raspberry_pi_os=True)
        if config.get('platform_profile') or legacy!=spec['baseline']:
            raise ValueError('Site baseline must match its platform profile')
    if config.get('network',{}).get('mode',spec['network_mode'])!=spec['network_mode']:
        raise ValueError('Choose a profile supporting the requested network mode')
    if config.get('platform_profile') and config.get('kiwix_image')!=spec['kiwix_image']:
        raise ValueError('Kiwix image must match the platform profile architecture pin')
    return spec


def query(args):
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=10,
                              env=os.environ|{'LC_ALL':'C','PATH':TOOL_PATH},check=False)
        return result.stdout.strip() if result.returncode==0 else ''
    except (OSError,subprocess.SubprocessError):return ''


def text(path):
    try:return Path(path).read_text().strip().replace('\x00','')
    except OSError:return ''


def discover():
    try:addresses=json.loads(query(['ip','-j','address','show']))
    except ValueError:addresses=[]
    try:routes=json.loads(query(['ip','-j','route','show','default']))
    except ValueError:routes=[]
    if len(addresses)>64:raise ValueError('Discovery is limited to 64 interfaces')
    interfaces=[]
    for row in addresses:
        name=row.get('ifname','')
        if name=='lo' or not INTERFACE.fullmatch(name):continue
        kind=query(['nmcli','-g','GENERAL.TYPE','device','show',name])
        wireless=(Path('/sys/class/net')/name/'wireless').exists() or kind in {'wifi','802-11-wireless'}
        permanent=query(['ethtool','-P',name]).split()[-1:]
        mac=permanent[0].lower() if permanent else ''
        if not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',mac) or mac=='00:00:00:00:00:00':mac=''
        ap=None
        if wireless:
            info=query(['iw','dev',name,'info']);match=re.search(r'\bwiphy (\d+)\b',info)
            if match:
                modes=query(['iw','phy','phy'+match[1],'info'])
                ap=bool(re.search(r'^\s*\* AP\s*$',modes,re.M)) if modes else None
        interfaces.append({'name':name,'kind':'wifi' if wireless else 'ethernet' if kind in {'ethernet','802-3-ethernet'} else kind or row.get('link_type','unknown'),
                           'permanent_mac':mac or None,'current_mac':row.get('address'),
                           'hotspot_capable':ap,'state':row.get('operstate','unknown'),
                           'addresses':[a['local'] for a in row.get('addr_info',[]) if a.get('local')]})
    info=dict(line.split('=',1) for line in text('/etc/os-release').replace('"','').splitlines() if '=' in line)
    return {'schema':1,'architecture':architecture(),'os':{'id':info.get('ID'),'version':info.get('VERSION_ID')},
            'raspberry_pi_os':Path('/etc/rpi-issue').exists(),
            'model':text('/proc/device-tree/model') or text('/sys/class/dmi/id/product_name'),
            'systemd':Path('/run/systemd/system').is_dir(),
            'network_manager':query(['systemctl','is-active','NetworkManager'])=='active',
            'tools':{name:bool(shutil.which(name,path=TOOL_PATH)) for name in ('ip','nmcli','ethtool','iw')},
            'machine_id_sha256':hashlib.sha256(text('/etc/machine-id').encode()).hexdigest(),
            'interfaces':interfaces,'default_routes':[{'interface':r.get('dev'),'metric':r.get('metric',0)} for r in routes if r.get('dev')]}


def proposal(config, facts):
    spec=validate(config);issues=[]
    baseline=spec['baseline']
    if facts['os']!={'id':baseline['os_id'],'version':baseline['version_id']} or facts['architecture']!=baseline['architecture']:
        issues.append('Operating system or processor architecture does not match the selected profile.')
    if config['baseline'].get('require_raspberry_pi_os') and not facts.get('raspberry_pi_os'):
        issues.append('This profile requires Raspberry Pi OS; choose a generic Debian profile for another machine.')
    if not facts.get('systemd') or not facts.get('network_manager'):
        issues.append('This profile requires an existing systemd and active NetworkManager setup.')
    required={'ip','nmcli','ethtool'}|({'iw'} if any(i['kind']=='wifi' for i in facts['interfaces']) else set())
    if any(not facts.get('tools',{}).get(name) for name in required):
        issues.append('Install the discovery prerequisites before review: iproute2, NetworkManager, ethtool and iw for wireless adapters.')
    routes=sorted(facts['default_routes'],key=lambda r:(r['metric'],r['interface']))
    uplinks=sorted({r['interface'] for r in routes})
    ap=config['hotspot']['interface'] if spec['network_mode']=='hotspot' else None
    if ap:
        radio=next((i for i in facts['interfaces'] if i['name']==ap),None)
        if not radio or radio['kind']!='wifi' or radio['hotspot_capable'] is not True:
            issues.append('The configured hotspot radio is absent or has no confirmed AP capability.')
        if ap in uplinks:issues.append('The hotspot radio carries a default route; keep that connection and choose a separate radio/upstream.')
        if not radio or not radio.get('permanent_mac'):issues.append('A stable hotspot hardware identity could not be established.')
    if not uplinks:issues.append('No existing upstream/default route was discovered.')
    roles={'hotspot':ap,'hotspot_identity':next((i['permanent_mac'] for i in facts['interfaces'] if i['name']==ap),None),
           'upstream':routes[0]['interface'] if routes else None,
           'ethernet':next((r['interface'] for r in routes if any(i['name']==r['interface'] and i['kind']=='ethernet' for i in facts['interfaces'])),None),
           'wifi':next((r['interface'] for r in routes if any(i['name']==r['interface'] and i['kind']=='wifi' for i in facts['interfaces'])),None)}
    roles['identities']={role:next((i['permanent_mac'] for i in facts['interfaces'] if i['name']==roles[role]),None) for role in ('ethernet','wifi','upstream')}
    # Link state and DHCP address churn do not change the hardware assignment.
    basis={'profile':spec,'configuration':config,'os':facts['os'],'architecture':facts['architecture'],
           'machine':facts['machine_id_sha256'],'roles':roles,
           'interfaces':[{k:i[k] for k in ('name','kind','permanent_mac','hotspot_capable')} for i in sorted(facts['interfaces'],key=lambda i:i['name'])],
           'upstreams':uplinks}
    return {'profile':spec['id'],'label':spec['label'],'network_mode':spec['network_mode'],
            'roles':roles,'interfaces':facts['interfaces'],'issues':issues,
            'network_changes':('Existing NetworkManager connections and addresses are preserved; no Ark hotspot, captive portal or internet pass-through rules are created.' if not ap else 'The reviewed radio becomes the DataArk hotspot; existing uplinks are retained.'),
            'services':'Docker and public library services will be installed and listen on the machine’s existing networks.',
            'plan_id':hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(',',':')).encode()).hexdigest()}


def elf_architecture(path):
    with Path(path).open('rb') as stream:header=stream.read(20)
    if len(header)!=20 or header[:4]!=b'\x7fELF' or header[4:6]!=b'\x02\x01':return 'unsupported'
    return {183:'aarch64',62:'x86_64'}.get(int.from_bytes(header[18:20],'little'),'unsupported')


class DebianAdapter:
    """The reviewed command family; profile data cannot supply shell commands."""
    def __init__(self,runner):self.run=runner
    def packages(self,names):
        self.run(['apt-get','update']);self.run(['apt-get','install','-y','--no-install-recommends',*names])
    def hostname(self,name):self.run(['hostnamectl','set-hostname',name])
    def country(self,country,raspberry=False):
        if raspberry and Path('/usr/bin/raspi-config').exists():self.run(['raspi-config','nonint','do_wifi_country',country])
        else:self.run(['iw','reg','set',country])
