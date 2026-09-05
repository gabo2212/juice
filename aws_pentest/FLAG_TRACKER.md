# AWS Fortress — Flag Tracker (7 flags)

HTB UI shows **7** challenge names. Legacy writeup used **10** technique sections. Track capture status here.

| # | HTB name | Status | Attack phase | Artifacts | Notes |
|---|----------|--------|--------------|-----------|-------|
| 1 | AcedDC | captured | AD foothold / DC | `scripts/ad_firmware_fetch.sh` | jameshauwnnel ASREPRoast + Product_Release firmware |
| 2 | Let's dance | captured | jobs portal IDOR | `scripts/flag1_token_brute.py` | htbgdr7d3 admin |
| 3 | Spongbob's neighbour | captured | SSRF + SQLi | `artifacts/flag2_ssrf_logs.json` | logs + keys_tbl |
| 4 | I want to break free | captured | JWT + SSTI | `scripts/flag4_exploit.py` | nonce reuse works; admin view blocked on live DB |
| 5 | Muppets love'em | partial | Lambda / workflow | `scripts/flag8_workflow_lambda.py` | workflow+Lambda chain OK; HTB name may map here |
| 6 | The HTB redemption | captured | S3 SQLite finale | `scripts/flag10_s3_sqlite_admin.py` | Administrator WinRM 2026-09-05 |
| 7 | *(unknown)* | blocked | backup_tool RE **or** SQS | — | Flag5 backup_tool blocked; Flag9 SQS 403 |

## Legacy flags 5–10 (this session)

| Legacy # | Flag | Status |
|----------|------|--------|
| 5 | backup_tool / `AWS{REDACTED}` | **blocked** — no company-support admin shell |
| 6 | DynamoDB `AWS{REDACTED}` | **captured** |
| 7 | david `AWS{REDACTED}` | **captured** |
| 8 | Lambda `AWS{REDACTED}` | **captured** (tracking_api chain) |
| 9 | SQS `AWS{REDACTED}` | **blocked** — IAM denied on `sensor_updates` |
| 10 | S3/SQLite `AWS{REDACTED}` | **captured** |

## Status legend

- `captured` — flag string recovered live
- `blocked` — chain identified, exploit incomplete
- `partial` — mid-chain access without flag string
