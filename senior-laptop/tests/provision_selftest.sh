#!/usr/bin/env bash
# Dry-run each provisioning script and check the review-fix behaviour is present.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
bad() { echo "FAIL: $1"; fail=1; }
dry() { DRY_RUN=1 SENIOR_LAPTOP_DIR="$HERE" HER_NAME=Ann WIFI_SSID=H TAILSCALE_AUTHKEY=k HEALTHCHECK_URL=u bash "$HERE/scripts/$1" 2>&1; }
expect() { dry "$1" | grep -qF -- "$2" || bad "$1 should do: $2"; }

expect 01-base.sh "chmod 0711 /home/grandma"                       # airlock must be able to reach ~/Downloads
expect 01-base.sh "chmod 0700 /home/admin"
expect 01-base.sh "write /etc/systemd/system/apt-daily.timer.d/10-senior.conf"
expect 01-base.sh "write /etc/systemd/system/apt-daily-upgrade.timer.d/10-senior.conf"
expect 01-base.sh "enable --now snapper-cleanup.timer"
grep -q -- "--cleanup-algorithm number" "$HERE/scripts/01-base.sh" || bad "snapshots must carry a cleanup algorithm"
expect 03-remote.sh "--accept-dns=false"
expect 05-browser.sh "--headless"
expect 05-browser.sh "HOME=/home/grandma"
expect 06-airlock.sh "AlertExceedsMax yes"
expect 08-printing-usb.sh "generate-policy -P"
expect 09-updates-monitoring.sh "chgrp airlock /etc/senior-laptop-monitor.env"

[ $fail -eq 0 ] && echo "provision selftest OK"
exit $fail
