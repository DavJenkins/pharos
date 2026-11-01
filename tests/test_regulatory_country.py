from pathlib import Path
import tempfile
import unittest
from deploy.bootstrap_platform import DebianAdapter


class RegulatoryCountry(unittest.TestCase):
    def test_headless_country_setup_preserves_boot_arguments_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'boot/firmware/cmdline.txt';target.parent.mkdir(parents=True)
            countries=root/'usr/share/zoneinfo/iso3166.tab';countries.parent.mkdir(parents=True);countries.write_text('US\tUnited States\nGB\tUnited Kingdom\n')
            original='console=tty1 root=PARTUUID=abc quiet cfg80211.ieee80211_regdom=GB\n';target.write_text(original)
            commands=[];adapter=DebianAdapter(lambda args:commands.append(args))
            adapter.country('US',True,root);adapter.country('US',True,root)
            self.assertEqual(target.read_text(),'console=tty1 root=PARTUUID=abc quiet cfg80211.ieee80211_regdom=US\n')
            self.assertEqual((root/'var/backups/dataark-bootstrap/cmdline-before-country.txt').read_text(),original)
            self.assertEqual(commands,[['iw','reg','set','US'],['nmcli','radio','wifi','on']]*2)
            self.assertFalse(any('raspi-config' in command for command in commands))
            with self.assertRaises(ValueError):adapter.country('ZZ',True,root)
            self.assertEqual(target.read_text(),'console=tty1 root=PARTUUID=abc quiet cfg80211.ieee80211_regdom=US\n')

    def test_invalid_country_does_not_mutate_anything(self):
        commands=[]
        with self.assertRaises(ValueError):DebianAdapter(lambda args:commands.append(args)).country('US;bad',True)
        self.assertEqual(commands,[])

    def test_generic_country_does_not_touch_pi_boot_files(self):
        commands=[];DebianAdapter(lambda args:commands.append(args)).country('US')
        self.assertEqual(commands,[['iw','reg','set','US']])
