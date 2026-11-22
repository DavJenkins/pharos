#!/usr/bin/python3
"""Show Pharos connection details and power down idle Wayland displays."""

import json
import math
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time

SHOW_AFTER = 10 * 60
STANDBY_AFTER = SHOW_AFTER + 20 * 60


SCENE_POSITIONS = ((0.30, 0.25), (0.88, 0.64), (0.40, 0.88), (0.12, 0.56))
POSITION_SECONDS = 30
GLIDE_SECONDS = 6


def scene_position(elapsed):
    index = int(elapsed // POSITION_SECONDS) % len(SCENE_POSITIONS)
    within = elapsed % POSITION_SECONDS
    progress = max(0, (within - (POSITION_SECONDS - GLIDE_SECONDS)) / GLIDE_SECONDS)
    eased = progress * progress * (3 - 2 * progress)
    current = SCENE_POSITIONS[index]
    following = SCENE_POSITIONS[(index + 1) % len(SCENE_POSITIONS)]
    return tuple(a + (b - a) * eased for a, b in zip(current, following))

def command_output(*command):
    try:
        return subprocess.check_output(command, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return ''


def wireless_interfaces():
    radios = {}
    for block in re.split(r'(?m)^[ \t]*Interface ', command_output('/usr/sbin/iw', 'dev'))[1:]:
        interface, *properties = block.splitlines()
        fields = dict(line.lstrip().split(' ', 1) for line in properties if ' ' in line.lstrip())
        radios[interface] = fields.get('type'), fields.get('ssid')
    return radios


def connection_details():
    radios = wireless_interfaces()
    try:
        interfaces = json.loads(command_output('ip', '-j', 'address', 'show', 'up', 'scope', 'global') or '[]')
    except ValueError:
        interfaces = []
    by_name = {interface['ifname']: interface for interface in interfaces}

    def addresses(interface):
        return tuple(dict.fromkeys(
            entry['local'] for entry in by_name.get(interface, {}).get('addr_info', [])
            if entry.get('family') in ('inet', 'inet6') and not entry.get('deprecated')
        ))

    connections = []
    for interface, (mode, ssid) in radios.items():
        if mode == 'AP' and ssid:
            connections.append((f'Wi-Fi network: {ssid}', addresses(interface)))

    for interface in interfaces:
        name = interface['ifname']
        if name in radios or 'LOWER_UP' not in interface.get('flags', []):
            continue
        if interface.get('link_type') == 'ether' and (Path('/sys/class/net') / name / 'device').exists():
            connections.append((f'Ethernet ({name})', addresses(name)))

    for interface, (mode, ssid) in radios.items():
        if mode != 'managed':
            continue
        link = command_output('/usr/sbin/iw', 'dev', interface, 'link')
        match = re.search(r'(?m)^[ \t]*SSID: (.+)$', link)
        if match:
            connections.append((f'Wi-Fi connection: {match[1]}', addresses(interface)))
        elif ssid and 'LOWER_UP' in by_name.get(interface, {}).get('flags', []):
            connections.append((f'Wi-Fi connection: {ssid}', addresses(interface)))

    return socket.gethostname(), tuple(connections)


def idle_command():
    return [
        'swayidle', '-C', '/dev/null', '-w',
        'timeout', str(SHOW_AFTER), r"printf 'show\n'",
        'resume', r"printf 'wake\n'",
        'timeout', str(STANDBY_AFTER), r"printf 'standby\n'",
        'resume', r"printf 'wake\n'",
    ]


def monitor_power(mode):
    try:
        subprocess.run(['wlopm', f'--{mode}', '*'], check=True, timeout=5)
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        print(f'Pharos display power {mode} failed: {exc}', file=sys.stderr)
        return False


def main():
    if not os.environ.get('WAYLAND_DISPLAY'):
        return

    import gi
    gi.require_version('Gdk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
    gi.require_version('Gtk', '3.0')
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell

    if not GtkLayerShell.is_supported():
        return

    display = Gdk.Display.get_default()
    css = Gtk.CssProvider()
    css.load_from_data(b"""
        window.pharos-idle { background-color: #03060b; }
        .pharos-idle .ark-title { color: #b39b66; font: 31px serif; }
        .pharos-idle .ark-subtitle { color: #769ec0; font: bold 16px sans-serif; }
        .pharos-idle .context { color: #a2aeba; font: 16px sans-serif; }
        .pharos-idle .wifi-network { color: #a2bbd0; font: bold 16px sans-serif; }
        .pharos-idle .device-name { color: #8996a5; font: 15px sans-serif; }
        .pharos-idle .local-address { color: #b0bdca; font: 16px monospace; }
        .pharos-idle .lighthouse { border: 1px solid #283444; }
        .pharos-idle .beacon {
            background: radial-gradient(circle, #b1dfff 0%, #589de0 16%, transparent 64%);
        }
    """)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    windows = []
    shown_at = 0.0
    lines = ()
    dimmed = False
    powered_off = False

    def set_details(name, networks):
        hostname, connections = lines
        name.set_text(f'Device name: {hostname}')
        for child in networks.get_children():
            networks.remove(child)
        if not connections:
            networks.add(styled_label('No active network address', 'context'))
        for label, addresses in connections:
            network = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            network.add(styled_label(label, 'wifi-network'))
            urls = (f'http://[{address}]/' if ':' in address else f'http://{address}/'
                    for address in addresses)
            text = '\n'.join(urls)
            network.add(styled_label(text or 'No IP address assigned', 'local-address'))
            networks.add(network)
        networks.show_all()

    def load_lighthouse():
        for path in (Path('/usr/share/dataark/desktop/icon.png'),
                     Path('/opt/dataark/app/static/assets/Pharos Data Ark.png')):
            try:
                artwork = GdkPixbuf.Pixbuf.new_from_file(str(path))
            except GLib.Error:
                continue
            width, height = artwork.get_width(), artwork.get_height()
            crop = artwork.new_subpixbuf(
                round(width * 0.365), round(height * 0.175),
                round(width * 0.28), round(height * 0.70),
            )
            return crop.scale_simple(152, 216, GdkPixbuf.InterpType.BILINEAR)
        return None

    def styled_label(text, style):
        label = Gtk.Label(label=text, xalign=0)
        label.get_style_context().add_class(style)
        return label

    def add_brand(details):
        for root in (Path('/var/www/html/assets'), Path('/opt/dataark/app/static/assets')):
            try:
                wordmark = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(root / 'pharos-data-ark-wordmark-v6.png'), 176, -1, True,
                )
            except GLib.Error:
                continue
            image = Gtk.Image.new_from_pixbuf(wordmark)
            image.set_halign(Gtk.Align.START)
            image.set_opacity(0.75)
            details.add(image)
            return
        details.add(styled_label('Pharos', 'ark-title'))
        details.add(styled_label('DATA ARK', 'ark-subtitle'))

    art = load_lighthouse()

    def lighthouse():
        if art is None:
            return None, None
        portrait = Gtk.Image.new_from_pixbuf(art)
        portrait.set_opacity(0.55)
        frame = Gtk.Overlay()
        frame.get_style_context().add_class('lighthouse')
        frame.add(portrait)

        lights = Gtk.Fixed()
        beacon = Gtk.EventBox()
        beacon.get_style_context().add_class('beacon')
        beacon.set_size_request(50, 50)
        lights.put(beacon, 52, 22)
        frame.add_overlay(lights)
        return frame, beacon

    def animate_scene():
        if not dimmed:
            return GLib.SOURCE_CONTINUE
        elapsed = time.monotonic() - shown_at
        x, y = scene_position(elapsed)
        phase = (1 + math.cos(elapsed * math.tau / 9)) / 2
        for _, canvas, info, _, _, beacon in windows:
            width, height = canvas.get_allocated_width(), canvas.get_allocated_height()
            if width <= 1 or height <= 1:
                continue
            _, natural = info.get_preferred_size()
            margin_x = min(48, max(0, (width - natural.width) // 2))
            margin_y = min(48, max(0, (height - natural.height) // 2))
            left = margin_x + round(x * max(0, width - natural.width - 2 * margin_x))
            top = margin_y + round(y * max(0, height - natural.height - 2 * margin_y))
            if (left != canvas.child_get_property(info, 'x')
                    or top != canvas.child_get_property(info, 'y')):
                canvas.move(info, left, top)
            if info.get_opacity() == 0:
                info.set_opacity(1)
            if beacon is not None:
                beacon.set_opacity(0.12 + 0.60 * phase ** 3)
        return GLib.SOURCE_CONTINUE

    def close_windows():
        while windows:
            window, *_ = windows.pop()
            window.destroy()

    def update_outputs(*_):
        close_windows()
        if not dimmed:
            return
        for index in range(display.get_n_monitors()):
            window = Gtk.Window()
            GtkLayerShell.init_for_window(window)
            GtkLayerShell.set_namespace(window, 'pharos-display-idle')
            GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_monitor(window, display.get_monitor(index))
            GtkLayerShell.set_exclusive_zone(window, -1)
            for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                         GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
                GtkLayerShell.set_anchor(window, edge, True)
            window.get_style_context().add_class('pharos-idle')
            canvas = Gtk.Fixed()
            info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
            info.set_opacity(0)
            portrait, beacon = lighthouse()
            if portrait is not None:
                info.add(portrait)
            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            details.set_valign(Gtk.Align.CENTER)
            add_brand(details)
            about = styled_label('Offline library and tools', 'context')
            about.set_margin_top(14)
            details.add(about)
            name = styled_label('', 'device-name')
            details.add(name)
            details.add(styled_label('Open the address for your network.', 'context'))
            networks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            networks.set_margin_top(8)
            details.add(networks)
            info.add(details)
            set_details(name, networks)
            canvas.put(info, 0, 0)
            window.add(canvas)
            windows.append((window, canvas, info, name, networks, beacon))
            window.show_all()

    def refresh_details():
        nonlocal lines
        if dimmed:
            updated = connection_details()
            if updated != lines:
                lines = updated
                for _, _, _, name, networks, _ in windows:
                    set_details(name, networks)
        return GLib.SOURCE_CONTINUE

    def handle_event(event):
        nonlocal dimmed, lines, shown_at, powered_off
        if event == b'show' and not powered_off:
            dimmed = True
            shown_at = time.monotonic()
            lines = connection_details()
            update_outputs()
        elif event == b'standby' and display.get_n_monitors():
            powered_off = True
            if monitor_power('off'):
                dimmed = False
                close_windows()
        elif event == b'wake':
            dimmed = False
            close_windows()
            if powered_off and monitor_power('on'):
                powered_off = False

    idle = subprocess.Popen(idle_command(), stdout=subprocess.PIPE)
    pending = b''

    def on_idle_output(fd, _condition):
        nonlocal pending
        chunk = os.read(fd, 4096)
        if not chunk:
            Gtk.main_quit()
            return GLib.SOURCE_REMOVE
        events = (pending + chunk).split(b'\n')
        pending = events.pop()
        for event in events:
            handle_event(event)
        return GLib.SOURCE_CONTINUE

    def stop():
        Gtk.main_quit()
        return GLib.SOURCE_REMOVE

    display.connect_after('monitor-added', update_outputs)
    display.connect_after('monitor-removed', update_outputs)
    GLib.timeout_add_seconds(30, refresh_details)
    GLib.timeout_add(40, animate_scene)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, stop)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, stop)
    GLib.io_add_watch(idle.stdout.fileno(), GLib.PRIORITY_DEFAULT,
                      GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, on_idle_output)
    try:
        Gtk.main()
    finally:
        handle_event(b'wake')
        idle.terminate()
        idle.wait(timeout=5)
        idle.stdout.close()


if __name__ == '__main__':
    main()
