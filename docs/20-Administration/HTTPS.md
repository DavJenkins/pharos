# Optional HTTPS

Open `/config/https.html` and unlock with the caretaker password. HTTP remains available. HTTPS is optional and is not a prerequisite for offline use.

Use a public domain you control and a contact email. Explicitly accept the certificate authority terms before requesting a certificate. The page displays a DNS TXT challenge. Add that record at your DNS provider, wait for publication, then choose Verify DNS. DNS-01 requires no inbound internet access to the Ark. Successful verification installs the certificate and checks local TLS before reporting success. No HTTP redirect or HSTS is enabled.

The hotspot resolves the chosen hostname locally. Other LAN clients need their own DNS or hosts entry pointing the hostname at the Ark. Remote desktop and terminal services retain their separate certificate settings.

Renewal uses the same manual DNS workflow; the Ark does not hold DNS-provider credentials. The health API and Home Assistant package warn within 30 days of expiry and report expired certificates. An expired certificate does not disable HTTP.

Private keys, ACME accounts, contact details and device identity live on the system drive under root-owned `/etc/dataark`, outside content/recovery exports. Configuration-only and populated source-based clones start with a new identity and deferred HTTPS setup. A raw full system-drive image can copy private identity and secrets: do not distribute it as a public seed.

The stock installer installs Certbot and `deploy/install_https.py`. The privileged helper accepts a fixed JSON protocol through a single no-argument command; it does not accept arbitrary shell commands. Failed activation rolls back the previous Apache/DNS configuration. A fresh device needs an internet connection for certificate issuance, but continues serving local content without one.
