"""ATS Match Agent - Streamlit web app entry point.

Two views, one product: Job Seeker (check your own CV) and Employer
(bulk-screen candidates), both backed by the shared ats_agent package.
"""
from __future__ import annotations

import os

import streamlit as st

st.set_page_config(page_title="ATS Match Agent", page_icon="🎯", layout="wide")


def render_sidebar() -> None:
    with st.sidebar:
        st.header("🎯 ATS Match Agent")
        st.caption("AI-powered CV ↔ job description matching.")

        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            st.text_input(
                "Gemini API key",
                type="password",
                key="api_key",
                help=(
                    "Free key from https://aistudio.google.com/apikey. "
                    "Not stored anywhere - only kept for this browser session."
                ),
            )
        else:
            st.success("API key loaded from environment.", icon="✅")

        st.divider()
        st.caption(f"Model: `{os.environ.get('ATS_AGENT_MODEL', 'gemini-2.5-flash')}`")
        st.caption("Supported files: PDF, DOCX, TXT")


render_sidebar()

pages = [
    st.Page("views/job_seeker.py", title="Job Seeker", icon="🧑‍💻", default=True),
    st.Page("views/employer.py", title="Employer", icon="🏢"),
]
st.navigation(pages).run()
