# Desktop and startup artwork

On Raspberry Pi OS Desktop, **Open Data Ark** opens the local dashboard in the browser. It is available on the desktop and in the application menu. It uses `http://127.0.0.1/`, so it does not depend on hostname discovery or internet access.

The Pharos scene is used for the desktop wallpaper, login background and native Plymouth boot splash. The approved widescreen artwork fills a 16:9 display without side bars. The original illustration remains a separate asset. The default fill mode crops edges rather than stretching the picture. The mode can be changed to fit when preserving the entire scene on another screen shape matters more than filling it.

`config/desktop.json` controls the shortcut label, artwork paths, wallpaper mode and background color, login background and boot splash. The installer discovers existing PCManFM monitor configurations, including named HDMI outputs, and preserves their other preferences. Hosts without this desktop are skipped; no graphical environment is installed on a headless server.

To apply the configuration:

```bash
sudo /usr/bin/python3 /opt/dataark/deploy/install_desktop.py
```

Existing settings are backed up under `/var/backups/dataark-desktop/`. The previous Plymouth theme name is recorded there. The native Pi splash script is reused with Ark artwork, and the normal initramfs updater rebuilds the boot images. Repeating the installer with unchanged settings does not rebuild them again.

The desktop reads its configuration when it starts. An already running PCManFM session can reload it with `pcmanfm --reconfigure` as the desktop user. The login background and splash are visible on the next login or boot; applying artwork does not require restarting the current web service.
