#!/usr/bin/env bash
# Run acceptance checks. Usage: verify/run.sh [--only NN[,NN...]]
# Each check is verify/checks/NN-*.sh (override dir with CHECKS_DIR); exit 0 = PASS.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CHECKS_DIR="${CHECKS_DIR:-$HERE/checks}"
only=""
if [ "${1:-}" = "--only" ]; then only="${2:?--only needs a number}"; fi

IFS=',' read -r -a prefixes <<<"$only"
[ "${#prefixes[@]}" -gt 0 ] || prefixes=("")

failed=0
matched=0
shopt -s nullglob
for prefix in "${prefixes[@]}"; do
  for check in "$CHECKS_DIR"/"${prefix}"*.sh; do
    matched=1
    name="$(basename "$check" .sh)"
    if bash "$check" >/dev/null 2>&1; then
      echo "PASS $name"
    else
      echo "FAIL $name"
      failed=1
    fi
  done
done
if [ -n "$only" ] && [ "$matched" -eq 0 ]; then
  echo "no checks matched --only $only" >&2
  exit 1
fi
exit "$failed"
