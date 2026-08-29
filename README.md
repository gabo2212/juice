# Juice Shop Pentest Toolkit

Autonomous attack framework + live web dashboard for the OWASP Juice Shop pen test.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

Juice Shop must be running on `http://localhost:3000/`.

## Run

```bash
python run.py
```

Open the dashboard at `http://localhost:5555`.

The solver runs all attack phases autonomously while the dashboard shows live progress:
- Solved/total donut + points-over-time line chart + category progress bars
- Live log stream
- Full challenge table with status

Solve detection is ground-truth: the scoreboard poller reads the `solved` boolean from
`GET /api/Challenges/` every 3s.

## Layout

```
juice_pentest/      attack framework (client, state, scoreboard, solver, attacks/*)
dashboard/          FastAPI + SSE backend, single-page Chart.js frontend
run.py             entrypoint
JUICE_SHOP_PENTEST_PLAN.md   reference plan with all 116 challenges mapped
```
