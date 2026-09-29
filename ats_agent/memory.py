"""What the agent remembers across a model switch.

A visitor can change model at any point, and each ATSAgent is built fresh for
the model it runs on. Anything the previous model worked out would be lost
with it unless it is kept somewhere that does not belong to a model. This is
that place: plain data, written in no model's own format, so whichever model
runs next reads the same memory the last one left behind.

What is kept:
- the conversation with the assistant, each reply tagged with the model that
  wrote it, so a switched model continues the thread instead of starting over;
- the CV and job description from the last analysis, so a new model can re-run
  it without the visitor uploading anything again;
- the cleaned Markdown of each CV, keyed by a hash of its text, so converting
  the same CV twice costs one model call rather than one per model;
- the score each model gave the last analysis, so results can be compared.

Memory lives for one visitor's session and is never written to disk - the
same promise the product makes about CVs everywhere outside the talent pool.
It is deliberately not shown to a model as "the previous model thought X"
when scoring: each model scores the CV on its own reading, or comparing them
would be comparing one opinion with itself.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Bounds on what one session holds, so a long visit cannot grow without limit.
MAX_TURNS = 50
MAX_CACHED_CVS = 10


def _digest(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Turn:
    """One message in the assistant conversation."""

    role: str  # "user" or "assistant"
    content: str
    model: str | None = None  # which model wrote it; None for the visitor's own turns


@dataclass
class ModelScore:
    """What one model made of the remembered CV and job description."""

    model: str
    match_percentage: int
    verdict: str
    at: str = field(default_factory=_now)


@dataclass
class AgentMemory:
    """Model-independent memory shared by every ATSAgent in a session."""

    turns: list[Turn] = field(default_factory=list)
    resume_text: str | None = None
    job_description: str | None = None
    scores: list[ModelScore] = field(default_factory=list)
    _markdown: dict[str, str] = field(default_factory=dict)

    # --- Conversation -----------------------------------------------------

    def add_turn(self, role: str, content: str, model: str | None = None) -> None:
        self.turns.append(Turn(role=role, content=content, model=model))
        del self.turns[:-MAX_TURNS]

    def history(self) -> list[dict[str, str]]:
        """The conversation in the shape ATSAgent.answer_question takes."""
        return [{"role": t.role, "content": t.content} for t in self.turns]

    def clear_conversation(self) -> None:
        self.turns.clear()

    # --- Documents --------------------------------------------------------

    def remember_documents(self, resume_text: str, job_description: str) -> None:
        """Keep the pair being analysed. A different pair starts a fresh comparison."""
        if (resume_text, job_description) != (self.resume_text, self.job_description):
            self.scores.clear()
        self.resume_text = resume_text
        self.job_description = job_description

    def has_documents(self) -> bool:
        return bool(self.resume_text and self.job_description)

    def cached_markdown(self, resume_text: str) -> str | None:
        return self._markdown.get(_digest(resume_text))

    def cache_markdown(self, resume_text: str, markdown: str) -> None:
        key = _digest(resume_text)
        self._markdown.pop(key, None)
        self._markdown[key] = markdown
        # Dicts keep insertion order, so the first key is the oldest.
        while len(self._markdown) > MAX_CACHED_CVS:
            del self._markdown[next(iter(self._markdown))]

    # --- Results ----------------------------------------------------------

    def record_score(self, model: str, match_percentage: int, verdict: str) -> None:
        """Keep one score per model: the latest run of a model replaces its earlier one."""
        self.scores = [s for s in self.scores if s.model != model]
        self.scores.append(ModelScore(model, match_percentage, verdict))

    def last_scored_model(self) -> str | None:
        return self.scores[-1].model if self.scores else None

    # --- Serialisation ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "turns": [vars(t) for t in self.turns],
            "resume_text": self.resume_text,
            "job_description": self.job_description,
            "scores": [vars(s) for s in self.scores],
            "markdown": dict(self._markdown),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentMemory:
        return cls(
            turns=[Turn(**t) for t in data.get("turns", [])],
            resume_text=data.get("resume_text"),
            job_description=data.get("job_description"),
            scores=[ModelScore(**s) for s in data.get("scores", [])],
            _markdown=dict(data.get("markdown", {})),
        )
