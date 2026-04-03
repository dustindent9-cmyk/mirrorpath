"""Executor Agent — carries out tasks: runs code, calls APIs, manages files."""
from __future__ import annotations

from .base import BaseAgent
from ..tools.file_tools import read_file, write_file, list_files
from ..tools.code_runner import run_code
from ..tools.api_caller import api_call


class ExecutorAgent(BaseAgent):
    role = "executor"
    use_thinking = False
    default_max_tokens = 16000

    system_prompt = """You are the Executor agent in a multi-agent AI system called Dallas.
Your job: take a concrete plan or instruction and execute it precisely.

Execution rules:
- Read files before modifying them.
- Run code only when explicitly asked or necessary to verify output.
- Log each action you take with a brief note.
- If an action fails, report the error clearly and suggest a fix — don't silently continue.
- Never execute destructive operations (delete, overwrite) without noting the impact.
- Complete the task fully. Don't stop partway.

After execution, summarize:
- What was done
- Files created/modified
- Any errors encountered
- Next recommended step (if any)
"""

    def tools(self) -> list[dict]:
        return [
            {
                "name": "run_code",
                "description": "Execute Python code and return output.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "timeout": {"type": "integer", "default": 30},
                    },
                    "required": ["code"],
                },
            },
            {
                "name": "read_file",
                "description": "Read a file.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write content to a file.",
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
                "name": "api_call",
                "description": "Make an HTTP API request.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                        "url": {"type": "string"},
                        "headers": {"type": "object", "default": {}},
                        "body": {"type": "object", "default": {}},
                        "timeout": {"type": "integer", "default": 30},
                    },
                    "required": ["method", "url"],
                },
            },
        ]

    def _dispatch_tool(self, name: str, input_data: dict):
        if name == "run_code":
            return run_code(input_data["code"], input_data.get("timeout", 30))
        if name == "read_file":
            return read_file(input_data["path"])
        if name == "write_file":
            return write_file(input_data["path"], input_data["content"])
        if name == "list_files":
            return list_files(input_data.get("directory", "."), input_data.get("pattern", "*"))
        if name == "api_call":
            return api_call(
                method=input_data["method"],
                url=input_data["url"],
                headers=input_data.get("headers", {}),
                body=input_data.get("body", {}),
                timeout=input_data.get("timeout", 30),
            )
        return super()._dispatch_tool(name, input_data)
