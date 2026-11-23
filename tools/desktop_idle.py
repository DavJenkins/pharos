#!/usr/bin/python3
"""Show Pharos connection details and power down idle Wayland displays."""

import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time

SHOW_AFTER = 10 * 60
STANDBY_AFTER = SHOW_AFTER + 20 * 60


# Visit each point in a five-column, four-row grid in a closed route.
SCENE_ROUTE = (
    (0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
    (4, 1), (3, 1), (2, 1), (1, 1),
    (1, 2), (2, 2), (3, 2), (4, 2),
    (4, 3), (3, 3), (2, 3), (1, 3), (0, 3),
    (0, 2), (0, 1),
)
SCENE_POSITIONS = tuple((0.08 + col * 0.21, 0.10 + row * (0.80 / 3))
                        for col, row in SCENE_ROUTE)
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
        fields = {}
        for line in properties:
            if line.lstrip().startswith(('phy#', 'Unnamed/non-netdev')):
                break
            key, _, value = line.lstrip().partition(' ')
            if key in ('type', 'ssid'):
                fields.setdefault(key, value)
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
            connections.append((f'Wi-Fi network: {ssid}', addresses(interface), interface))

    for interface in interfaces:
        name = interface['ifname']
        if name in radios or 'LOWER_UP' not in interface.get('flags', []):
            continue
        if interface.get('link_type') == 'ether' and (Path('/sys/class/net') / name / 'device').exists():
            connections.append(('Ethernet', addresses(name), name))

    for interface, (mode, ssid) in radios.items():
        if mode != 'managed':
            continue
        link = command_output('/usr/sbin/iw', 'dev', interface, 'link')
        match = re.search(r'(?m)^[ \t]*SSID: (.+)$', link)
        if match:
            connections.append((f'Wi-Fi connection: {match[1]}', addresses(interface), interface))
        elif ssid and 'LOWER_UP' in by_name.get(interface, {}).get('flags', []):
            connections.append((f'Wi-Fi connection: {ssid}', addresses(interface), interface))

    return socket.gethostname(), tuple(connections)


def hotspot_short_names(connections):
    hotspot_addresses = {ip for label, group, _ in connections
                         if label.startswith('Wi-Fi network: ') for ip in group}
    if not hotspot_addresses:
        return {}
    try:
        config = Path('/etc/dataark/portal-dns.conf').read_text(encoding='utf-8')
    except OSError:
        return {}
    prefix = 'address=/dataark/'
    published = {line.strip()[len(prefix):] for line in config.splitlines()
                 if line.strip().startswith(prefix)}
    matching = hotspot_addresses & published
    if not matching or command_output('systemctl', 'is-active', 'dataark-portal-dns.service').strip() != 'active':
        return {}
    return {ip: 'dataark' for ip in matching}


def verified_names(hostname, connections):
    addresses = tuple(dict.fromkeys(ip for _, group, _ in connections for ip in group))
    if not addresses:
        return {}
    local_name = f'{hostname.split(".")[0]}.local'
    names = {}
    for _, group, interface in connections:
        try:
            index = socket.if_nametoindex(interface)
        except OSError:
            continue
        for protocol in sorted({int(':' in ip) for ip in group}):
            response = command_output(
                'busctl', '--system', 'call', 'org.freedesktop.Avahi', '/',
                'org.freedesktop.Avahi.Server', 'ResolveHostName', 'iisiu',
                str(index), str(protocol), local_name, str(protocol), '0',
            )
            try:
                fields = shlex.split(response)
            except ValueError:
                continue
            if len(fields) == 7 and fields[0] == 'iisisu' and fields[1] == str(index):
                name, resolved = fields[3], fields[5]
                if resolved in group and name.casefold() == local_name.casefold():
                    names[resolved] = name
    for address in addresses:
        records = command_output('getent', '-s', 'dns', 'hosts', address).split()
        if len(records) < 2:
            continue
        name = records[1].rstrip('.')
        if not name:
            continue
        forward = command_output('getent', '-s', 'dns', 'ahosts', name)
        if any(line.split()[:1] == [address] for line in forward.splitlines()):
            names[address] = name
    for address, short_name in hotspot_short_names(connections).items():
        existing = names.get(address)
        names[address] = f'{short_name}, {existing}' if existing else short_name
    return names


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
    from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell, Pango

    if not GtkLayerShell.is_supported():
        return

    display = Gdk.Display.get_default()
    css = Gtk.CssProvider()
    css.load_from_data(b"""
        window.pharos-idle { background-color: #03060b; }
        .pharos-idle label {
            color: #e8f4ff;
            font-family: "DejaVu Sans", sans-serif;
            text-shadow: 0 1px 2px #02050a, 0 0 4px #02050a, 0 0 7px #02050a;
        }
        .pharos-idle .copy-panel {
            background-color: rgba(3, 9, 17, 0.54);
            border-radius: 5px;
            padding: 4px 8px;
        }
        .pharos-idle .ark-title { color: #f3faff; font-size: 22px; font-weight: bold; }
        .pharos-idle .section-title { color: #b7e2ff; font-size: 17px; font-weight: bold; }
        .pharos-idle .context, .pharos-idle .device-name { font-size: 14px; }
        .pharos-idle .wifi-network { color: #b7e2ff; font-size: 15px; font-weight: bold; }
        .pharos-idle .local-address {
            font-family: "DejaVu Sans Mono", monospace;
            font-size: 14px;
            font-weight: bold;
        }
        .pharos-idle .lighthouse { border: 1px solid #283444; background-color: #050b15; }
    """)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    windows = []
    shown_at = 0.0
    lines = ()
    dimmed = False
    powered_off = False
    dns_names = {}
    lookup_pending = False

    def set_details(name, networks):
        hostname, connections = lines
        name.set_text(f'Device name: {hostname}')
        for child in networks.get_children():
            networks.remove(child)
        if not connections:
            networks.add(styled_label('No active network address', 'context'))
        for label, addresses, _ in connections:
            network = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            network.add(styled_label(label, 'wifi-network'))
            entries = []
            for address in addresses:
                dns_name = dns_names.get(address, '')
                first, _, other_names = dns_name.partition(', ')
                if first == 'dataark':
                    entries.append('http://dataark/')
                    dns_name = other_names
                entries.append(f'{dns_name} ({address})' if dns_name else address)
            text = '\n'.join(entries)
            address_block = styled_label(text or 'No IP address assigned', 'local-address')
            address_block.set_line_wrap(True)
            address_block.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            address_block.set_max_width_chars(46)
            network.add(address_block)
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
                0, round(height * 0.13),
                round(width * 0.66), round(height * 0.55),
            )
            return crop.scale_simple(504, 315, GdkPixbuf.InterpType.BILINEAR)
        return None

    def styled_label(text, style):
        label = Gtk.Label(label=text, xalign=0)
        label.get_style_context().add_class(style)
        return label

    def make_beacon():
        size = 76
        center = (size - 1) / 2
        pixels = bytearray()
        for y in range(size):
            for x in range(size):
                radius = math.hypot(x - center, y - center) / center
                halo = max(0, 1 - radius) ** 2
                core = max(0, 1 - radius / 0.25) ** 2
                pixels.extend((round(72 + 167 * core), round(146 + 98 * core),
                               255, round(245 * halo)))
        return GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new(bytes(pixels)), GdkPixbuf.Colorspace.RGB,
            True, 8, size, size, size * 4,
        )

    art = load_lighthouse()
    glow = make_beacon() if art is not None else None

    def lighthouse(header, details):
        if art is None:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            card.add(header)
            card.add(details)
            return card, None
        portrait = Gtk.Image.new_from_pixbuf(art)
        portrait.set_opacity(0.49)
        frame = Gtk.Overlay()
        frame.get_style_context().add_class('lighthouse')
        frame.add(portrait)

        lights = Gtk.Fixed()
        beacon = Gtk.Image.new_from_pixbuf(glow)
        lights.put(beacon, 348, 74)
        frame.add_overlay(lights)

        header.get_style_context().add_class('copy-panel')
        header.set_halign(Gtk.Align.START)
        header.set_valign(Gtk.Align.START)
        header.set_margin_start(152)
        header.set_margin_end(16)
        header.set_margin_top(9)
        frame.add_overlay(header)

        details.get_style_context().add_class('copy-panel')
        details.set_halign(Gtk.Align.START)
        details.set_valign(Gtk.Align.START)
        details.set_margin_start(16)
        details.set_margin_end(16)
        details.set_margin_top(141)
        frame.add_overlay(details)
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
                beacon.set_opacity(0.06 + 0.89 * phase ** 2)
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
            header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            header.add(styled_label('Pharos Data Ark', 'ark-title'))
            header.add(styled_label('Offline library and tools', 'section-title'))

            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            name = styled_label('', 'device-name')
            details.add(name)
            details.add(styled_label('Open the address for your network.', 'context'))
            networks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            details.add(networks)
            set_details(name, networks)
            info, beacon = lighthouse(header, details)
            info.set_opacity(0)
            canvas.put(info, 0, 0)
            window.add(canvas)
            windows.append((window, canvas, info, name, networks, beacon))
            window.show_all()

    def update_labels():
        for _, _, _, name, networks, _ in windows:
            set_details(name, networks)

    def look_up_names():
        nonlocal lookup_pending
        if lookup_pending:
            return
        lookup_pending = True
        snapshot = lines

        def apply_names(names):
            nonlocal dns_names, lookup_pending
            lookup_pending = False
            if dimmed and lines == snapshot and names != dns_names:
                dns_names = names
                update_labels()
            return GLib.SOURCE_REMOVE

        def resolve():
            GLib.idle_add(apply_names, verified_names(*snapshot))

        threading.Thread(target=resolve, daemon=True).start()

    def refresh_details():
        nonlocal lines, dns_names
        if dimmed:
            updated = connection_details()
            if updated != lines:
                lines, dns_names = updated, {}
                update_labels()
            look_up_names()
        return GLib.SOURCE_CONTINUE

    def handle_event(event):
        nonlocal dimmed, lines, shown_at, powered_off, dns_names
        if event == b'show' and not powered_off:
            dimmed = True
            shown_at = time.monotonic()
            lines, dns_names = connection_details(), {}
            update_outputs()
            look_up_names()
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
    dns_names = {}
    lookup_pending = False

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
