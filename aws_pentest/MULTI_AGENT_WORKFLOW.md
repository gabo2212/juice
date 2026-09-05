# AWS Fortress — Multi-Agent Workflow

**Last updated:** 2026-09-05 (Flags 6–8, 10 captured; legacy 5 & 9 blocked)

## Current phase / state machine

```
VPN_OK → TARGET_CORRECTED(10.13.37.15) → HOSTS_OK → RECON_DONE
  → FLAG1-4_DONE → FLAG6-8_DONE → FLAG10_DONE → FLAG5_BLOCKED → FLAG9_BLOCKED
```

| Phase | Status | Notes |
|-------|--------|-------|
| VPN (us-fort-1) | ✅ | tun0 `10.10.14.225`, fortress routes present |
| Target IP | ✅ | **Correct DC: `10.13.37.15`** (NOT `.13`) |
| /etc/hosts | ✅ | All subdomains → `10.13.37.15` |
| Recon | ✅ | nmap on `.15`, vhost map, git dump |
| Flag 1 | ✅ | Admin token IDOR uuid=955 |
| Flag 2 | ✅ | SSRF logs + base64 decode |
| Flag 3 | ✅ | Role escalation + SQLi keys_tbl |
| Flag 4 | ✅ | company-support JWT forge + SSTI RCE |
| Flag 5 | 🚫 | backup_tool — company-support admin 403; binary+creds in artifacts; OTP needs on-target gdb/ntp |
| Flag 6 | ✅ | john DynamoDB scan |
| Flag 7 | ✅ | david desktop via Administrator (S3 SQLite) |
| Flag 8 | ✅ | olivia Airflow varexport → will Lambda / tracking_api |
| Flag 9 | 🚫 | SQS sensor_updates — 403 for will/roy |
| Flag 10 | ✅ | S3 amzcorp_users.db → Administrator WinRM |

---

## Critical discovery: wrong target IP

User-provided `10.13.37.13` is a **decoy** (Apache default page, only port 80).

| IP | Role |
|----|------|
| `10.13.37.15` | **DC01** — AD + Apache redirect → jobs portal |
| `10.13.37.13` | Decoy Debian Apache default |
| `10.13.37.14` | Redirect service |
| `10.13.37.10` | nginx |
| `10.13.37.11` | WordPress-ish |

Entry: `curl http://10.13.37.15/` → meta-refresh to `jobs.amzcorp.local`

---

## Active credentials / tokens

### Jobs portal (`htbgdr7d3`) — Administrators
```
username: htbgdr7d3
password: <REDACTED>
role: Administrators (promoted via /api/v4/users/edit)
```

### Admin API token (Flag 1)
```
uuid: <from Flag 1 IDOR>
api_token: <REDACTED>
```

### Tyler (Managers — used for role escalation)
```
username: tyler
password: <REDACTED>
source: URL-decoded from SSRF logs dump (password=<url-encoded-tyler-password>)
```

### Airflow / LocalStack (`olivia` → `will`)
```
username: olivia
password: <REDACTED>
workflow: http://workflow.amzcorp.local
export: POST /variable/action_post action=varexport

will AWS (from Airflow variables):
AWS_ACCESS_KEY_ID: AKIA_REDACTED
AWS_SECRET_ACCESS_KEY: <REDACTED>
endpoint: http://cloud.amzcorp.local
```

### Company-support (`ssti001`)
```
username: ssti001
password: <REDACTED>
confirmed: yes (URLSafeSerializer secret: <REDACTED>
```

---

## Flags captured

| # | Flag | Vector |
|---|------|--------|
| 1 | `AWS{REDACTED}` | POST `/api/v4/tokens/get` uuid=955, username=admin |
| 2 | `AWS{REDACTED}` | SSRF `/api/v4/status` → logs.amzcorp.local, base64 in hostname |
| 3 | `AWS{REDACTED}` | tyler+admin token promote user → SQLi `/admin/users/search` |
| 4 | `AWS{REDACTED}` | ECDSA nonce reuse + SSTI |
| 6 | `AWS{REDACTED}` | DynamoDB users scan (john) |
| 7 | `AWS{REDACTED}` | david desktop (Administrator read) |
| 8 | `AWS{REDACTED}` | workflow + Lambda tracking_api |
| 10 | `AWS{REDACTED}` | S3 SQLite → Administrator |

Saved: `artifacts/flags_captured.txt`

---

## Blockers / failed attempts

1. **Initial wrong IP (`10.13.37.13`)** — all vhosts returned 10676-byte Apache default; AD ports filtered. Fixed by subnet sweep → `.15`.

2. **Login HTTP 500 (jobs + company-support)** — root cause: POST missing **`login` submit field**. Form requires `login=Sign IN` (or any value where `'login' in request.form`). Without it, wrong-password path returns 200; with valid creds + missing login field, behavior differs. **Fix:** always include `"login": "Sign IN"` in login POST.

3. **flag1_token_brute.py false positive** — script treats any non-"Invalid" response as hit; unauthenticated session returns 403 HTML. Needs logged-in session cookie.

4. **`/api/v4/users/edit` requires Managers session** — admin api_token alone returns "Unauthorized Access". Need tyler session (Managers) + admin api_token cookie.

5. **JWT nonce reuse (Flag 4)** — resolved via `scripts/jwt_nonce_reuse.py --fresh`. Shared `r` prefix in signatures confirms reuse. SSTI `__` blacklist bypass: put RCE payload in **ticket title** (only message/email/args are filtered).

