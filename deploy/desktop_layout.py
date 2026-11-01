#!/usr/bin/python3
"""Keep visible desktop items in a configured row above the Pharos lighthouse."""
import configparser
import io
import json
from pathlib import Path
import subprocess


def positions(items, width, settings):
    spacing = min(settings.get('spacing',132), max(64, width // max(1,len(items))))
    cell = settings.get('cell_width',124)
    start = max(0,(width - (len(items)-1)*spacing-cell)//2)
    return {name:{'x':str(start+i*spacing),'y':str(settings.get('top',60))} for i,name in enumerate(items)}


def main():
    import gi
    gi.require_version('Gdk','3.0')
    from gi.repository import Gdk,Gio,GLib
    config=Path('/opt/dataark/config/desktop.json')
    settings=json.loads(config.read_text()).get('icons',{})
    if settings.get('layout')!='top-center':return
    if settings.get('panel',{}).get('enabled'):
        import importlib.util
        module=Path(__file__).with_name('dataark_desktop_panel.py')
        if not module.exists():module=Path(__file__).with_name('desktop_panel.py')
        spec=importlib.util.spec_from_file_location('dataark_desktop_panel',module)
        panel=importlib.util.module_from_spec(spec);spec.loader.exec_module(panel)
        panel.run(settings)
        return
    home=Path.home();directory=home/'.config/pcmanfm/default'
    display=Gdk.Display.get_default();screen=display.get_default_screen()
    volumes=Gio.VolumeMonitor.get();pending=[False]
    def arrange():
        pending[0]=False;changed=False
        for i in range(display.get_n_monitors()):
            monitor=display.get_monitor(i);width=monitor.get_geometry().width
            connector=screen.get_monitor_plug_name(i)
            path=directory/('desktop-items-'+(connector or str(i))+'.conf')
            if not path.exists():
                fallback=directory/'desktop-items-0.conf'
                if not fallback.exists():continue
                text=fallback.read_text()
            else:text=path.read_text()
            ini=configparser.RawConfigParser(strict=False);ini.optionxform=str;ini.read_string(text)
            visible=[]
            if ini.getboolean('*','show_trash',fallback=True):visible.append('trash:///')
            visible.extend(p.name for p in sorted((home/'Desktop').iterdir()) if not p.name.startswith('.'))
            if ini.getboolean('*','show_home',fallback=False):visible.append(home.name)
            if ini.getboolean('*','show_documents',fallback=False):visible.append('Documents')
            if ini.getboolean('*','show_mounts',fallback=True):
                for mount in volumes.get_mounts():
                    location=mount.get_root().get_path()
                    if location:visible.append(Path(location).name)
            visible=list(dict.fromkeys(visible))
            for name,xy in positions(visible,width,settings).items():
                name=name.replace('\\','\\\\').replace('\r','\\r').replace('\n','\\n').replace('[','\\[').replace(']','\\]')
                if not ini.has_section(name):ini.add_section(name)
                for key,value in xy.items():ini.set(name,key,value)
            out=io.StringIO();ini.write(out,space_around_delimiters=False)
            if out.getvalue()!=text:
                path.write_text(out.getvalue());changed=True
        if changed:subprocess.run(['pcmanfm','--reconfigure'],check=False)
        return False
    def queue(*unused):
        if not pending[0]:pending[0]=True;GLib.timeout_add_seconds(2,arrange)
    for event in ['mount-added','mount-removed']:volumes.connect(event,queue)
    screen.connect('monitors-changed',queue)
    watch=Gio.File.new_for_path(str(home/'Desktop')).monitor_directory(Gio.FileMonitorFlags.NONE,None)
    watch.connect('changed',queue)
    GLib.timeout_add_seconds(5,arrange)
    GLib.MainLoop().run()


if __name__=='__main__':main()
