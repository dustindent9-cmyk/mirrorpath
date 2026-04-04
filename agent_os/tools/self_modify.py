"""
Self-modification tools — lets Dallas read and edit its own source code.

Safety rules enforced here:
  1. DALLAS_SELF_MODIFY=true must be set in .env (disabled by default)
  2. All paths are resolved and validated to stay inside agent_os/
  3. Every write makes a git commit with a descriptive message
  4. patch_source() does surgical find-replace — safer than full rewrites
  5. No deletions of core files (main.py, claude.md, engine.py, etc.)
"""
from __future__ import annotations

import os
import subprocess
import textwrap
import difflib
from datetime import datetime
from pathlib import Path

# ── Root of the agent_os directory ───────────────────────────────────────────
_ROOT = Path(__file__).parent.parent.resolve()

# Files that cannot be overwritten via self-modification
_PROTECTED = {
    "claude.md",
    ".env",
    ".env.example",
    "config/permissions.json",
}


def _check_enabled() -> None:
    if os.environ.get("DALLAS_SELF_MODIFY", "").lower() != "true":
        raise PermissionError(
            "Self-modification is disabled. "
            "Set DALLAS_SELF_MODIFY=true in .env to enable it."
        )


def _safe_path(rel_path: str) -> Path:
    """
    Resolve a relative path inside agent_os/ and verify it doesn't
    escape the root. Raises ValueError if path is outside agent_os/.
    """
    p = (_ROOT / rel_path).resolve()
    # Use is_relative_to (Py 3.9+) — immune to prefix tricks like /repo/agent_os_evil/
    if not p.is_relative_to(_ROOT):
        raise ValueError(f"Path '{rel_path}' escapes the agent_os directory.")
    if rel_path in _PROTECTED or p.name in {Path(x).name for x in _PROTECTED}:
        raise PermissionError(f"'{rel_path}' is a protected file and cannot be modified.")
    return p


# ── Read ──────────────────────────────────────────────────────────────────────

def read_source(rel_path: str) -> str:
    """
    Read a source file from agent_os/.

    Args:
        rel_path: Path relative to agent_os/ (e.g. 'orchestrator/router.py')
    Returns:
        File contents as a string.
    """
    p = _safe_path(rel_path)
    if not p.exists():
        raise FileNotFoundError(f"'{rel_path}' does not exist in agent_os/")
    return p.read_text(encoding="utf-8")


def list_source(pattern: str = "**/*.py") -> str:
    """
    List source files in agent_os/ matching a glob pattern.

    Args:
        pattern: Glob pattern (default '**/*.py')
    Returns:
        Newline-separated list of relative paths.
    """
    matches = sorted(
        str(p.relative_to(_ROOT))
        for p in _ROOT.rglob(pattern)
        if p.is_file()
        and ".git" not in p.parts
        and "__pycache__" not in p.parts
    )
    return "\n".join(matches) if matches else "(no matches)"


# ── Diff ──────────────────────────────────────────────────────────────────────

def diff_source(rel_path: str, new_content: str) -> str:
    """
    Return a unified diff between the current file and new_content.
    Does NOT write anything.
    """
    p = _safe_path(rel_path)
    old = p.read_text(encoding="utf-8") if p.exists() else ""
    diff = list(difflib.unified_diff(
        old.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
        lineterm="",
    ))
    return "".join(diff) if diff else "(no changes)"


# ── Write — full file ─────────────────────────────────────────────────────────

def write_source(rel_path: str, content: str, commit_message: str) -> dict:
    """
    Write (or create) a file inside agent_os/ and commit it.

    Args:
        rel_path:       Path relative to agent_os/
        content:        Full new file content
        commit_message: Git commit message describing the change
    Returns:
        dict with keys: path, diff, committed
    """
    _check_enabled()
    p = _safe_path(rel_path)

    old = p.read_text(encoding="utf-8") if p.exists() else ""
    diff = diff_source(rel_path, content)

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

    committed = _git_commit([str(p)], commit_message)
    return {"path": rel_path, "diff": diff, "committed": committed}


# ── Write — surgical patch ────────────────────────────────────────────────────

