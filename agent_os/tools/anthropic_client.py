"""Anthropic client wrapper — streaming, retry, adaptive thinking."""
from __future__ import annotations

import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def claude_chat(
    system: str,
    prompt: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 16000,
    thinking: bool = False,
) -> str:
    """Single-turn Claude call. Returns text output."""
    params: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    if thinking:
        params["thinking"] = {"type": "adaptive"}

    resp = client.messages.create(**params)
    parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def claude_stream(
    system: str,
    prompt: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> str:
    """Streaming Claude call — prints tokens as they arrive, returns full text."""
    full_text: list[str] = []
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text.append(text)
    print()
    return "".join(full_text)


def claude_with_tools(
    system: str,
    prompt: str,
    tools: list[dict],
    model: str = "claude-opus-4-6",
    max_tokens: int = 16000,
) -> dict:
    """Claude call with tool use. Returns full response dict."""
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=tools,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "content": resp.content,
        "stop_reason": resp.stop_reason,
        "usage": resp.usage,
    }
