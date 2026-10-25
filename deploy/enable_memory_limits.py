#!/usr/bin/env python3
"""Enable Pi memory accounting/limits at the next boot; never reboots the device."""
from pathlib import Path
import argparse,os,shutil

def updated(text):
    if len(text.strip().splitlines())!=1:raise ValueError('Expected one kernel command line.')
    return text if 'cgroup_enable=memory' in text.split() else text.rstrip()+' cgroup_enable=memory\n'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args()
    path=Path('/boot/firmware/cmdline.txt');original=path.read_text();replacement=updated(original)
    print('Next boot: enable memory cgroup controller. No network, password, partition or watchdog change.')
    if not a.apply:print('Preview only. Use --apply to save; a separate controlled reboot is required.');return
    if os.geteuid()!=0:raise SystemExit('Run with sudo.')
    if replacement!=original:
        backup=Path('/var/backups/dataark-reliability');backup.mkdir(parents=True,exist_ok=True,mode=0o700)
        target=backup/'cmdline-before-memory.txt'
        if not target.exists():shutil.copy2(path,target)
        temporary=path.with_suffix('.dataark-new');temporary.write_text(replacement);temporary.chmod(0o644);temporary.replace(path)
    print('Saved. Not active until reboot. Verify memory appears in /sys/fs/cgroup/cgroup.controllers afterwards.')
if __name__=='__main__':main()
