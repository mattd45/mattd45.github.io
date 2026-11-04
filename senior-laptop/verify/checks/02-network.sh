#!/usr/bin/env bash
# Task 3 check: firewall, filtering DNS, no listening TCP ports.
set -eu
ufw status verbose | grep -q 'Default: deny (incoming)'
ufw status verbose | grep -q 'deny (outgoing)'
resolvectl status | grep -q '9\.9\.9\.9'
# TCP listeners other than loopback and the tailnet must not exist.
bad="$(ss -H -tln | awk '{print $4}' | grep -Ev '^(127\.|\[?::1\]?|100\.|\[?fd7a:115c)' || true)"
if [ -n "$bad" ]; then echo "listening: $bad"; exit 1; fi
