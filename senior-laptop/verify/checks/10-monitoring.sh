#!/usr/bin/env bash
# Task 9 check: heartbeat timer active, health-check reachable, alert helper installed.
# Manual: `senior-laptop-alert test` reaches the admin; Wi-Fi off for 15 minutes triggers the alert.
set -eu
systemctl is-active --quiet senior-laptop-heartbeat.timer
[ -x /usr/local/bin/senior-laptop-alert ]
[ "$(stat -c %a /etc/senior-laptop-monitor.env)" = 600 ]
# shellcheck source=/dev/null
. /etc/senior-laptop-monitor.env
[ -n "$HEALTHCHECK_URL" ]
curl -fsS -m 10 -o /dev/null "$HEALTHCHECK_URL"
[ -f /etc/systemd/system/airlock.service.d/10-alert.conf ]
