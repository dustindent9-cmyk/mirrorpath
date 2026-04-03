"""OpenAI client wrapper — responses API, code interpreter, reasoning."""
from __future__ import annotations

import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def openai_reason(prompt: str, model: str = "gpt-4o") -> str:
    """Standard reasoning call via the Responses API."""
    response = client.responses.create(
        model=model,
        input=prompt,
    )
    return response.output_text


def openai_code_task(prompt: str, model: str = "gpt-4o") -> str:
    """Code task with code interpreter tool enabled."""
    response = client.responses.create(
        model=model,
        input=prompt,
        tools=[{"type": "code_interpreter"}],
    )
    return response.output_text


def openai_chat(
    system: str,
    prompt: str,
    model: str = "gpt-4o",
    max_tokens: int = 4096,
) -> str:
    """Chat completions API — compatible with older integrations."""
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content or ""
