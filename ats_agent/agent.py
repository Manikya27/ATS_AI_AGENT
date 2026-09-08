"""The ATS matching agent - the product's core."""
from __future__ import annotations

import os

import anthropic

from .models import MatchResult
from .prompts import SYSTEM_PROMPT

DEFAULT_MODEL = os.environ.get("ATS_AGENT_MODEL", "claude-opus-5")

# Rough character budget to stay well within context and keep costs predictable.
MAX_DOCUMENT_CHARS = 60_000


class ATSAgentError(Exception):
    """Raised when the agent cannot produce a match result."""


class ATSAgent:
    """Compares a candidate's CV against a job description and scores the match."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
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
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                output_format=MatchResult,
            )
        except anthropic.AuthenticationError as e:
            raise ATSAgentError("Invalid Anthropic API key.") from e
        except anthropic.RateLimitError as e:
            raise ATSAgentError("Rate limited by the Anthropic API. Please try again shortly.") from e
        except anthropic.APIStatusError as e:
            raise ATSAgentError(f"Anthropic API error: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ATSAgentError("Could not reach the Anthropic API. Check your network connection.") from e

        return response.parsed_output
