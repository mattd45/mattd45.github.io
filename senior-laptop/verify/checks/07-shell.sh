#!/usr/bin/env bash
# Task 7 check: shell files are root-owned and read-only; sway and the shell run as grandma.
set -eu
for f in sway.conf shell.py core.py theme.css; do
  [ "$(stat -c %U "/opt/senior-laptop/shell/$f")" = root ]
  if runuser -u grandma -- test -w "/opt/senior-laptop/shell/$f"; then echo "grandma can edit $f"; exit 1; fi
done
pgrep -u grandma -x sway >/dev/null
pgrep -u grandma -f '/opt/senior-laptop/shell/shell.py' >/dev/null
