from pathlib import Path
import subprocess,sys,io,json
import pycdlib
import argparse
parser=argparse.ArgumentParser(description='Prepare the seed and overlay after downloading verified QEMU and Debian ARM64 images.')
parser.add_argument('--vm-root',default='F:/DataArk-Emulator');args=parser.parse_args()
profile=json.loads((Path(__file__).resolve().parents[2]/'config/emulator.json').read_text(encoding='utf-8'))
assert profile['schema']==1 and profile['media']['read_only'] is True
ports=profile['loopback_ports']
root=Path(args.vm_root);root.mkdir(parents=True,exist_ok=True)
for name in ['downloads','disks','logs','seed']:(root/name).mkdir(exist_ok=True)
key=root/'seed/admin-ed25519'
if not key.exists():subprocess.run(['ssh-keygen','-t','ed25519','-f',str(key),'-N','','-C','dataark-emulator-local'],check=True,stdout=subprocess.DEVNULL)
pub=key.with_suffix('.pub').read_text().strip()
user='''#cloud-config
hostname: dataark-emulator
manage_etc_hosts: true
ssh_pwauth: false
disable_root: true
users:
  - name: admin
    gecos: Data Ark emulator administrator
    shell: /bin/bash
    groups: [sudo]
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: true
    ssh_authorized_keys:
      - '''+pub+'''
package_update: false
package_upgrade: false
write_files:
  - path: /etc/dataark-emulator
    permissions: '0644'
    content: |
      Isolated software-emulated ARM64 test Ark. Production hardware services are not installed.
final_message: 'Data Ark emulator cloud-init ready after $UPTIME seconds'
'''
meta='instance-id: dataark-emulator-20261028\nlocal-hostname: dataark-emulator\n'
for name,text in [('user-data',user),('meta-data',meta)]: (root/'seed'/name).write_text(text,encoding='utf-8')
iso=pycdlib.PyCdlib();iso.new(interchange_level=3,joliet=3,vol_ident='cidata',rock_ridge='1.09')
for name in ['user-data','meta-data']:
 b=(root/'seed'/name).read_bytes();iso.add_fp(io.BytesIO(b),len(b),iso_path='/'+name.upper().replace('-','_')+';1',rr_name=name,joliet_path='/'+name)
iso.write(str(root/'seed/seed.iso'));iso.close()
qemu=root/'qemu';disk=root/'disks/system.qcow2'
if not disk.exists():subprocess.run([str(qemu/'qemu-img.exe'),'create','-f','qcow2','-F','qcow2','-b',str(root/'downloads/debian-13-genericcloud-arm64.qcow2'),str(disk),str(profile['system_disk_gib'])+'G'],check=True)
args=['-machine',profile['machine'],'-cpu',profile['cpu'],'-smp',str(profile['cpus']),'-m',str(profile['memory_mib']),'-accel','tcg,thread=multi','-bios',str(qemu/'share/edk2-aarch64-code.fd'),'-drive','file='+str(disk)+',if=virtio,format=qcow2','-drive','file='+str(root/'seed/seed.iso')+',if=virtio,format=raw,readonly=on','-netdev',f"user,id=net0,hostfwd=tcp:127.0.0.1:{ports['ssh']}-:22,hostfwd=tcp:127.0.0.1:{ports['http']}-:80,hostfwd=tcp:127.0.0.1:{ports['kiwix']}-:8080",'-device','virtio-net-pci,netdev=net0','-display','none','-serial','file:'+str(root/'logs/serial.log'),'-qmp',f"tcp:127.0.0.1:{ports['qmp']},server=on,wait=off"]
(root/'qemu-arguments.json').write_text(json.dumps(args,indent=2))
print('Cloud-init seed and 32 GiB copy-on-write system disk ready.')
