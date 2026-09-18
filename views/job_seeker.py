"""Job Seeker view - check your own CV against a job description."""
from __future__ import annotations

import streamlit as st

from ats_agent import ATSAgent, ATSAgentError, LOW_MATCH_THRESHOLD
from ats_agent.parsers import SUPPORTED_EXTENSIONS, UnsupportedFileType, extract_text
from views.common import (
    record_usage,
    render_improvement_plan,
    render_job_suggestions,
    render_result,
    require_api_key,
)
from views.theme import step_label, view_header


def render() -> None:
    view_header(
        "Check your CV against a role",
        "Upload your CV and the job description you're applying to. You'll get a match "
        "score, see what's missing, and get concrete edits to improve your chances.",
    )

    col1, col2 = st.columns(2)

    with col1:
        step_label("01", "Your CV")
        resume_file = st.file_uploader(
            "Upload CV", type=list(SUPPORTED_EXTENSIONS), key="js_resume_file"
        )

    with col2:
        step_label("02", "Job description")
        jd_file = st.file_uploader(
            "Upload JD (optional)", type=list(SUPPORTED_EXTENSIONS), key="js_jd_file"
        )
        jd_text_input = st.text_area(
            "...or paste the job description here", height=200, key="js_jd_text"
        )

    analyze_clicked = st.button(
        "Analyze match", type="primary", use_container_width=True, key="js_analyze"
    )

    if analyze_clicked:
        api_key = require_api_key()
        if not api_key:
            st.stop()
        if resume_file is None:
            st.error("Please upload your CV.")
            st.stop()

        try:
            resume_text = extract_text(resume_file.getvalue(), resume_file.name)
        except UnsupportedFileType as e:
            st.error(str(e))
            st.stop()

        if jd_file is not None:
            try:
                job_description = extract_text(jd_file.getvalue(), jd_file.name)
            except UnsupportedFileType as e:
                st.error(str(e))
                st.stop()
        else:
            job_description = jd_text_input

        if not job_description.strip():
            st.error("Please provide a job description (upload a file or paste text).")
            st.stop()

        agent = ATSAgent(api_key=api_key)

        with st.spinner("Reading your CV..."):
            try:
                resume_md = agent.cv_to_markdown(resume_text)
            except ATSAgentError as e:
                st.error(str(e))
                st.stop()

        with st.spinner("Analyzing match..."):
            try:
                result = agent.analyze(resume_md, job_description)
            except ATSAgentError as e:
                st.error(str(e))
                st.stop()

        st.session_state["js_last_result"] = result
        st.session_state["js_last_improvement_plan"] = None
        st.session_state["js_last_job_suggestions"] = None

        if result.match_percentage < LOW_MATCH_THRESHOLD:
            with st.spinner("Working out how to close the gap..."):
                try:
                    st.session_state["js_last_improvement_plan"] = agent.suggest_improvement_plan(
                        resume_md, job_description, result
                    )
                except ATSAgentError as e:
                    st.warning(f"Couldn't generate an improvement plan: {e}")

            with st.spinner("Looking for roles that fit your CV..."):
                try:
                    st.session_state["js_last_job_suggestions"] = agent.suggest_jobs(resume_md)
                except ATSAgentError as e:
                    st.warning(f"Couldn't generate job suggestions: {e}")

        record_usage(cvs=1)

    if "js_last_result" in st.session_state:
        st.divider()
        render_result(st.session_state["js_last_result"])

        improvement_plan = st.session_state.get("js_last_improvement_plan")
        if improvement_plan is not None:
            st.divider()
            render_improvement_plan(improvement_plan)

        job_suggestions = st.session_state.get("js_last_job_suggestions")
        if job_suggestions is not None:
            st.divider()
            render_job_suggestions(job_suggestions)
