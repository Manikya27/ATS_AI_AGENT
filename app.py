"""Employee 360 - Streamlit web app entry point.

A landing page plus two views - Job Seeker (check your own CV) and Employer
(bulk-screen candidates) - routed by ?view= so each has its own shareable
URL. Both views are backed by the shared ats_agent package. The API key and
model are server-side configuration only, never exposed or collected in the UI.
"""
from __future__ import annotations

import streamlit as st

from ats_agent.stats import load_stats
from views import employer, job_seeker, landing
from views.router import EMPLOYER, HOME, JOB_SEEKER, current_view
from views.theme import inject_theme, render_navbar

st.set_page_config(page_title="Employee 360", page_icon="🎯", layout="wide")

inject_theme()

view = current_view()
stats = st.session_state.get("usage_stats") or load_stats()

if view == HOME:
    landing.render(stats)
else:
    render_navbar(view)
    if view == JOB_SEEKER:
        job_seeker.render()
    elif view == EMPLOYER:
        employer.render()
