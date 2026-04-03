"""
Consensus System — synthesizes agreement across multiple agent outputs.
When agents disagree, uses a meta-Claude call to arbitrate.

Scoring (Dustin's spec):
  confidence > 0.7  → +1
  no errors         → +1
  aligned_with_user → +1
Best score wins.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import anthropic


def score_responses(responses: list[dict]) -> dict:
    """
    Score agent response dicts and return the highest-scoring one.
    Each response dict may contain: confidence (float), errors (list), aligned_with_user (bool).
    """
    scored = []
    for r in responses:
        score = 0
        if r.get("confidence", 0) > 0.7:
            score += 1
        if not r.get("errors"):
            score += 1
        if r.get("aligned_with_user"):
            score += 1
        scored.append((score, r))
    scored.sort(reverse=True)
    return scored[0][1] if scored else {}

from .mcp import AgentResult


@dataclass
class ConsensusResult:
    agreed: bool
    synthesis: str
    dissenting_agents: list[str]
    confidence: float  # 0.0 – 1.0
    arbitration_used: bool = False


class ConsensusEngine:
    """
    Takes outputs from multiple agents and determines if they agree.
    If not, calls Claude to arbitrate and produce a synthesized answer.
    """

    SYNTHESIS_SYSTEM = """You are a consensus arbitrator for a multi-agent AI system.
You receive outputs from several specialized AI agents that all worked on the same task.
Your job:
1. Identify where agents agree and where they diverge.
2. Synthesize the best possible answer, drawing on each agent's strengths.
3. Note any unresolved disagreements clearly.
4. Be concise and direct — output the final synthesized answer, not meta-commentary.
"""

    def __init__(self, client: anthropic.Anthropic | None = None, model: str = "claude-opus-4-6"):
        self.client = client or anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def evaluate(self, results: list[AgentResult], task: str) -> ConsensusResult:
        """
        Evaluate agreement across agent results.
        If only one result, return it directly (trivial consensus).
        """
        if not results:
            return ConsensusResult(agreed=True, synthesis="No agent results.", dissenting_agents=[], confidence=0.0)

        if len(results) == 1:
            return ConsensusResult(
                agreed=True,
                synthesis=results[0].output,
                dissenting_agents=[],
                confidence=1.0,
            )

        # Filter out errors
        valid = [r for r in results if r.stop_reason != "error"]
        if not valid:
            return ConsensusResult(
                agreed=False,
                synthesis="All agents encountered errors.",
                dissenting_agents=[r.agent for r in results],
                confidence=0.0,
            )

        # Check semantic agreement (simple heuristic: overlap in key phrases)
        similarity = self._estimate_similarity(valid)
        if similarity >= 0.7:
            # Sufficient agreement — use the most complete output
            best = max(valid, key=lambda r: len(r.output))
            return ConsensusResult(
                agreed=True,
                synthesis=best.output,
                dissenting_agents=[],
                confidence=similarity,
            )

        # Disagreement — arbitrate with Claude
        synthesis = self._arbitrate(valid, task)
        dissenting = [r.agent for r in valid if r.output not in synthesis]
        return ConsensusResult(
            agreed=False,
            synthesis=synthesis,
            dissenting_agents=dissenting,
            confidence=0.6,
            arbitration_used=True,
        )

    def _estimate_similarity(self, results: list[AgentResult]) -> float:
        """
        Rough word-overlap similarity between all result pairs.
        Returns average Jaccard similarity.
        """
        if len(results) < 2:
            return 1.0
        scores = []
        texts = [set(r.output.lower().split()) for r in results]
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                a, b = texts[i], texts[j]
                if not a and not b:
                    scores.append(1.0)
                elif not a or not b:
                    scores.append(0.0)
                else:
                    scores.append(len(a & b) / len(a | b))
        return sum(scores) / len(scores) if scores else 1.0

    def _arbitrate(self, results: list[AgentResult], task: str) -> str:
        """Call Claude to synthesize divergent agent outputs."""
        agent_block = "\n\n".join(
            f"## Agent: {r.agent}\n{r.output}" for r in results
        )
        prompt = (
            f"## Original Task\n{task}\n\n"
            f"## Agent Outputs\n{agent_block}\n\n"
            "Synthesize the best answer from these agent outputs."
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=self.SYNTHESIS_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if block.type == "text":
                return block.text
        return "Arbitration produced no output."
