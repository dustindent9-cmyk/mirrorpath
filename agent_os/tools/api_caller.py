"""Generic HTTP API caller — requests + tenacity retry."""
from __future__ import annotations

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def api_call(
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    json: dict | None = None,
    timeout: int = 30,
):
    """
    Make an HTTP request with automatic retry (3 attempts, exponential backoff).
    Returns parsed JSON if Content-Type is application/json, else raw text.
    Raises on 4xx/5xx after all retries exhausted.
    """
    r = requests.request(
        method=method.upper(),
        url=url,
        headers=headers or {},
        params=params or {},
        json=json,
        timeout=timeout,
    )
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "application/json" in ctype:
        return r.json()
    return r.text
