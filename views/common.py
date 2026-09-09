"""Helpers shared by the Job Seeker and Employer views."""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from ats_agent.models import ImprovementPlan, JobSuggestions, MatchResult

# Validated categorical palette slots (blue, orange) - see project dataviz guidance.
COLOR_MATCHED = "#2a78d6"
COLOR_MISSING = "#eb6834"


def get_api_key() -> str | None:
    """The API key is a server-side deployment secret - never collected from visitors."""
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or None


def require_api_key() -> str | None:
    """Return the configured API key, or show an error and return None."""
    api_key = get_api_key()
    if not api_key:
        st.error(
            "This service isn't configured yet. An administrator needs to set the "
            "GEMINI_API_KEY environment variable on the server."
        )
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

    if result.matched_skills or result.missing_skills:
        st.markdown("**📊 Skill match breakdown**")
        chart_df = pd.DataFrame(
            {
                "Matched": [len(result.matched_skills)],
                "Missing": [len(result.missing_skills)],
            }
        )
        st.bar_chart(chart_df, color=[COLOR_MATCHED, COLOR_MISSING], stack=False, height=220)

    st.divider()
    st.markdown("**📝 Suggestions to improve the match**")
    if result.suggestions:
        for suggestion in result.suggestions:
            st.markdown(f"- {suggestion}")
    else:
        st.caption("No suggestions.")


def render_improvement_plan(plan: ImprovementPlan) -> None:
    st.markdown(f"#### 📈 How to reach ~{plan.target_match_percentage}% match")
    st.write(plan.gap_analysis)
    for item in plan.action_items:
        st.markdown(f"- {item}")

    if plan.recommended_courses:
        st.markdown("##### 📚 Courses worth exploring")
        st.caption(
            "A little upskilling here goes a long way - these are AI-suggested learning "
            "paths for your biggest gaps, not specific real courses or providers."
        )
        for course in plan.recommended_courses:
            with st.expander(course.skill_or_topic):
                st.write(course.course_suggestion)
                st.caption(course.why_it_helps)


def render_job_suggestions(jobs: JobSuggestions) -> None:
    st.markdown("#### 🔎 Roles that might fit your CV better")
    st.caption(
        "AI-generated suggestions based on your CV's skills and experience - not live job "
        "market listings."
    )
    if not jobs.suggestions:
        st.caption("No suggestions.")
        return

    for job in jobs.suggestions:
        with st.expander(f"{job.title} ({job.seniority})"):
            st.write(job.why_fit)
            if job.key_skills_matched:
                st.markdown("**Matching skills from your CV:** " + ", ".join(job.key_skills_matched))
            st.markdown(f"**Try searching:** `{job.search_keywords}`")
