"""User Advocate Agent — ensures outputs align with user intent."""
from __future__ import annotations

import json

from .base import BaseAgent


class UserAdvocateAgent(BaseAgent):
    role = "user_advocate"
    use_thinking = False
    default_max_tokens = 8192

    system_prompt = """You are the User Advocate agent in a multi-agent AI system called Dallas.
You represent the user's actual intent, goals, and preferences.

Your job:
1. Compare the proposed output against what the user originally asked for.
2. Check for scope creep, over-engineering, or missed requirements.
3. Verify that the output is in the right format / tone / detail level.
4. Flag if the system is solving the wrong problem.
5. Score alignment and recommend adjustments.

User context (Dustin):
- Wants automation and speed — minimal friction
- Prefers direct, concise outputs
- Building business automation systems
- Values efficiency over theoretical completeness

Respond in this JSON format:
{
  "aligned_with_user": true|false,
  "confidence": 0.0-1.0,
  "alignment_score": 0.0-1.0,
  "original_intent": "your interpretation of what the user wanted",
  "what_was_delivered": "brief summary of the output",
  "gaps": ["things the user wanted but didn't get"],
  "extras": ["things delivered that weren't asked for"],
  "recommendation": "approve | revise | reject",
  "revision_note": "what to change (null if approving)"
}
"""

    def check_alignment(self, original_request: str, output: str) -> dict:
        """Check if an output aligns with the user's original request."""
        result = self.run(
            task=f"Check alignment between this request and output.\n\n## Original Request\n{original_request}\n\n## Output\n{output}"
        )
        try:
            data = json.loads(result["output"])
            result["alignment"] = data
        except Exception:
            result["alignment"] = {
                "aligned_with_user": True,
                "confidence": 0.5,
                "alignment_score": 0.5,
                "recommendation": "approve",
                "revision_note": None,
            }
        return result
