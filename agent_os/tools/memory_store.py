"""
Memory store — persistent knowledge via claude.md and structured JSON entries.
Single source of truth for all agent memory operations.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .file_tools import append_file

MEMORY_PATH = str(Path(__file__).parent.parent / "claude.md")


# ── Core write operation ─────────────────────────────────────────────────────

def save_memory(note: str, category: str = "Learned Corrections") -> None:
    """Append a timestamped note to claude.md under the given category header."""
    timestamp = datetime.utcnow().isoformat()
    append_file(MEMORY_PATH, f"\n## {category}\n- [{timestamp}] {note}\n")


# ── Typed helpers ────────────────────────────────────────────────────────────

def remember_user_preference(note: str) -> None:
    """Store a user preference that should persist across sessions."""
    save_memory(note, category="User Preferences")


def remember_correction(note: str) -> None:
    """Store a correction — overrides a previous incorrect assumption."""
    save_memory(note, category="Learned Corrections")


def remember_conversation_summary(note: str) -> None:
    """Store a high-level summary of a conversation or session."""
    save_memory(note, category="Conversation Logs")


def remember_task_outcome(note: str) -> None:
    """Store the outcome of a completed task."""
    save_memory(note, category="Task Outcomes")


# ── Read operations ──────────────────────────────────────────────────────────

def read_memory() -> str:
    """Return full contents of claude.md."""
    return Path(MEMORY_PATH).read_text(encoding="utf-8")


def recall(query: str, top_lines: int = 20) -> str:
    """
    Simple keyword recall from claude.md.
    Returns up to top_lines lines containing any word from query.
    """
    query_words = query.lower().split()
    matches: list[str] = []
    for line in Path(MEMORY_PATH).read_text(encoding="utf-8").splitlines():
        if any(w in line.lower() for w in query_words):
            matches.append(line)
    return "\n".join(matches[:top_lines]) if matches else "No matching memories found."
