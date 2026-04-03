"""
Multi-Model Control Plane (MCP)
Routes tasks to the appropriate agents and manages multi-model coordination.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import anthropic


@dataclass
class AgentResult:
    agent: str
    output: str
    thinking: str | None = None
    tool_calls: list = field(default_factory=list)
    stop_reason: str = "end_turn"
    metadata: dict = field(default_factory=dict)


class MultiModelControlPlane:
    """
    Routes tasks across multiple agents and Claude model variants.
    Decides which agent(s) handle a given task, collects results,
    and prepares them for the consensus or verifier stages.
    """

    # Agent role → task keyword mapping for auto-routing
    ROUTING_MAP = {
        "planner":       ["plan", "break down", "design", "architect", "strategy", "roadmap"],
        "researcher":    ["research", "find", "search", "look up", "what is", "how does", "explain"],
        "coder":         ["code", "implement", "write", "build", "fix", "debug", "function", "class", "script"],
        "critic":        ["review", "critique", "evaluate", "assess", "check", "audit", "quality"],
        "executor":      ["execute", "run", "do", "perform", "automate", "trigger"],
        "browser_agent": ["browse", "navigate", "visit", "website", "url", "scrape", "click"],
        "user_advocate": ["align", "user need", "requirement", "confirm", "validate intent"],
        "memory_agent":  ["remember", "store", "recall", "memory", "history", "what did"],
    }

    def __init__(self, agents: dict[str, Any] | None = None):
        """
        Args:
            agents: Dict mapping role name → agent instance.
                    If None, agents are lazy-instantiated on first use.
        """
        self._agents: dict[str, Any] = agents or {}
        self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self._session_log: list[AgentResult] = []

    def register(self, role: str, agent: Any) -> None:
        self._agents[role] = agent

    def route(self, task: str) -> list[str]:
        """
        Determine which agents should handle this task.
        Returns list of role names, ordered by execution priority.
        """
        task_lower = task.lower()
        matched: list[str] = []
        for role, keywords in self.ROUTING_MAP.items():
            if any(kw in task_lower for kw in keywords):
                matched.append(role)

        # Always include planner for multi-step tasks (sentence length heuristic)
        if len(task.split()) > 15 and "planner" not in matched:
            matched.insert(0, "planner")

        # Default: researcher + executor if nothing matched
        if not matched:
            matched = ["researcher", "executor"]

        return matched

    def dispatch(
        self,
        task: str,
        roles: list[str] | None = None,
        context: dict | None = None,
        history: list | None = None,
    ) -> list[AgentResult]:
        """
        Dispatch task to one or more agents and collect results.
        """
        roles = roles or self.route(task)
        results: list[AgentResult] = []

        for role in roles:
            agent = self._agents.get(role)
            if agent is None:
                results.append(AgentResult(
                    agent=role,
                    output=f"[Agent '{role}' not registered in MCP]",
                    stop_reason="error",
                ))
                continue
            try:
                raw = agent.run(task=task, context=context, history=history)
                result = AgentResult(
                    agent=role,
                    output=raw.get("output", ""),
                    thinking=raw.get("thinking"),
                    tool_calls=raw.get("tool_calls", []),
                    stop_reason=raw.get("stop_reason", "end_turn"),
                )
            except Exception as exc:
                result = AgentResult(
                    agent=role,
                    output=f"[Error in {role}: {exc}]",
                    stop_reason="error",
                )
            results.append(result)
            self._session_log.append(result)

        return results

    def dispatch_parallel_concept(
        self,
        task: str,
        roles: list[str],
        context: dict | None = None,
    ) -> list[AgentResult]:
        """
        Conceptual parallel dispatch — runs agents sequentially but
        each with independent context (no shared history).
        For true async parallelism, run each agent.run() in asyncio tasks.
        """
        return self.dispatch(task=task, roles=roles, context=context, history=None)

    def summarize_session(self) -> str:
        """Return a text summary of all agent results this session."""
        if not self._session_log:
            return "No agent activity this session."
        lines = []
        for r in self._session_log:
            lines.append(f"[{r.agent.upper()}] stop={r.stop_reason}")
            lines.append(r.output[:300] + ("..." if len(r.output) > 300 else ""))
            lines.append("")
        return "\n".join(lines)

    def clear_session(self) -> None:
        self._session_log.clear()

    @property
    def registered_roles(self) -> list[str]:
        return list(self._agents.keys())
