"""Web search tool — uses DuckDuckGo Instant Answer API (no key required)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request


def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo's instant answer API.
    Returns formatted results as a string.
    """
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Dallas-AgentOS/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        results = []

        # Abstract / instant answer
        if data.get("AbstractText"):
            results.append(f"Summary: {data['AbstractText']}")
            if data.get("AbstractURL"):
                results.append(f"Source: {data['AbstractURL']}")

        # Related topics
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                text = topic["Text"]
                url_link = topic.get("FirstURL", "")
                results.append(f"• {text}" + (f"\n  {url_link}" if url_link else ""))

        if not results:
            return f"No results found for: {query}"

        return f"Search results for '{query}':\n\n" + "\n\n".join(results[:num_results])

    except Exception as exc:
        return f"Search error for '{query}': {exc}"


def fetch_page(url: str, max_chars: int = 8000) -> str:
    """
    Fetch raw text from a URL (simple HTTP get, no JS rendering).
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Dallas-AgentOS/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode(errors="replace")
        # Very basic HTML strip
        import re
        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars] + ("..." if len(text) > max_chars else "")
    except Exception as exc:
        return f"Fetch error for {url}: {exc}"
