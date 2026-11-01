"""A native DEJ-colored icon group for the Pi desktop, using its real files/mounts."""
import configparser
import io
from pathlib import Path
import signal
import subprocess


def panel_css(style):
    return ('window {background:transparent;} #ark-icon-group {background-color:'+style['background']+';border:1px solid '+style['border']+';border-radius:'+str(style['radius'])+'px;padding:10px;} '
            '#ark-icon-group button {background:transparent;box-shadow:none;border:1px solid transparent;border-radius:7px;color:'+style['text']+';padding:6px 10px;} '
            '#ark-icon-group button:hover {background-color:rgba(212,175,55,0.16);border-color:'+style['border']+';} '
            '#ark-icon-group button:focus {border-color:'+style['border']+';} #ark-icon-group label {font-size:14px;}')


def run(settings):
    import gi
    gi.require_version('Gtk','3.0');gi.require_version('GtkLayerShell','0.1')
    from gi.repository import Gtk,Gdk,Gio,GLib,GtkLayerShell,Pango
    home=Path.home();desktop=home/'Desktop';directory=home/'.config/pcmanfm/default'
    display=Gdk.Display.get_default();screen=display.get_default_screen();volumes=Gio.VolumeMonitor.get()
    record=home/'.config/dataark/native-desktop-icons.json'
    import json
    original={Path(k):v for k,v in json.loads(record.read_text()).items()} if record.exists() else {}
    windows=[];watches=[];pending=[False]
    def read(path):
        ini=configparser.RawConfigParser(strict=False);ini.optionxform=str;ini.read_string(path.read_text())
        return ini
    def write(path,ini):
        stream=io.StringIO();ini.write(stream,space_around_delimiters=False);path.write_text(stream.getvalue())
    def native_icons(hidden):
        changed=False
        for path in directory.glob('desktop-items-*.conf'):
            ini=read(path)
            if not ini.has_section('*'):continue
            if hidden:
                if path not in original:original[path]={key:ini.get('*',key,fallback=None) for key in ['folder','show_trash','show_mounts','show_home','show_documents']}
                record.parent.mkdir(parents=True,exist_ok=True)
                record.write_text(json.dumps({str(k):v for k,v in original.items()},indent=2))
                values={'folder':'','show_trash':'0','show_mounts':'0','show_home':'0','show_documents':'0'}
            else:
                if path not in original:continue
                values=original[path]
            for key,value in values.items():
                if value is None:ini.remove_option('*',key)
                else:ini.set('*',key,value)
            write(path,ini);changed=True
        if changed:subprocess.run(['pcmanfm','--reconfigure'],check=False)
    def launch(uri,filename=None):
        if filename and filename.suffix=='.desktop':
            app=Gio.DesktopAppInfo.new_from_filename(str(filename))
            if app:app.launch([],None);return
        Gio.AppInfo.launch_default_for_uri(uri,None)
    def items():
        groups={'trash':[('Trash',Gio.ThemedIcon.new('user-trash'),'trash:///',None)],'files':[],'mounts':[]}
        for path in sorted(desktop.iterdir()):
            if path.name.startswith('.'):continue
            name=path.name;icon=Gio.ThemedIcon.new('folder' if path.is_dir() else 'text-x-generic')
            if path.suffix=='.desktop':
                app=Gio.DesktopAppInfo.new_from_filename(str(path))
                if app:name=app.get_display_name();icon=app.get_icon() or icon
            groups['files'].append((name,icon,path.as_uri(),path))
        for mount in volumes.get_mounts():
            groups['mounts'].append((mount.get_name(),mount.get_icon(),mount.get_root().get_uri(),None))
        return [item for group in settings.get('order',['files','trash','mounts']) for item in groups.get(group,[])]
    provider=Gtk.CssProvider();provider.load_from_data(panel_css(settings['panel']).encode())
    Gtk.StyleContext.add_provider_for_screen(screen,provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    def rebuild():
        pending[0]=False
        for window in windows:window.destroy()
        windows.clear()
        for i in range(display.get_n_monitors()):
            window=Gtk.Window();window.set_decorated(False);window.set_app_paintable(True)
            visual=screen.get_rgba_visual()
            if visual:window.set_visual(visual)
            GtkLayerShell.init_for_window(window);GtkLayerShell.set_layer(window,GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_monitor(window,display.get_monitor(i));GtkLayerShell.set_anchor(window,GtkLayerShell.Edge.TOP,True)
            GtkLayerShell.set_margin(window,GtkLayerShell.Edge.TOP,settings.get('top',60))
            GtkLayerShell.set_keyboard_mode(window,getattr(GtkLayerShell.KeyboardMode,'ON_DEMAND',GtkLayerShell.KeyboardMode.NONE))
            box=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=2);box.set_name('ark-icon-group');window.add(box)
            for name,icon,uri,path in items():
                button=Gtk.Button();button.set_size_request(122,-1);column=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5)
                image=Gtk.Image.new_from_gicon(icon,Gtk.IconSize.DIALOG);image.set_pixel_size(48);column.pack_start(image,False,False,0)
                label=Gtk.Label(label=name);label.set_max_width_chars(15);label.set_line_wrap(True);label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR);label.set_justify(Gtk.Justification.CENTER)
                column.pack_start(label,False,False,0);button.add(column);button.connect('clicked',lambda unused,u=uri,p=path:launch(u,p));box.pack_start(button,False,False,0)
            windows.append(window);window.show_all()
        native_icons(True)
        return False
    def queue(*unused):
        if not pending[0]:pending[0]=True;GLib.timeout_add_seconds(1,rebuild)
    for event in ['mount-added','mount-removed']:volumes.connect(event,queue)
    screen.connect('monitors-changed',queue)
    watch=Gio.File.new_for_path(str(desktop)).monitor_directory(Gio.FileMonitorFlags.NONE,None);watches.append(watch);watch.connect('changed',queue)
    GLib.timeout_add_seconds(2,rebuild)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGTERM,lambda: (Gtk.main_quit(),False)[1])
    try:Gtk.main()
    finally:native_icons(False)
