"""Employee 360 - Streamlit web app entry point.

A landing page plus two views - Job Seeker (check your own CV) and Employer
(bulk-screen candidates) - routed by ?view= so each has its own shareable URL.
Both views are backed by the shared ats_agent package.

Which view a visitor is offered depends on the persona they chose at the
entrance: an employer is not shown the job seeker view, and vice versa. Which
model runs the analysis is theirs to pick from what this deployment allows.
The API key remains server-side configuration, never exposed or collected.
"""
from __future__ import annotations

import streamlit as st

from ats_agent.stats import load_stats
from views import assistant, employer, job_seeker, landing
from views.model_picker import render_model_picker
from views.persona import can_see, current_persona
from views.router import ASSISTANT, EMPLOYER, HOME, JOB_SEEKER, current_view
from views.theme import inject_theme, render_navbar

st.set_page_config(page_title="Employee 360", page_icon="🎯", layout="wide")

inject_theme()

view = current_view()
persona = current_persona()
stats = st.session_state.get("usage_stats") or load_stats()

# A view this persona isn't offered falls back to the landing page rather than
# erroring. Someone arriving on a shared link for the other side should meet
# the chooser, not a dead end.
if not can_see(view, persona):
    view = HOME

if view == HOME:
    landing.render(stats, persona)
else:
    render_navbar(view)
    render_model_picker()
    if view == JOB_SEEKER:
        job_seeker.render()
    elif view == EMPLOYER:
        employer.render()
    elif view == ASSISTANT:
        assistant.render()
