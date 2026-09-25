"""Authentication and invocation boundary for network administration."""
import base64
import hashlib
import hmac
import json
from pathlib import Path
import subprocess

CREDENTIAL_FILE = Path('/etc/dataark/network-admin.json')
HELPER = '/usr/local/libexec/dataark-network'

def authorized(header):
    try:
        scheme, encoded = header.split(' ', 1)
        if scheme.lower() != 'basic':
            return False
        username, password = base64.b64decode(encoded, validate=True).decode('utf-8').split(':', 1)
        if username != 'admin' or not 1 <= len(password) <= 256:
            return False
        saved = json.loads(CREDENTIAL_FILE.read_text(encoding='utf-8'))
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(saved['salt']), 300000)
        return hmac.compare_digest(digest.hex(), saved['hash'])
    except (ValueError, OSError, KeyError, TypeError, UnicodeError):
        return False

def invoke(data):
    try:
        result = subprocess.run(['/usr/bin/sudo', '-n', '--', HELPER],
                                input=json.dumps(data), capture_output=True, text=True,
                                timeout=150, check=False)
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict) or not isinstance(payload.get('ok'), bool):
            raise ValueError('Invalid helper response')
        return payload
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'Operation timed out. Check the current network before retrying.'}
    except (OSError, ValueError):
        return {'ok': False, 'error': 'Network helper unavailable. Run the network administration installer on the Pi.'}
