"""Planner Agent — breaks complex tasks into ordered execution steps."""
from __future__ import annotations

import json

from .base import BaseAgent


class PlannerAgent(BaseAgent):
    role = "planner"
    use_thinking = True
    default_max_tokens = 16000

    system_prompt = """You are the Planner agent in a multi-agent AI system called Dallas.
Your sole responsibility: decompose any task into a clear, ordered execution plan.

Output format — always respond with this JSON structure:
{
  "goal": "one-sentence restatement of the task",
  "phases": [
    {
      "id": 1,
      "title": "Phase name",
      "agent": "researcher|coder|executor|browser_agent|memory_agent",
      "instructions": "what this agent should do",
      "depends_on": [],
      "expected_output": "what success looks like"
    }
  ],
  "success_criteria": ["measurable outcomes"],
  "risks": ["potential failure points"]
}

Rules:
- Assign each phase to the most appropriate agent role.
- Keep phases atomic — one agent, one clear objective.
- Order by dependency (things that must happen first come first).
- If the task is simple (< 3 steps), still use the JSON format.
"""

    def run(self, task: str, context: dict | None = None, history: list | None = None) -> dict:
        result = super().run(task, context, history)
        # Try to parse the output as a plan JSON
        try:
            plan = json.loads(result["output"])
            result["plan"] = plan
        except Exception:
            result["plan"] = None
        return result
