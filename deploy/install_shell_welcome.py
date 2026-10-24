#!/usr/bin/python3
"""Install idempotent interactive shell orientation, without changing logins."""
import os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HOOK='''# Data Ark shell orientation; silent for automation and once per shell.
case $- in
  *i*)
    if [ -z "${DATAARK_WELCOME_SHOWN-}" ] && [ -t 1 ] && [ -x /usr/local/bin/ark-help ]; then
      DATAARK_WELCOME_SHOWN=1
      /usr/local/bin/ark-help --welcome
    fi
    ;;
esac
'''
BLOCK='''# BEGIN DATAARK SHELL WELCOME
if [ -r /etc/profile.d/dataark-welcome.sh ]; then
    . /etc/profile.d/dataark-welcome.sh
fi
# END DATAARK SHELL WELCOME
'''
def main():
 if os.geteuid()!=0:raise SystemExit('Run with sudo to install system shell guidance.')
 source=ROOT/'tools/ark_help.py';target=Path('/usr/local/bin/ark-help');shutil.copyfile(source,target);target.chmod(0o755)
 hook=Path('/etc/profile.d/dataark-welcome.sh');hook.write_text(HOOK);hook.chmod(0o644)
 rc=Path('/etc/bash.bashrc');text=rc.read_text();start='# BEGIN DATAARK SHELL WELCOME';end='# END DATAARK SHELL WELCOME'
 if start in text:
  before,rest=text.split(start,1)
  if end not in rest:raise SystemExit('Incomplete existing welcome block; inspect /etc/bash.bashrc.')
  text=before+rest.split(end,1)[1].lstrip('\n')
 updated=text.rstrip()+'\n\n'+BLOCK
 if updated!=rc.read_text():
  backup=Path('/etc/bash.bashrc.before-dataark-welcome')
  if not backup.exists():shutil.copy2(rc,backup)
  rc.write_text(updated)
 subprocess.run(['bash','-n',str(rc)],check=True);subprocess.run(['bash','-n',str(hook)],check=True)
 print('Installed ark-help and interactive login/non-login Bash welcome. Existing shells are unchanged.')
if __name__=='__main__':main()
