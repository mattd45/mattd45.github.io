#!/usr/bin/env bash
# Task 8: CUPS (admin-only) with her USB printer, and USBGuard allowing only her devices.
# Plug in her mouse, keyboard and printer BEFORE running this: USBGuard learns them now.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root
KIT="${SENIOR_LAPTOP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
name="${PRINTER_NAME:-Home-Printer}"

run apt-get install -y cups ipp-usb usbguard python3
run systemctl enable --now cups ipp-usb
run_ok systemctl disable --now cups-browsed          # network printer discovery: not needed, has had remote bugs
run_ok gpasswd -d grandma lpadmin
run_ok usermod -aG lpadmin admin

# The queue: driverless where the printer supports it (plan Task 8 step 1 picks the driver otherwise).
uri="${PRINTER_URI:-}"
if [ -z "$uri" ] && [ "$DRY_RUN" != 1 ]; then uri="$(driverless 2>/dev/null | head -n1 || true)"; fi
if [ -z "$uri" ] && [ "$DRY_RUN" != 1 ]; then
  echo "No printer found. Plug it in, or set PRINTER_URI in config.env (runbook Task 8 step 1)." >&2; exit 1
fi
run lpadmin -p "$name" -E -v "${uri:-ipp://localhost:60000/ipp/print}" -m everywhere
run lpoptions -d "$name"

# USBGuard: allow what is plugged in now if it is a mouse, keyboard, printer or hub; block the rest.
run install -d -m 0755 /opt/senior-laptop/scripts
run install -m 0644 "$KIT/scripts/usbguard_tools.py" /opt/senior-laptop/scripts/usbguard_tools.py
if [ "$DRY_RUN" = 1 ]; then
  echo "+ usbguard generate-policy -P | usbguard_tools.py filter > /etc/usbguard/rules.conf"
else
  rules="$(usbguard generate-policy -P | python3 "$KIT/scripts/usbguard_tools.py" filter)"
  inputs="$(printf '%s\n' "$rules" | python3 "$KIT/scripts/usbguard_tools.py" count)"
  [ "$inputs" -ge 1 ] || { echo "No mouse or keyboard found among USB devices; plug them in first." >&2; exit 1; }
  printf '%s\n' "$rules" | write_file /etc/usbguard/rules.conf 0600
fi
for kv in ImplicitPolicyTarget=block PresentDevicePolicy=apply-policy InsertedDevicePolicy=apply-policy; do
  set_kv /etc/usbguard/usbguard-daemon.conf "${kv%%=*}" "${kv#*=}"
done
write_file /etc/systemd/system/usb-blocked-flag.service 0644 <<'UNIT'
[Unit]
Description=Flag when a new input device was blocked (shows a message to her)
After=usbguard.service

[Service]
ExecStart=/bin/sh -c 'usbguard watch | /usr/bin/python3 /opt/senior-laptop/scripts/usbguard_tools.py watch'
Restart=always

[Install]
WantedBy=multi-user.target
UNIT
run systemctl daemon-reload
run systemctl enable --now usbguard usb-blocked-flag
log "done. Admin recovery: usbguard list-devices -b ; usbguard allow-device <id> -p"
