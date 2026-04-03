"""Base agent class — all specialized agents inherit from this."""
from __future__ import annotations

import json
import os
from typing import Any

import anthropic


class BaseAgent:
    """
    Wraps a Claude API call with tool use, streaming, and adaptive thinking.
    Subclasses define role, system_prompt, and optionally override tools().
    """

    role: str = "base"
    system_prompt: str = "You are a helpful AI agent."
    default_max_tokens: int = 16000
    use_thinking: bool = False  # subclasses opt in

    def __init__(self, client: anthropic.Anthropic | None = None, model: str | None = None):
        self.client = client or anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model or self._resolve_model()

    def _resolve_model(self) -> str:
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "models.json")
        try:
            with open(cfg_path) as f:
                cfg = json.load(f)
            return cfg["agents"].get(self.role, cfg["default"])
        except Exception:
            return "claude-opus-4-6"

    def _thinking_params(self) -> dict:
        if not self.use_thinking:
            return {}
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "models.json")
        try:
            with open(cfg_path) as f:
                cfg = json.load(f)
            return {"thinking": cfg["thinking"].get(self.role, cfg["thinking"]["default"])}
        except Exception:
            return {"thinking": {"type": "adaptive"}}

    def tools(self) -> list[dict]:
        """Override in subclasses to declare Claude tool schemas."""
        return []

    def run(self, task: str, context: dict | None = None, history: list | None = None) -> dict:
        """
        Send a task to Claude and return structured result.

        Returns:
            {
                "agent": str,
                "output": str,
                "thinking": str | None,
                "tool_calls": list,
                "stop_reason": str,
            }
        """
        messages = list(history or [])
        prompt = self._build_prompt(task, context)
        messages.append({"role": "user", "content": prompt})

        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.default_max_tokens,
            "system": self.system_prompt,
            "messages": messages,
        }
        params.update(self._thinking_params())
        if self.tools():
            params["tools"] = self.tools()

        return self._agentic_loop(params)

    def _build_prompt(self, task: str, context: dict | None) -> str:
        if not context:
            return task
        ctx_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
        return f"## Context\n{ctx_str}\n\n## Task\n{task}"

    def _agentic_loop(self, params: dict) -> dict:
        """Run the tool-use loop until end_turn."""
        messages = list(params["messages"])
        thinking_text = None
        tool_calls_log: list[dict] = []

        while True:
            response = self.client.messages.create(**{**params, "messages": messages})

            # Collect thinking + text
            output_parts: list[str] = []
            for block in response.content:
                if block.type == "thinking":
                    thinking_text = block.thinking
                elif block.type == "text":
                    output_parts.append(block.text)

            if response.stop_reason == "end_turn":
                return {
                    "agent": self.role,
                    "output": "\n".join(output_parts),
                    "thinking": thinking_text,
                    "tool_calls": tool_calls_log,
                    "stop_reason": "end_turn",
                }

            if response.stop_reason != "tool_use":
                return {
                    "agent": self.role,
                    "output": "\n".join(output_parts),
                    "thinking": thinking_text,
                    "tool_calls": tool_calls_log,
                    "stop_reason": response.stop_reason,
                }

            # Handle tool calls
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self._dispatch_tool(block.name, block.input)
                    tool_calls_log.append({"name": block.name, "input": block.input, "result": result})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            messages.append({"role": "user", "content": tool_results})

    def _dispatch_tool(self, name: str, input_data: dict) -> Any:
        """Override or extend in subclasses to handle specific tools."""
        return f"Tool '{name}' not implemented in {self.role} agent."

    def stream_run(self, task: str, context: dict | None = None) -> str:
        """Stream the response and return full text."""
        prompt = self._build_prompt(task, context)
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.default_max_tokens,
            "system": self.system_prompt,
            "messages": [{"role": "user", "content": prompt}],
        }
        params.update(self._thinking_params())

        full_text = []
        with self.client.messages.stream(**params) as stream:
            for text in stream.text_stream:
                full_text.append(text)
                print(text, end="", flush=True)
        print()
        return "".join(full_text)
