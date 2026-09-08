"""Helpers shared by the Job Seeker and Employer views."""
from __future__ import annotations

import os

import streamlit as st

from ats_agent.models import MatchResult


def get_api_key() -> str | None:
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env_key:
        return env_key
    return st.session_state.get("api_key") or None


def require_api_key() -> str | None:
    """Return the configured API key, or show an error and return None."""
    api_key = get_api_key()
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar to continue.")
    return api_key


def render_result(result: MatchResult) -> None:
    score = result.match_percentage

    if score >= 75:
        color = "green"
    elif score >= 50:
        color = "orange"
    else:
        color = "red"

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Match score", f"{score}%")
        st.progress(score / 100)
        st.markdown(f":{color}[**{result.verdict}**]")
    with col2:
        st.markdown("**Summary**")
        st.write(result.summary)

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**✅ Matched skills**")
        if result.matched_skills:
            for skill in result.matched_skills:
                st.markdown(f"- {skill}")
        else:
            st.caption("None identified.")

        st.markdown("**💪 Strengths**")
        if result.strengths:
            for item in result.strengths:
                st.markdown(f"- {item}")
        else:
            st.caption("None identified.")

    with col_b:
        st.markdown("**❌ Missing skills**")
        if result.missing_skills:
            for skill in result.missing_skills:
                st.markdown(f"- {skill}")
        else:
            st.caption("None identified.")

        st.markdown("**⚠️ Gaps**")
        if result.gaps:
            for item in result.gaps:
                st.markdown(f"- {item}")
        else:
            st.caption("None identified.")

    st.divider()
    st.markdown("**📝 Suggestions to improve the match**")
    if result.suggestions:
        for suggestion in result.suggestions:
            st.markdown(f"- {suggestion}")
    else:
        st.caption("No suggestions.")
