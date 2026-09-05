#!/usr/bin/env bash
# Post-VPN recon for AWS Fortress
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ART="$REPO/artifacts"
IP="$(cat "$ART/target_ip.txt" 2>/dev/null || echo '10.13.37.13')"
HOSTS=(
  amzcorp.local
  jobs.amzcorp.local
  logs.amzcorp.local
  services.amzcorp.local
  cloud.amzcorp.local
  inventory.amzcorp.local
  workflow.amzcorp.local
  company-support.amzcorp.local
  jobs-development.amzcorp.local
)

echo "[*] Attacker: $(ip -4 addr show tun0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 || echo unknown)"
echo "[*] Target IP: $IP"

ping -c2 -W3 "$IP" || true

echo "[*] Full TCP scan (top 1000)..."
nmap -Pn -sT -T4 --top-ports 1000 -sV -oN "$ART/nmap_top1000.txt" "$IP"

echo "[*] HTTP probe..."
curl -sI --max-time 8 "http://$IP/" | tee "$ART/http_root_headers.txt" || true
curl -s --max-time 8 "http://$IP/" | tee "$ART/http_root_body.txt" || true

echo "[*] Vhost probe (Host header)..."
: > "$ART/vhost_probe.txt"
for h in "${HOSTS[@]}"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 -H "Host: $h" "http://$IP/" || echo err)
  echo "$code $h" | tee -a "$ART/vhost_probe.txt"
done

echo "[+] Artifacts in $ART"
