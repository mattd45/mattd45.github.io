#!/usr/bin/env bash
# Self-test for the alert and heartbeat helpers, using a fake curl.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ALERT="$HERE/monitoring/senior-laptop-alert"
BEAT="$HERE/monitoring/senior-laptop-heartbeat"
fail=0
bad() { echo "FAIL: $1"; fail=1; }
[ -x "$ALERT" ] || bad "monitoring/senior-laptop-alert missing or not executable"
[ -x "$BEAT" ]  || bad "monitoring/senior-laptop-heartbeat missing or not executable"
[ $fail -eq 0 ] || exit 1

d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT
mkdir "$d/bin"
# shellcheck disable=SC2016
printf '#!/bin/sh\necho "$@" >> "$CURL_LOG"\nexit "${CURL_EXIT:-0}"\n' >"$d/bin/curl"
chmod +x "$d/bin/curl"
export CURL_LOG="$d/curl.log" PATH="$d/bin:$PATH"
printf 'HEALTHCHECK_URL=https://hc.example/ping/abc\n' >"$d/env"
export SENIOR_MONITOR_ENV="$d/env"

"$ALERT" "scanner down"
grep -q 'https://hc.example/ping/abc/fail' "$CURL_LOG" || bad "alert did not post to <url>/fail"
grep -q 'scanner down' "$CURL_LOG" || bad "alert did not send the message"

: >"$CURL_LOG"
"$BEAT"
grep -q 'https://hc.example/ping/abc$' "$CURL_LOG" || bad "heartbeat did not ping the plain URL"
grep -q '/fail' "$CURL_LOG" && bad "heartbeat must not hit /fail"

: >"$CURL_LOG"
if ! CURL_EXIT=22 "$ALERT" "still ok"; then bad "alert must exit 0 even if curl fails"; fi

printf 'HEALTHCHECK_URL=\n' >"$d/env"
: >"$CURL_LOG"
if ! "$ALERT" "no url"; then bad "alert without a URL must exit 0"; fi
[ ! -s "$CURL_LOG" ] || bad "alert without a URL must not call curl"

[ $fail -eq 0 ] && echo "alert selftest OK"
exit $fail
