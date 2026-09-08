"""Structured output schema for the ATS matching result."""
from __future__ import annotations

from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    match_percentage: int = Field(
        ..., ge=0, le=100, description="Overall CV-to-JD match score, 0-100"
    )
    verdict: str = Field(
        ..., description="One short phrase, e.g. 'Strong match', 'Partial match', 'Weak match'"
    )
    matched_skills: list[str] = Field(
        default_factory=list, description="Skills/requirements evidenced in both the CV and JD"
    )
    missing_skills: list[str] = Field(
        default_factory=list, description="JD requirements not evidenced anywhere in the CV"
    )
    strengths: list[str] = Field(
        default_factory=list, description="Candidate strengths most relevant to this role"
    )
    gaps: list[str] = Field(
        default_factory=list, description="Notable gaps or risks versus the JD"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Concrete, actionable edits the candidate could make to improve their match score",
    )
    summary: str = Field(..., description="2-4 sentence overall assessment")
