#!/usr/bin/env bash
# Run acceptance checks. Usage: verify/run.sh [--only NN]
# Each check is verify/checks/NN-*.sh (override dir with CHECKS_DIR); exit 0 = PASS.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CHECKS_DIR="${CHECKS_DIR:-$HERE/checks}"
only=""
if [ "${1:-}" = "--only" ]; then only="${2:?--only needs a number}"; fi

failed=0
shopt -s nullglob
for check in "$CHECKS_DIR"/"${only}"*.sh; do
  name="$(basename "$check" .sh)"
  if bash "$check" >/dev/null 2>&1; then
    echo "PASS $name"
  else
    echo "FAIL $name"
    failed=1
  fi
done
exit "$failed"
