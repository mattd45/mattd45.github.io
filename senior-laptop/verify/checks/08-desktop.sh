#!/usr/bin/env bash
# Task 8 check: no terminals, no text consoles, clean-slate cache mount.
set -eu
for bin in foot xterm lxterminal; do
  if command -v "$bin" >/dev/null 2>&1; then echo "$bin is installed"; exit 1; fi
done
for n in 2 3 4 5 6; do
  [ "$(systemctl is-enabled "getty@tty${n}.service" 2>/dev/null || true)" = masked ]
done
[ "$(findmnt -no FSTYPE /home/grandma/.cache)" = tmpfs ]
[ "$(systemctl is-enabled ctrl-alt-del.target 2>/dev/null || true)" = masked ]
