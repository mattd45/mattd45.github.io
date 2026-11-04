#!/usr/bin/env bash
# Self-test for verify/run.sh: exit 0 with no checks; PASS/FAIL reporting; --only filter.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
RUN="$HERE/verify/run.sh"
fail=0
t() { printf '%s\n' "$1"; }

d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT

CHECKS_DIR="$d" "$RUN" >/dev/null 2>&1 || { t "FAIL: empty checks dir should exit 0"; fail=1; }

printf '#!/usr/bin/env bash\nexit 0\n' >"$d/01-good.sh"
printf '#!/usr/bin/env bash\nexit 1\n' >"$d/02-bad.sh"
chmod +x "$d"/*.sh

out="$(CHECKS_DIR="$d" "$RUN" 2>&1)"; rc=$?
[ $rc -ne 0 ] || { t "FAIL: failing check should give non-zero exit"; fail=1; }
grep -q 'PASS 01-good' <<<"$out" || { t "FAIL: missing 'PASS 01-good'"; fail=1; }
grep -q 'FAIL 02-bad'  <<<"$out" || { t "FAIL: missing 'FAIL 02-bad'"; fail=1; }

out="$(CHECKS_DIR="$d" "$RUN" --only 01 2>&1)"; rc=$?
[ $rc -eq 0 ] || { t "FAIL: --only 01 should exit 0"; fail=1; }
grep -q '02-bad' <<<"$out" && { t "FAIL: --only 01 ran 02-bad"; fail=1; }

[ $fail -eq 0 ] && t "selftest OK"
exit $fail
