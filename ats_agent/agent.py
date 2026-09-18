"""The ATS matching agent - the product's core."""
from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import TypeVar

from pydantic import BaseModel

from google import genai
from google.genai import errors, types

from .models import ImprovementPlan, JobSuggestions, MatchResult
from .prompts import (
    CV_TO_MARKDOWN_SYSTEM_PROMPT,
    IMPROVEMENT_PLAN_SYSTEM_PROMPT,
    JOB_SUGGESTIONS_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)

# gemini-2.5-flash is available on Google AI Studio's free tier.
DEFAULT_MODEL = os.environ.get("ATS_AGENT_MODEL", "gemini-2.5-flash")

# Rough character budget to stay well within context and keep the free tier's
# per-request quota predictable.
MAX_DOCUMENT_CHARS = 60_000

# The bar for a strong match. Below it the Job Seeker view offers an
# improvement plan aimed at reaching it; at or above it the Employer view
# offers to schedule an interview. One number, one meaning, used throughout.
STRONG_MATCH_THRESHOLD = 75

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class ATSAgentError(Exception):
    """Raised when the agent cannot produce a result."""


class ATSAgent:
    """Compares a candidate's CV against a job description and scores the match."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.model = model

    def cv_to_markdown(self, resume_text: str) -> str:
        """Clean/reformat raw extracted CV text into compact Markdown.

        Downstream calls (analyze, suggest_improvement_plan, suggest_jobs) should
        be given this Markdown version rather than the raw extracted text - it
        strips PDF/DOCX extraction noise (repeated headers, stray breaks, excess
        whitespace) so later calls spend fewer tokens re-parsing it, and the same
        cleaned version can be reused across all of them instead of re-sending
        raw text each time.
        """
        resume_text = resume_text.strip()[:MAX_DOCUMENT_CHARS]
        if not resume_text:
            raise ATSAgentError("The CV appears to be empty or unreadable.")
        return self._generate_text(CV_TO_MARKDOWN_SYSTEM_PROMPT, resume_text)

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
        """Guidance for reaching a strong match, for a CV that isn't there yet."""
        resume_text, job_description = self._prepare_documents(resume_text, job_description)

        user_prompt = (
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"CANDIDATE CV:\n{resume_text}\n\n"
            f"Current match score: {current_result.match_percentage}% ({current_result.verdict})\n"
            f"Missing skills already identified: {', '.join(current_result.missing_skills) or 'none listed'}\n"
            f"Gaps already identified: {', '.join(current_result.gaps) or 'none listed'}\n\n"
            f"Give the candidate a plan to raise their match to "
            f"{STRONG_MATCH_THRESHOLD}% or better."
        )
        plan = self._generate(IMPROVEMENT_PLAN_SYSTEM_PROMPT, user_prompt, ImprovementPlan)
        plan.target_match_percentage = STRONG_MATCH_THRESHOLD
        return plan

    def suggest_jobs(
        self, resume_text: str, job_description: str | None = None
    ) -> JobSuggestions:
        """Roles the CV already supports.

        Given the job description the candidate is targeting, these are roles of
        the same kind they are qualified for today - the adjacent openings worth
        searching for. Without one, they are simply the best fits for the CV.

        These are AI-generated role suggestions, not live vacancies: the agent
        has no job-board access and never claims a named company is hiring.
        """
        resume_text = resume_text.strip()[:MAX_DOCUMENT_CHARS]
        if not resume_text:
            raise ATSAgentError("The CV appears to be empty or unreadable.")

        user_prompt = f"CANDIDATE CV:\n{resume_text}\n\n"
        if job_description and job_description.strip():
            user_prompt += (
                "ROLE THEY ARE TARGETING:\n"
                f"{job_description.strip()[:MAX_DOCUMENT_CHARS]}\n\n"
                "Suggest roles of this kind that their CV already supports, so they know "
                "what else to search for alongside this application."
            )
        else:
            user_prompt += "Suggest job titles/roles this candidate is well-qualified for right now."
        return self._generate(JOB_SUGGESTIONS_SYSTEM_PROMPT, user_prompt, JobSuggestions)

    def answer_question(self, question: str, history: Sequence[Mapping[str, str]] = ()) -> str:
        """Answer a visitor's question about the product, grounded in the reference.

        `history` is the prior conversation as {"role": "user"|"assistant",
        "content": str}, oldest first, excluding the question being asked.
        """
        # Imported here rather than at module scope: knowledge.py reads this
        # module's threshold constants, so a top-level import would be circular.
        from .knowledge import ASSISTANT_SYSTEM_PROMPT, MAX_HISTORY_TURNS

        question = question.strip()
        if not question:
            raise ATSAgentError("Please enter a question.")

        contents = [
            {
                "role": "model" if turn["role"] == "assistant" else "user",
                "parts": [{"text": turn["content"]}],
            }
            for turn in list(history)[-MAX_HISTORY_TURNS:]
        ]
        contents.append({"role": "user", "parts": [{"text": question[:4000]}]})

        response = self._call(ASSISTANT_SYSTEM_PROMPT, contents)
        text = (response.text or "").strip()
        if not text:
            raise ATSAgentError("The assistant didn't return an answer. Please try again.")
        return text

    def _prepare_documents(self, resume_text: str, job_description: str) -> tuple[str, str]:
        resume_text = resume_text.strip()
        job_description = job_description.strip()

        if not resume_text:
            raise ATSAgentError("The CV appears to be empty or unreadable.")
        if not job_description:
            raise ATSAgentError("The job description is empty.")

        return resume_text[:MAX_DOCUMENT_CHARS], job_description[:MAX_DOCUMENT_CHARS]

    def _call(self, system_prompt: str, contents, *, schema: type[BaseModel] | None = None):
        """`contents` is a prompt string, or a list of turns for a conversation."""
        config_kwargs: dict = {"system_instruction": system_prompt}
        if schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = schema

        try:
            return self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs),
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

    def _generate(self, system_prompt: str, user_prompt: str, schema: type[SchemaT]) -> SchemaT:
        response = self._call(system_prompt, user_prompt, schema=schema)
        if response.parsed is None:
            raise ATSAgentError("The model did not return a valid structured response.")
        return response.parsed

    def _generate_text(self, system_prompt: str, user_prompt: str) -> str:
        response = self._call(system_prompt, user_prompt)
        text = (response.text or "").strip()
        if not text:
            raise ATSAgentError("The model did not return any content.")
        return text
