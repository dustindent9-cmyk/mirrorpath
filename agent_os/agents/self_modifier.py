"""
SelfModifierAgent — lets Dallas edit its own source code at Dustin's command.

The agent:
  1. Reads the relevant source file(s) to understand what's there
  2. Plans the exact change needed
  3. Uses patch_source (surgical) or write_source (full rewrite) to apply it
  4. Commits the change to git with a descriptive message
  5. Returns a summary with the diff

Requires DALLAS_SELF_MODIFY=true in .env.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .base import BaseAgent
from tools.self_modify import (
    SELF_MODIFY_TOOLS,
    dispatch_self_modify_tool,
)


SYSTEM = """\
You are the SelfModifier agent for Dallas, a personal AI assistant owned by Dustin.

Your job: modify Dallas's own source code when Dustin explicitly asks you to.

Workflow you MUST follow:
1. Use list_source to find the relevant file(s) if you don't know the path
2. Use read_source to read the current content of the file
3. Plan the minimal, surgical change that achieves what Dustin wants
4. Use patch_source for targeted changes (preferred — safer)
   OR write_source only if you need to rewrite more than ~40% of the file
5. Write a clear commit_message describing WHAT changed and WHY
6. Report back: what file was changed, a summary of the diff, and the commit message

Rules:
- Make only the change Dustin asked for. Do not refactor unrelated code.
- Preserve all existing imports, docstrings, and formatting style.
- If the change could break something, mention it clearly.
- If you are unsure which file to edit, read multiple files before deciding.
- Protected files (.env, claude.md, config/permissions.json) cannot be modified.
- If DALLAS_SELF_MODIFY is not enabled, explain that to Dustin and show what the change would look like without applying it.
"""


class SelfModifierAgent(BaseAgent):
    role = "self_modifier"
    system_prompt = SYSTEM
    default_max_tokens = 32000
    use_thinking = True

    def tools(self) -> list[dict]:
        return SELF_MODIFY_TOOLS

    def _dispatch_tool(self, name: str, input_data: dict) -> Any:
        try:
            result = dispatch_self_modify_tool(name, input_data)
            # For dicts, return pretty JSON so Claude can read it clearly
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
        except PermissionError as e:
            return f"[PERMISSION DENIED] {e}"
        except FileNotFoundError as e:
            return f"[NOT FOUND] {e}"
        except ValueError as e:
            return f"[ERROR] {e}"
        except Exception as e:
            return f"[UNEXPECTED ERROR] {type(e).__name__}: {e}"

    def run(self, task: str, context: dict | None = None, history: list | None = None) -> dict:
        enabled = os.environ.get("DALLAS_SELF_MODIFY", "").lower() == "true"
        ctx = dict(context or {})
        ctx["self_modify_enabled"] = str(enabled)
        ctx["agent_os_root"] = "agent_os/"
        return super().run(task=task, context=ctx, history=history)


# ── Convenience function ──────────────────────────────────────────────────────

_agent: SelfModifierAgent | None = None

def self_modify(instruction: str) -> str:
    """
    Run a self-modification instruction and return a text summary.

    Example:
        result = self_modify(
            "Add 'real estate' to the router so it routes to the researcher agent"
        )
        print(result)
    """
    global _agent
    if _agent is None:
        _agent = SelfModifierAgent()
    result = _agent.run(instruction)
    return result.get("output", "")
