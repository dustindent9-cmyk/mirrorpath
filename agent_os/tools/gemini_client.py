"""Google Gemini client wrapper — text, vision, and video understanding."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def gemini_text(prompt: str, model: str = "gemini-2.5-pro") -> str:
    """Standard text generation."""
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return resp.text


def gemini_video_summary(
    video_uri: str,
    prompt: str = "Summarize this video and extract key lessons with timestamps.",
    model: str = "gemini-2.5-pro",
) -> str:
    """Video understanding — pass a Google Cloud Storage or YouTube URI."""
    resp = client.models.generate_content(
        model=model,
        contents=[
            {"file_data": {"file_uri": video_uri}},
            prompt,
        ],
    )
    return resp.text


def gemini_vision(image_path: str, prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Image understanding — pass a local file path."""
    import pathlib
    image_bytes = pathlib.Path(image_path).read_bytes()
    resp = client.models.generate_content(
        model=model,
        contents=[
            {"inline_data": {"mime_type": "image/png", "data": image_bytes}},
            prompt,
        ],
    )
    return resp.text


def gemini_long_context(document: str, prompt: str, model: str = "gemini-2.5-pro") -> str:
    """Long-context document analysis (Gemini 1M token window)."""
    resp = client.models.generate_content(
        model=model,
        contents=f"{document}\n\n{prompt}",
    )
    return resp.text
