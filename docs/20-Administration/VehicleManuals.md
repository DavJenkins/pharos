# Vehicle manuals

The Ark preserves Honda’s official owner’s manuals and quick owner’s guides for the **2017 Accord Sedan** and **2017 Civic Sedan**. Open them from the Vehicle Manuals card on the landing page, or copy the original PDFs from `/library-files/vehicles/`, the public file share, or anonymous FTP.

These are owner documents, including routine maintenance and roadside procedures. They are **not factory workshop/service manuals** and do not supply a complete repair library or all wiring diagrams. Trim, engine, transmission, hybrid status, and fitted equipment have not been confirmed. Check the manual’s applicability before using a procedure; do not assume the Accord hybrid or Civic Si uses the same procedures.

## Sources and restoration

- Human-readable selection: `/opt/dataark/deploy/reference/vehicle-manuals.json`.
- Installer: `sudo /usr/bin/python3 /opt/dataark/tools/install_vehicle_manuals.py`.
- Original PDFs and verified retrieval metadata: `/mnt/storage/vehicles/`.
- Saved content recipe: `/opt/dataark/config/content/content.yaml`, mirrored in `DATA-ARK-CONFIG` on the content drive.
- Config-only restoration downloads these PDFs as direct files. Populated drive replication includes the public `vehicles` folder. Honda copyright and original notices remain unchanged.

Honda’s download server currently omits an intermediate certificate. `deploy/reference/honda-intermediate.pem` supplies DigiCert EV RSA CA G2 for these downloads only; it was verified against the system’s trusted root bundle. Certificate and hostname checks remain enabled. No system trust settings are changed. Replace this intermediate if Honda’s chain changes; never work around a failure by disabling verification.

Additional factory repair material may require a Honda service-information subscription or an owner-supplied licensed manual. No subscription has been purchased and no paid workshop material has been installed.
