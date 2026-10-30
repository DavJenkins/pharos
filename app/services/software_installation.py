"""Unprivileged UI boundary; only the fixed root helper may change software."""
import json
from pathlib import Path
import subprocess

INBOX=Path('/var/lib/dataark/software-inbox')
HELPER='/usr/local/libexec/dataark-software-update'

def invoke(data):
    try:
        result=subprocess.run(['/usr/bin/sudo','-n','--',HELPER],input=json.dumps(data),capture_output=True,text=True,timeout=180,check=False)
        value=json.loads(result.stdout)
        if not isinstance(value,dict) or not isinstance(value.get('ok'),bool):raise ValueError()
        return value
    except (OSError,ValueError,subprocess.SubprocessError):return {'ok':False,'configured':False,'error':'Software updater is not installed or is unavailable.'}

def status():
    value=invoke({'action':'status'})
    if not value.get('ok'):return {**value,'state':'not_installed','installation_supported':False}
    return value
