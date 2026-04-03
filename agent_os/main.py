"""
Dallas — Multi-Agent OS
Entry point. Run with: python main.py
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import anthropic

from agents import (
    PlannerAgent, CoderAgent, ResearcherAgent, CriticAgent,
    ExecutorAgent, MemoryAgent, UserAdvocateAgent, BrowserAgent,
)
from orchestrator import MultiModelControlPlane, ConsensusEngine, Verifier
from orchestrator.consensus import ConsensusResult
from orchestrator.mcp import AgentResult


# ── Consensus scoring (Dustin's spec) ──────────────────────────────────────

def score_responses(responses: list[dict]) -> dict:
    """
    Score agent responses and return the best one.
    scoring: confidence > 0.7 (+1), no errors (+1), aligned_with_user (+1)
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


# ── Verification loop (Dustin's spec) ──────────────────────────────────────

def verification_loop(output: str, task: str, verifier: Verifier, max_retries: int = 3) -> str:
    """
    1. Check factual correctness
    2. Check logic consistency
    3. Check tool outputs
    4. Run code if applicable
    5. Compare against alternatives
    6. Approve or revise
    """
    result = verifier.verify_with_retry(output, task, max_retries=max_retries)
    if result.passed:
        return result.revised_output or output
    # Return best version with issues noted
    issues = "; ".join(result.issues) if result.issues else "verification failed"
    note = f"\n\n⚠️  Verification issues (score {result.score:.2f}): {issues}"
    return (result.revised_output or output) + note


# ── Main agent loop (Dustin's spec) ────────────────────────────────────────

