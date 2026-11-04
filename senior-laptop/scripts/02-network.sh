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

# Saved Wi-Fi: her home network, plus the admin's phone hotspot as a fallback, so the laptop can
# still reach Tailscale if her Wi-Fi fails on delivery day (turn the hotspot on, fix hers remotely).
add_wifi() {  # SSID PSK FILE-NAME PRIORITY
  local ssid="$1" psk="$2" file="$3" prio="$4" uuid
  uuid="$(uuidgen --sha1 --namespace @dns --name "$ssid" 2>/dev/null || echo 00000000-0000-0000-0000-000000000000)"
  write_file "/etc/NetworkManager/system-connections/${file}.nmconnection" 0600 <<CONN
[connection]
id=${ssid}
uuid=${uuid}
type=wifi
autoconnect=true
autoconnect-priority=${prio}

[wifi]
mode=infrastructure
ssid=${ssid}

[wifi-security]
key-mgmt=wpa-psk
psk=${psk}

[ipv4]
method=auto

[ipv6]
method=auto
CONN
}
if [ -n "${WIFI_SSID:-}" ]; then add_wifi "$WIFI_SSID" "${WIFI_PSK:-}" home-wifi 10; else log "WIFI_SSID not set; skipping home Wi-Fi"; fi
if [ -n "${HOTSPOT_SSID:-}" ]; then add_wifi "$HOTSPOT_SSID" "${HOTSPOT_PSK:-}" admin-hotspot 0; fi
run_ok nmcli connection reload

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
