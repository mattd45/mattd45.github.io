#!/usr/bin/env bash
# Provision the laptop. Usage: sudo ./provision.sh [--only NN[,NN...]]
# Sources config.env, then runs scripts/NN-*.sh in order. Every script is idempotent.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/config.env" ] || { echo "Copy config.env.example to config.env and fill it in." >&2; exit 1; }
set -a
# shellcheck source=/dev/null
. "$HERE/config.env"
set +a
export SENIOR_LAPTOP_DIR="$HERE"

only=""
if [ "${1:-}" = "--only" ]; then only="${2:?--only needs a number}"; fi

IFS=',' read -r -a prefixes <<<"$only"
[ "${#prefixes[@]}" -gt 0 ] || prefixes=("")

matched=0
shopt -s nullglob
for prefix in "${prefixes[@]}"; do
  for script in "$HERE"/scripts/"${prefix}"*.sh; do
    [ "$(basename "$script")" = lib.sh ] && continue
    matched=1
    echo "==> $(basename "$script")"
    bash "$script"
  done
done
if [ -n "$only" ] && [ "$matched" -eq 0 ]; then
  echo "no scripts matched --only $only" >&2
  exit 1
fi
