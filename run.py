#!/usr/bin/env python3
"""Entrypoint: start the dashboard + scoreboard monitor + solver."""

from __future__ import annotations

import asyncio
import sys
import threading
import time

from dashboard import server as dashboard_server
from juice_pentest.client import JuiceShopClient
from juice_pentest.scoreboard import ScoreboardMonitor
from juice_pentest.solver import Solver
from juice_pentest.state import bus, state

DASH_HOST = "127.0.0.1"
DASH_PORT = 5555


def main() -> int:
    client = JuiceShopClient()
    dashboard_server.set_client(client)

    # Bind the event bus to a dedicated asyncio loop for the dashboard.
    dash_loop = asyncio.new_event_loop()
    bus.bind_loop(dash_loop)

    # Start dashboard in a thread running its own loop.
    def run_dashboard():
        asyncio.set_event_loop(dash_loop)
        import uvicorn
        uvicorn.run(dashboard_server.app, host=DASH_HOST, port=DASH_PORT,
                    log_level="warning", loop="asyncio")

    dash_thread = threading.Thread(target=run_dashboard, daemon=True, name="dashboard")
    dash_thread.start()
    time.sleep(1.0)  # let uvicorn bind

    # Start scoreboard monitor in a thread.
    monitor = ScoreboardMonitor(client, interval=3.0)
    monitor.start()

    print(f"Dashboard: http://{DASH_HOST}:{DASH_PORT}")
    print("Starting solver...\n")

    try:
        Solver(client).run()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        monitor.stop()
        # Give the dashboard a moment to flush final events.
        time.sleep(2.0)

    print(f"\nFinal: {len(state.solved)}/{state.total_challenges} solved, "
          f"{state.points} points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
