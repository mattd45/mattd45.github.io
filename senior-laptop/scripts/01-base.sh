#!/usr/bin/env bash
# Task 2: accounts, auto-login, quiet boot, snapshots, updates, nightly reboot.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root

run apt-get install -y sudo snapper btrfs-progs unattended-upgrades greetd

# Accounts (admin's password is set by hand; see runbook).
id grandma >/dev/null 2>&1 || run useradd -m -s /bin/bash -c "${HER_NAME:-Grandma}" grandma
id admin >/dev/null 2>&1 || run useradd -m -s /bin/bash -G sudo admin
run_ok gpasswd -d grandma sudo
run chmod 0700 /home/admin
run chmod 0711 /home/grandma     # others may pass through (not list) so the airlock service can reach ~/Downloads
run passwd -l root

# Services she must not have.
for svc in ssh bluetooth; do run_ok systemctl disable --now "$svc"; done

# Auto-login straight to the shell: no login screen.
write_file /etc/greetd/config.toml 0644 <<'TOML'
[terminal]
vt = 1

[default_session]
command = "sway --config /opt/senior-laptop/shell/sway.conf"
user = "grandma"

[initial_session]
command = "sway --config /opt/senior-laptop/shell/sway.conf"
user = "grandma"
TOML
run systemctl enable greetd

# Quiet boot, hidden boot menu.
if [ -f /etc/default/grub ] || [ "$DRY_RUN" = 1 ]; then
  set_kv /etc/default/grub GRUB_TIMEOUT 0
  set_kv /etc/default/grub GRUB_TIMEOUT_STYLE hidden
  grub_add_param /etc/default/grub quiet
  run update-grub
fi

# Snapshots: one before and one after every apt run, pruned so the disk never fills.
[ -e /etc/snapper/configs/root ] || run snapper -c root create-config /
run_ok snapper -c root set-config NUMBER_CLEANUP=yes NUMBER_LIMIT=8 NUMBER_LIMIT_IMPORTANT=4
run systemctl enable --now snapper-cleanup.timer
write_file /etc/apt/apt.conf.d/80snapper 0644 <<'APT'
DPkg::Pre-Invoke  { "snapper -c root create -t single --cleanup-algorithm number -d 'apt-pre' || true"; };
DPkg::Post-Invoke { "snapper -c root create -t single --cleanup-algorithm number -d 'apt-post' || true"; };
APT

# Unattended security upgrades, nightly reboot at 04:00.
write_file /etc/apt/apt.conf.d/20auto-upgrades 0644 <<'APT'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT
run systemctl enable unattended-upgrades

write_file /etc/systemd/system/nightly-reboot.service 0644 <<'UNIT'
[Unit]
Description=Nightly reboot

[Service]
Type=oneshot
ExecStart=/bin/systemctl reboot
UNIT
write_file /etc/systemd/system/nightly-reboot.timer 0644 <<'UNIT'
[Unit]
Description=Nightly reboot at 04:00

[Timer]
OnCalendar=*-*-* 04:00:00

[Install]
WantedBy=timers.target
UNIT
# Updates land at 03:00-03:30, before the 04:00 reboot, never while she is using Firefox.
write_file /etc/systemd/system/apt-daily.timer.d/10-senior.conf 0644 <<'CONF'
[Timer]
OnCalendar=
OnCalendar=*-*-* 03:00
RandomizedDelaySec=0
CONF
write_file /etc/systemd/system/apt-daily-upgrade.timer.d/10-senior.conf 0644 <<'CONF'
[Timer]
OnCalendar=
OnCalendar=*-*-* 03:30
RandomizedDelaySec=0
CONF
run systemctl daemon-reload
run systemctl enable --now nightly-reboot.timer
log "done"
