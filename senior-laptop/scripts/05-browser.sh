#!/usr/bin/env bash
# Task 5: Firefox ESR with enforced policies, two profiles, AppArmor profile.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root
KIT="${SENIOR_LAPTOP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

run apt-get install -y firefox-esr apparmor apparmor-utils python3

# Policy file: root-owned. Installed in both locations Debian packaging may read;
# confirm with about:policies on the laptop (runbook).
tmp="$(mktemp)"
run python3 "$KIT/scripts/render_policies.py" "$KIT/browser/allowlist.txt" "$tmp"
for dest in /etc/firefox/policies /usr/lib/firefox-esr/distribution; do
  run install -d -m 0755 "$dest"
  run install -m 0644 -o root -g root "$tmp" "$dest/policies.json"
done
rm -f "$tmp"

# Two profiles for her: one for Google (Gmail + Docs), one for Facebook.
for name in google facebook; do
  [ -d "/home/grandma/.mozilla/$name" ] || run runuser -u grandma -- firefox-esr -CreateProfile "$name /home/grandma/.mozilla/$name"
done

# AppArmor (complain mode first; see the profile header).
run install -m 0644 "$KIT/browser/firefox.apparmor" /etc/apparmor.d/usr.lib.firefox-esr.firefox-esr
run apparmor_parser -r /etc/apparmor.d/usr.lib.firefox-esr.firefox-esr
log "done"
