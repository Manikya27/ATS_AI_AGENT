"""Employee 360 - Streamlit web app entry point.

Two views, one product: Job Seeker (check your own CV) and Employer
(bulk-screen candidates), both backed by the shared ats_agent package.
The API key and model are server-side configuration only - never
exposed or collected in the UI.
"""
from __future__ import annotations

import streamlit as st

from views import employer, job_seeker

st.set_page_config(page_title="Employee 360", page_icon="🎯", layout="wide")

st.title("🎯 Employee 360")
st.caption("AI-powered CV ↔ job description matching for job seekers and employers.")

tab_job_seeker, tab_employer = st.tabs(["🧑‍💻 Job Seeker", "🏢 Employer"])

with tab_job_seeker:
    job_seeker.render()

with tab_employer:
    employer.render()
