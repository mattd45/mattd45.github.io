#!/usr/bin/env bash
# Task 2 check: accounts, services, snapshots, updates.
set -eu
id grandma >/dev/null
id admin >/dev/null
if id -nG grandma | tr ' ' '\n' | grep -qx -e sudo -e adm; then echo "grandma has admin rights"; exit 1; fi
for svc in ssh bluetooth; do
  if systemctl is-active --quiet "$svc"; then echo "$svc is running"; exit 1; fi
  if systemctl is-enabled --quiet "$svc" 2>/dev/null; then echo "$svc is enabled"; exit 1; fi
done
[ "$(passwd -S root | awk '{print $2}')" = "L" ]
snapper -c root list >/dev/null
systemctl is-enabled --quiet nightly-reboot.timer
systemctl is-enabled --quiet unattended-upgrades
grep -q 'user = "grandma"' /etc/greetd/config.toml
