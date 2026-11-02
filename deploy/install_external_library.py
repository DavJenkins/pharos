"""Install reviewed root-owned USB library handover helper; never starts a copy."""
from pathlib import Path
import os,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deploy.install_network_admin import install

def main():
    if os.geteuid()!=0:raise SystemExit('Run as root')
    root=Path(__file__).resolve().parents[1]
    source=(root/'tools/external_library.py').read_text(encoding='utf-8').replace('\r\n','\n').encode();compile(source,'external_library.py','exec')
    if not source.startswith(b'#!/usr/bin/python3\n'):raise ValueError('Executable helper requires its Python interpreter')
    rule=b'admin ALL=(root) NOPASSWD: /usr/local/libexec/dataark-external-library ""\n'
    with tempfile.NamedTemporaryFile() as f:
        f.write(rule);f.flush();subprocess.run(['visudo','-cf',f.name],check=True)
    install(Path('/usr/local/libexec/dataark-external-library'),source,0o755)
    install(Path('/etc/sudoers.d/dataark-external-library'),rule,0o440)
    for kind,arg in [('copy','--worker'),('switch','--switch')]:
        unit=f'''[Unit]
Description=Data Ark external library {kind}
After=local-fs.target
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/dataark-external-library {arg}
TimeoutStartSec=infinity
UMask=0077
'''
        install(Path('/etc/systemd/system/dataark-external-'+kind+'.service'),unit.encode(),0o644)
    for path,mode in [('/etc/dataark/external-library',0o700),('/var/lib/dataark/external-library',0o755)]:
        p=Path(path)
        if p.is_symlink():raise ValueError('Unexpected state symlink')
        p.mkdir(parents=True,exist_ok=True);p.chmod(mode)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    print('External library transition installed; no drives changed.')

if __name__=='__main__':main()
