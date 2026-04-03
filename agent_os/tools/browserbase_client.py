"""Browserbase client — cloud browser sessions via Browserbase API."""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

API_KEY    = os.getenv("BROWSERBASE_API_KEY")
PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
BASE_URL   = "https://api.browserbase.com/v1"

HEADERS = {
    "x-bb-api-key": API_KEY,
    "Content-Type": "application/json",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def create_session() -> dict:
    """Create a new cloud browser session. Returns session metadata including id."""
    url = f"{BASE_URL}/sessions"
    r = requests.post(url, headers=HEADERS, json={"projectId": PROJECT_ID}, timeout=30)
    r.raise_for_status()
    return r.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_page(url_to_fetch: str) -> dict:
    """Fetch a page via Browserbase (JS-rendered, no local browser needed)."""
    url = f"{BASE_URL}/fetches"
    r = requests.post(
        url,
        headers=HEADERS,
        json={"projectId": PROJECT_ID, "url": url_to_fetch},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def list_sessions() -> list[dict]:
    """List all sessions for this project."""
    url = f"{BASE_URL}/sessions?projectId={PROJECT_ID}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def stop_session(session_id: str) -> dict:
    """Stop a running browser session."""
    url = f"{BASE_URL}/sessions/{session_id}"
    r = requests.delete(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def get_session_recording(session_id: str) -> dict:
    """Retrieve recording metadata for a completed session."""
    url = f"{BASE_URL}/sessions/{session_id}/recording"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()
