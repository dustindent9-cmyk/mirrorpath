"""
Agent contracts — Pydantic schemas for all agent inputs and outputs.
Enforces a consistent interface across every agent in Dallas.
"""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Input contracts ──────────────────────────────────────────────────────────

class AgentInput(BaseModel):
    task: str
    context: dict[str, Any] = Field(default_factory=dict)
    history: list[dict] = Field(default_factory=list)
    output_format: Literal["text", "json", "code", "plan"] = "text"
    max_retries: int = 3


# ── Output contracts ─────────────────────────────────────────────────────────

class AgentOutput(BaseModel):
    agent: str
    output: str
    thinking: str | None = None
    tool_calls: list[dict] = Field(default_factory=list)
    stop_reason: str = "end_turn"
    errors: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    aligned_with_user: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanPhase(BaseModel):
    id: int
    title: str
    agent: str
    instructions: str
    depends_on: list[int] = Field(default_factory=list)
    expected_output: str = ""


class PlanOutput(AgentOutput):
    goal: str = ""
    phases: list[PlanPhase] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ReviewDimensions(BaseModel):
    correctness: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    quality: float = Field(ge=0.0, le=1.0)
    safety: float = Field(ge=0.0, le=1.0)
    alignment: float = Field(ge=0.0, le=1.0)


class CriticOutput(AgentOutput):
    overall_score: float = Field(default=0.5, ge=0.0, le=1.0)
    passed: bool = False
    dimensions: ReviewDimensions | None = None
    issues: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    approved: bool = False


class AlignmentOutput(AgentOutput):
    alignment_score: float = Field(default=0.8, ge=0.0, le=1.0)
    original_intent: str = ""
    gaps: list[str] = Field(default_factory=list)
    extras: list[str] = Field(default_factory=list)
    recommendation: Literal["approve", "revise", "reject"] = "approve"
    revision_note: str | None = None


class VerificationOutput(AgentOutput):
    passed: bool = False
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    revised_output: str | None = None


# ── Session contract ─────────────────────────────────────────────────────────

class SessionResult(BaseModel):
    task: str
    final_output: str
    plan: PlanOutput | None = None
    critic_review: CriticOutput | None = None
    alignment: AlignmentOutput | None = None
    verification: VerificationOutput | None = None
    consensus_used: bool = False
    total_agent_calls: int = 0
    memory_stored: bool = False
