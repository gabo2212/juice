# Juice Shop Pentest Toolkit

Autonomous attack framework and live dashboard for **OWASP Juice Shop** (tested against **v20.2.0**).

Point it at a local Juice Shop instance. The solver walks 15 challenge categories in dependency order, a background poller reads the real scoreboard, and a web UI streams progress as challenges flip to solved.

This is for **your own Juice Shop** on `localhost`. Juice Shop is an intentionally vulnerable training app. Do not point this toolkit at anything you do not own.

Companion lab repo: [htb](https://github.com/gabo2212/htb).

---

## What you get

- **Solver** — 16 attack modules (`juice_pentest/attacks/`) run in a fixed order. One failing attack does not stop the rest.
- **HTTP client** — thin wrapper around Juice Shop’s REST API (login, search, baskets, B2B, GDPR, uploads, redirects, chatbot, and so on).
- **Ground-truth scoring** — `ScoreboardMonitor` polls `GET /api/Challenges/` every 3 seconds and treats Juice Shop’s own `solved` boolean as source of truth.
- **Live dashboard** — Chart.js UI on `http://127.0.0.1:5555` (solved/total donut, points over time, category bars, SSE log, full challenge table).
- **Persisted state** — `state.json` so a reload of the dashboard still shows the last run.

The full 116-challenge map (recon notes, phases, and what’s already confirmed) lives in [`JUICE_SHOP_PENTEST_PLAN.md`](JUICE_SHOP_PENTEST_PLAN.md).

---

## Prerequisites

- Python 3.10+
- OWASP Juice Shop running at **`http://localhost:3000/`**
- Chromium for Playwright (XSS module launches a browser last)

Start Juice Shop however you usually do, for example:

```bash
docker run --rm -p 3000:3000 bkimminich/juice-shop
```

Confirm the shop is up: open `http://localhost:3000/` and the scoreboard at `/#/score-board`.

---

## Setup

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

`.venv/` is gitignored. Re-create it on a new machine.

### Python dependencies

| Package | Why |
|---|---|
| `requests` | Juice Shop REST client |
| `fastapi` + `uvicorn` | Dashboard + SSE |
| `playwright` | Browser XSS challenges |
| `python-socketio` | Socket.IO XSS / notification challenges |
| `eth-account` | NFT / wallet challenges |
| `pyotp` | 2FA |
| `hashids` | Coupon / ID encoding |

---

## Run

```bash
python run.py
```

That starts three things:

1. **Dashboard** on `http://127.0.0.1:5555` (uvicorn in a daemon thread).
2. **Scoreboard monitor** polling `/api/Challenges/` every 3s.
3. **Solver** on the main thread, module by module.

Open the dashboard, then watch the log and charts. Ctrl+C stops the solver; the monitor shuts down in `finally`.

On exit you’ll see something like:

```text
Final: <solved>/<total> solved, <points> points
```

---

## Dashboard

URL: **http://127.0.0.1:5555**

| Surface | What it shows |
|---|---|
| Header | Solved / total, points, category count, live pulse |
| Donut | Solved vs remaining |
| Line chart | Points over time |
| Category bars | Per-category progress |
| Log | SSE stream from the solver (`info` / `success` / `warn` / `error`) |
| Table | Every challenge: name, category, difficulty, solved/pending |

Backend endpoints (`dashboard/server.py`):

| Path | Role |
|---|---|
| `GET /` | Single-page UI |
| `GET /api/state` | Snapshot from `state.json` |
| `GET /api/challenges` | Live challenge list from Juice Shop, merged with local solved set |
| `GET /events` | Server-Sent Events (hello + keepalives every 15s) |

---

## How a run works

```text
run.py
  ├─ JuiceShopClient  ── HTTP to localhost:3000
  ├─ dashboard thread ── FastAPI + SSE (bus.bind_loop)
  ├─ ScoreboardMonitor ── poll /api/Challenges/ ──► solved events
  └─ Solver.run()
        ensure_admin()     # SQLi login, JWT cached under /tmp/juice_leak/
        for each module:
            module.run()   # each attack wrapped in try/except
```

Events go through `juice_pentest.state.EventBus`. The solver thread publishes; the dashboard’s asyncio loop fans out to every SSE subscriber. `State` writes `state.json` so the UI can hydrate after a refresh.

**Solve detection is not guessed from HTTP status.** A challenge counts only when Juice Shop itself marks it `solved` on `/api/Challenges/`.

Difficulty → points (Juice Shop scoring):

| ★ | Points |
|---|--------|
| 1 | 10 |
| 2 | 25 |
| 3 | 50 |
| 4 | 100 |
| 5 | 250 |
| 6 | 500 |

---

## Attack modules (solver order)

Order is intentional: recon and data leaks first, XSS last (heaviest — Playwright).

| # | Module | Category | File |
|---|---|---|---|
| 1 | SensitiveData | Sensitive Data Exposure | `attacks/sensitive_data.py` |
| 2 | Observability | Observability Failures | `attacks/observability.py` |
| 3 | Misc | Miscellaneous | `attacks/misc.py` |
| 4 | Injection | Injection | `attacks/injection.py` |
| 5 | Auth | Broken Authentication | `attacks/auth.py` |
| 6 | AccessControl | Broken Access Control | `attacks/access_control.py` |
| 7 | Crypto | Cryptographic Issues | `attacks/crypto.py` |
| 8 | InputValidation | Improper Input Validation | `attacks/input_validation.py` |
| 9 | VulnComponents | Vulnerable Components | `attacks/vuln_components.py` |
| 10 | Deserialization | Insecure Deserialization | `attacks/deserialization.py` |
| 11 | XXE | XXE | `attacks/xxe.py` |
| 12 | Misconfig | Security Misconfiguration | `attacks/misconfig.py` |
| 13 | Obscurity | Security through Obscurity | `attacks/obscurity.py` |
| 14 | AntiAutomation | Broken Anti Automation | `attacks/anti_automation.py` |
| 15 | Redirects | Unvalidated Redirects | `attacks/redirects.py` |
| 16 | XSS | XSS | `attacks/xss.py` |

Each module subclasses `AttackBase`. `attacks()` returns callables; `run()` logs, executes, and swallows exceptions so one failure cannot abort the whole category.

Recommended human execution order (from the plan): bank recon/data points → injection → auth takeover → access control → crypto → input validation → components / deserialization / XXE → XSS → misconfig / obscurity / anti-automation / redirects.

---

## Layout

```text
.
├── run.py                         # entrypoint (dashboard + monitor + solver)
├── requirements.txt
├── state.json                     # last-run progress (safe to delete)
├── JUICE_SHOP_PENTEST_PLAN.md     # 116-challenge map from live recon
├── dashboard/
│   ├── server.py                  # FastAPI + SSE
│   └── static/index.html          # Chart.js frontend
└── juice_pentest/
    ├── client.py                  # REST wrapper (default http://localhost:3000)
    ├── solver.py                  # module orchestrator
    ├── scoreboard.py              # poller + point math
    ├── state.py                   # EventBus + persisted State
    ├── passwords.py               # known Juice Shop default creds for the lab
    └── attacks/                   # one file per category
```

Target base URL defaults to `http://localhost:3000` in `JuiceShopClient`. Change it there (or pass `base=...`) if your shop is on another port.

Admin JWT is cached at `/tmp/juice_leak/admin_token.txt` after the first SQLi login so later modules reuse it.

---

## Notes

- **Local only.** Default bind is `127.0.0.1:5555` for the dashboard and `localhost:3000` for the shop.
- **Idempotent-ish.** Re-running against an already-solved shop is fine; the scoreboard still reports what’s solved. `state.json` will update.
- **XSS is last** because it needs Chromium. If Playwright isn’t installed, earlier categories still run.
- **Plan vs code.** The markdown plan is the human map. The Python modules are what `run.py` actually executes.

---

## License / use

Educational use against a Juice Shop instance you run yourself. Not a scanner for third-party sites.