6. **Flag 5 LocalStack lambda invoke** — use `aws --cli-binary-format raw-in-base64-out` for JSON payloads. `will` can CreateFunction/Invoke with `serviceadm` role but SQS ReceiveMessage needs admin context. LocalStack may return 500/timeouts after heavy invoke — wait and retry.

7. **`jwt_nonce_reuse.py` missing from repo** — flag4_exploit.py depends on it; restore from prior session or re-implement ECDSA nonce recovery.

---

## Exact next commands for next agent

### Verify environment
```bash
ip -4 addr show tun0
ping -c1 10.13.37.15
grep 10.13.37.15 /etc/hosts
curl -sI http://10.13.37.15/ | head -5
```

### Re-login jobs portal (if session expired)
```bash
cd aws_pentest
python3 << 'EOF'
import re, requests
BASE = "http://jobs.amzcorp.local"
s = requests.Session()
r = s.get(f"{BASE}/login")
csrf = re.search(r'csrf_token" type="hidden" value="([^"]+)"', r.text).group(1)
s.post(f"{BASE}/login", data={"csrf_token": csrf, "username": "htbgdr7d3", "password": "<REDACTED>", "login": "Sign IN"})
print("session:", s.cookies.get("session"))
EOF
```

### Flag 4 — JWT forge + SSTI (company-support)
1. Register 2+ users, collect `aws_auth` cookies after login
2. If signatures match → ECDSA nonce reuse → forge `tony` JWT (see `artifacts/jobs_dev_git/support_portal/apps/authentication/custom_jwt.py`)
3. Set `aws_auth` cookie, access `/admin/tickets/view/<id>`
4. SSTI payload in ticket message (blacklist bypass): avoid `__`, `request[`, `file`, `write`
5. Source: `support_portal/apps/home/routes.py` → `render_template_string(rendered_template)`

### Flag 4+ chain references
- Git source: `artifacts/jobs_dev_git/` (jobs_portal + support_portal)
- Workflow: `http://workflow.amzcorp.local` (Airflow login page)
- Cloud: `http://cloud.amzcorp.local` (LocalStack IAM errors — expected)

### Submit flags (HTB platform)
```bash
bash aws_pentest/scripts/submit_flag.sh 'AWS{REDACTED}'
```

---

## Artifact index

| File | Contents |
|------|----------|
| `artifacts/target_ip.txt` | `10.13.37.15` (corrected) |
| `artifacts/attacker_ip.txt` | VPN IP `10.10.14.225` |
| `artifacts/subdomains_known.txt` | All amzcorp.local subdomains |
| `artifacts/nmap_key_ports.txt` | Key port scan on `.13` (decoy) |
| `artifacts/nmap_top1000_15.txt` | Full top-1000 on DC `.15` |
| `artifacts/nmap_10.13.37.15.txt` | AD ports: 53,80,88,389,445,5985,... |
| `artifacts/vhost_probe.txt` | Vhost codes (pre-correction, stale) |
| `artifacts/http_root_body_full.txt` | Decoy `.13` Apache page |
| `artifacts/app.js` | Obfuscated jobs portal JS (257KB) |
| `artifacts/app_beautified.js` | Beautified JS (still obfuscated) |
| `artifacts/flag1_brute_output.txt` | Token brute run output |
| `artifacts/flag1_result.json` | Flag 1 JSON response |
| `artifacts/flag2_ssrf_logs.json` | 5.4MB SSRF logs dump |
| `artifacts/flag2_logs_parsed.json` | Parsed logs JSON |
| `artifacts/flag3_sqli_response.html` | SQLi result page |
| `artifacts/flags_captured.txt` | Flags 1–4 |
| `artifacts/flag4_result.txt` | Flag 4 SSTI RCE output |
| `artifacts/creds_jobs.txt` | Jobs creds + admin token |
| `artifacts/creds_company_support.txt` | Support portal account |
| `artifacts/jwt_samples.txt` | Two JWTs for nonce analysis |
| `artifacts/jobs_dev_git/` | Full git dump (jobs_portal + support_portal) |
| `notes/progress.log` | Timestamped session log |

---

## Open ports on DC (10.13.37.15)

```
53/tcp   domain (Simple DNS Plus)
80/tcp   http (Apache 2.4.52 Win64) — vhost routes to internal apps
88/tcp   kerberos-sec
135/tcp  msrpc
139/tcp  netbios-ssn
389/tcp  ldap (amzcorp.local)
445/tcp  microsoft-ds
5985/tcp http (WinRM)
3268/tcp ldap (Global Catalog)
```

---

## /etc/hosts (must point to .15)

```
10.13.37.15 amzcorp.local jobs.amzcorp.local logs.amzcorp.local
10.13.37.15 services.amzcorp.local cloud.amzcorp.local inventory.amzcorp.local
10.13.37.15 workflow.amzcorp.local company-support.amzcorp.local
10.13.37.15 jobs-development.amzcorp.local dc01.amzcorp.local
```

Re-apply if missing:
```bash
sudo bash -c 'grep -q "10.13.37.15 amzcorp.local" /etc/hosts || cat aws_pentest/artifacts/subdomains_known.txt | while read s; do echo "10.13.37.15 $s"; done >> /etc/hosts'
```
