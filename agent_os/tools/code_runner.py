"""Code runner — executes Python snippets in a subprocess sandbox."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


def run_code(code: str, timeout: int = 30) -> dict:
    """
    Execute Python code in a subprocess and return result.

    Returns:
        {
            "stdout": str,
            "stderr": str,
            "returncode": int,
            "error": str | None,
        }
    """
    # Write code to temp file so tracebacks have real line numbers
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(textwrap.dedent(code))
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Timed out after {timeout}s",
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": str(exc),
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def format_run_result(result: dict) -> str:
    """Format a run_code result as a human-readable string."""
    parts = []
    if result.get("stdout"):
        parts.append(f"STDOUT:\n{result['stdout']}")
    if result.get("stderr"):
        parts.append(f"STDERR:\n{result['stderr']}")
    if result.get("error"):
        parts.append(f"ERROR: {result['error']}")
    parts.append(f"Return code: {result['returncode']}")
    return "\n".join(parts) if parts else "No output."
