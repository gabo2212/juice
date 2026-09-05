#!/usr/bin/env python3
"""Compute backup_tool OTP from reversed g_o logic."""
import hashlib
import struct
import time


def xor_key(key: bytes, val: int, size: int = 0x40) -> bytes:
    buf = bytearray(key.ljust(size, b"\x00")[:size])
    for i in range(size):
        buf[i] ^= val
    return bytes(buf)


def otp_for_ts(ts: int) -> int:
    counter = ts // 30
    counter_bytes = struct.pack("<Q", counter)[:8]
    key = b"5932978879260647462"

    outer = xor_key(key, 0x5c)
    msg = outer + counter_bytes
    msg = msg.ljust(0x80, b"\x00")
    digest = hashlib.sha1(msg).digest()

    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return code % 1_000_000


if __name__ == "__main__":
    now = int(time.time())
    print("now", now, otp_for_ts(now))
    for d in (-30, 0, 30):
        ts = now + d
        print(ts, otp_for_ts(ts))
