"""Coder Agent — writes, fixes, and refactors code."""
from __future__ import annotations

from .base import BaseAgent
from ..tools.file_tools import read_file, write_file, list_files
from ..tools.code_runner import run_code


class CoderAgent(BaseAgent):
    role = "coder"
    use_thinking = True
    default_max_tokens = 32000

    system_prompt = """You are the Coder agent in a multi-agent AI system called Dallas.
Your job: write clean, correct, production-quality code.

Standards:
- Write idiomatic, readable code with meaningful names.
- Handle errors gracefully — never swallow exceptions silently.
- Add brief comments only where logic isn't obvious.
- Test your logic mentally before returning it.
- Use run_code to verify snippets when appropriate.
- Read existing files before modifying them.
- After writing, always state: file written, language, and a one-line summary.

You produce code that works the first time.
"""

    def tools(self) -> list[dict]:
        return [
            {
                "name": "read_file",
                "description": "Read an existing source file.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write code to a file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "list_files",
                "description": "List files in a directory.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "default": "."},
                        "pattern": {"type": "string", "default": "*"},
                    },
                },
            },
            {
                "name": "run_code",
                "description": "Execute a Python snippet and return stdout/stderr.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python code to run"},
                        "timeout": {"type": "integer", "default": 30},
                    },
                    "required": ["code"],
                },
            },
        ]

    def _dispatch_tool(self, name: str, input_data: dict):
        if name == "read_file":
            return read_file(input_data["path"])
        if name == "write_file":
            return write_file(input_data["path"], input_data["content"])
        if name == "list_files":
            return list_files(input_data.get("directory", "."), input_data.get("pattern", "*"))
        if name == "run_code":
            return run_code(input_data["code"], input_data.get("timeout", 30))
        return super()._dispatch_tool(name, input_data)
