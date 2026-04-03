"""
Verification Loop — validates agent outputs for correctness and safety.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import anthropic


@dataclass
class VerificationResult:
    passed: bool
    score: float          # 0.0 – 1.0
    issues: list[str]
    suggestions: list[str]
    revised_output: str | None = None


class Verifier:
    """
    Runs a second-pass verification on agent outputs.
    Checks for correctness, completeness, safety, and alignment.
    """

    VERIFIER_SYSTEM = """You are a strict verification agent in a multi-agent AI system.
Your job: critically review the output below and determine if it is:
1. Correct — factually accurate and logically sound
2. Complete — fully addresses the original task
3. Safe — contains no harmful instructions or content
4. Actionable — can be directly used without further clarification

Respond in this exact JSON format (no markdown fences):
{
  "passed": true|false,
  "score": 0.0-1.0,
  "issues": ["list of specific problems, empty if none"],
  "suggestions": ["list of concrete improvements, empty if none"],
  "revised_output": "improved version if score < 0.8, else null"
}"""

    def __init__(self, client: anthropic.Anthropic | None = None, model: str = "claude-opus-4-6"):
        self.client = client or anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def verify(self, output: str, task: str, output_type: str = "general") -> VerificationResult:
        """
        Verify an output against its original task.

        Args:
            output: The agent output to verify.
            task: The original task that produced this output.
            output_type: hint for domain-specific checks (code, plan, research, general).
        """
        prompt = (
            f"## Original Task\n{task}\n\n"
            f"## Output Type\n{output_type}\n\n"
            f"## Output to Verify\n{output}"
        )

        import json as _json
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self.VERIFIER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = ""
        for block in response.content:
            if block.type == "text":
                raw = block.text
                break

        try:
            data = _json.loads(raw)
            return VerificationResult(
                passed=bool(data.get("passed", False)),
                score=float(data.get("score", 0.0)),
                issues=list(data.get("issues", [])),
                suggestions=list(data.get("suggestions", [])),
                revised_output=data.get("revised_output"),
            )
        except Exception:
            # Fallback if JSON parsing fails
            passed = "passed" in raw.lower() and "true" in raw.lower()
            return VerificationResult(
                passed=passed,
                score=0.7 if passed else 0.3,
                issues=["Verification response was not parseable JSON."],
                suggestions=["Re-run verification."],
                revised_output=None,
            )

    def verify_with_retry(
        self,
        output: str,
        task: str,
        output_type: str = "general",
        max_retries: int = 3,
    ) -> VerificationResult:
        """
        Verify and auto-revise until passing or retries exhausted.
        Returns the best result seen.
        """
        best: VerificationResult | None = None
        current_output = output

        for attempt in range(max_retries):
            result = self.verify(current_output, task, output_type)
            if best is None or result.score > best.score:
                best = result
            if result.passed or result.score >= 0.85:
                return result
            if result.revised_output:
                current_output = result.revised_output
            else:
                break  # no revision produced, stop retrying

        return best or VerificationResult(passed=False, score=0.0, issues=["Verification failed."], suggestions=[])
