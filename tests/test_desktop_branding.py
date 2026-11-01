from pathlib import Path
import json
import tempfile
from types import SimpleNamespace
import unittest

from deploy.install_desktop import install, ini_update


class DesktopBrandingTests(unittest.TestCase):
    def test_ini_preserves_other_preferences(self):
        text=ini_update('[*]\nshow_trash=1\nwallpaper=old.png\n','*',{'wallpaper':'new.png'})
        self.assertIn('show_trash=1',text)
        self.assertIn('wallpaper=new.png',text)

    def test_headless_host_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);repo=root/'repo';(repo/'config').mkdir(parents=True)
            (repo/'config/desktop.json').write_text('{"schema":1,"enabled":true}')
            self.assertEqual(install(repo,root)['status'],'skipped')
            self.assertFalse((root/'usr').exists())

    def test_desktop_login_splash_and_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);repo=root/'repo';(repo/'config').mkdir(parents=True)
            config=json.loads((Path(__file__).resolve().parents[1]/'config/desktop.json').read_text())
            (repo/'config/desktop.json').write_text(json.dumps(config))
            image=repo/config['wallpaper']['source'];image.parent.mkdir(parents=True);image.write_bytes(b'configured artwork')
            icon=repo/config['shortcut']['icon'];icon.parent.mkdir(parents=True,exist_ok=True);icon.write_bytes(b'configured icon')
            desktop=root/'etc/xdg/pcmanfm/default';desktop.mkdir(parents=True)
            (desktop/'desktop-items-0.conf').write_text('[*]\nshow_trash=1\nwallpaper=old.png\n')
            monitor=root/'home/admin/.config/pcmanfm/default/desktop-items-HDMI-A-2.conf'
            monitor.parent.mkdir(parents=True);monitor.write_text('[*]\ndesktop_bg=#eeeeee\n')
            greeter=root/'etc/lightdm/pi-greeter.conf';greeter.parent.mkdir(parents=True);greeter.write_text('[greeter]\ngtk-theme-name=Existing\n')
            script=root/'usr/share/plymouth/themes/pix/pix.script';script.parent.mkdir(parents=True);script.write_text('stock native script')
            calls=[]
            def runner(args,**kwargs):calls.append(args);return SimpleNamespace(stdout='pix\n')
            result=install(repo,root,runner=runner)
            self.assertEqual(result['status'],'installed')
            entry=(root/'home/admin/Desktop/Open Data Ark.desktop').read_text()
            self.assertIn('Exec=xdg-open http://127.0.0.1/',entry)
            self.assertIn('show_trash=1',(desktop/'desktop-items-0.conf').read_text())
            self.assertIn('desktop_bg=#172d40',monitor.read_text())
            self.assertIn('gtk-theme-name=Existing',greeter.read_text())
            self.assertIn(['update-initramfs','-u'],calls)
            self.assertEqual((root/'var/backups/dataark-desktop/etc/xdg/pcmanfm/default/desktop-items-0.conf').read_text(),'[*]\nshow_trash=1\nwallpaper=old.png\n')
            count=len(calls);self.assertEqual(install(repo,root,runner=runner)['changed'],[]);self.assertEqual(len(calls),count)
