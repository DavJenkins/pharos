#!/usr/bin/python3
"""Linux/Pi host writer. Preview first; only an exact ERASE token writes media."""
from pathlib import Path
import argparse,base64,hashlib,html,json,os,secrets,shutil,subprocess,tempfile,time

HERE=Path(__file__).resolve().parent

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(2*1024**2),b''):h.update(block)
    return h.hexdigest()

def make_seed(config,driver):
    seed={k:config[k] for k in ('library_gib','country','kit_sha256')}
    seed.update(pairing_code=f'{secrets.randbelow(10000):04d}',hostname='dataark-'+secrets.token_hex(6))
    unit='[Unit]\nDescription=Build a recipient-ready Data Ark card\nAfter=network-online.target\nWants=network-online.target\nConditionPathExists=!/var/lib/dataark/card-build/ready\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /usr/local/libexec/dataark-card-build\nTimeoutStartSec=infinity\n[Install]\nWantedBy=multi-user.target\n'
    cloud={'hostname':seed['hostname'],'manage_etc_hosts':True,'ssh_pwauth':False,'disable_root':True,'package_update':False,'package_upgrade':False,
           'users':[{'name':'admin','uid':1000,'groups':['adm','sudo','audio','video','plugdev','netdev','gpio','i2c','spi'],'shell':'/bin/bash','lock_passwd':True,'sudo':'ALL=(ALL) NOPASSWD:ALL'}],
           'write_files':[{'path':'/usr/local/libexec/dataark-card-build','permissions':'0700','encoding':'b64','content':base64.b64encode(driver).decode()},
                          {'path':'/etc/systemd/system/dataark-card-build.service','permissions':'0644','content':unit}],
           'runcmd':[['systemctl','daemon-reload'],['systemctl','enable','--now','dataark-card-build.service']]}
    template=HERE/'welcome-template.html'
    if template.is_file():
        sheet=template.read_text(encoding='utf-8').replace('{{SETUP_CODE}}',seed['pairing_code']).replace('DATAARK_HOSTNAME',seed['hostname']).replace('{{LIBRARY_GIB}}',str(seed['library_gib']))
    else:
        from app.services.welcome_guides import render
        sheet=render('microsd',code=seed['pairing_code'],hostname=seed['hostname'],note='Sender: finish the initial online build and wait for successful power-off before handoff. Library capacity: '+str(seed['library_gib'])+' GiB; capacity does not imply it is full.')

    return seed,cloud,sheet

def candidates():
    data=json.loads(subprocess.check_output(['lsblk','-J','-p','-b','-o','PATH,TYPE,TRAN,RM,SIZE,SERIAL,MODEL,MOUNTPOINTS,FSTYPE'],text=True))
    def descendants(row):
        yield row
        for child in row.get('children',[]):yield from descendants(child)
    result=[]
    for disk in data['blockdevices']:
        entries=list(descendants(disk));mounts=[m for row in entries for m in row.get('mountpoints',[]) if m]
        if disk['type']!='disk' or not (disk.get('tran')=='usb' or disk.get('rm')) or any(m in ('/','/boot','/boot/firmware','/mnt/storage') for m in mounts):continue
        # Never overwrite the volume carrying the input image or this package.
        protected=False
        for source in [HERE]:
            source_device=subprocess.check_output(['findmnt','-n','-o','SOURCE','--target',str(source)],text=True).strip()
            if source_device in [row['path'] for row in entries]:protected=True
        if any((Path(m)/marker).exists() for m in mounts for marker in ('DATA-ARK-CONFIG','DATA-ARK-RECOVERY')):protected=True
        if protected:continue
        result.append({'path':disk['path'],'bytes':disk['size'],'serial':(disk.get('serial') or '').strip(),'model':(disk.get('model') or '').strip()})
    return result

