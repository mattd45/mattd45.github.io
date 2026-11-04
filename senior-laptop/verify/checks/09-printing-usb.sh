#!/usr/bin/env bash
# Task 8 check: printing set up and admin-only; USBGuard active with her devices allowed.
# Manual: a printed test page, a spare USB stick that does not mount, an unknown mouse that is blocked.
set -eu
name="${PRINTER_NAME:-Home-Printer}"
lpstat -d | grep -q "$name"
if id -nG grandma | tr ' ' '\n' | grep -qx lpadmin; then echo "grandma can administer printers"; exit 1; fi
if runuser -u grandma -- lpadmin -p check-queue -E -v file:/dev/null >/dev/null 2>&1; then echo "grandma added a printer"; exit 1; fi
if systemctl is-active --quiet cups-browsed; then echo "cups-browsed is running"; exit 1; fi
systemctl is-active --quiet usbguard
systemctl is-active --quiet usb-blocked-flag
[ "$(usbguard list-devices | grep -c allow)" -ge 2 ]
