"""The ATS matching agent - the product's core."""
from __future__ import annotations

import os

from google import genai
from google.genai import errors, types

from .models import MatchResult
from .prompts import SYSTEM_PROMPT

# gemini-2.5-flash is available on Google AI Studio's free tier.
DEFAULT_MODEL = os.environ.get("ATS_AGENT_MODEL", "gemini-2.5-flash")

# Rough character budget to stay well within context and keep the free tier's
# per-request quota predictable.
MAX_DOCUMENT_CHARS = 60_000


class ATSAgentError(Exception):
    """Raised when the agent cannot produce a match result."""


class ATSAgent:
    """Compares a candidate's CV against a job description and scores the match."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.model = model

    def analyze(self, resume_text: str, job_description: str) -> MatchResult:
        resume_text = resume_text.strip()
        job_description = job_description.strip()

        if not resume_text:
            raise ATSAgentError("The CV appears to be empty or unreadable.")
        if not job_description:
            raise ATSAgentError("The job description is empty.")

        resume_text = resume_text[:MAX_DOCUMENT_CHARS]
        job_description = job_description[:MAX_DOCUMENT_CHARS]

        user_prompt = (
            "JOB DESCRIPTION:\n"
            f"{job_description}\n\n"
            "CANDIDATE CV:\n"
            f"{resume_text}\n\n"
            "Evaluate how well this CV matches this job description."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=MatchResult,
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
