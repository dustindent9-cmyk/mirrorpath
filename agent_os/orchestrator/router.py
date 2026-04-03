"""
Router — decides which model provider and agent handles each task.
Separate from MCP (which manages agent dispatch); Router decides *what* runs *where*.

Provider map (Dustin's spec):
  video / timestamps          → gemini
  run code / debug / mcp      → openai
  browse / website / tab      → browser
  everything else             → claude
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RouteDecision:
    provider: str          # "anthropic" | "openai" | "gemini"
    model: str             # exact model ID
    agent_role: str        # agent to handle this task
    reason: str            # why this route was chosen
    parallel_roles: list[str]  # additional agents to run in parallel


# ── Provider → model defaults ───────────────────────────────────────────────

PROVIDER_DEFAULTS = {
    "anthropic": "claude-opus-4-6",
    "openai":    "gpt-4o",
    "gemini":    "gemini-2.0-flash",
}

# ── Task-type → provider preference ─────────────────────────────────────────
# Maps regex patterns → (provider, agent_role, parallel_roles)
ROUTING_TABLE: list[tuple[str, str, str, list[str]]] = [
    # Video / multimodal
    (r"\b(video|youtube|image analys|vision|watch)\b",
     "gemini", "researcher", []),

    # Long context / document analysis
    (r"\b(entire codebase|full document|summarize all|entire repo)\b",
     "gemini", "researcher", ["critic"]),

    # Code generation
    (r"\b(write code|implement|function|class|script|debug|fix bug|refactor)\b",
     "anthropic", "coder", ["critic"]),

    # Research / web
    (r"\b(research|search|find|what is|how does|explain|news|latest)\b",
     "anthropic", "researcher", []),

    # Browser automation
    (r"\b(browse|navigate|click|scrape|website|url|fill form|login)\b",
     "anthropic", "browser_agent", []),

    # Planning
    (r"\b(plan|design|architect|strategy|roadmap|break down|steps to)\b",
     "anthropic", "planner", ["critic"]),

    # Math / data analysis
    (r"\b(calculate|math|statistics|data analysis|chart|graph|plot)\b",
     "openai", "coder", []),

    # Memory / recall
    (r"\b(remember|recall|what did|history|store|memory)\b",
     "anthropic", "memory_agent", []),
]


class Router:
    """
    Stateless router — takes a task string and returns a RouteDecision.
    Priority: routing table first, then heuristics, then default.
    """

    def route(self, task: str, prefer_provider: str | None = None) -> RouteDecision:
        task_lower = task.lower()

        for pattern, provider, agent_role, parallel in ROUTING_TABLE:
            if re.search(pattern, task_lower, re.IGNORECASE):
                if prefer_provider:
                    provider = prefer_provider
                return RouteDecision(
                    provider=provider,
                    model=PROVIDER_DEFAULTS[provider],
                    agent_role=agent_role,
                    reason=f"Matched pattern: {pattern}",
                    parallel_roles=parallel,
                )

        # Heuristic: long tasks → planner first
        if len(task.split()) > 20:
            return RouteDecision(
                provider="anthropic",
                model=PROVIDER_DEFAULTS["anthropic"],
                agent_role="planner",
                reason="Long task — planner decomposes first",
                parallel_roles=[],
            )

        # Default
        return RouteDecision(
            provider=prefer_provider or "anthropic",
            model=PROVIDER_DEFAULTS[prefer_provider or "anthropic"],
            agent_role="executor",
            reason="Default route",
            parallel_roles=[],
        )

    def route_to_provider(self, task: str) -> str:
        """
        Simple provider routing (Dustin's spec):
          video / watch / timestamp → gemini
          run code / debug / mcp    → openai
          browse / website / tab    → browser
          default                   → claude
        """
        t = task.lower()
        if "video" in t or "watch this" in t or "timestamp" in t:
            return "gemini"
        if "run code" in t or "write code" in t or "debug" in t or "mcp" in t:
            return "openai"
        if "browse" in t or "website" in t or "browser" in t or "tab" in t:
            return "browser"
        return "claude"

    def explain(self, task: str) -> str:
        """Return a human-readable routing explanation."""
        d = self.route(task)
        parallel = f" + parallel: {d.parallel_roles}" if d.parallel_roles else ""
        return (
            f"→ {d.provider}/{d.model} | agent: {d.agent_role}{parallel}\n"
            f"  reason: {d.reason}"
        )
