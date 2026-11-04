#!/usr/bin/env bash
# Task 6: ClamAV, the airlock service, folders and permissions, zram on low-RAM machines.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root
KIT="${SENIOR_LAPTOP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

run apt-get install -y clamav-daemon clamav-freshclam inotify-tools file python3
id airlock >/dev/null 2>&1 || run useradd --system --no-create-home --shell /usr/sbin/nologin airlock

# Quarantine is a tmpfs (Task 4): ownership must be set at every boot, so use tmpfiles.d.
# She can drop files into quarantine but cannot list or read it; the airlock owns it.
write_file /etc/tmpfiles.d/senior-laptop.conf 0644 <<'CONF'
d /var/lib/senior-laptop/quarantine 0730 airlock grandma -
d /run/senior-laptop/messages 0755 airlock airlock -
d /home/grandma/Downloads 0775 grandma airlock -
CONF
run systemd-tmpfiles --create /etc/tmpfiles.d/senior-laptop.conf

run install -d -m 0755 /opt/senior-laptop/airlock /opt/senior-laptop/shell
run install -m 0644 "$KIT/airlock/airlock.py" /opt/senior-laptop/airlock/airlock.py
run install -m 0644 "$KIT/shell/copydeck.py" /opt/senior-laptop/shell/copydeck.py
run install -m 0644 "$KIT/airlock/airlock.service" /etc/systemd/system/airlock.service

run systemctl enable --now clamav-freshclam clamav-daemon
run systemctl daemon-reload
run systemctl enable --now airlock.service

# 4GB machines: compressed swap so Firefox + ClamAV have headroom (plan Task 6 step 6).
mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
if [ "$mem_kb" -lt 6000000 ]; then
  run apt-get install -y systemd-zram-generator
  write_file /etc/systemd/zram-generator.conf 0644 <<'CONF'
[zram0]
zram-size = ram / 2
CONF
fi
log "done"
