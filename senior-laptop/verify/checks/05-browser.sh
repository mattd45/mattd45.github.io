#!/usr/bin/env bash
# Task 5 check: policy file is root-owned, valid, and grandma can't change it or use sudo.
set -eu
f=/etc/firefox/policies/policies.json
[ "$(stat -c %U "$f")" = root ]
python3 -c 'import json,sys; p=json.load(open(sys.argv[1]))["policies"]; assert p["WebsiteFilter"]["Block"]==["<all_urls>"]' "$f"
if runuser -u grandma -- test -w "$f"; then echo "grandma can write $f"; exit 1; fi
sudo -l -U grandma 2>&1 | grep -q 'not allowed'
aa-status | grep -q firefox-esr
