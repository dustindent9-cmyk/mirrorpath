"""
Verifier Agent — verification as a first-class agent, not just a utility.
Implements the full 6-step verification loop from skills/verification_loop.md.
"""
from __future__ import annotations

import json

from .base import BaseAgent
from ..tools.code_runner import run_code


# ── Lightweight standalone verifier (fast path) ──────────────────────────────

def verify_response(answer: str) -> dict:
    """
    Quick sanity-check before invoking the full VerifierAgent.
    Returns {"verified": bool, "issues": list[str]}.
    """
    issues: list[str] = []

    if len(answer.strip()) < 20:
        issues.append("Answer too short")

    if answer.strip().startswith("Error") or answer.strip().startswith("[Error"):
        issues.append("Answer begins with an error message")

    return {"verified": len(issues) == 0, "issues": issues}


class VerifierAgent(BaseAgent):
    role = "verifier_agent"
    use_thinking = True
    default_max_tokens = 8192

    system_prompt = """You are the Verifier agent in a multi-agent AI system called Dallas.
You run a rigorous 6-step verification loop on any output before it is delivered.

## Your 6-Step Verification Protocol

1. **Factual Correctness** — Are all claims verifiable and accurate?
2. **Logic Consistency** — Does reasoning flow without contradiction?
3. **Tool Outputs** — Did tools return expected results? Any errors?
4. **Code Execution** — If code is present, does it run? Use run_code to verify.
5. **Alternative Comparison** — Is there a simpler or more robust solution?
6. **Approve or Revise** — Score ≥ 0.85 → approve. Below → revise with specific issues.

## Scoring Rubric
- 0.95–1.0 : Excellent, ship it
- 0.85–0.94: Good, minor notes
- 0.70–0.84: Approve with caveats
- 0.50–0.69: Revise — specific issues must be fixed
- < 0.50   : Reject — fundamental problems

## Output Format (always JSON)
{
  "passed": true|false,
  "score": 0.0-1.0,
  "steps": {
    "factual": true|false,
    "logic": true|false,
    "tool_outputs": true|false,
    "code_runs": true|false,
    "alternatives_checked": true|false
  },
  "issues": ["specific problems"],
  "suggestions": ["concrete fixes"],
  "revised_output": "improved version or null"
}
"""

    def tools(self) -> list[dict]:
        return [
            {
                "name": "run_code",
                "description": "Execute Python code to verify it runs correctly.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "timeout": {"type": "integer", "default": 30},
                    },
                    "required": ["code"],
                },
            },
        ]

    def _dispatch_tool(self, name: str, input_data: dict):
        if name == "run_code":
            result = run_code(input_data["code"], input_data.get("timeout", 30))
            return (
                f"stdout: {result['stdout']}\n"
                f"stderr: {result['stderr']}\n"
                f"returncode: {result['returncode']}"
            )
        return super()._dispatch_tool(name, input_data)

    def verify(self, output: str, task: str, output_type: str = "general") -> dict:
        """Run the full verification loop. Returns structured result."""
        prompt = (
            f"## Original Task\n{task}\n\n"
            f"## Output Type\n{output_type}\n\n"
            f"## Output to Verify\n{output}\n\n"
            "Run all 6 verification steps and return your JSON verdict."
        )
        result = self.run(task=prompt)

        try:
            verdict = json.loads(result["output"])
            result["verdict"] = verdict
        except Exception:
            result["verdict"] = {
                "passed": False,
                "score": 0.4,
                "issues": ["Verifier response could not be parsed as JSON"],
                "suggestions": ["Re-run verification"],
                "revised_output": None,
            }
        return result

    def verify_with_retry(
        self,
        output: str,
        task: str,
        output_type: str = "general",
        max_retries: int = 3,
    ) -> dict:
        """Verify, and if failing, use revised_output for the next attempt."""
        best = None
        current = output

        for _ in range(max_retries):
            result = self.verify(current, task, output_type)
            verdict = result.get("verdict", {})
            score = verdict.get("score", 0)

            if best is None or score > best.get("verdict", {}).get("score", 0):
                best = result

            if verdict.get("passed") or score >= 0.85:
                return result

            revised = verdict.get("revised_output")
            if revised:
                current = revised
            else:
                break

        return best or result
