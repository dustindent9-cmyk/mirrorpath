"""
Dallas Engine — top-level orchestration loop.

This is the single entry point for running the Dallas multi-agent system.
It wires together: Router → MCP dispatch → Consensus → Verifier → Memory.

Usage:
    from orchestrator.engine import Engine

    engine = Engine()
    result = engine.run("Research the latest LLM benchmarks and summarize findings")
    print(result.output)

Or from the CLI:
    python -m orchestrator.engine "your task here"
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any

from .router import Router, RouteDecision
from .mcp import MultiModelControlPlane, AgentResult
from .consensus import score_responses, choose_best
from .verifier import Verifier
from .contracts import AgentInput, AgentOutput, SessionResult


# ── Result model ─────────────────────────────────────────────────────────────

@dataclass
class EngineResult:
    task:           str
    output:         str = ""
    route:          RouteDecision | None = None
    agent_results:  list[AgentResult] = field(default_factory=list)
    verified:       bool = False
    verification_issues: list[str] = field(default_factory=list)
    consensus_score: float = 0.0
    notes:          list[str] = field(default_factory=list)


# ── Engine ────────────────────────────────────────────────────────────────────

class Engine:
    """
    Dallas orchestration engine.

    Steps per request:
      1. Route  — Router picks provider + agent role
      2. Dispatch — MCP calls the primary agent (+ parallel agents if any)
      3. Score  — consensus.score_responses() ranks candidates
      4. Verify — Verifier fast-checks the best response
      5. Memory — persist a summary to claude.md
      6. Return — EngineResult with full trace

    Agents are lazy-loaded on first use unless pre-registered via
    Engine(agents={...}).
    """

    def __init__(self, agents: dict[str, Any] | None = None):
        self._router   = Router()
        self._mcp      = MultiModelControlPlane(agents=agents or {})
        self._verifier = Verifier()
        self._memory_enabled = True

    # ── Registration helpers ─────────────────────────────────────────────────

    def register(self, role: str, agent: Any) -> None:
        """Register an agent instance under a role name."""
        self._mcp.register(role, agent)

    def register_all(self, agents: dict[str, Any]) -> None:
        for role, agent in agents.items():
            self.register(role, agent)

    # ── Main entry point ─────────────────────────────────────────────────────

    def run(
        self,
        task: str,
        prefer_provider: str | None = None,
        context: dict | None = None,
        history: list | None = None,
    ) -> EngineResult:
        """
        Run a task through the full Dallas orchestration loop.

        Args:
            task:             Natural language task description
            prefer_provider:  Force a provider ("anthropic"|"openai"|"gemini")
            context:          Extra key/value context passed to agents
            history:          Prior conversation turns

        Returns:
            EngineResult with output, verification status, and full trace
        """
        notes: list[str] = []
        result = EngineResult(task=task)

        # ── 1. Route ──────────────────────────────────────────────────────────
        route = self._router.route(task, prefer_provider=prefer_provider)
        result.route = route
        notes.append(f"Route: {route.provider}/{route.model} → {route.agent_role}")

        # ── 2. Dispatch ───────────────────────────────────────────────────────
        roles = [route.agent_role] + route.parallel_roles
        agent_results = self._mcp.dispatch(
            task=task,
            roles=roles,
            context=context,
            history=history,
        )
        result.agent_results = agent_results

        if not agent_results:
            result.output = "[Engine] No agent results returned."
            result.notes = notes
            return result

        # ── 3. Consensus scoring ──────────────────────────────────────────────
        candidates = [
            {
                "agent":      r.agent,
                "output":     r.output,
                "confidence": 0.85 if r.stop_reason == "end_turn" else 0.4,
                "errors":     1 if r.stop_reason == "error" else 0,
            }
            for r in agent_results
        ]
        scored = score_responses(candidates)
        best   = choose_best(scored) if scored else (candidates[0] if candidates else {})
        best_output = best.get("output", agent_results[0].output)
        result.consensus_score = best.get("confidence", 0.0)

        # ── 4. Verification ───────────────────────────────────────────────────
        verdict = self._verifier.verify(task=task, answer=best_output)
        result.verified = verdict.get("approved", False)
        result.verification_issues = verdict.get("issues", [])
        if result.verification_issues:
            notes.append(f"Verification issues: {result.verification_issues}")

        result.output = best_output

        # ── 5. Memory ─────────────────────────────────────────────────────────
        if self._memory_enabled:
            try:
                from tools.memory_store import remember_conversation_summary
                remember_conversation_summary(
                    f"Task: {task[:200]}\nResult: {best_output[:300]}"
                )
            except Exception:
                notes.append("Memory write skipped (memory_store unavailable)")

        result.notes = notes
        return result

    def explain_route(self, task: str) -> str:
        """Return a human-readable routing explanation without running the task."""
        return self._router.explain(task)

    def session_summary(self) -> str:
        """Return a text summary of all agent activity this session."""
        return self._mcp.summarize_session()

    def clear_session(self) -> None:
        self._mcp.clear_session()


# ── CLI entry point ───────────────────────────────────────────────────────────

def _cli() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m orchestrator.engine \"<task>\"")
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    engine = Engine()
    result = engine.run(task)

    print(f"\n{'='*60}")
    print(f"TASK:   {result.task}")
    print(f"ROUTE:  {result.route.provider}/{result.route.model} → {result.route.agent_role}")
    print(f"VERIFIED: {result.verified}")
    if result.verification_issues:
        print(f"ISSUES: {result.verification_issues}")
    print(f"{'='*60}")
    print(result.output)
    print(f"{'='*60}\n")

    if result.notes:
        for note in result.notes:
            print(f"[note] {note}")


if __name__ == "__main__":
    _cli()
