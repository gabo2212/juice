"""FastAPI dashboard backend with SSE live event stream."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from juice_pentest.state import bus, state

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Juice Shop Pentest Dashboard")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Set by run.py so the dashboard can proxy challenge data.
_client = None


def set_client(client) -> None:
    global _client
    _client = client


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text())


@app.get("/api/state")
def api_state() -> JSONResponse:
    return JSONResponse(state.snapshot())


@app.get("/api/challenges")
def api_challenges() -> JSONResponse:
    if _client is None:
        return JSONResponse({"data": []})
    try:
        data = _client.challenges()
    except Exception as e:
        return JSONResponse({"data": [], "error": str(e)})
    solved = state.solved
    enriched = []
    for c in data:
        cc = dict(c)
        cc["solved"] = bool(c.get("solved")) or c.get("key") in solved
        enriched.append({"key": cc.get("key"), "name": cc.get("name"),
                         "category": cc.get("category"),
                         "difficulty": cc.get("difficulty"),
                         "solved": cc["solved"]})
    return JSONResponse({"data": enriched})


@app.get("/events")
async def events(request: Request) -> StreamingResponse:
    queue = bus.subscribe()

    async def event_generator():
        # initial hello so the client knows the stream is alive
        yield f"data: {json.dumps({'type': 'hello', 'state': state.snapshot()})}\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                     "X-Accel-Buffering": "no",
                                     "Connection": "keep-alive"})


def serve(host: str = "127.0.0.1", port: int = 5555) -> None:
    """Run the dashboard in the current thread (blocking)."""
    import uvicorn
    bus.bind_loop(asyncio.new_event_loop())
    uvicorn.run(app, host=host, port=port, log_level="warning")


def serve_in_thread(host: str = "127.0.0.1", port: int = 5555) -> threading.Thread:
    t = threading.Thread(target=serve, args=(host, port), daemon=True, name="dashboard")
    return t
