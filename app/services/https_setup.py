"""Unprivileged public certificate health and fixed helper boundary."""
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess

STATUS = Path('/var/lib/dataark/https/status.json')

def public_status():
    try: value = json.loads(STATUS.read_text())
    except (OSError, ValueError): return {'available':False,'enabled':False,'phase':'not_configured','http_available':True}
    certificate = value.get('certificate')
    if certificate and certificate.get('expires_at'):
        try:
            remaining = (datetime.fromisoformat(certificate['expires_at']) - datetime.now(timezone.utc)).total_seconds()
            value['days_remaining'] = max(0, int(remaining//86400))
            value['certificate_health'] = 'expired' if remaining <= 0 else 'renewal_due' if remaining < 30*86400 else 'valid'
        except (ValueError,TypeError): value['certificate_health'] = 'unknown'
    return value

def invoke(data):
    try:
        result = subprocess.run(['/usr/bin/sudo','-n','--','/usr/local/libexec/dataark-https'],
            input=json.dumps(data),capture_output=True,text=True,timeout=75)
        value = json.loads(result.stdout)
        if not isinstance(value,dict) or type(value.get('ok')) is not bool: raise ValueError('Invalid helper response')
        return value
    except subprocess.TimeoutExpired: return {'ok':False,'error':'HTTPS operation timed out. Refresh status before retrying.'}
    except (OSError,ValueError): return {'ok':False,'error':'HTTPS setup helper is unavailable. Run deploy/install_https.py on the Ark.'}