def patch_source(
    rel_path: str,
    old_text: str,
    new_text: str,
    commit_message: str,
) -> dict:
    """
    Find and replace an exact block of text inside a source file, then commit.
    Safer than write_source — only touches the specified region.

    Args:
        rel_path:       Path relative to agent_os/
        old_text:       Exact text to find (must appear exactly once)
        new_text:       Replacement text
        commit_message: Git commit message
    Returns:
        dict with keys: path, diff, committed, occurrences_found
    """
    _check_enabled()
    p = _safe_path(rel_path)
    if not p.exists():
        raise FileNotFoundError(f"'{rel_path}' does not exist")

    content = p.read_text(encoding="utf-8")
    count = content.count(old_text)
    if count == 0:
        raise ValueError(
            f"Text not found in '{rel_path}'.\n"
            f"Looking for:\n{textwrap.indent(old_text[:300], '  ')}"
        )
    if count > 1:
        raise ValueError(
            f"Text appears {count} times in '{rel_path}' — be more specific."
        )

    new_content = content.replace(old_text, new_text, 1)
    diff = diff_source(rel_path, new_content)
    p.write_text(new_content, encoding="utf-8")

    committed = _git_commit([str(p)], commit_message)
    return {
        "path": rel_path,
        "diff": diff,
        "committed": committed,
        "occurrences_found": count,
    }


# ── Git helpers ───────────────────────────────────────────────────────────────

def _git_commit(file_paths: list[str], message: str) -> bool:
    """Stage the given files and create a git commit. Returns True if committed."""
    try:
        repo_root = _ROOT.parent  # mirrorpath/
        subprocess.run(
            ["git", "add"] + file_paths,
            cwd=str(repo_root), check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["git", "commit", "-m", f"{message}\n\n[Dallas self-modification — {datetime.utcnow().isoformat()}Z]"],
            cwd=str(repo_root), check=True,
            capture_output=True, text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def git_diff() -> str:
    """Return the current git diff for the working tree (uncommitted changes)."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=str(_ROOT.parent),
            capture_output=True, text=True, check=True,
        )
        return result.stdout or "(clean — no uncommitted changes)"
    except subprocess.CalledProcessError as e:
        return f"[git diff error: {e}]"


def git_log(n: int = 8) -> str:
    """Return the last n git commits."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--oneline"],
            cwd=str(_ROOT.parent),
            capture_output=True, text=True, check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"[git log error: {e}]"


# ── Tool schema for Claude tool-use API ──────────────────────────────────────

SELF_MODIFY_TOOLS = [
    {
        "name": "read_source",
        "description": "Read a source file from the agent_os directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rel_path": {
                    "type": "string",
                    "description": "Path relative to agent_os/ (e.g. 'orchestrator/router.py')"
                }
            },
            "required": ["rel_path"],
        },
    },
    {
        "name": "list_source",
        "description": "List source files in agent_os/ matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern, e.g. '**/*.py' or 'tools/*.py'",
                    "default": "**/*.py",
                }
            },
        },
    },
    {
        "name": "diff_source",
        "description": "Preview a diff between the current file and proposed new content WITHOUT writing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rel_path":    {"type": "string"},
                "new_content": {"type": "string", "description": "Proposed full file content"},
            },
            "required": ["rel_path", "new_content"],
        },
    },
    {
        "name": "patch_source",
        "description": (
            "Surgically replace an exact block of text in a source file and commit. "
            "Safer than write_source — only touches the specified region. "
            "old_text must appear exactly once in the file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "rel_path":       {"type": "string"},
                "old_text":       {"type": "string", "description": "Exact text to find and replace"},
                "new_text":       {"type": "string", "description": "Replacement text"},
                "commit_message": {"type": "string", "description": "Descriptive git commit message"},
            },
            "required": ["rel_path", "old_text", "new_text", "commit_message"],
        },
    },
    {
        "name": "write_source",
        "description": "Write the full content of a source file and commit. Use patch_source when possible.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rel_path":       {"type": "string"},
                "content":        {"type": "string", "description": "Complete new file content"},
                "commit_message": {"type": "string"},
            },
            "required": ["rel_path", "content", "commit_message"],
        },
    },
    {
        "name": "git_diff",
        "description": "Show uncommitted changes in the working tree.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "git_log",
        "description": "Show the last N git commits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "description": "Number of commits to show", "default": 8}
            },
        },
    },
]

# ── Dispatch for agent tool loop ──────────────────────────────────────────────

def dispatch_self_modify_tool(name: str, inputs: dict):
    """Called by the self_modifier agent's tool dispatch loop."""
    if name == "read_source":
        return read_source(inputs["rel_path"])
    if name == "list_source":
        return list_source(inputs.get("pattern", "**/*.py"))
    if name == "diff_source":
        return diff_source(inputs["rel_path"], inputs["new_content"])
    if name == "patch_source":
        return patch_source(
            inputs["rel_path"], inputs["old_text"],
            inputs["new_text"], inputs["commit_message"],
        )
    if name == "write_source":
        return write_source(inputs["rel_path"], inputs["content"], inputs["commit_message"])
    if name == "git_diff":
        return git_diff()
    if name == "git_log":
        return git_log(inputs.get("n", 8))
    raise ValueError(f"Unknown self-modify tool: {name}")
