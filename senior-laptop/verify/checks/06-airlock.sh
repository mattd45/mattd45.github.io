#!/usr/bin/env bash
# Task 6 check: services up, permissions right, EICAR never delivered, clean PDF delivered.
# NOTE: this check leaves a harmless clean-check.pdf in ~grandma/Downloads; delete it by hand.
set -eu
q=/var/lib/senior-laptop/quarantine
d=/home/grandma/Downloads
systemctl is-active --quiet clamav-daemon
systemctl is-active --quiet airlock
[ "$(stat -c %a "$q")" = 730 ]
if runuser -u grandma -- ls "$q" >/dev/null 2>&1; then echo "grandma can list quarantine"; exit 1; fi

eicar_a='X5O!P%@AP[4\PZX54(P^)7CC)7}$'
# shellcheck disable=SC2016
eicar_b='EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
printf '%s%s\n' "$eicar_a" "$eicar_b" | runuser -u grandma -- tee "$q/eicar-check.txt" >/dev/null
printf '%s\n' '%PDF-1.4' '1 0 obj' '<< >>' 'endobj' '%%EOF' | runuser -u grandma -- tee "$q/clean-check.pdf" >/dev/null
sleep 45
[ ! -e "$d/eicar-check.txt" ]
[ ! -e "$q/eicar-check.txt" ]
[ -e "$d/clean-check.pdf" ]
