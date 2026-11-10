"""Alibi website: runs the shopping agent in the background and streams each step to the page.

Start it:   uvicorn server:app --reload
Then open:  http://localhost:8000

Environment (.env):
    PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET   real sandbox payments (otherwise a fake PayPal is used)
    GEMINI_API_KEY / GEMINI_MODEL              the AI agent (otherwise only the obedient agent works)
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import store
from agent import AgentError, Session, run_gemini, run_scripted
from alibi.paypal import FakePayPal, PayPal

load_dotenv()
WEB = Path(__file__).parent / "web"
APPROVAL_TIMEOUT = 300  # seconds the agent waits for the customer before giving up

app = FastAPI(title="Alibi")
app.mount("/static", StaticFiles(directory=WEB), name="static")


def make_paypal():
    if os.environ.get("PAYPAL_CLIENT_ID") and os.environ.get("PAYPAL_CLIENT_SECRET"):
        return PayPal()
    return FakePayPal()


PAYPAL = make_paypal()
LEDGER: list[dict] = []          # every payment attempt across all runs, newest first
LEDGER_LOCK = threading.Lock()
RUNS: dict[str, "Run"] = {}


class Run:
    def __init__(self, req: "RunRequest"):
        self.id = uuid.uuid4().hex[:10]
        self.req = req
        self.events: list[dict] = []
        self.status = "running"   # running | waiting | done | error
        self.lock = threading.Lock()
        self._decision = threading.Event()
        self._answer: bool | None = None
        self.created = time.time()

    def emit(self, kind: str, **data) -> None:
        with self.lock:
            self.events.append({"n": len(self.events), "kind": kind, "t": time.time(), **data})

    def approver(self, attempt: dict) -> bool | None:
        """Called by the agent when Alibi holds a payment. Waits for the customer to answer."""
        self._answer = None
        self._decision.clear()
        self.status = "waiting"
        self.emit("approval_needed", attempt=attempt)
        answered = self._decision.wait(APPROVAL_TIMEOUT)
        self.status = "running"
        return self._answer if answered else None

    def answer(self, approve: bool) -> None:
        self._answer = approve
        self._decision.set()


class RunRequest(BaseModel):
    request: str = Field(store.REQUEST, max_length=400)
    budget: float = Field(60, gt=0, le=10_000)
    shop: str = "ai-notice"
    agent: str = "obedient"      # obedient | gemini
    protected: bool = True
    page: str | None = Field(None, max_length=4000)  # custom shop page from the playground


def _worker(run: Run) -> None:
    r = run.req
    custom = r.page is not None
    session = Session(r.request, r.budget, "custom" if custom else r.shop, r.protected, PAYPAL,
                      page=r.page, emit=run.emit, approver=run.approver)
    try:
        if r.agent == "gemini":
            reply = run_gemini(session, r.request)
        else:
            reply = run_scripted(session, r.request, True, None if custom else r.shop)
        run.emit("done", reply=reply)
        run.status = "done"
    except AgentError as e:
        run.emit("error", message=str(e), daily=e.daily)
        run.status = "error"
    except Exception as e:  # never leave the page spinning
        run.emit("error", message=f"{type(e).__name__}: {e}")
        run.status = "error"
    finally:
        from agent import attempt_json
        with LEDGER_LOCK:
            for e in session.events:
                row = attempt_json(e, session.protected)
                row.update(run=run.id, shop="Your page" if custom else store.SCENARIOS[r.shop].trick,
                           agent=r.agent, when=time.strftime("%H:%M:%S"))
                LEDGER.insert(0, row)
            del LEDGER[500:]


# ---------------------------------------------------------------- API

@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/config")
def config():
    return {
        "paypal": "sandbox" if isinstance(PAYPAL, PayPal) else "simulated",
        "gemini": bool(os.environ.get("GEMINI_API_KEY")),
        "model": os.environ.get("GEMINI_MODEL", "gemini-flash-latest"),
        # "poisoned" is an old alias for ai-notice, so skip it by key to avoid listing that shop twice
        "shops": [{"id": s.name, "kind": s.kind, "trick": s.trick, "page": s.page}
                  for key, s in store.SCENARIOS.items() if key != "poisoned"],
        "catalog": store.CATALOG,
        "request": store.REQUEST,
        "base_page": store._BASE,
    }


@app.post("/api/runs")
def start(req: RunRequest):
    if req.page is None and req.shop not in store.SCENARIOS:
        raise HTTPException(400, "Unknown shop")
    if req.agent not in ("obedient", "gemini"):
        raise HTTPException(400, "Unknown agent")
    # keep memory bounded on a long-running server
    for rid in [k for k, v in RUNS.items() if time.time() - v.created > 3600]:
        RUNS.pop(rid, None)
    run = Run(req)
    RUNS[run.id] = run
    threading.Thread(target=_worker, args=(run,), daemon=True).start()
    return {"id": run.id}


@app.get("/api/runs/{rid}")
def poll(rid: str, after: int = -1):
    run = RUNS.get(rid)
    if not run:
        raise HTTPException(404, "Run not found")
    with run.lock:
        events = [e for e in run.events if e["n"] > after]
    return {"status": run.status, "events": events}


class Decision(BaseModel):
    approve: bool


@app.post("/api/runs/{rid}/decision")
def decide(rid: str, d: Decision):
    run = RUNS.get(rid)
    if not run or run.status != "waiting":
        raise HTTPException(409, "Nothing is waiting for approval")
    run.answer(d.approve)
    return {"ok": True}


@app.get("/api/ledger")
def ledger():
    with LEDGER_LOCK:
        return LEDGER[:200]
