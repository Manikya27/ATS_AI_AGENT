"""Who the visitor is here as, and therefore which views they see.

Employee 360 has two audiences with opposite interests looking at the same
engine. Showing both doors to everyone made the product read as a demo of two
things rather than as one thing for you. Picking a side at the entrance means
an employer never sees the job-seeker view and a job seeker never sees the
employer view.

This is a preference, not an access control. There are no accounts and no
passwords: the persona travels in the URL, so anyone can change it by editing
the address bar, and nothing here is a security boundary. It is the product
deciding what to show you, not a lock on what you may reach - every UI string
about it is worded to avoid implying otherwise.

Why the URL rather than the session: navigating between views is a full page
load, which starts a fresh Streamlit session and would drop anything held only
in session state. The query parameter survives the reload, keeps links
shareable, and keeps the back button honest.
"""
from __future__ import annotations

import re

import streamlit as st

from ats_agent.talent_pool import DEFAULT_WORKSPACE
from views.router import EMPLOYER, JOB_SEEKER

PERSONA_PARAM = "as"
WORKSPACE_PARAM = "ws"

PERSONAS = (JOB_SEEKER, EMPLOYER)

PERSONA_LABELS = {JOB_SEEKER: "Job seeker", EMPLOYER: "Employer"}

# Which views each persona is offered. The landing page and the assistant are
# shared: one is how you change your mind, the other answers questions about
# the product rather than doing work for either side.
_PERSONA_VIEWS = {
    JOB_SEEKER: (JOB_SEEKER,),
    EMPLOYER: (EMPLOYER,),
}

MAX_WORKSPACE_LENGTH = 40

_WORKSPACE_CLEAN_RE = re.compile(r"[^a-z0-9-]+")


def current_persona() -> str | None:
    """The persona named by ?as=, or None if the visitor hasn't chosen."""
    value = st.query_params.get(PERSONA_PARAM)
    return value if value in PERSONAS else None


def current_workspace() -> str:
    """The talent pool partition this employer is working in."""
    return normalise_workspace(st.query_params.get(WORKSPACE_PARAM))


def normalise_workspace(value: str | None) -> str:
    """Fold a typed team name into a stable key.

    'Acme Hiring' and 'acme-hiring' are the same workspace; a blank or
    unusable name is the shared default rather than an error, because an
    employer mistyping their team name should not silently get an empty pool.
    """
    if not value:
        return DEFAULT_WORKSPACE
    cleaned = _WORKSPACE_CLEAN_RE.sub("-", value.strip().lower()).strip("-")
    return cleaned[:MAX_WORKSPACE_LENGTH] or DEFAULT_WORKSPACE


def can_see(view: str, persona: str | None) -> bool:
    """Whether this view is offered to this persona."""
    if view in (JOB_SEEKER, EMPLOYER):
        return persona is not None and view in _PERSONA_VIEWS[persona]
    return True


def visible_views(persona: str | None) -> tuple[str, ...]:
    return _PERSONA_VIEWS.get(persona, ())


def set_workspace(value: str) -> None:
    """Move this employer to another pool partition and reload into it."""
    workspace = normalise_workspace(value)
    if workspace == DEFAULT_WORKSPACE:
        st.query_params.pop(WORKSPACE_PARAM, None)
    else:
        st.query_params[WORKSPACE_PARAM] = workspace
    st.rerun()
