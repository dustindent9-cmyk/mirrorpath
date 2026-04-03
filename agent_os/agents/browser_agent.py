"""Browser Agent — navigates web pages and extracts information."""
from __future__ import annotations

from .base import BaseAgent
from ..tools.browser_control import BrowserController


class BrowserAgent(BaseAgent):
    role = "browser_agent"
    use_thinking = False
    default_max_tokens = 16000

    system_prompt = """You are the Browser Agent in a multi-agent AI system called Dallas.
Your job: navigate websites, extract information, and interact with web UIs.

Capabilities:
- Navigate to URLs and read page content.
- Click elements, fill forms, submit data.
- Extract structured data from pages.
- Take screenshots for visual verification.

Guidelines:
- Always navigate to the URL first before attempting interactions.
- Extract only relevant content — don't dump entire pages.
- Report clearly what you found and what actions you took.
- If a page requires authentication you don't have, report it immediately.
- Respect robots.txt and don't scrape at high frequency.
"""

    def __init__(self, *args, headless: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self._headless = headless
        self._browser: BrowserController | None = None

    def _get_browser(self) -> BrowserController:
        if self._browser is None:
            self._browser = BrowserController(headless=self._headless)
        return self._browser

    def tools(self) -> list[dict]:
        return [
            {
                "name": "navigate",
                "description": "Navigate to a URL and return page content.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "wait_for": {"type": "string", "description": "CSS selector to wait for", "default": ""},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "click",
                "description": "Click an element by CSS selector.",
                "input_schema": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"],
                },
            },
            {
                "name": "fill",
                "description": "Fill a form field.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["selector", "value"],
                },
            },
            {
                "name": "extract_text",
                "description": "Extract visible text from a CSS selector.",
                "input_schema": {
                    "type": "object",
                    "properties": {"selector": {"type": "string", "default": "body"}},
                },
            },
            {
                "name": "screenshot",
                "description": "Take a screenshot and return the file path.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "default": "/tmp/screenshot.png"}},
                },
            },
        ]

    def _dispatch_tool(self, name: str, input_data: dict):
        browser = self._get_browser()
        if name == "navigate":
            return browser.navigate(input_data["url"], input_data.get("wait_for", ""))
        if name == "click":
            return browser.click(input_data["selector"])
        if name == "fill":
            return browser.fill(input_data["selector"], input_data["value"])
        if name == "extract_text":
            return browser.extract_text(input_data.get("selector", "body"))
        if name == "screenshot":
            return browser.screenshot(input_data.get("path", "/tmp/screenshot.png"))
        return super()._dispatch_tool(name, input_data)

    def close(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
