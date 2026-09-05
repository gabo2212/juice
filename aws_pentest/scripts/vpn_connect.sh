#!/usr/bin/env bash
# HTB AWS Fortress VPN — us-fort-1
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
ART="$REPO/artifacts"
CFG="$REPO/config/fortresses_us-fort-1.ovpn"
LOG="/tmp/htb-fort-ovpn.log"

wait_tun() {
  local secs="${1:-45}"
  for _ in $(seq 1 "$secs"); do
    if ip link show tun0 &>/dev/null; then
      ip -4 addr show tun0
      ip -4 addr show tun0 | awk '/inet /{print $2}' | cut -d/ -f1 > "$ART/attacker_ip.txt"
      echo "[+] attacker IP: $(cat "$ART/attacker_ip.txt")"
      ping -c2 -W3 10.13.37.13 && echo "[+] target reachable" || echo "[!] tun up but target not pinging (ICMP may be filtered)"
      return 0
    fi
    sleep 1
  done
  return 1
}

echo "[*] Killing any existing OpenVPN sessions..."
sudo killall openvpn 2>/dev/null || true
sleep 2

echo "[*] Connecting to HTB Fortress VPN (us-fort-1)..."
sudo openvpn --config "$CFG" --disable-dco --daemon --log "$LOG" --writepid /tmp/htb-fort-ovpn.pid

if wait_tun 45; then
  echo '10.13.37.13' > "$ART/target_ip.txt"
  echo "[+] VPN ready. Log: $LOG"
  exit 0
fi

echo "[!] VPN failed. Foreground retry:"
echo "  sudo killall openvpn; sudo openvpn --config \"$CFG\" --disable-dco"
sudo tail -25 "$LOG" 2>/dev/null || true
exit 1
