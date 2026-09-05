#!/usr/bin/env bash
set -euo pipefail
OVPN="${1:-/home/gablegoob/Downloads/machines_eu-5.ovpn}"
ART="$(cd "$(dirname "$0")/.." && pwd)/artifacts"
LOG="/tmp/htb-cobblestone-ovpn.log"

wait_tun() {
  for _ in $(seq 1 30); do
    if ip link show tun0 &>/dev/null; then
      ip -4 addr show tun0 | awk '/inet /{print $2}' | cut -d/ -f1 > "$ART/attacker_ip.txt"
      echo "[+] attacker IP: $(cat "$ART/attacker_ip.txt")"
      return 0
    fi
    sleep 1
  done
  return 1
}

sudo killall openvpn 2>/dev/null || true
sleep 1
sudo openvpn --config "$OVPN" --disable-dco --daemon --log "$LOG" --writepid /tmp/htb-cobblestone-ovpn.pid
wait_tun || { sudo tail -20 "$LOG"; exit 1; }
