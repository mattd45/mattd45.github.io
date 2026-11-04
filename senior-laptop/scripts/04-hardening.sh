#!/usr/bin/env bash
# Task 4: kernel, mount and AppArmor hardening.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root
KIT="${SENIOR_LAPTOP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

run apt-get install -y apparmor apparmor-utils apparmor-profiles lynis

write_file /etc/sysctl.d/99-senior.conf 0644 <"$KIT/hardening/sysctl.conf"
write_file /etc/modprobe.d/senior-blacklist.conf 0644 <"$KIT/hardening/modprobe-blacklist.conf"
run_ok sysctl --system

# Mounts: replace or append each line in the template.
uuid="$(findmnt -no UUID / 2>/dev/null || echo ROOTUUID)"
run install -d -m 0750 /var/lib/senior-laptop/quarantine
while read -r line; do
  case "$line" in ''|'#'*) continue ;; esac
  line="${line//@ROOTUUID@/$uuid}"
  mp="$(awk '{print $2}' <<<"$line")"
  if [ "$DRY_RUN" = 1 ]; then echo "+ fstab: $line"; continue; fi
  if awk -v mp="$mp" '$1 !~ /^#/ && $2==mp {f=1} END{exit !f}' /etc/fstab; then
    awk -v mp="$mp" -v new="$line" '$1 !~ /^#/ && $2==mp {print new; next} {print}' /etc/fstab >/etc/fstab.new
    mv /etc/fstab.new /etc/fstab
  else
    echo "$line" >>/etc/fstab
  fi
done <"$KIT/hardening/fstab-mounts.txt"
run systemctl daemon-reload

# Boot parameters (Kicksecure-style) and AppArmor.
for p in slab_nomerge init_on_alloc=1 init_on_free=1 page_alloc.shuffle=1 randomize_kstack_offset=on vsyscall=none debugfs=off apparmor=1 security=apparmor; do
  grub_add_param /etc/default/grub "$p"
done
run update-grub
run systemctl enable --now apparmor
log "done (reboot to apply boot parameters and mounts)"
