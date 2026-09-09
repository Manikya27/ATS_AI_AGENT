"""The ATS matching agent - the product's core."""
from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel

from google import genai
from google.genai import errors, types

from .models import ImprovementPlan, JobSuggestions, MatchResult
from .prompts import (
    IMPROVEMENT_PLAN_SYSTEM_PROMPT,
    JOB_SUGGESTIONS_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)

# gemini-2.5-flash is available on Google AI Studio's free tier.
DEFAULT_MODEL = os.environ.get("ATS_AGENT_MODEL", "gemini-2.5-flash")

# Rough character budget to stay well within context and keep the free tier's
# per-request quota predictable.
MAX_DOCUMENT_CHARS = 60_000

# A CV/JD match below this score is considered a weak fit for this specific role.
LOW_MATCH_THRESHOLD = 50

# The score the improvement plan's guidance is aimed at reaching.
IMPROVEMENT_TARGET_PERCENTAGE = 75

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class ATSAgentError(Exception):
    """Raised when the agent cannot produce a result."""


class ATSAgent:
    """Compares a candidate's CV against a job description and scores the match."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.model = model

    def analyze(self, resume_text: str, job_description: str) -> MatchResult:
        resume_text, job_description = self._prepare_documents(resume_text, job_description)

        user_prompt = (
            "JOB DESCRIPTION:\n"
            f"{job_description}\n\n"
            "CANDIDATE CV:\n"
            f"{resume_text}\n\n"
            "Evaluate how well this CV matches this job description."
        )
        return self._generate(SYSTEM_PROMPT, user_prompt, MatchResult)

    def suggest_improvement_plan(
        self, resume_text: str, job_description: str, current_result: MatchResult
    ) -> ImprovementPlan:
        """Guidance for closing the gap on a low-scoring CV/JD match."""
        resume_text, job_description = self._prepare_documents(resume_text, job_description)

        user_prompt = (
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"CANDIDATE CV:\n{resume_text}\n\n"
            f"Current match score: {current_result.match_percentage}% ({current_result.verdict})\n"
            f"Missing skills already identified: {', '.join(current_result.missing_skills) or 'none listed'}\n"
            f"Gaps already identified: {', '.join(current_result.gaps) or 'none listed'}\n\n"
            f"Give the candidate a plan to raise their match toward "
            f"{IMPROVEMENT_TARGET_PERCENTAGE}%."
        )
        plan = self._generate(IMPROVEMENT_PLAN_SYSTEM_PROMPT, user_prompt, ImprovementPlan)
        plan.target_match_percentage = IMPROVEMENT_TARGET_PERCENTAGE
        return plan

    def suggest_jobs(self, resume_text: str) -> JobSuggestions:
        """AI-suggested job titles/roles that fit the CV, independent of any specific JD."""
        resume_text = resume_text.strip()[:MAX_DOCUMENT_CHARS]
        if not resume_text:
            raise ATSAgentError("The CV appears to be empty or unreadable.")

        user_prompt = (
            f"CANDIDATE CV:\n{resume_text}\n\n"
            "Suggest job titles/roles this candidate is well-qualified for right now."
        )
        return self._generate(JOB_SUGGESTIONS_SYSTEM_PROMPT, user_prompt, JobSuggestions)

    def _prepare_documents(self, resume_text: str, job_description: str) -> tuple[str, str]:
        resume_text = resume_text.strip()
        job_description = job_description.strip()

        if not resume_text:
            raise ATSAgentError("The CV appears to be empty or unreadable.")
        if not job_description:
            raise ATSAgentError("The job description is empty.")

        return resume_text[:MAX_DOCUMENT_CHARS], job_description[:MAX_DOCUMENT_CHARS]

    def _generate(self, system_prompt: str, user_prompt: str, schema: type[SchemaT]) -> SchemaT:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        except errors.ClientError as e:
            if e.code in (401, 403):
                raise ATSAgentError("Invalid or unauthorized Gemini API key.") from e
            if e.code == 429:
                raise ATSAgentError(
                    "Gemini free-tier rate limit reached. Please wait a bit and try again."
                ) from e
            raise ATSAgentError(f"Gemini API error: {e.message}") from e
        except errors.ServerError as e:
            raise ATSAgentError(f"Gemini server error, please retry: {e.message}") from e
        except errors.APIError as e:
            raise ATSAgentError(f"Gemini API error: {e.message}") from e

        if response.parsed is None:
            raise ATSAgentError("The model did not return a valid structured response.")

        return response.parsed