class DallasAgentLoop:
    """
    Full agent loop:
    1. Receive user input
    2. Planner breaks task into steps
    3. Assign to agents (researcher / coder / executor)
    4. Critic reviews
    5. User Advocate checks alignment
    6. Verifier validates
    7. Consensus resolves disagreements
    8. Memory Agent stores learnings
    9. Return final answer
    """

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("⚠️  ANTHROPIC_API_KEY not set. Set it in .env or environment.")

        self.client = anthropic.Anthropic(api_key=api_key)

        # Instantiate all agents
        self.planner       = PlannerAgent(self.client)
        self.researcher    = ResearcherAgent(self.client)
        self.coder         = CoderAgent(self.client)
        self.critic        = CriticAgent(self.client)
        self.executor      = ExecutorAgent(self.client)
        self.memory        = MemoryAgent(self.client)
        self.user_advocate = UserAdvocateAgent(self.client)
        self.browser       = BrowserAgent(self.client)
        self.verifier      = Verifier(self.client)
        self.consensus     = ConsensusEngine(self.client)

        # Register agents with MCP
        self.mcp = MultiModelControlPlane()
        for role, agent in {
            "planner":       self.planner,
            "researcher":    self.researcher,
            "coder":         self.coder,
            "critic":        self.critic,
            "executor":      self.executor,
            "memory_agent":  self.memory,
            "user_advocate": self.user_advocate,
            "browser_agent": self.browser,
        }.items():
            self.mcp.register(role, agent)

        self._session_log: list[dict] = []

    def run(self, task: str) -> str:
        """Execute the full agent loop for a task."""
        print(f"\n{'='*60}")
        print(f"DALLAS  |  Task: {task[:80]}")
        print(f"{'='*60}\n")

        # ── Step 1: Reverse prompting pre-flight ──────────────────────────
        # (agents do this internally; logged here)
        self._log("input", {"task": task})

        # ── Step 2: Plan ──────────────────────────────────────────────────
        print("🗺  Planning...")
        plan_result = self.planner.run(task=task)
        plan = plan_result.get("plan")
        self._log("plan", plan_result)

        # ── Step 3: Route to agents ───────────────────────────────────────
        if plan and plan.get("phases"):
            results = self._execute_plan(plan, task)
        else:
            # Fallback: auto-route by task keywords
            print("📡  Auto-routing...")
            roles = self.mcp.route(task)
            results = self.mcp.dispatch(task=task, roles=roles)

        # ── Step 4: Critic review ─────────────────────────────────────────
        print("🔍  Critic reviewing...")
        if results:
            primary_output = results[-1].output  # Last agent's output
            critic_result = self.critic.review(
                output=primary_output,
                task=task,
                output_type=self._detect_output_type(primary_output),
            )
            review = critic_result.get("review", {})
            score = review.get("overall_score", 0.5)
            print(f"   Critic score: {score:.2f}")
            self._log("critic", critic_result)

            if score < 0.7:
                print(f"   ⚠️  Score {score:.2f} — requesting revision...")
                roles = self.mcp.route(task)
                context = {"critic_feedback": json.dumps(review)}
                results = self.mcp.dispatch(task=task, roles=roles, context=context)
                primary_output = results[-1].output if results else primary_output
        else:
            primary_output = "No agent output produced."

        # ── Step 5: User Advocate alignment check ─────────────────────────
        print("👤  Checking user alignment...")
        advocate_result = self.user_advocate.check_alignment(task, primary_output)
        alignment = advocate_result.get("alignment", {})
        aligned = alignment.get("aligned_with_user", True)
        print(f"   Aligned: {aligned} | Score: {alignment.get('alignment_score', '?')}")
        self._log("user_advocate", advocate_result)

        # ── Step 6: Verification ──────────────────────────────────────────
        print("✅  Verifying...")
        verified_output = verification_loop(primary_output, task, self.verifier)

        # ── Step 7: Consensus (if multiple agents ran) ────────────────────
        if len(results) > 1:
            print("🤝  Consensus check...")
            consensus_result: ConsensusResult = self.consensus.evaluate(results, task)
            print(f"   Agreed: {consensus_result.agreed} | Confidence: {consensus_result.confidence:.2f}")
            final_output = consensus_result.synthesis
        else:
            final_output = verified_output

        # ── Step 8: Memory ────────────────────────────────────────────────
        print("🧠  Storing to memory...")
        self.memory.store(
            key=f"task_{len(self._session_log)}",
            value=final_output[:1000],
            category="task_output",
            source="dallas_loop",
        )

        # ── Step 9: Return ────────────────────────────────────────────────
        self._log("output", {"final": final_output})
        print(f"\n{'─'*60}")
        return final_output

    def _execute_plan(self, plan: dict, original_task: str) -> list[AgentResult]:
        """Execute a structured plan phase by phase."""
        results: list[AgentResult] = []
        phases = plan.get("phases", [])
        completed: dict[int, AgentResult] = {}

        for phase in phases:
            phase_id = phase.get("id", 0)
            agent_role = phase.get("agent", "executor")
            instructions = phase.get("instructions", original_task)

            # Build context from dependencies
            context: dict[str, Any] = {}
            for dep_id in phase.get("depends_on", []):
                if dep_id in completed:
                    context[f"phase_{dep_id}_output"] = completed[dep_id].output[:500]

            print(f"  Phase {phase_id}: [{agent_role}] {phase.get('title', '')}")
            phase_results = self.mcp.dispatch(
                task=instructions,
                roles=[agent_role],
                context=context or None,
            )
            if phase_results:
                completed[phase_id] = phase_results[0]
                results.extend(phase_results)

        return results

    def _detect_output_type(self, output: str) -> str:
        if "def " in output or "import " in output or "class " in output:
            return "code"
        if output.strip().startswith("{") or output.strip().startswith("["):
            return "json"
        if "##" in output or "**" in output:
            return "plan"
        return "general"

    def _log(self, event: str, data: Any) -> None:
        self._session_log.append({"event": event, "data": data})


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    loop = DallasAgentLoop()

    if len(sys.argv) > 1:
        # Single task from command line
        task = " ".join(sys.argv[1:])
        result = loop.run(task)
        print(f"\n{result}\n")
        return

    # Interactive REPL
    print("\n╔══════════════════════════════════════╗")
    print("║         DALLAS  —  Agent OS          ║")
    print("║   Multi-Agent Orchestration System   ║")
    print("╚══════════════════════════════════════╝")
    print("Type your task. 'exit' to quit. 'memory' to view stored memories.\n")

    while True:
        try:
            task = input("Dallas> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not task:
            continue
        if task.lower() in ("exit", "quit", "q"):
            print("Goodbye.")
            break
        if task.lower() == "memory":
            memories = loop.memory.list_memories()
            for m in memories[:10]:
                print(f"  [{m.get('category')}] {m.get('key')}: {m.get('value', '')[:80]}")
            continue

        result = loop.run(task)
        print(f"\n{result}\n")


if __name__ == "__main__":
    main()
