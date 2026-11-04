#!/usr/bin/env bash
# Task 4 check: kernel, mount and AppArmor hardening in effect.
set -eu
[ "$(sysctl -n kernel.kptr_restrict)" -ge 1 ]
[ "$(sysctl -n kernel.dmesg_restrict)" -ge 1 ]
[ "$(sysctl -n kernel.unprivileged_bpf_disabled)" -ge 1 ]
for m in firewire_core thunderbolt usb_storage uas; do
  if lsmod | awk '{print $1}' | grep -qx "$m"; then echo "module $m loaded"; exit 1; fi
done
for mnt in /tmp /home; do findmnt -no OPTIONS "$mnt" | grep -q noexec; done
findmnt -no OPTIONS /var/lib/senior-laptop/quarantine | grep -q noexec
aa-status --enabled
