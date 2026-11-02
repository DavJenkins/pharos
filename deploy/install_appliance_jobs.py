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
    recovery=(root/'deploy/dataark-recovery.service').read_text().replace('\r\n','\n')
    recovery=recovery.replace('TimeoutStartSec=infinity','ExecStopPost=/usr/local/libexec/dataark-appliance-jobs --restore-report\nTimeoutStartSec=infinity')
    install(Path('/etc/systemd/system/dataark-recovery.service'),recovery.encode(),0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    print('Browser copy/restore controls installed; no jobs started.')
if __name__=='__main__':main()
