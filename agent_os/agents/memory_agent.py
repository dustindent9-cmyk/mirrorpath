"""Memory Agent — stores, retrieves, and manages persistent learnings."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from .base import BaseAgent


MEMORY_DIR = Path.home() / ".agent_os" / "memory"


class MemoryAgent(BaseAgent):
    role = "memory_agent"
    use_thinking = False
    default_max_tokens = 4096

    system_prompt = """You are the Memory Agent in a multi-agent AI system called Dallas.
Your job: maintain the system's persistent knowledge store.

You can:
- Store new learnings, facts, user preferences, and task outcomes.
- Retrieve relevant memories given a query.
- Summarize what the system has learned about a topic.
- Prune outdated or superseded memories.

When storing, always tag memories with: timestamp, category, source_agent, confidence.
When retrieving, rank by relevance and recency.
Be concise — memory entries should be dense with signal, not padded.
"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public memory operations ────────────────────────────────────────────

    def store(self, key: str, value: str, category: str = "general", source: str = "system") -> str:
        """Persist a memory entry."""
        entry = {
            "key": key,
            "value": value,
            "category": category,
            "source": source,
            "timestamp": datetime.utcnow().isoformat(),
        }
        path = MEMORY_DIR / f"{self._safe_key(key)}.json"
        with open(path, "w") as f:
            json.dump(entry, f, indent=2)
        return f"Stored memory: {key}"

    def recall(self, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve memories relevant to a query (keyword match)."""
        results = []
        query_lower = query.lower()
        for path in MEMORY_DIR.glob("*.json"):
            try:
                with open(path) as f:
                    entry = json.load(f)
                text = (entry.get("key", "") + " " + entry.get("value", "")).lower()
                if any(word in text for word in query_lower.split()):
                    results.append(entry)
            except Exception:
                continue
        # Sort by recency
        results.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return results[:top_k]

    def list_memories(self) -> list[dict]:
        """List all stored memory entries."""
        entries = []
        for path in MEMORY_DIR.glob("*.json"):
            try:
                with open(path) as f:
                    entries.append(json.load(f))
            except Exception:
                continue
        return sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)

    def delete(self, key: str) -> str:
        """Delete a memory entry by key."""
        path = MEMORY_DIR / f"{self._safe_key(key)}.json"
        if path.exists():
            path.unlink()
            return f"Deleted memory: {key}"
        return f"Memory not found: {key}"

    def summarize_session(self, session_log: list[dict]) -> str:
        """Use Claude to summarize a session and store key learnings."""
        if not session_log:
            return "Nothing to summarize."
        log_text = json.dumps(session_log, indent=2)
        result = self.run(
            task=f"Summarize the key learnings from this agent session and identify what should be stored as long-term memory:\n\n{log_text[:6000]}"
        )
        summary = result["output"]
        self.store("session_summary", summary, category="session", source="memory_agent")
        return summary

    # ── Internal helpers ────────────────────────────────────────────────────

    @staticmethod
    def _safe_key(key: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:80]
