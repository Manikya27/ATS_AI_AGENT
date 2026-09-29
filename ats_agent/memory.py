"""What the agent remembers across a model switch, kept by a LangGraph graph.

A visitor can change model at any point, and each ATSAgent is built fresh for
the model it runs on. Memory therefore cannot belong to an agent. It belongs to
a LangGraph thread instead: the graph's state is checkpointed per thread, and
the agent - and with it the model - is handed to each run as runtime context,
which LangGraph never writes into a checkpoint. Run the same thread with a
different model and the new model starts from exactly the state the last one
left behind.

The graph has two entry points, picked by the `task` a run is started with:

    chat:    answer
    analyze: prepare -> analyze -> review_cv -> improvement_plan | interview_prep
                                                   -> suggest_jobs

What the state keeps:
- the conversation with the assistant, each reply tagged with the model that
  wrote it, so a switched model continues the thread instead of starting over;
- the CV and job description from the last analysis, so a new model can re-run
  it without the visitor uploading anything again;
- the cleaned Markdown of each CV, keyed by a hash of its text, so converting
  the same CV costs one model call rather than one per model;
- the score each model gave the remembered CV and role, so they can be compared;
- the last analysis's results, for the view to render.

The default checkpointer is in memory and lives as long as the AgentMemory that
owns it - one visitor's session - which keeps the product's promise that CVs
are not stored outside the opt-in talent pool. A deployment that wants memory
to outlive a session can pass any LangGraph checkpointer instead, and takes on
that promise itself.

A model is deliberately not told what an earlier model scored: each one scores
the CV on its own reading, or comparing them would compare one opinion with
itself.
"""
from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from . import models
from .agent import STRONG_MATCH_THRESHOLD, ATSAgent, ATSAgentError
from .models import CVReview, ImprovementPlan, InterviewPrep, JobSuggestions, MatchResult

# Bounds on what one thread holds, so a long visit cannot grow without limit.
MAX_TURNS = 50
MAX_CACHED_CVS = 10

# The result schemas a checkpoint may carry. LangGraph only restores types it
# has been told about, so anything stored in state has to be listed here.
_STORED_MODELS = (MatchResult, CVReview, ImprovementPlan, InterviewPrep, JobSuggestions)


class MemoryState(TypedDict, total=False):
    task: Literal["chat", "analyze"]

    # Conversation. Turns are {"role", "content", "model"}; model is None for
    # the visitor's own turns and for error replies.
    question: str | None
    turns: list[dict[str, Any]]

    # Documents. The new_* fields are a run's input; prepare moves them into
    # the remembered pair, and a run without them re-uses that pair.
    new_resume_text: str | None
    new_job_description: str | None
    resume_text: str | None
    job_description: str | None
    resume_markdown: str | None
    markdown_cache: dict[str, str]

    # Scores for the remembered pair: {"model", "match_percentage", "verdict", "at"}.
    scores: list[dict[str, Any]]

    # The last analysis. `error` is set when a step the rest depends on failed;
    # `warnings` collects the optional steps that did.
    result: MatchResult | None
    cv_review: CVReview | None
    improvement_plan: ImprovementPlan | None
    interview_prep: InterviewPrep | None
    job_suggestions: JobSuggestions | None
    warnings: list[str]
    error: str | None


@dataclass(frozen=True)
class AgentContext:
    """What a run is given but never remembers: the agent, and so the model."""

    agent: ATSAgent


