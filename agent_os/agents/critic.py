"""Critic Agent — reviews outputs for quality, correctness, and alignment."""
from __future__ import annotations

import json

from .base import BaseAgent


class CriticAgent(BaseAgent):
    role = "critic"
    use_thinking = True
    default_max_tokens = 8192

    system_prompt = """You are the Critic agent in a multi-agent AI system called Dallas.
Your job: rigorously evaluate any output and provide actionable feedback.

Review dimensions:
1. **Correctness** — Is it factually accurate and logically consistent?
2. **Completeness** — Does it fully address the task? What's missing?
3. **Quality** — Is the code/plan/text clean, efficient, and maintainable?
4. **Safety** — Any risks, security issues, or harmful content?
5. **Alignment** — Does it match what the user actually asked for?

Always respond in this JSON format:
{
  "overall_score": 0.0-1.0,
  "passed": true|false,
  "dimensions": {
    "correctness": 0.0-1.0,
    "completeness": 0.0-1.0,
    "quality": 0.0-1.0,
    "safety": 0.0-1.0,
    "alignment": 0.0-1.0
  },
  "issues": ["specific problems found"],
  "strengths": ["what works well"],
  "recommendations": ["concrete improvements"],
  "approved": true|false
}

Be honest. A score of 0.9+ means near-perfect. Don't inflate scores.
"""

    def review(self, output: str, task: str, output_type: str = "general") -> dict:
        """Convenience method — calls run() and parses the critic JSON."""
        context = {"output_type": output_type, "output_to_review": output}
        result = self.run(task=f"Review this {output_type} output for the task: {task}", context=context)
        try:
            review_data = json.loads(result["output"])
            result["review"] = review_data
        except Exception:
            result["review"] = {
                "overall_score": 0.5,
                "passed": False,
                "issues": ["Could not parse critic response as JSON"],
                "approved": False,
            }
        return result
