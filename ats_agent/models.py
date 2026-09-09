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


class CourseSuggestion(BaseModel):
    """An upskilling suggestion aimed at closing one specific gap."""

    skill_or_topic: str = Field(..., description="The gap this course/certification would close")
    course_suggestion: str = Field(
        ...,
        description=(
            "The type of course, certification, or learning path that would help - a "
            "description of what to look for, not a specific real course/provider"
        ),
    )
    why_it_helps: str = Field(..., description="1 sentence on how this closes the gap for this JD")


class ImprovementPlan(BaseModel):
    """Guidance for closing the gap on a low-scoring CV/JD match."""

    target_match_percentage: int = Field(
        ..., ge=0, le=100, description="The match score this guidance is aimed at reaching"
    )
    gap_analysis: str = Field(
        ..., description="2-3 sentences on why the CV currently falls short of this job's requirements"
    )
    action_items: list[str] = Field(
        default_factory=list,
        description=(
            "Specific, high-impact changes the candidate should make to their CV to close "
            "the gap toward the target score - concrete directions (what to add, quantify, "
            "reorder, or remove), not rewritten resume text"
        ),
    )
    recommended_courses: list[CourseSuggestion] = Field(
        default_factory=list,
        description="Upskilling suggestions (course/certification types) for the biggest gaps",
    )


class JobSuggestion(BaseModel):
    """A role suggested as a better fit for the candidate's existing CV."""

    title: str = Field(..., description="Suggested job title")
    why_fit: str = Field(..., description="1-2 sentences on why this role suits the candidate's CV")
    seniority: str = Field(..., description="e.g. 'Entry-level', 'Mid-level', 'Senior'")
    key_skills_matched: list[str] = Field(
        default_factory=list, description="CV skills/experience that support this suggestion"
    )
    search_keywords: str = Field(
        ..., description="Keywords the candidate could paste into a job board's search box"
    )


class JobSuggestions(BaseModel):
    suggestions: list[JobSuggestion] = Field(default_factory=list)
