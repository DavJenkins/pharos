"""Install fixed browser copy/restore controls; no jobs are started."""
from pathlib import Path
import os,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deploy.install_network_admin import install

def main():
    if os.geteuid()!=0:raise SystemExit('Run as root')
    root=Path(__file__).resolve().parents[1]
    if not Path('/usr/local/libexec/dataark-external-library').is_file():raise ValueError('Install external-library support first')
    source=(root/'tools/appliance_jobs.py').read_text(encoding='utf-8').replace('\r\n','\n').encode();compile(source,'appliance_jobs.py','exec')
    assert source.startswith(b'#!/opt/dataark/venv/bin/python\n')
    rule=b'admin ALL=(root) NOPASSWD: /usr/local/libexec/dataark-appliance-jobs ""\n'
    with tempfile.NamedTemporaryFile() as f:
        f.write(rule);f.flush();subprocess.run(['visudo','-cf',f.name],check=True)
    path=Path('/etc/dataark/appliance-jobs')
    if path.is_symlink():raise ValueError('Unexpected state symlink')
    path.mkdir(parents=True,exist_ok=True);path.chmod(0o700)
    install(Path('/usr/local/libexec/dataark-appliance-jobs'),source,0o755)
    install(Path('/etc/sudoers.d/dataark-appliance-jobs'),rule,0o440)
    unit='''[Unit]
Description=Data Ark approved public content-drive copy
After=local-fs.target
ConditionPathIsMountPoint=/mnt/storage
[Service]
Type=oneshot
WorkingDirectory=/opt/dataark
ExecStart=/usr/local/libexec/dataark-appliance-jobs --clone-worker
TimeoutStartSec=infinity
Nice=10
IOSchedulingClass=idle
UMask=0022
'''
    install(Path('/etc/systemd/system/dataark-clone.service'),unit.encode(),0o644)
    storage=unit.replace('approved public content-drive copy','reviewed library storage handover').replace('ConditionPathIsMountPoint=/mnt/storage\n','').replace('--clone-worker','--storage-worker')
    install(Path('/etc/systemd/system/dataark-storage.service'),storage.encode(),0o644)
    card=unit.replace('approved public content-drive copy','recipient card preparation package').replace('ConditionPathIsMountPoint=/mnt/storage\n','').replace('--clone-worker','--card-package')
    install(Path('/etc/systemd/system/dataark-card-package.service'),card.encode(),0o644)
    recovery_unit='''[Unit]
Description=Restore an interrupted Data Ark storage handover
After=local-fs.target
Before=dataark.service
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/dataark-appliance-jobs --storage-recover
[Install]
WantedBy=multi-user.target
'''
    install(Path('/etc/systemd/system/dataark-storage-recover.service'),recovery_unit.encode(),0o644)
    for path in ['/etc/dataark/storage','/var/lib/dataark/storage']:
        folder=Path(path)
        if folder.is_symlink():raise ValueError('Unexpected storage state symlink')
        folder.mkdir(parents=True,exist_ok=True);folder.chmod(0o700 if path.startswith('/etc/') else 0o755)
    recovery=(root/'deploy/dataark-recovery.service').read_text().replace('\r\n','\n')
    recovery=recovery.replace('TimeoutStartSec=infinity','ExecStopPost=/usr/local/libexec/dataark-appliance-jobs --restore-report\nTimeoutStartSec=infinity')
    install(Path('/etc/systemd/system/dataark-recovery.service'),recovery.encode(),0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','dataark-storage-recover.service'],check=True)
    # Management must remain reachable to reconnect/recover a missing library.
    api=Path('/etc/systemd/system/dataark.service')
    if api.exists():
        text=api.read_text();updated=text.replace('RequiresMountsFor=/mnt/storage\n','')
        if updated!=text:install(api,updated.encode(),0o644)
        subprocess.run(['systemctl','daemon-reload'],check=True)
    print('Browser copy/restore controls installed; no jobs started.')
if __name__=='__main__':main()
