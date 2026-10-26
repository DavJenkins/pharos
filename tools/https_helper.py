#!/usr/bin/python3
"""Fixed-scope root ACME helper. Public recovery recipes never contain its state."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

PRIVATE = Path('/etc/dataark/https')
PUBLIC = Path('/var/lib/dataark/https')
IDENTITY = Path('/etc/dataark/device-identity.json')
SITE = Path('/etc/apache2/sites-available/dataark-https.conf')
ENABLED = Path('/etc/apache2/sites-enabled/dataark-https.conf')
DNS = PRIVATE / 'local-dns.conf'
MARKER = '# Managed by Data Ark optional HTTPS'
UNIT = 'dataark-https-setup.service'
ACME = 'https://acme-v02.api.letsencrypt.org/directory'
TERMS = 'https://letsencrypt.org/repository/'
BUSY = {'requesting', 'waiting_dns', 'verifying', 'installing'}

def read(path, default=None):
    try: return json.loads(path.read_text())
    except FileNotFoundError: return {} if default is None else default

def atomic(path, data, mode=0o600):
    if path.is_symlink(): raise ValueError('Refusing unexpected symlink: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temporary = Path(f.name); f.write(data.encode() if isinstance(data, str) else data)
    try:
        temporary.chmod(mode); temporary.replace(path)
    finally: temporary.unlink(missing_ok=True)

def save(path, value, mode=0o600):
    atomic(path, json.dumps(value, indent=2) + '\n', mode)

def command(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=60, **kwargs).stdout.strip()

def domain_name(value):
    if not isinstance(value, str): raise ValueError('Enter a domain name you control')
    value = value.strip().lower().rstrip('.')
    try: value = value.encode('idna').decode('ascii')
    except UnicodeError: raise ValueError('Invalid domain name')
    try: ipaddress.ip_address(value)
    except ValueError: pass
    else: raise ValueError('Use a domain name, not an IP address')
    if len(value) > 253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}', value):
        raise ValueError('Enter a complete public domain name, without a URL, port, path or wildcard')
    if value.rsplit('.', 1)[-1] in {'local', 'lan', 'localhost', 'internal', 'home', 'arpa', 'invalid', 'test', 'example'}:
        raise ValueError('A publicly registered domain is required')
    if any(value == d or value.endswith('.' + d) for d in ('example.com', 'example.org', 'example.net')):
        raise ValueError('Replace the example domain with a domain you control')
    return value

def contact_email(value):
    if not isinstance(value, str) or len(value) > 254 or not re.fullmatch(r'[A-Za-z0-9][^\s@]{0,127}@[A-Za-z0-9][A-Za-z0-9.-]+\.[A-Za-z]{2,63}', value):
        raise ValueError('Enter a valid contact email for the certificate account')
    return value

def identity():
    if not IDENTITY.exists(): save(IDENTITY, {'device_id': 'ark-' + uuid.uuid4().hex[:16], 'created_at': time.time()})
    return read(IDENTITY)['device_id']

def status(phase=None, **fields):
    value = read(PUBLIC / 'status.json')
    active = read(PRIVATE / 'active.json')
    value.update({'available': True, 'device_id': identity(), 'enabled': ENABLED.is_symlink(),
                  'domain': active.get('domain'), 'certificate': active.get('certificate'),
                  'renewal': 'manual_dns', 'http_available': True})
    if phase is not None: value['phase'] = phase
    value.setdefault('phase', 'not_configured')
    value.update(fields); value['updated_at'] = datetime.now(timezone.utc).isoformat()
    save(PUBLIC / 'status.json', value, 0o644)
    return value

def running():
    return subprocess.run(['/usr/bin/systemctl', 'is-active', '--quiet', UNIT], capture_output=True).returncode == 0

def cert_name(domain): return 'dataark-' + hashlib.sha256(domain.encode()).hexdigest()[:16]

def apache_config(domain, live):
    domain = domain_name(domain)
    return f'''{MARKER}
<VirtualHost *:443>
 ServerName {domain}
 DocumentRoot /var/www/html
 SSLEngine on
 SSLCertificateFile {live}/fullchain.pem
 SSLCertificateKeyFile {live}/privkey.pem
 SSLProtocol -all +TLSv1.2 +TLSv1.3
 ProxyPreserveHost On
 RequestHeader set X-Forwarded-Proto "https"
 ProxyPass /api/ http://127.0.0.1:8000/
 ProxyPassReverse /api/ http://127.0.0.1:8000/
 <Directory /var/www/html>
  Options Indexes FollowSymLinks
  AllowOverride All
  Require all granted
 </Directory>
 ErrorLog ${{APACHE_LOG_DIR}}/dataark-https-error.log
 CustomLog ${{APACHE_LOG_DIR}}/dataark-https-access.log combined
</VirtualHost>
'''

def validate_certificate(domain, live):
    command(['/usr/bin/openssl', 'x509', '-in', str(live/'cert.pem'), '-noout', '-checkhost', domain])
    command(['/usr/bin/openssl', 'x509', '-in', str(live/'cert.pem'), '-noout', '-checkend', '86400'])
    command(['/usr/bin/openssl', 'verify', '-untrusted', str(live/'chain.pem'), str(live/'cert.pem')])
    public = command(['/usr/bin/openssl', 'x509', '-in', str(live/'cert.pem'), '-pubkey', '-noout'])
    key = command(['/usr/bin/openssl', 'pkey', '-in', str(live/'privkey.pem'), '-pubout'])
    if public != key: raise ValueError('Certificate does not match its private key')
    end = command(['/usr/bin/openssl', 'x509', '-in', str(live/'cert.pem'), '-noout', '-enddate']).split('=', 1)[1]
    expiry = datetime.strptime(end, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
    return {'expires_at': expiry.isoformat(), 'issuer': command(['/usr/bin/openssl', 'x509', '-in', str(live/'cert.pem'), '-noout', '-issuer'])}

def activate(domain, live, certificate):
    if SITE.exists() and not SITE.read_text().startswith(MARKER): raise ValueError('Refusing unmanaged HTTPS configuration')
    if (ENABLED.exists() or ENABLED.is_symlink()) and (not ENABLED.is_symlink() or ENABLED.resolve() != SITE): raise ValueError('Unexpected HTTPS site link')
    old_site = SITE.read_bytes() if SITE.exists() else None
    old_dns = DNS.read_bytes() if DNS.exists() else (MARKER + '\n').encode()
    was_enabled = ENABLED.is_symlink()
    try:
        command(['/usr/sbin/a2enmod', 'ssl'])
        atomic(SITE, apache_config(domain, live), 0o644)
        if not was_enabled: ENABLED.symlink_to(SITE)
        command(['/usr/sbin/apache2ctl', 'configtest'])
        atomic(DNS, MARKER + '\nhost-record=' + domain + ',192.168.4.1\n', 0o644)
        command(['/usr/sbin/dnsmasq', '--test', '--conf-file=/etc/dataark/portal-dns.conf'])
        command(['/usr/bin/systemctl', 'reload', 'apache2'])
        if subprocess.run(['/usr/bin/systemctl','is-active','--quiet','dataark-portal-dns.service']).returncode == 0:
            command(['/usr/bin/systemctl', 'restart', 'dataark-portal-dns.service'])
        # Verify the installed leaf over the local TLS listener, with hostname
        # and system trust verification, before announcing success.
        command(['/usr/bin/curl', '--fail', '--silent', '--show-error', '--noproxy', '*', '--max-time', '15',
                 '--resolve', domain + ':443:127.0.0.1', 'https://' + domain + '/api/', '--output', '/dev/null'])
    except Exception:
        if not was_enabled: ENABLED.unlink(missing_ok=True)
        if old_site is not None: atomic(SITE, old_site, 0o644)
        else: SITE.unlink(missing_ok=True)
        atomic(DNS, old_dns, 0o644)
        subprocess.run(['/usr/bin/systemctl', 'reload', 'apache2'], capture_output=True)
        subprocess.run(['/usr/bin/systemctl', 'try-restart', 'dataark-portal-dns.service'], capture_output=True)
        raise
    save(PRIVATE / 'active.json', {'domain': domain, 'certificate': certificate, 'live': str(live)})

def certbot_command(job):
    return ['/usr/bin/certbot', 'certonly', '--manual', '--preferred-challenges', 'dns',
        '--manual-auth-hook', '/usr/local/libexec/dataark-https-auth', '--non-interactive',
        '--agree-tos', '--email', job['email'], '--server', ACME,
        '--config-dir', str(PRIVATE/'acme'), '--work-dir', str(PRIVATE/'work'),
        '--logs-dir', str(PRIVATE/'logs'), '--cert-name', cert_name(job['domain']),
        '--key-type', 'ecdsa', '--domain', job['domain'], '--keep-until-expiring']

def worker_main():
    os.umask(0o077)
    job = read(PRIVATE / 'job.json')
    domain = domain_name(job['domain']); contact_email(job['email'])
    if job.get('agree_terms') is not True: raise ValueError('Certificate terms were not accepted')
    status('requesting', setup_domain=domain, message='Contacting Let’s Encrypt for a DNS challenge.')
    try:
        with (PRIVATE/'operation.log').open('w') as log:
            result = subprocess.run(certbot_command(job), stdout=log, stderr=subprocess.STDOUT, timeout=2100)
        if result.returncode: raise RuntimeError('Certificate request failed. Review the DNS record and the private log at /etc/dataark/https/operation.log, then start again.')
        live = PRIVATE / 'acme/live' / cert_name(domain)
        certificate = validate_certificate(domain, live)
        with (PRIVATE/'helper.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            status('installing', message='Validating and installing the certificate. HTTP remains available.')
            installed = PRIVATE / 'installed' / job['job_id']
            installed.mkdir(parents=True, mode=0o700)
            for name in ('cert.pem', 'chain.pem', 'fullchain.pem', 'privkey.pem'):
                atomic(installed/name, (live/name).read_bytes(), 0o600)
            activate(domain, installed, certificate)
            status('ready', setup_domain=domain, message='HTTPS is ready. You may remove the displayed temporary TXT record.')
    except Exception as error:
        message = 'Certificate request timed out. Start again when ready.' if isinstance(error, subprocess.TimeoutExpired) else str(error)[:600]
        status('failed', message=message)
        raise

def auth_main():
    os.umask(0o077)
    job = read(PRIVATE/'job.json')
    domain = domain_name(os.environ.get('CERTBOT_DOMAIN', ''))
    token = os.environ.get('CERTBOT_VALIDATION', '')
    if domain != job['domain'] or not re.fullmatch(r'[A-Za-z0-9_-]{16,200}', token): raise ValueError('Unexpected ACME challenge')
    challenge = {'job_id': job['job_id'], 'challenge_id': secrets.token_hex(16),
                 'name': '_acme-challenge.' + domain, 'type': 'TXT', 'value': token,
                 'expires_at': time.time() + 1800}
    save(PRIVATE/'challenge.json', challenge)
    status('waiting_dns', message='Add the TXT record at your DNS provider, then choose Verify DNS.')
    while time.time() < challenge['expires_at']:
        approval = read(PRIVATE/'approval.json')
        if approval.get('job_id') == challenge['job_id'] and approval.get('challenge_id') == challenge['challenge_id']:
            status('verifying', message='Let’s Encrypt is checking public DNS.')
            return
        time.sleep(2)
    raise RuntimeError('DNS setup timed out after 30 minutes. Start again when ready.')

def helper_action(data):
    if not isinstance(data, dict): raise ValueError('Expected a JSON object')
    action = data.get('action')
    if action == 'details' and set(data) == {'action'}:
        value = read(PUBLIC/'status.json')
        value['challenge'] = read(PRIVATE/'challenge.json') or None
        if value['phase'] not in BUSY | {'ready', 'failed'}: value['challenge'] = None
        job = read(PRIVATE/'job.json')
        value['setup_domain'] = job.get('domain', value.get('domain'))
        return value
    if action == 'start' and set(data) == {'action','domain','email','agree_terms'}:
        domain = domain_name(data['domain']); email = contact_email(data['email'])
        if data['agree_terms'] is not True: raise ValueError('You must read and accept Let’s Encrypt’s subscriber agreement before requesting a certificate')
        if running(): raise ValueError('A certificate request is already running')
        job = {'domain':domain,'email':email,'agree_terms':True,'terms_link':TERMS,'accepted_at':time.time(),'job_id':secrets.token_hex(16)}
        save(PRIVATE/'job.json', job)
        for name in ('approval.json','challenge.json'): (PRIVATE/name).unlink(missing_ok=True)
        status('requesting', setup_domain=domain, message='Starting owner-controlled DNS certificate setup.')
        command(['/usr/bin/systemctl','start','--no-block',UNIT])
        return {'message':'Certificate request started. Keep this page open for the DNS record.'}
    if action == 'verify' and set(data) == {'action','job_id','challenge_id'}:
        challenge = read(PRIVATE/'challenge.json')
        if not running() or read(PUBLIC/'status.json').get('phase') != 'waiting_dns': raise ValueError('No DNS challenge is waiting')
        if any(data.get(k) != challenge.get(k) for k in ('job_id','challenge_id')) or time.time() >= challenge['expires_at']:
            raise ValueError('This challenge is stale. Refresh the setup details.')
        save(PRIVATE/'approval.json', {k: challenge[k] for k in ('job_id','challenge_id')})
        return {'message':'Verification requested. Waiting for Let’s Encrypt.'}
    if action == 'cancel' and set(data) == {'action'}:
        command(['/usr/bin/systemctl','stop',UNIT])
        status('cancelled', message='Setup cancelled. Existing HTTP and any previously installed certificate remain available.')
        return {'message':'Setup cancelled.'}
    raise ValueError('Unsupported HTTPS operation or fields')

def helper_main():
    os.umask(0o077)
    try:
        if len(sys.argv) != 1: raise ValueError('No command-line arguments are accepted')
        raw = sys.stdin.buffer.read(4097)
        if len(raw) > 4096: raise ValueError('Request too large')
        with (PRIVATE/'helper.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = helper_action(json.loads(raw))
        print(json.dumps({'ok':True, **result}))
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error)[:600]})); sys.exit(1)

def reconcile_main():
    phase = read(PUBLIC/'status.json').get('phase')
    if phase in BUSY and not running(): status('interrupted', message='Setup was interrupted. HTTP remains available; start certificate setup again when ready.')
    else: status()