def _digest(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Nodes ---------------------------------------------------------------


def _answer(state: MemoryState, runtime: Runtime[AgentContext]) -> MemoryState:
    agent = runtime.context.agent
    question = (state.get("question") or "").strip()
    turns = list(state.get("turns") or [])
    history = [{"role": t["role"], "content": t["content"]} for t in turns]

    try:
        reply = {
            "role": "assistant",
            "content": agent.answer_question(question, history),
            "model": agent.model,
        }
    except ATSAgentError as e:
        # Kept in the transcript so the person sees what happened against their
        # question, rather than a banner that vanishes on rerun.
        reply = {"role": "assistant", "content": f"Sorry - {e}", "model": None}

    turns += [{"role": "user", "content": question, "model": None}, reply]
    return {"turns": turns[-MAX_TURNS:], "question": None}


def _prepare(state: MemoryState, runtime: Runtime[AgentContext]) -> MemoryState:
    """Settle which CV and role this run is about, and clean the CV."""
    resume_text = state.get("new_resume_text") or state.get("resume_text")
    job_description = state.get("new_job_description") or state.get("job_description")

    update: MemoryState = {
        "new_resume_text": None,
        "new_job_description": None,
        # Every run starts from a clean slate, so nothing from the previous
        # analysis is shown as if this one had produced it.
        "result": None,
        "cv_review": None,
        "improvement_plan": None,
        "interview_prep": None,
        "job_suggestions": None,
        "resume_markdown": None,
        "warnings": [],
        "error": None,
    }
    if not resume_text or not job_description:
        update["error"] = "There is no CV and job description in memory to analyse."
        return update

    # A different pair starts a fresh comparison: scores for another CV or
    # role say nothing about this one.
    if (resume_text, job_description) != (state.get("resume_text"), state.get("job_description")):
        update["scores"] = []
    update["resume_text"] = resume_text
    update["job_description"] = job_description

    # Cleaning is formatting, not judgement, so a version any model produced
    # is good for every model - no call needed after a switch.
    cache = dict(state.get("markdown_cache") or {})
    key = _digest(resume_text)
    markdown = cache.get(key)
    if markdown is None:
        try:
            markdown = runtime.context.agent.cv_to_markdown(resume_text)
        except ATSAgentError as e:
            update["error"] = str(e)
            return update
        cache[key] = markdown
        # Dicts keep insertion order, so the first key is the oldest.
        while len(cache) > MAX_CACHED_CVS:
            del cache[next(iter(cache))]
    update["markdown_cache"] = cache
    update["resume_markdown"] = markdown
    return update


def _analyze(state: MemoryState, runtime: Runtime[AgentContext]) -> MemoryState:
    agent = runtime.context.agent
    try:
        result = agent.analyze(state["resume_markdown"], state["job_description"])
    except ATSAgentError as e:
        return {"error": str(e)}

    # One score per model: the latest run of a model replaces its earlier one.
    scores = [s for s in state.get("scores") or [] if s["model"] != agent.model]
    scores.append(
        {
            "model": agent.model,
            "match_percentage": result.match_percentage,
            "verdict": result.verdict,
            "at": _now(),
        }
    )
    return {"result": result, "scores": scores}


def _optional_step(field: str, failure: str, call):
    """A node whose failure is a warning on the result, not the end of the run."""

    def node(state: MemoryState, runtime: Runtime[AgentContext]) -> MemoryState:
        try:
            return {field: call(runtime.context.agent, state)}
        except ATSAgentError as e:
            return {"warnings": [*(state.get("warnings") or []), f"{failure}: {e}"]}

    return node


_review_cv = _optional_step(
    "cv_review",
    "Couldn't run the keyword and formatting check",
    lambda agent, s: agent.review_cv(s["resume_markdown"], s["job_description"]),
)
_improvement_plan = _optional_step(
    "improvement_plan",
    "Couldn't generate an improvement plan",
    lambda agent, s: agent.suggest_improvement_plan(
        s["resume_markdown"], s["job_description"], s["result"]
    ),
)
_interview_prep = _optional_step(
    "interview_prep",
    "Couldn't prepare interview questions",
    lambda agent, s: agent.prepare_interview(
        s["resume_markdown"], s["job_description"], s["result"]
    ),
)
_suggest_jobs = _optional_step(
    "job_suggestions",
    "Couldn't suggest similar roles",
    lambda agent, s: agent.suggest_jobs(s["resume_markdown"], s["job_description"]),
)


# --- Edges ---------------------------------------------------------------


def _route_task(state: MemoryState) -> str:
    return "answer" if state.get("task") == "chat" else "prepare"


def _stop_on_error(next_node: str):
    def route(state: MemoryState) -> str:
        return END if state.get("error") else next_node

    return route


def _route_by_score(state: MemoryState) -> str:
    # The two sides of the bar need opposite things. Short of it, the useful
    # help is closing the gap; at or above it the CV has done its job and the
    # interview is what is left.
    if state["result"].match_percentage < STRONG_MATCH_THRESHOLD:
        return "improvement_plan"
    return "interview_prep"


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """The compiled memory graph. Every run needs a thread_id and an AgentContext."""
    graph = StateGraph(MemoryState, context_schema=AgentContext)

    graph.add_node("answer", _answer)
    graph.add_node("prepare", _prepare)
    graph.add_node("analyze", _analyze)
    graph.add_node("review_cv", _review_cv)
    graph.add_node("improvement_plan", _improvement_plan)
    graph.add_node("interview_prep", _interview_prep)
    graph.add_node("suggest_jobs", _suggest_jobs)

    graph.add_conditional_edges(START, _route_task, ["answer", "prepare"])
    graph.add_edge("answer", END)
    graph.add_conditional_edges("prepare", _stop_on_error("analyze"), ["analyze", END])
    # The keyword check runs at every score: it is what decides whether a CV is
    # read at all, so a strong match needs it as much as a weak one.
    graph.add_conditional_edges("analyze", _stop_on_error("review_cv"), ["review_cv", END])
    graph.add_conditional_edges(
        "review_cv", _route_by_score, ["improvement_plan", "interview_prep"]
    )
    # Similar roles are useful at any score.
    graph.add_edge("improvement_plan", "suggest_jobs")
    graph.add_edge("interview_prep", "suggest_jobs")
    graph.add_edge("suggest_jobs", END)

    if checkpointer is None:
        checkpointer = InMemorySaver(serde=serializer())
    return graph.compile(checkpointer=checkpointer)


def serializer() -> JsonPlusSerializer:
    """A checkpoint serializer that can restore this package's result schemas.

    Pass it to any other checkpointer used with `build_graph`.
    """
    return JsonPlusSerializer(
        allowed_msgpack_modules=[(models.__name__, m.__name__) for m in _STORED_MODELS]
    )


class AgentMemory:
    """One visitor's memory: a LangGraph thread, and the graph that runs on it.

    Hand every call the ATSAgent for the model currently selected. The agent
    changes when the model does; the thread, and everything in it, does not.
    """

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
        thread_id: str | None = None,
    ):
        self.thread_id = thread_id or uuid.uuid4().hex
        self._graph = build_graph(checkpointer)

    @property
    def config(self) -> dict[str, Any]:
        return {"configurable": {"thread_id": self.thread_id}}

    @property
    def values(self) -> MemoryState:
        """The thread's current state."""
        return self._graph.get_state(self.config).values

    # --- Conversation -----------------------------------------------------

    def ask(self, agent: ATSAgent, question: str) -> str:
        """Answer `question` in the ongoing conversation, and return the reply."""
        state = self._graph.invoke(
            {"task": "chat", "question": question},
            self.config,
            context=AgentContext(agent),
        )
        return state["turns"][-1]["content"]

    @property
    def turns(self) -> list[dict[str, Any]]:
        return list(self.values.get("turns") or [])

    def clear_conversation(self) -> None:
        self._graph.update_state(self.config, {"turns": []})

    # --- Analysis ---------------------------------------------------------

    def analyze(
        self,
        agent: ATSAgent,
        resume_text: str | None = None,
        job_description: str | None = None,
    ) -> Iterator[str]:
        """Run the analysis, yielding each step's name as it finishes.

        Without documents it re-runs the pair already in memory - which is how
        a newly selected model takes over the last analysis. Read the outcome
        from `values` once the iterator is exhausted.
        """
        run = {
            "task": "analyze",
            "new_resume_text": resume_text,
            "new_job_description": job_description,
        }
        for update in self._graph.stream(
            run, self.config, context=AgentContext(agent), stream_mode="updates"
        ):
            yield from update

    @property
    def resume_text(self) -> str | None:
        return self.values.get("resume_text")

    @property
    def job_description(self) -> str | None:
        return self.values.get("job_description")

    @property
    def scores(self) -> list[dict[str, Any]]:
        return list(self.values.get("scores") or [])

    def has_documents(self) -> bool:
        return bool(self.resume_text and self.job_description)

    def last_scored_model(self) -> str | None:
        scores = self.scores
        return scores[-1]["model"] if scores else None
