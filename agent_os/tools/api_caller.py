"""
Generic HTTP API caller.
Uses `requests` if installed, falls back to urllib.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


def api_call(
    method: str,
    url: str,
    headers: dict | None = None,
    body: dict | Any | None = None,
    timeout: int = 30,
) -> dict:
    """
    Make an HTTP request.

    Returns:
        {
            "status": int,
            "headers": dict,
            "body": str,
            "json": dict | None,
            "error": str | None,
        }
    """
    headers = headers or {}
    if "Content-Type" not in headers and body:
        headers["Content-Type"] = "application/json"
    if "User-Agent" not in headers:
        headers["User-Agent"] = "Dallas-AgentOS/1.0"

    data = None
    if body and method.upper() != "GET":
        data = json.dumps(body).encode("utf-8") if isinstance(body, dict) else str(body).encode()

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method.upper(),
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_body = resp.read().decode("utf-8", errors="replace")
            resp_headers = dict(resp.headers)
            status = resp.status

        parsed_json = None
        try:
            parsed_json = json.loads(raw_body)
        except Exception:
            pass

        return {
            "status": status,
            "headers": resp_headers,
            "body": raw_body[:4096],
            "json": parsed_json,
            "error": None,
        }
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return {
            "status": exc.code,
            "headers": {},
            "body": body_text[:2048],
            "json": None,
            "error": f"HTTP {exc.code}: {exc.reason}",
        }
    except Exception as exc:
        return {
            "status": 0,
            "headers": {},
            "body": "",
            "json": None,
            "error": str(exc),
        }
