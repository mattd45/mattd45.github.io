#!/usr/bin/env bash
# Task 3 check: Tailscale is up. (Remote SSH from the admin's machine is a manual step.)
set -eu
systemctl is-active --quiet tailscaled
tailscale status --json | grep -q '"BackendState": "Running"'
