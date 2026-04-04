"""
Dallas Web — Personal AI Assistant Server

Runs the Dallas engine behind a clean web UI.

Start:
    cd agent_os
    uvicorn web.app:app --reload --port 8000

Then open: http://localhost:8000
"""
from __future__ import annotations

import json
import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Any

# ── Path setup so imports work from inside web/ ───────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator.engine import Engine, EngineResult
from tools.memory_store import read_memory, remember_conversation_summary

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Dallas", description="Personal AI Assistant", version="1.0.0")

import logging
log = logging.getLogger("dallas")

_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Mount static files
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

# ── Engine (singleton) ────────────────────────────────────────────────────────
_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = Engine()
        # Lazy-load agents that are available
        try:
            from agents.planner import PlannerAgent
            from agents.coder import CoderAgent
            from agents.researcher import ResearcherAgent
            from agents.critic import CriticAgent
            from agents.executor import ExecutorAgent
            from agents.memory_agent import MemoryAgent
            from agents.user_advocate import UserAdvocateAgent
            from agents.self_modifier import SelfModifierAgent

            _engine.register_all({
                "planner":       PlannerAgent(),
                "coder":         CoderAgent(),
                "researcher":    ResearcherAgent(),
                "critic":        CriticAgent(),
                "executor":      ExecutorAgent(),
                "memory_agent":  MemoryAgent(),
                "user_advocate": UserAdvocateAgent(),
                "self_modifier": SelfModifierAgent(),
            })
        except Exception as e:
            log.warning("Agent registration failed (partial setup): %s", e, exc_info=True)
    return _engine


# ── Request / Response models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    prefer_provider: str | None = None


class ChatResponse(BaseModel):
    output: str
    route_provider: str
    route_model: str
    route_agent: str
    verified: bool
    verification_issues: list[str]
    consensus_score: float
    elapsed_ms: int
    notes: list[str]
    self_modified: bool = False   # True when the self_modifier agent ran


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = STATIC / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    keys = {
        "anthropic":     bool(os.environ.get("ANTHROPIC_API_KEY")),
        "openai":        bool(os.environ.get("OPENAI_API_KEY")),
        "gemini":        bool(os.environ.get("GEMINI_API_KEY")),
        "bridge":        bool(os.environ.get("BRIDGE_API_KEY")),
        "zillow":        bool(os.environ.get("ZILLOW_ZWSID")),
        "self_modify":   os.environ.get("DALLAS_SELF_MODIFY", "").lower() == "true",
    }
    return {"status": "ok", "keys": keys}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    engine = get_engine()
    t0 = time.time()

    # Run in thread pool so we don't block the event loop
    loop = asyncio.get_event_loop()
    result: EngineResult = await loop.run_in_executor(
        None,
        lambda: engine.run(req.message, prefer_provider=req.prefer_provider),
    )

    elapsed = int((time.time() - t0) * 1000)

    route = result.route
    agent = route.agent_role if route else "executor"
    return ChatResponse(
        output=result.output,
        route_provider=route.provider if route else "anthropic",
        route_model=route.model if route else "claude-opus-4-6",
        route_agent=agent,
        verified=result.verified,
        verification_issues=result.verification_issues,
        consensus_score=round(result.consensus_score, 2),
        elapsed_ms=elapsed,
        notes=result.notes,
        self_modified=agent == "self_modifier",
    )


@app.post("/api/route-explain")
async def route_explain(req: ChatRequest):
    """Return routing decision without running the task."""
    engine = get_engine()
    explanation = engine.explain_route(req.message)
    route = engine._router.route(req.message)
    return {
        "explanation": explanation,
        "provider": route.provider,
        "model": route.model,
        "agent": route.agent_role,
        "parallel": route.parallel_roles,
        "reason": route.reason,
    }


@app.get("/api/memory")
async def get_memory():
    """Return the contents of claude.md (persistent memory)."""
    try:
        content = read_memory()
        return {"content": content, "chars": len(content)}
    except Exception as e:
        return {"content": "", "chars": 0, "error": str(e)}


@app.get("/api/session")
async def session_summary():
    engine = get_engine()
    return {"summary": engine.session_summary()}


@app.post("/api/session/clear")
async def clear_session():
    engine = get_engine()
    engine.clear_session()
    return {"status": "cleared"}