def validate_image(image,config):
    spec=config['image']
    if image.stat().st_size!=spec['download_bytes'] or digest(image)!=spec['download_sha256']:raise ValueError('Image does not match the reviewed Raspberry Pi OS reference. No media written.')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',type=Path);parser.add_argument('--disk');parser.add_argument('--apply',action='store_true');parser.add_argument('--confirm');a=parser.parse_args()
    config=json.loads((HERE/'card-package.json').read_text());rows=candidates()
    for n,row in enumerate(rows,1):print(n,json.dumps(row))
    if not a.disk:
        chosen=input('Destination number (Enter cancels): ').strip()
        if not chosen:return
        if not chosen.isdigit() or not 1<=int(chosen)<=len(rows):raise ValueError('Choose a listed disk')
        a.disk=rows[int(chosen)-1]['path']
    disk=next((d for d in rows if d['path']==a.disk),None)
    if disk is None:raise ValueError('Destination is not an eligible removable disk')
    image=(a.image or Path(input('Path to '+config['image']['filename']+': ').strip())).resolve()
    validate_image(image,config)
    source_device=subprocess.check_output(['findmnt','-n','-o','SOURCE','--target',str(image)],text=True).strip()
    tree=json.loads(subprocess.check_output(['lsblk','-J','-p','-o','PATH',disk['path']],text=True))
    if source_device in json.dumps(tree):raise ValueError('Input image is on the destination disk')
    minimum=(config['library_gib']+config['image']['image_allowance_gib']+config['image']['os_reserve_gib'])*1024**3
    if disk['bytes']<minimum:raise ValueError('Card is too small for the selected library and Linux reserve')
    token='ERASE '+disk['path']+' '+(disk['serial'] or 'NO-SERIAL')
    print('This replaces ALL contents of:',json.dumps(disk));print('Required confirmation:',token)
    if not a.apply and input('Continue to writing? [y/N]: ').strip().lower() not in ('y','yes'):return
    if (a.confirm or input('Type the exact ERASE confirmation: '))!=token:raise ValueError('Erase confirmation did not match')
    if os.geteuid()!=0:raise ValueError('Run with sudo to write the selected disk')
    imager=shutil.which('rpi-imager')
    if not imager:raise ValueError('Install Raspberry Pi Imager 2.0.12 or newer from its official source')
    if next((d for d in candidates() if d['path']==a.disk),None)!=disk:raise ValueError('Destination identity changed')
    if digest(HERE/'kit.tar.gz')!=config['kit_sha256']:raise ValueError('Kit checksum differs')
    seed,cloud,sheet=make_seed(config,(HERE/'first-boot.py').read_bytes())
    with tempfile.TemporaryDirectory(prefix='dataark-card-writer-') as temporary:
        userdata=Path(temporary)/'user-data';userdata.write_text('#cloud-config\n'+json.dumps(cloud,indent=2)+'\n');userdata.chmod(0o600)
        subprocess.run([imager,'--cli','--disable-eject','--sha256',config['image']['uncompressed_sha256'],'--cloudinit-userdata',str(userdata),str(image),disk['path']],check=True)
        subprocess.run(['udevadm','settle'],check=True)
        parts=json.loads(subprocess.check_output(['lsblk','-J','-p','-o','PATH,FSTYPE',disk['path']],text=True))['blockdevices'][0].get('children',[])
        boot=next((p for p in parts if p.get('fstype')=='vfat'),None)
        if not boot:raise ValueError('Verified image has no expected boot partition')
        mount=Path(temporary)/'boot';mount.mkdir();subprocess.run(['mount',boot['path'],str(mount)],check=True)
        try:
            folder=mount/'dataark-card';folder.mkdir();shutil.copyfile(HERE/'kit.tar.gz',folder/'kit.tar.gz');(folder/'provision.json').write_text(json.dumps(seed)+'\n')
            if digest(folder/'kit.tar.gz')!=config['kit_sha256']:raise ValueError('Copied kit verification failed')
            subprocess.run(['sync'],check=True)
        finally:subprocess.run(['umount',str(mount)],check=True)
    welcome=HERE/(seed['hostname']+'-PRIVATE-welcome.html');welcome.write_text(sheet,encoding='utf-8');welcome.chmod(0o600)
    print('Installer card written and verified. Private welcome sheet:',welcome)
    print('Boot with Ethernet/internet. Only after a successful build powers off is this a ready-to-run recipient card.')

if __name__=='__main__':main()
