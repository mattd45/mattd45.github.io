#!/usr/bin/env bash
# Shared helpers for provisioning scripts. Source this file; do not execute it.
# DRY_RUN=1 prints what would happen and changes nothing.
DRY_RUN="${DRY_RUN:-0}"

log() { echo "[$(basename "$0")] $*"; }

# run CMD...: execute, or print "+ CMD..." in dry-run.
run() { if [ "$DRY_RUN" = 1 ]; then echo "+ $*"; else "$@"; fi; }

# run_ok CMD...: like run but a failure is not fatal.
run_ok() { run "$@" || true; }

require_root() {
  [ "$DRY_RUN" = 1 ] || [ "$(id -u)" -eq 0 ] || { echo "Run as root." >&2; exit 1; }
}

# write_file PATH [MODE] < content: install content, report "updated" or "unchanged".
write_file() {
  local path="$1" mode="${2:-0644}" tmp
  tmp="$(mktemp)"; cat >"$tmp"
  if [ "$DRY_RUN" = 1 ]; then echo "+ write $path"; rm -f "$tmp"; return 0; fi
  if cmp -s "$tmp" "$path" 2>/dev/null; then
    echo "unchanged $path"
  else
    install -D -m "$mode" "$tmp" "$path"; echo "updated $path"
  fi
  rm -f "$tmp"
}

# set_kv FILE KEY VALUE: set KEY=VALUE, replacing an existing KEY= line or appending.
set_kv() {
  local file="$1" key="$2" value="$3"
  if [ "$DRY_RUN" = 1 ]; then echo "+ set $key=$value in $file"; return 0; fi
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

# grub_add_param FILE PARAM: add PARAM to GRUB_CMDLINE_LINUX_DEFAULT once.
grub_add_param() {
  local file="$1" param="$2"
  if [ "$DRY_RUN" = 1 ]; then echo "+ grub param $param in $file"; return 0; fi
  grep -q "^GRUB_CMDLINE_LINUX_DEFAULT=.*[\" ]${param}[\" ]" "$file" && return 0
  sed -i "/^GRUB_CMDLINE_LINUX_DEFAULT=/ s/\"\$/ ${param}\"/" "$file"
}
