"""Unprivileged API boundary for the root-owned forwarding helper."""
import json
import subprocess

def control(address, enabled=None):
    data = {'address':address}
    if enabled is not None:
        data['enabled'] = enabled
    try:
        result = subprocess.run(['/usr/bin/sudo','-n','--','/usr/local/libexec/dataark-pass-through'],
            input=json.dumps(data),capture_output=True,text=True,timeout=12,check=False)
        payload = json.loads(result.stdout)
        if result.returncode or payload.get('ok') is not True or type(payload.get('enabled')) is not bool:
            raise ValueError('Invalid result')
        return payload['enabled']
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        raise RuntimeError('Pass-through control unavailable') from None
