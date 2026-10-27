#!/usr/bin/env python3
"""Install local aggregate usage collection, without restarting the API."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 if os.geteuid()!=0:raise SystemExit('Run as root')
 p=Path('/var/lib/dataark/usage');p.mkdir(parents=True,exist_ok=True);p.chmod(0o700)
 for name in ['dataark-usage.service','dataark-usage.timer']:
  Path('/etc/systemd/system',name).write_bytes((ROOT/'deploy'/name).read_bytes())
 subprocess.run(['systemctl','daemon-reload'],check=True)
 subprocess.run(['systemctl','enable','--now','dataark-usage.timer'],check=True)
 subprocess.run(['systemctl','start','dataark-usage.service'],check=True)
if __name__=='__main__':main()
