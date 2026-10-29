#!/bin/bash
# Explicit software-emulator profile; never run the physical-Pi bootstrap here.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run inside the guest with sudo.' >&2; exit 1; }
[[ -f /etc/dataark-emulator ]] && [[ $(systemd-detect-virt --vm) == qemu ]] && [[ $(uname -m) == aarch64 ]] || { echo 'Only the marked QEMU ARM64 guest is supported.' >&2; exit 1; }
[[ -f /home/admin/ark-source.tar.gz ]] && [[ -f /home/admin/arm64-venv.tar.gz ]]
mkdir -p /opt/dataark /var/lib/dataark/community /var/lib/dataark/configuration /var/lib/ark /var/log/dataark-emulator /var/www/html /etc/dataark
if [[ ! -f /opt/dataark/app/main.py ]]; then
  tar -xzf /home/admin/ark-source.tar.gz -C /opt/dataark
  tar -xzf /home/admin/arm64-venv.tar.gz -C /opt/dataark
fi
mkdir -p /opt/dataark/deploy/emulator
install -m 644 /home/admin/asgi.py /opt/dataark/deploy/emulator/asgi.py
chown -R admin:admin /opt/dataark /var/lib/dataark /var/lib/ark /var/www/html
cd /opt/dataark
# Source snapshots originating on Windows may contain CRLF shell scripts.
python3 - <<'PY'
from pathlib import Path
for p in Path('/opt/dataark').rglob('*.sh'):
 if 'venv' not in p.parts:p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
PY
venv/bin/python -c 'import fastapi, PIL, yaml; print("ARM64 Python dependencies ready")'
venv/bin/python - <<'PY'
from pathlib import Path
import yaml,os,json,hashlib,secrets
root=Path('/opt/dataark');p=root/'dataark.yaml';data=yaml.safe_load(p.read_text())
assert 'bugout' not in data,'Production household configuration must not be cloned.'
data['system']['project_name']='Data Ark — Emulator'
data['system'].setdefault('services',{})['kiwix_port']=18081
p.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True));os.chown(p,1000,1000)
from app.services.configuration_project import write,public
write(root/'config/library',public(data))
credential=Path('/etc/dataark/network-admin.json')
if not credential.exists():
 password=secrets.token_urlsafe(18);salt=secrets.token_bytes(16)
 credential.write_text(json.dumps({'salt':salt.hex(),'hash':hashlib.pbkdf2_hmac('sha256',password.encode(),salt,300000).hex()}));credential.chmod(0o640);os.chown(credential,0,1000)
 secret=Path('/home/admin/emulator-caretaker-password.txt');secret.write_text(password+'\n');secret.chmod(0o600);os.chown(secret,1000,1000)
from app.services.community import initialize
initialize()
PY
chown -R admin:admin /var/lib/dataark
share=${DATAARK_MEDIA_SHARE:-}
if [[ -n $share ]]; then
 [[ $share =~ ^//[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$ ]] || { echo 'Use a simple //server/share path.' >&2; exit 1; }
 mkdir -p /mnt/storage
 if ! mountpoint -q /mnt/storage; then mount -t cifs "$share" /mnt/storage -o ro,guest,vers=3.0,nosuid,nodev,noexec,uid=1000,gid=1000; fi
 findmnt -no OPTIONS /mnt/storage | tr ',' '\n' | grep -qx ro
 if ! grep -q '[[:space:]]/mnt/storage[[:space:]]' /etc/fstab; then
  printf '%s /mnt/storage cifs ro,guest,vers=3.0,nosuid,nodev,noexec,uid=1000,gid=1000,_netdev,nofail,x-systemd.automount,x-systemd.mount-timeout=15s 0 0\n' "$share" >> /etc/fstab
 fi
fi
cat > /etc/systemd/system/dataark.service <<'UNIT'
[Unit]
Description=Data Ark isolated ARM64 emulator API
After=network-online.target
[Service]
User=admin
Group=admin
WorkingDirectory=/opt/dataark
ExecStart=/opt/dataark/venv/bin/python -m uvicorn deploy.emulator.asgi:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
UNIT
cat > /etc/systemd/system/kiwix-serve.service <<'UNIT'
[Unit]
Description=Read-only emulator Kiwix library
After=network-online.target
RequiresMountsFor=/mnt/storage
[Service]
User=admin
Group=admin
ExecStart=/bin/sh -c 'set -- /mnt/storage/*.zim; test -f "$1" || exit 0; exec /usr/bin/kiwix-serve --port=8080 "$@"'
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ReadOnlyPaths=/mnt/storage
[Install]
WantedBy=multi-user.target
UNIT
cat > /etc/apache2/sites-available/dataark-emulator.conf <<'APACHE'
<VirtualHost *:80>
 ServerName dataark-emulator
 DocumentRoot /var/www/html
 ProxyPreserveHost On
 ProxyPass /api/ http://127.0.0.1:8000/
 ProxyPassReverse /api/ http://127.0.0.1:8000/
 Alias /library-files/ /mnt/storage/
 <Directory /var/www/html>
  Require all granted
  Options FollowSymLinks
  AllowOverride None
 </Directory>
 <Directory /mnt/storage>
  Require all granted
  Options Indexes
  AllowOverride None
  DirectoryIndex disabled
  <FilesMatch "^\.">
   Require all denied
  </FilesMatch>
 </Directory>
</VirtualHost>
APACHE
a2enmod proxy proxy_http headers alias >/dev/null
a2dissite 000-default >/dev/null
a2ensite dataark-emulator >/dev/null
apache2ctl configtest
# Mark this instance clearly without importing the physical Ark's messages.
venv/bin/python - <<'PY'
from pathlib import Path
p=Path('/opt/dataark/app/templates/index.html');s=p.read_text();notice='<aside class="ark-notice" style="background:#203e54;color:#f5da83">ARM64 TEST ARK · Shared media is read-only. Hardware and household control actions are disabled.</aside>'
if notice not in s:s=s.replace('<body','<body',1);at=s.index('>',s.index('<body'))+1;s=s[:at]+notice+s[at:];p.write_text(s)
PY
bash deploy/deploy-web.sh > /var/log/dataark-emulator/publish.log 2>&1
systemctl daemon-reload
systemctl enable --now dataark apache2 kiwix-serve
systemctl restart apache2
printf 'Emulator API, dashboard, documents and Kiwix configured.\n'
