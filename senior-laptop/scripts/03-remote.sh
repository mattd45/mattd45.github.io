#!/usr/bin/env bash
# Task 3: Tailscale (SSH, no inbound ports) and RustDesk (screen, tailnet only).
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root

codename="${VERSION_CODENAME:-}"
if [ -z "$codename" ] && [ -r /etc/os-release ]; then
  codename="$(. /etc/os-release && echo "${VERSION_CODENAME:-}")"
fi
codename="${codename:-trixie}"

run install -d -m 0755 /usr/share/keyrings
run curl -fsSL "https://pkgs.tailscale.com/stable/debian/${codename}.noarmor.gpg" -o /usr/share/keyrings/tailscale-archive-keyring.gpg
run curl -fsSL "https://pkgs.tailscale.com/stable/debian/${codename}.tailscale-keyring.list" -o /etc/apt/sources.list.d/tailscale.list
run apt-get update
run apt-get install -y tailscale
run systemctl enable --now tailscaled
run tailscale up --auth-key="${TAILSCALE_AUTHKEY:?set TAILSCALE_AUTHKEY in config.env}" --ssh --hostname=senior-laptop

if [ -n "${RUSTDESK_DEB:-}" ]; then
  run apt-get install -y "$RUSTDESK_DEB"
else
  log "RUSTDESK_DEB not set; RustDesk skipped (spike pending, see runbook)"
fi
log "done"
