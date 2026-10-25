#!/usr/bin/env python3
"""Install Chromium capture on the Ark itself. Run as root; restart Chromium afterward."""
import json, os, pwd, shutil, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXTENSION=Path('/usr/share/chromium/extensions/dataark-capture')
HOST=Path('/usr/local/lib/dataark-browser-capture')

def put(path,data,mode=0o644):
 if path.is_symlink():raise ValueError('Refusing symlink: '+str(path))
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
  temp=Path(f.name);f.write(data)
 try:
  temp.chmod(mode);os.chown(temp,0,0);os.replace(temp,path)
 finally:temp.unlink(missing_ok=True)

def main():
 if os.geteuid()!=0:raise SystemExit('Run with sudo python3 deploy/install_pi_browser_capture.py')
 account=pwd.getpwnam('admin');home=Path(account.pw_dir)
 for command in ['/usr/bin/chromium','/usr/bin/sudo','/usr/sbin/visudo','/usr/bin/python3']:
  if not Path(command).is_file():raise SystemExit('Missing '+command)
 source=ROOT/'tools/browser-capture'
 # Chromium already loads /usr/share/chromium/extensions/* through Debian's wrapper.
 loader=Path('/etc/chromium.d/extensions')
 if not loader.is_file() or '/usr/share/chromium/extensions/*' not in loader.read_text():
  raise SystemExit('Expected Debian Chromium extension loader; inspect before installing.')
 for directory in [EXTENSION,HOST]:
  if directory.is_symlink():raise SystemExit('Refusing symlink directory')
  directory.mkdir(parents=True,exist_ok=True);os.chown(directory,0,0);directory.chmod(0o755)
 for name in ['manifest.json','background.js','content.js','targets.json']:
  put(EXTENSION/name,(source/name).read_bytes())
 for name in ['native_host.py','targets.json']:
  put(HOST/name,(source/name).read_bytes())
 downloads=home/'Downloads'
 downloads.mkdir(exist_ok=True);os.chown(downloads,account.pw_uid,account.pw_gid)
 put(HOST/'config.json',(json.dumps({'transport':'local','download_directories':[str(downloads)]},indent=2)+'\n').encode())
 put(HOST/'native-host',b'#!/bin/sh\nexec /usr/bin/python3 -B /usr/local/lib/dataark-browser-capture/native_host.py\n',0o755)
 wrapper=b'#!/bin/sh\n[ "$#" -eq 0 ] || exit 2\nexec /usr/bin/python3 -B /opt/dataark/tools/import_browser_reference.py\n'
 rule=b'admin ALL=(root) NOPASSWD: /usr/local/libexec/dataark-browser-import ""\n'
 with tempfile.NamedTemporaryFile() as f:
  f.write(rule);f.flush();subprocess.run(['/usr/sbin/visudo','-cf',f.name],check=True)
 put(Path('/usr/local/libexec/dataark-browser-import'),wrapper,0o755)
 put(Path('/etc/sudoers.d/dataark-browser-capture'),rule,0o440)
 manifest={'name':'com.dejsoftware.dataark_capture','description':'Data Ark local approved PDF capture','path':str(HOST/'native-host'),'type':'stdio','allowed_origins':['chrome-extension://gilcpcndoddadpkefaeecjemhhcahhig/']}
 put(Path('/etc/chromium/native-messaging-hosts/com.dejsoftware.dataark_capture.json'),(json.dumps(manifest,indent=2)+'\n').encode())
 print('Installed for admin: '+str(EXTENSION))
 print('Restart Chromium, then open http://dataark/capture.html. No SSH key or network pairing is needed.')
if __name__=='__main__':main()
