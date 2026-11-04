#!/usr/bin/env bash
# Task 7: install the custom shell and the kiosk compositor config (read-only for her).
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root
KIT="${SENIOR_LAPTOP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

run apt-get install -y --no-install-recommends sway swaybg python3-gi gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 wtype \
  wireplumber pipewire-audio fonts-dejavu fonts-noto-color-emoji adwaita-icon-theme

run install -d -m 0755 /opt/senior-laptop/shell
for f in core.py messages.py copydeck.py shell.py tiles.json theme.css sway.conf; do
  run install -m 0644 -o root -g root "$KIT/shell/$f" "/opt/senior-laptop/shell/$f"
done

# Non-secret settings the shell shows (name, phone, her name).
write_file /etc/senior-laptop.env 0644 <<ENV
ADMIN_NAME="${ADMIN_NAME:-}"
ADMIN_PHONE="${ADMIN_PHONE:-}"
HER_NAME="${HER_NAME:-}"
ENV
log "done"
