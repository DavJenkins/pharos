# Public content configuration

The authoritative copy is this directory on the Pi system drive. A readable mirror is kept under `/mnt/storage/DATA-ARK-CONFIG`.

Edit `content.yaml` enabled flags and the named files in `deploy/reference`; run `tools/content_profile.py plan` before restoring. See `docs/20-Administration/ContentRestoration.md` for capture, shipping, restoration and limitations. Never overwrite this selection with an empty-drive inventory.
