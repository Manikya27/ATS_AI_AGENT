"""Employee 360 - Streamlit web app entry point.

Two views, one product: Job Seeker (check your own CV) and Employer
(bulk-screen candidates), both backed by the shared ats_agent package.
The API key and model are server-side configuration only - never
exposed or collected in the UI.
"""
from __future__ import annotations

import streamlit as st

from ats_agent.stats import load_stats
from views import employer, job_seeker
from views.theme import inject_theme, render_header

st.set_page_config(page_title="Employee 360", page_icon="🎯", layout="wide")

inject_theme()
render_header(st.session_state.get("usage_stats") or load_stats())

tab_job_seeker, tab_employer = st.tabs(["JOB SEEKER", "EMPLOYER"])

with tab_job_seeker:
    job_seeker.render()

with tab_employer:
    employer.render()
