"""Query-param routing, so each view has its own shareable URL.

Navigation is plain `<a href="?view=...">` anchors rather than buttons: the
URL is the single source of truth, links can be copied and shared, and the
browser's back button works the way it does on any website.
"""
from __future__ import annotations

import streamlit as st

HOME = "home"
JOB_SEEKER = "job-seeker"
EMPLOYER = "employer"

VIEWS = (HOME, JOB_SEEKER, EMPLOYER)

# Labels used by the nav bar and the landing page's cards.
VIEW_LABELS = {JOB_SEEKER: "Job Seeker", EMPLOYER: "Employer"}


def current_view() -> str:
    """The view named by ?view=, falling back to the landing page."""
    view = st.query_params.get("view", HOME)
    return view if view in VIEWS else HOME


def href(view: str) -> str:
    return "?" if view == HOME else f"?view={view}"
