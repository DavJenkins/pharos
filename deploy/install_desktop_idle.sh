#!/bin/bash
set -euo pipefail

DEPLOY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
install -D -m 0755 "$DEPLOY_DIR/../tools/desktop_idle.py" /usr/local/libexec/pharos-desktop-idle
install -D -m 0644 "$DEPLOY_DIR/pharos-desktop-idle.desktop" /etc/xdg/autostart/pharos-desktop-idle.desktop
