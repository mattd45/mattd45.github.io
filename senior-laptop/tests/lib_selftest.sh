#!/usr/bin/env bash
# Self-test for scripts/lib.sh helpers (write_file, set_kv, run, dry-run).
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
. "$HERE/scripts/lib.sh" || { echo "FAIL: cannot source lib.sh"; exit 1; }
fail=0
bad() { echo "FAIL: $1"; fail=1; }
d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT

# write_file: creates, then reports unchanged on identical content
printf 'hello\n' | write_file "$d/a.conf" 0644 >/dev/null
[ "$(cat "$d/a.conf")" = "hello" ] || bad "write_file did not write content"
out="$(printf 'hello\n' | write_file "$d/a.conf" 0644)"
grep -q unchanged <<<"$out" || bad "second identical write should say unchanged"
out="$(printf 'bye\n' | write_file "$d/a.conf" 0644)"
grep -q updated <<<"$out" || bad "changed write should say updated"

# set_kv: replaces existing, appends missing, idempotent
printf 'A=1\nB=2\n' >"$d/k"
set_kv "$d/k" A 9; set_kv "$d/k" C 3; set_kv "$d/k" C 3
[ "$(grep -c '^A=9$' "$d/k")" = 1 ] || bad "set_kv did not replace A"
[ "$(grep -c '^C=3$' "$d/k")" = 1 ] || bad "set_kv should append C exactly once"
grep -q '^B=2$' "$d/k" || bad "set_kv lost B"

# dry run: run prints, write_file writes nothing
out="$(DRY_RUN=1 run touch "$d/never2")"; [ "$out" = "+ touch $d/never2" ] || bad "dry-run run should print the command, got '$out'"
[ ! -e "$d/never2" ] || bad "dry-run run executed the command"
printf 'x\n' | DRY_RUN=1 write_file "$d/never" 0644 >/dev/null
[ ! -e "$d/never" ] || bad "dry-run write_file created a file"

[ $fail -eq 0 ] && echo "lib selftest OK"
exit $fail
