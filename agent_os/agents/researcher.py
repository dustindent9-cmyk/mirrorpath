"""Researcher Agent — gathers information using web search and knowledge retrieval."""
from __future__ import annotations

from .base import BaseAgent
from ..tools.web_search import web_search
from ..tools.file_tools import read_file


class ResearcherAgent(BaseAgent):
    role = "researcher"
    use_thinking = False
    default_max_tokens = 16000

    system_prompt = """You are the Researcher agent in a multi-agent AI system called Dallas.
Your job: gather accurate, relevant information to support the task.

Guidelines:
- Use the web_search tool to find current information.
- Use read_file to access local documents when relevant.
- Synthesize findings into a clear, structured summary.
- Cite sources where possible.
- Flag uncertainty explicitly — never fabricate facts.
- Be thorough but concise. Prioritize actionable findings.
"""

    def tools(self) -> list[dict]:
        return [
            {
                "name": "web_search",
                "description": "Search the web for current information on a topic.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "num_results": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "read_file",
                "description": "Read the contents of a local file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to read"},
                    },
                    "required": ["path"],
                },
            },
        ]

    def _dispatch_tool(self, name: str, input_data: dict):
        if name == "web_search":
            return web_search(input_data["query"], input_data.get("num_results", 5))
        if name == "read_file":
            return read_file(input_data["path"])
        return super()._dispatch_tool(name, input_data)
