"""Which models this deployment offers, and which of them the key can reach.

Two lists meet here. The first is the allowlist: the models this product is
willing to run on, set by ATS_AGENT_MODELS or the curated default below. The
second is what the configured API key can actually call, which the provider
reports at runtime. The picker shows the intersection, so a model that is
allowlisted but unavailable to this key never appears as a broken choice.

Discovery is best-effort. If the provider cannot be reached, the allowlist is
offered unfiltered - a picker that works on a guess beats no picker at all, and
an unusable model fails loudly on first use rather than silently here.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

# The model used when nothing is chosen, and the fallback for an unrecognised
# request. Kept as its own env var so an operator can pin the default without
# touching the list on offer.
DEFAULT_MODEL_ID = os.environ.get("ATS_AGENT_MODEL", "gemini-2.5-flash")

# How long a discovered model list is trusted before it is fetched again. The
# set of available models changes rarely; Streamlit reruns the script on every
# interaction, and none of them should cost an API call.
_DISCOVERY_TTL_SECONDS = 900

_LOCK = threading.Lock()
_cache: tuple[float, frozenset[str]] | None = None


@dataclass(frozen=True)
class ModelOption:
    """One model a visitor can pick, as the UI describes it."""

    id: str
    label: str
    blurb: str

    @property
    def display(self) -> str:
        return f"{self.label} - {self.id}"


# Curated metadata for the models this product ships with knowledge of. Anything
# offered but not listed here still works; it is described from whatever the
# provider reports instead.
_CURATED: dict[str, tuple[str, str]] = {
    "gemini-2.5-flash": (
        "Balanced",
        "The default. Quick enough for bulk screening, strong enough for the reasoning "
        "the match score needs.",
    ),
    "gemini-2.5-flash-lite": (
        "Fastest",
        "The quickest and cheapest option. Best for screening a large stack of CVs where "
        "throughput matters more than nuance.",
    ),
    "gemini-2.5-pro": (
        "Most capable",
        "The most thorough reasoning, and the slowest. Worth it for a single CV you care "
        "about; heavy going for a batch on a free-tier quota.",
    ),
    "gemini-2.0-flash": (
        "Previous generation",
        "An older fast model. Kept as a fallback for comparing results or when newer "
        "models are rate limited.",
    ),
}

_DEFAULT_ALLOWLIST = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
)


def allowlist() -> tuple[str, ...]:
    """The models this deployment is willing to offer, default first."""
    configured = os.environ.get("ATS_AGENT_MODELS", "").strip()
    ids = (
        tuple(part.strip() for part in configured.split(",") if part.strip())
        if configured
        else _DEFAULT_ALLOWLIST
    )
    # The default always belongs on the list, and always first: it is what a
    # visitor who never touches the picker gets.
    ordered = [DEFAULT_MODEL_ID] + [i for i in ids if i != DEFAULT_MODEL_ID]
    return tuple(dict.fromkeys(ordered))


def describe(model_id: str) -> ModelOption:
    label, blurb = _CURATED.get(
        model_id,
        ("Available model", "Offered by this deployment's configuration."),
    )
    if model_id == DEFAULT_MODEL_ID:
        blurb = f"{blurb} Used when no other model is chosen."
    return ModelOption(id=model_id, label=label, blurb=blurb)


def available_model_ids(client=None) -> tuple[str, ...]:
    """The allowlist, narrowed to what the configured key can actually call."""
    allowed = allowlist()
    reachable = _reachable_ids(client)
    if reachable is None:
        return allowed

    narrowed = tuple(i for i in allowed if i in reachable)
    # Never hand back nothing: an empty picker is worse than an optimistic one,
    # and if discovery disagrees with the allowlist this badly it is discovery
    # that is more likely wrong.
    return narrowed or allowed


def available_models(client=None) -> list[ModelOption]:
    return [describe(model_id) for model_id in available_model_ids(client)]


def resolve(requested: str | None, client=None) -> str:
    """The model to actually run with, given what a visitor asked for.

    Anything not on offer falls back to the default rather than being passed
    through - the model id arrives from a query parameter, so it is visitor
    input and cannot be trusted to name something this deployment allows.
    """
    if requested and requested in available_model_ids(client):
        return requested
    return DEFAULT_MODEL_ID


def _reachable_ids(client) -> frozenset[str] | None:
    """Model ids the provider says this key can generate content with.

    None means "could not find out" - the caller should not treat that as an
    empty set.
    """
    global _cache

    if client is None:
        return None

    with _LOCK:
        if _cache is not None and time.monotonic() - _cache[0] < _DISCOVERY_TTL_SECONDS:
            return _cache[1]

    try:
        ids = set()
        for model in client.models.list():
            name = (getattr(model, "name", "") or "").split("/")[-1]
            if not name:
                continue
            actions = getattr(model, "supported_actions", None)
            # An empty/absent action list means the provider didn't say. Keep
            # the model rather than dropping it on a guess about the schema.
            if actions and not any("generatecontent" == str(a).lower() for a in actions):
                continue
            ids.add(name)
    except Exception:
        # Discovery is a convenience, never a dependency: a provider outage or
        # an SDK change must not empty the picker or break the page.
        return None

    frozen = frozenset(ids)
    with _LOCK:
        _cache = (time.monotonic(), frozen)
    return frozen


def _reset_cache_for_tests() -> None:
    global _cache
    with _LOCK:
        _cache = None
