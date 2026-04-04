"""OpenAI client wrapper — chat completions, compatible with any OpenAI-spec endpoint."""
from __future__ import annotations

import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_kwargs: dict = {"api_key": os.getenv("OPENAI_API_KEY")}
if os.getenv("OPENAI_BASE_URL"):
    _kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")

client = OpenAI(**_kwargs)

_DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def openai_reason(prompt: str, model: str | None = None) -> str:
    """Reasoning call via Chat Completions — works with any OpenAI-compatible endpoint."""
    resp = client.chat.completions.create(
        model=model or _DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def openai_code_task(prompt: str, model: str | None = None) -> str:
    """Code task via Chat Completions — system prompt primes for code output."""
    resp = client.chat.completions.create(
        model=model or _DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "You are an expert software engineer. Return clean, working code with brief explanation."},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content or ""


def openai_chat(
    system: str,
    prompt: str,
    model: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Chat completions with explicit system prompt."""
    resp = client.chat.completions.create(
        model=model or _DEFAULT_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content or ""
