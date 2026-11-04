#!/usr/bin/env bash
# Task 8: no terminals, no text consoles, no Ctrl+Alt+Del. (Clean-slate cache is the tmpfs from Task 4.)
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root

# Remove terminals outright rather than hiding their icons.
run_ok apt-get purge -y foot xterm lxterminal x11-xserver-utils

# No virtual consoles to log in on.
for n in 2 3 4 5 6; do run systemctl mask "getty@tty${n}.service"; done
run systemctl mask autovt@.service
write_file /etc/systemd/logind.conf.d/10-senior.conf 0644 <<'CONF'
[Login]
NAutoVTs=0
ReserveVT=0
HandlePowerKey=poweroff
CONF
run systemctl mask ctrl-alt-del.target
log "done (reboot to apply)"
