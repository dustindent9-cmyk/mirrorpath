"""
Dallas — Multi-Agent OS
Entry point. Run: python main.py
"""
from __future__ import annotations

import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from orchestrator.router import Router
from tools.anthropic_client import claude_chat
from tools.openai_client import openai_reason, openai_code_task
from tools.gemini_client import gemini_text
from tools.browserbase_client import fetch_page
from tools.memory_store import remember_conversation_summary

_router = Router()

SYSTEM = """
You are Dallas, a multi-agent orchestrator.
Always:
- break work into steps
- let critic challenge assumptions
- let user_advocate protect user intent
- verify before finalizing
- save lasting lessons to memory
"""


def handle_task(task: str) -> str:
    """Route task to the correct provider and return result."""
    route = _router.route_to_provider(task)

    if route == "claude":
        result = claude_chat(SYSTEM, task)

    elif route == "openai":
        if "run code" in task.lower() or "debug" in task.lower():
            result = openai_code_task(task)
        else:
            result = openai_reason(task)

    elif route == "gemini":
        result = gemini_text(task)

    elif route == "browser":
        page = fetch_page(task) if task.startswith("http") else fetch_page("https://example.com")
        result = f"Browser fetch complete:\n{page}"

    else:
        result = claude_chat(SYSTEM, task)  # safe default

    remember_conversation_summary(f"Task: {task}\nResult summary: {result[:300]}")
    return result


def main() -> None:
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        print(handle_task(task))
        return

    print("\n╔══════════════════════════════════════╗")
    print("║         DALLAS  —  Agent OS          ║")
    print("╚══════════════════════════════════════╝\n")

    while True:
        try:
            user_task = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_task:
            continue
        if user_task.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        print(handle_task(user_task))


if __name__ == "__main__":
    main()
