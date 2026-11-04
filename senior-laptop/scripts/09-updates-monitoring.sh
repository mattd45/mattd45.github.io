#!/usr/bin/env bash
# Task 9: heartbeat, alert helper, and "alert me if this service fails" for the important units.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root
KIT="${SENIOR_LAPTOP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

run apt-get install -y curl
run install -m 0755 "$KIT/monitoring/senior-laptop-alert" /usr/local/bin/senior-laptop-alert
run install -m 0755 "$KIT/monitoring/senior-laptop-heartbeat" /usr/local/bin/senior-laptop-heartbeat

# The health-check URL is a secret: root-only, never in the repo.
write_file /etc/senior-laptop-monitor.env 0600 <<ENV
HEALTHCHECK_URL="${HEALTHCHECK_URL:-}"
ENV

write_file /etc/systemd/system/senior-laptop-heartbeat.service 0644 <<'UNIT'
[Unit]
Description=Health-check heartbeat

[Service]
Type=oneshot
ExecStart=/usr/local/bin/senior-laptop-heartbeat
UNIT
write_file /etc/systemd/system/senior-laptop-heartbeat.timer 0644 <<'UNIT'
[Unit]
Description=Health-check heartbeat every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
UNIT

# systemd runs this when a watched unit fails.
write_file /etc/systemd/system/senior-laptop-alert@.service 0644 <<'UNIT'
[Unit]
Description=Alert the administrator that %i failed

[Service]
Type=oneshot
ExecStart=/usr/local/bin/senior-laptop-alert "%i failed on the laptop"
UNIT
for unit in apt-daily-upgrade clamav-daemon clamav-freshclam airlock usbguard; do
  write_file "/etc/systemd/system/${unit}.service.d/10-alert.conf" 0644 <<'CONF'
[Unit]
OnFailure=senior-laptop-alert@%n.service
CONF
done

run systemctl daemon-reload
run systemctl enable --now senior-laptop-heartbeat.timer
log "done"
