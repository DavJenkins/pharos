# Optional HTTPS acceptance

**1 November 2026 - physical Raspberry Pi 4 test appliance.**

The Ark obtained and installed a publicly trusted Let's Encrypt certificate for the dedicated test hostname `ark-test.dejsoftware.com`. DNS-01 verification used temporary TXT records in the domain's authoritative Cloudflare zone. No inbound internet exposure, website record changes or DNS-provider credentials on the Ark were needed.

## Verified

- Staging certificate issuance completed. The staging certificate was kept in an isolated test directory and was not installed into Apache or a normal trust store.
- Certbot's staging renewal dry run completed after publishing a fresh DNS challenge. Renewal remains the manual DNS approval workflow, not unattended renewal.
- The normal Ark HTTPS worker issued a production certificate, verified its hostname, private-key match and public trust chain, and activated it in Apache. The certificate expires on 30 January 2027.
- Linux system trust, Windows system trust and a normal browser accepted HTTPS without disabling certificate verification or bypassing a warning.
- HTTP remained available. HTTPS continued serving the API in the wired browser while the Pi's IPv4 upstream default route was temporarily removed. There was no IPv6 default route. Original upstream routing was restored automatically.
- Temporary renewal-due and expired status metadata produced warning/error health states. Home Assistant recorded warning at 15:34:28, error at 15:35:30 and OK at 15:36:01, America/New_York. The actual certificate and system clock were unchanged; original status was restored and the alert cleared.
- The captive DNS listener at port 1053 resolved the certificate hostname to the hotspot address. Its nftables client DNS redirect was present. A local query to NetworkManager's port 53 is not the captive-client path.
- Recipient preparation refused an installed owner-specific certificate. A certificate added after a card was armed also blocks identity replacement before any identity changes. A configured owner certificate must be retired before preparing that card for a different owner.
- All 27 focused HTTPS, integration-health and recipient tests passed. No systemd units were failed at the end.
- Temporary challenge TXT records and the Windows test hostname mapping were removed. No private certificate keys or ACME account credentials are included in the public result.

## Corrections retained in source

The root HTTPS helper treated only systemd's `active` state as running. A long `Type=oneshot` certificate worker remains `activating` while waiting for DNS, so the normal Verify action incorrectly rejected its pending challenge. The helper now recognizes active, activating and reloading states; regression coverage includes the oneshot wait.

Recipient identity establishment now precedes HTTPS status reconciliation, preventing stale device identity in certificate telemetry. Recipient startup checks for an owner certificate added after preparation was armed.

## Phone acceptance and test-card cleanup

The owner confirmed that a phone connected through the DataArk hotspot opened the trusted HTTPS hostname without any certificate warning, then used internet pass-through to continue the conversation. This completes the phone-radio acceptance check.

After that check, the temporary test certificate, its private key, production and staging ACME account material, and the test hostname's captive-DNS mapping were removed from the test card. Apache and captive DNS configuration checks passed, and local HTTP returned 200 after cleanup. Public acceptance results remain available.

Recipient preparation remains unarmed and the current test login is retained for the clean physical installation replay. The card is not yet prepared for mailing; recipient preparation will replace its identity and credentials before handoff.

The [machine-readable result](HTTPSAcceptance.json) records the public certificate details, observations and exact tested helper hashes. This test does not establish an uninterrupted fresh-OS recovery replay or imply that the older published bootstrap archive contains these fixes.
