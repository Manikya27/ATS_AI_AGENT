"""Query-param routing, so each view has its own shareable URL.

Navigation is plain `<a href="?view=...">` anchors rather than buttons: the
URL is the single source of truth, links can be copied and shared, and the
browser's back button works the way it does on any website.

That choice has a consequence the rest of the app has to respect. Every click
is a full page load, which starts a fresh Streamlit session, so anything that
should survive navigation has to travel in the URL rather than in session
state. STICKY_PARAMS is that list, and href() carries it automatically - a
link built any other way silently drops the visitor's persona and model.
"""
from __future__ import annotations

from urllib.parse import urlencode

import streamlit as st

HOME = "home"
JOB_SEEKER = "job-seeker"
EMPLOYER = "employer"
ASSISTANT = "assistant"

VIEWS = (HOME, JOB_SEEKER, EMPLOYER, ASSISTANT)

# Labels used by the nav bar and the landing page's cards.
VIEW_LABELS = {JOB_SEEKER: "Job Seeker", EMPLOYER: "Employer", ASSISTANT: "Assistant"}

# Parameters that follow the visitor from page to page: which side of the
# product they are here as, which talent pool partition they are working in,
# and which model they picked.
STICKY_PARAMS = ("as", "ws", "model")


def current_view() -> str:
    """The view named by ?view=, falling back to the landing page."""
    view = st.query_params.get("view", HOME)
    return view if view in VIEWS else HOME


def href(view: str, **overrides: str | None) -> str:
    """A link to `view` that keeps the visitor's sticky parameters.

    An override of None drops that parameter, which is how the landing page
    offers a way out of a persona.
    """
    params = {k: v for k, v in st.query_params.items() if k in STICKY_PARAMS}
    for key, value in overrides.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value

    if view != HOME:
        params["view"] = view
    return f"?{urlencode(params)}" if params else "?"
