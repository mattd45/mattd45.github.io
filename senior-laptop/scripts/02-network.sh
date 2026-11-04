#!/usr/bin/env bash
# Task 3: firewall, filtering DNS (Quad9), pre-loaded home Wi-Fi.
set -euo pipefail
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_root

run apt-get install -y ufw network-manager systemd-resolved uuid-runtime

# Filtering DNS.
write_file /etc/systemd/resolved.conf.d/10-quad9.conf 0644 <<'CONF'
[Resolve]
DNS=9.9.9.9 149.112.112.112
FallbackDNS=
DNSOverTLS=opportunistic
CONF
run systemctl enable --now systemd-resolved

# Her home Wi-Fi, saved so the laptop joins it on delivery day.
if [ -n "${WIFI_SSID:-}" ]; then
  uuid="$(uuidgen --sha1 --namespace @dns --name "$WIFI_SSID" 2>/dev/null || echo 00000000-0000-0000-0000-000000000000)"
  write_file "/etc/NetworkManager/system-connections/home-wifi.nmconnection" 0600 <<CONN
[connection]
id=${WIFI_SSID}
uuid=${uuid}
type=wifi
autoconnect=true

[wifi]
mode=infrastructure
ssid=${WIFI_SSID}

[wifi-security]
key-mgmt=wpa-psk
psk=${WIFI_PSK:-}

[ipv4]
method=auto

[ipv6]
method=auto
CONN
  run_ok nmcli connection reload
else
  log "WIFI_SSID not set; skipping Wi-Fi profile"
fi

# Firewall: nothing in; out only web, DNS, time, DHCP and Tailscale.
run ufw --force reset
run ufw default deny incoming
run ufw default deny outgoing
run ufw allow out 53
run ufw allow out 853/tcp
run ufw allow out 80/tcp
run ufw allow out 443/tcp
run ufw allow out 123/udp
run ufw allow out 67:68/udp
run ufw allow out 41641/udp
# RustDesk direct access, reachable only over the tailnet interface (verify in the Task 3 spike).
run ufw allow in on tailscale0 to any port 21118 proto tcp
run ufw --force enable
log "done"
