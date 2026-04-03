"""Browser control — wraps Playwright for headless web automation.
Also provides lightweight tab-opener utilities via webbrowser (no Playwright needed).
"""
from __future__ import annotations

import webbrowser
from pathlib import Path


# ── Lightweight tab helpers (no Playwright required) ────────────────────────

def open_tab(url: str) -> None:
    """Open a URL in the user's default browser."""
    webbrowser.open(url)


def open_multiple(urls: list[str]) -> None:
    """Open each URL in a new browser tab."""
    for url in urls:
        webbrowser.open_new_tab(url)


class BrowserController:
    """
    Thin wrapper around Playwright for browser automation.
    Falls back to HTTP-only mode if Playwright is not installed.
    """

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._page = None
        self._browser = None
        self._playwright = None
        self._fallback_mode = False
        self._init()

    def _init(self) -> None:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
            self._pw = sync_playwright().__enter__()
            self._browser = self._pw.chromium.launch(headless=self._headless)
            self._page = self._browser.new_page()
            self._page.set_extra_http_headers({"User-Agent": "Dallas-AgentOS/1.0"})
        except ImportError:
            self._fallback_mode = True
        except Exception:
            self._fallback_mode = True

    def navigate(self, url: str, wait_for: str = "") -> str:
        """Navigate to URL and return page text."""
        if self._fallback_mode:
            return self._http_get(url)
        try:
            self._page.goto(url, timeout=30000)
            if wait_for:
                self._page.wait_for_selector(wait_for, timeout=10000)
            return self._page.inner_text("body")[:8000]
        except Exception as exc:
            return f"Navigation error: {exc}"

    def click(self, selector: str) -> str:
        if self._fallback_mode:
            return "Browser not available (Playwright not installed)"
        try:
            self._page.click(selector)
            return f"Clicked: {selector}"
        except Exception as exc:
            return f"Click error: {exc}"

    def fill(self, selector: str, value: str) -> str:
        if self._fallback_mode:
            return "Browser not available"
        try:
            self._page.fill(selector, value)
            return f"Filled {selector} with value"
        except Exception as exc:
            return f"Fill error: {exc}"

    def extract_text(self, selector: str = "body") -> str:
        if self._fallback_mode:
            return "Browser not available"
        try:
            return self._page.inner_text(selector)[:6000]
        except Exception as exc:
            return f"Extract error: {exc}"

    def screenshot(self, path: str = "/tmp/screenshot.png") -> str:
        if self._fallback_mode:
            return "Browser not available"
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._page.screenshot(path=path)
            return f"Screenshot saved: {path}"
        except Exception as exc:
            return f"Screenshot error: {exc}"

    def close(self) -> None:
        try:
            if self._browser:
                self._browser.close()
            if hasattr(self, "_pw") and self._pw:
                self._pw.__exit__(None, None, None)
        except Exception:
            pass

    @staticmethod
    def _http_get(url: str) -> str:
        """Fallback plain HTTP fetch."""
        import re
        import urllib.request
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Dallas-AgentOS/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:8000]
        except Exception as exc:
            return f"HTTP fetch error: {exc}"
