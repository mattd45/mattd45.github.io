#!/usr/bin/env bash
# Acceptance checks that are not covered by the numbered checks (spec section 9).
# Manual items (a printed page, an unknown USB stick, a fake alert page, rollback) live in docs/runbook.md.
set -eu
python3 - /etc/firefox/policies/policies.json <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))["policies"]
assert p["WebsiteFilter"]["Block"] == ["<all_urls>"]
assert p["Preferences"]["full-screen-api.enabled"]["Value"] is False   # no fullscreen fake alerts
assert p["DisableDeveloperTools"] is True and p["DisablePrivateBrowsing"] is True
PY
if runuser -u grandma -- ls /home/admin >/dev/null 2>&1; then echo "grandma can read /home/admin"; exit 1; fi
if runuser -u grandma -- sh -c 'command -v sudo >/dev/null && sudo -n true' >/dev/null 2>&1; then echo "grandma can sudo"; exit 1; fi
aa-status | grep -q firefox-esr
idx="$(lynis audit system --quick --no-colors 2>/dev/null | grep -o 'Hardening index : [0-9]*' | grep -o '[0-9]*$' || true)"
echo "lynis hardening index: ${idx:-unknown}"
[ "${idx:-0}" -ge 80 ]
