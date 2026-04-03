"""File system tools — read, write, append, list, delete."""
from __future__ import annotations

from pathlib import Path


def read_file(path: str) -> str:
    """Read and return file contents."""
    return Path(path).read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    """Write content to file, creating parent directories as needed."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")
    return f"Written: {path} ({len(content)} chars)"


def append_file(path: str, content: str) -> str:
    """Append content to a file, creating it if needed."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)
    return f"Appended to: {path}"


def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List files matching a glob pattern in directory."""
    d = Path(directory)
    if not d.exists():
        return f"Directory not found: {directory}"
    matches = sorted(str(p.relative_to(d)) for p in d.rglob(pattern) if p.is_file())
    return "\n".join(matches) if matches else f"No files matching '{pattern}' in {directory}"


def delete_file(path: str) -> str:
    """Delete a file."""
    p = Path(path)
    if not p.exists():
        return f"Not found: {path}"
    p.unlink()
    return f"Deleted: {path}"


def file_exists(path: str) -> bool:
    return Path(path).exists()
