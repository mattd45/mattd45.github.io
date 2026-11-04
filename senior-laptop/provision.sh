#!/usr/bin/env bash
# Provision the laptop. Usage: sudo ./provision.sh [--only NN]
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

shopt -s nullglob
for script in "$HERE"/scripts/"${only}"*.sh; do
  echo "==> $(basename "$script")"
  bash "$script"
done
