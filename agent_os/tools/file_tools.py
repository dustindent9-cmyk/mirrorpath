"""File system tools — read, write, list files."""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path


def read_file(path: str) -> str:
    """Read and return file contents. Returns error string on failure."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"Error: file not found: {path}"
        if p.stat().st_size > 10 * 1024 * 1024:  # 10 MB cap
            return f"Error: file too large to read (> 10 MB): {path}"
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Error reading {path}: {exc}"


def write_file(path: str, content: str) -> str:
    """Write content to file, creating parent dirs as needed."""
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written: {path} ({len(content)} chars)"
    except Exception as exc:
        return f"Error writing {path}: {exc}"


def append_file(path: str, content: str) -> str:
    """Append content to a file."""
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended to: {path}"
    except Exception as exc:
        return f"Error appending to {path}: {exc}"


def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List files matching a glob pattern in directory."""
    try:
        d = Path(directory).expanduser()
        if not d.exists():
            return f"Error: directory not found: {directory}"
        matches = [
            str(p.relative_to(d))
            for p in sorted(d.rglob(pattern))
            if p.is_file()
        ]
        if not matches:
            return f"No files matching '{pattern}' in {directory}"
        return "\n".join(matches)
    except Exception as exc:
        return f"Error listing {directory}: {exc}"


def delete_file(path: str) -> str:
    """Delete a file (non-recursive). Returns confirmation."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"Not found: {path}"
        p.unlink()
        return f"Deleted: {path}"
    except Exception as exc:
        return f"Error deleting {path}: {exc}"


def file_exists(path: str) -> bool:
    return Path(path).expanduser().exists()
