#!/usr/bin/python3
"""Show Pharos connection details and power down idle Wayland displays."""

import json
import os
import signal
import socket
import subprocess
import sys

SHOW_AFTER = 10 * 60
STANDBY_AFTER = SHOW_AFTER + 20 * 60
POSITIONS = ((0.2, 0.25), (0.75, 0.65), (0.35, 0.8), (0.65, 0.3))


def local_url():
    try:
        interfaces = json.loads(subprocess.check_output(
            ['ip', '-j', '-4', 'address', 'show', 'up', 'scope', 'global'],
            text=True, timeout=3,
        ))
    except (OSError, ValueError, subprocess.SubprocessError):
        return 'No local IPv4 address'

    addresses = [address['local'] for interface in interfaces
                 for address in interface.get('addr_info', [])]
    if '192.168.4.1' in addresses:
        return 'http://192.168.4.1/'
    return f'http://{addresses[0]}/' if addresses else 'No local IPv4 address'


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
    gi.require_version('Gtk', '3.0')
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

    if not GtkLayerShell.is_supported():
        return

    display = Gdk.Display.get_default()
    windows = []
    position = 0
    lines = ()
    dimmed = False
    powered_off = False

    def draw(widget, context):
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        context.set_source_rgb(0.015, 0.015, 0.015)
        context.paint()
        context.set_source_rgb(0.47, 0.49, 0.51)
        context.select_font_face('Sans')
        size = max(14, min(32, width / 30, height / 12))
        x, y = POSITIONS[position]

        for index, line in enumerate(lines):
            context.set_font_size(size if index == 0 else size * 0.8)
            bearing, _, text_width, _, _, _ = context.text_extents(line)
            left = max(0, min(width - text_width - 12, width * x - text_width / 2))
            context.move_to(left + 6 - bearing, height * y + index * size * 1.3)
            context.show_text(line)

    def close_windows():
        while windows:
            windows.pop().destroy()

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
            canvas = Gtk.DrawingArea()
            canvas.connect('draw', draw)
            window.add(canvas)
            windows.append(window)
            window.show_all()

    def move_text():
        nonlocal position, lines
        if dimmed:
            position = (position + 1) % len(POSITIONS)
            lines = (socket.gethostname(), local_url())
            for window in windows:
                window.queue_draw()
        return GLib.SOURCE_CONTINUE

    def handle_event(event):
        nonlocal dimmed, lines, position, powered_off
        if event == b'show' and not powered_off:
            dimmed = True
            position = 0
            lines = (socket.gethostname(), local_url())
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
    GLib.timeout_add_seconds(30, move_text)
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
