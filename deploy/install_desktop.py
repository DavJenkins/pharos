#!/usr/bin/python3
"""Install configured Ark branding on an existing Pi desktop; headless hosts skip it."""
import configparser
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def ini_update(text, section, values):
    ini = configparser.RawConfigParser(strict=False)
    ini.optionxform = str
    ini.read_string(text)
    if not ini.has_section(section):
        ini.add_section(section)
    for key, value in values.items():
        ini.set(section, key, value)
    stream = io.StringIO()
    ini.write(stream, space_around_delimiters=False)
    return stream.getvalue()


def asset(repo, name):
    path = repo / name
    if Path(name).is_absolute() or '..' in Path(name).parts or not path.resolve().is_relative_to(repo.resolve()) or not path.is_file():
        raise ValueError('Desktop artwork must be an existing repository asset.')
    return path.read_bytes()


def install(repo=ROOT, system=Path('/'), user='admin', runner=subprocess.run, owner=None):
    config = json.loads((repo / 'config/desktop.json').read_text(encoding='utf-8'))
    if config.get('schema') != 1:
        raise ValueError('Unsupported desktop configuration schema.')
    if not config.get('enabled'):
        return {'status': 'disabled'}
    desktop = system / 'etc/xdg/pcmanfm/default'
    if not desktop.is_dir():
        return {'status': 'skipped', 'reason': 'No supported desktop installed'}
    shortcut = config['shortcut']; wallpaper = config['wallpaper']
    if shortcut['url'] != 'http://127.0.0.1/' or any('\n' in shortcut[k] for k in ('name', 'comment')):
        raise ValueError('Desktop shortcut must open the local Ark.')
    if wallpaper['mode'] not in ('fit', 'crop', 'center', 'stretch', 'tile'):
        raise ValueError('Unsupported wallpaper mode.')
    changed = []
    def write(relative, data, mode=0o644, owned=False):
        target = system / relative
        if target.is_symlink() or any(p.is_symlink() for p in target.parents):
            raise ValueError('Desktop configuration paths cannot be symlinks.')
        if isinstance(data, str):
            data = data.encode('utf-8')
        if target.is_file() and target.read_bytes() == data:
            return
        if target.is_file():
            backup = system / 'var/backups/dataark-desktop' / relative
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            stream.write(data); temp = Path(stream.name)
        temp.chmod(mode)
        if owned and owner is not None:
            os.chown(temp, *owner)
            # Create a usable Desktop/config directory on fresh installations.
            for parent in target.parents:
                if parent == system / 'home' / user:
                    break
                os.chown(parent, *owner)
        temp.replace(target); changed.append(relative)

    image = '/usr/share/dataark/desktop/wallpaper.png'
    icon = '/usr/share/dataark/desktop/icon.png'
    write(image.lstrip('/'), asset(repo, wallpaper['source']))
    write(icon.lstrip('/'), asset(repo, shortcut['icon']))
    entry = '[Desktop Entry]\nType=Application\nName='+shortcut['name']+'\nComment='+shortcut['comment']+'\nExec=xdg-open '+shortcut['url']+'\nIcon='+icon+'\nTerminal=false\nCategories=Education;Utility;\n'
    write('usr/share/applications/dataark.desktop', entry)
    write('home/'+user+'/Desktop/Open Data Ark.desktop', entry, 0o755, True)
    if config.get('icons',{}).get('layout')=='top-center':
        write('usr/local/libexec/dataark-desktop-layout',(repo/'deploy/desktop_layout.py').read_bytes(),0o755)
        if config['icons'].get('panel',{}).get('enabled'):
            write('usr/local/libexec/dataark_desktop_panel.py',(repo/'deploy/desktop_panel.py').read_bytes())
            if system==Path('/') and not any((system/'usr/lib').glob('*/girepository-1.0/GtkLayerShell-0.1.typelib')) and not (system/'usr/lib/girepository-1.0/GtkLayerShell-0.1.typelib').exists():
                runner(['apt-get','install','-y','gir1.2-gtklayershell-0.1'],check=True)
        write('home/'+user+'/.config/autostart/dataark-desktop-layout.desktop','[Desktop Entry]\nType=Application\nName=Data Ark desktop layout\nExec=/usr/bin/python3 /usr/local/libexec/dataark-desktop-layout\nTryExec=pcmanfm\nTerminal=false\nNoDisplay=true\n',owned=True)
    names={'desktop-items-0.conf','desktop-items-1.conf'}
    names.update(p.name for p in desktop.glob('desktop-items-*.conf'))
    user_desktop=system/'home'/user/'.config/pcmanfm/default'
    names.update(p.name for p in user_desktop.glob('desktop-items-*.conf'))
    for filename in sorted(names):
        default=desktop/filename
        text=default.read_text() if default.is_file() else '[*]\n'
        values={'wallpaper':image,'wallpaper_mode':wallpaper['mode'],'wallpaper_common':'1','desktop_bg':wallpaper['background'],'desktop_fg':'#ffffffffffff','desktop_shadow':'#000000000000'}
        write('etc/xdg/pcmanfm/default/'+filename, ini_update(text, '*', values))
        relative='home/'+user+'/.config/pcmanfm/default/'+filename
        existing=system/relative
        write(relative, ini_update(existing.read_text() if existing.is_file() else text, '*', values), owned=True)
    greeter=system/'etc/lightdm/pi-greeter.conf'
    if config['login_background'] and greeter.is_file():
        write('etc/lightdm/pi-greeter.conf', ini_update(greeter.read_text(), 'greeter', {'wallpaper':image,'wallpaper_mode':wallpaper['mode']}))
    splash_script=system/'usr/share/plymouth/themes/pix/pix.script'
    if config['boot_splash'] and splash_script.is_file():
        theme='usr/share/plymouth/themes/dataark/'
        write(theme+'splash.png', asset(repo, wallpaper['source']))
        write(theme+'dataark.script', splash_script.read_bytes())
        write(theme+'dataark.plymouth', '[Plymouth Theme]\nName=Pharos Data Ark\nDescription=Pharos Data Ark\nModuleName=script\n\n[script]\nImageDir=/usr/share/plymouth/themes/dataark\nScriptFile=/usr/share/plymouth/themes/dataark/dataark.script\n')
        if any(name.startswith(theme) for name in changed):
            previous=runner(['plymouth-set-default-theme'],check=True,capture_output=True,text=True).stdout.strip()
            record=system/'var/backups/dataark-desktop/previous-plymouth-theme'
            if not record.exists():
                record.parent.mkdir(parents=True,exist_ok=True);record.write_text(previous+'\n')
            runner(['plymouth-set-default-theme','dataark'],check=True)
            runner(['update-initramfs','-u'],check=True)
    return {'status':'installed','changed':changed,'wallpaper':image,'shortcut':'Open Data Ark'}


if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('Run with sudo to install desktop branding.')
    import pwd
    account=pwd.getpwnam('admin')
    print(json.dumps(install(owner=(account.pw_uid,account.pw_gid)),indent=2))
