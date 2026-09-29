"""Job Seeker view - check your own CV against a job description."""
from __future__ import annotations

import streamlit as st

from ats_agent import ATSAgent
from ats_agent.parsers import SUPPORTED_EXTENSIONS, UnsupportedFileType, extract_text
from views.memory import session_memory
from views.model_picker import selected_model
from views.common import (
    record_usage,
    render_cv_review,
    render_improvement_plan,
    render_interview_prep,
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

        _run_analysis(api_key, resume_text, job_description)

    _render_model_switch()
    _render_last_analysis()


# What the visitor is told while each step of the analysis graph runs, keyed by
# the step that has just finished.
_STEP_LABELS = {
    "prepare": "Analyzing match...",
    "analyze": "Checking the CV against the role's own wording...",
    "review_cv": "Tailoring the next steps to your score...",
    "improvement_plan": "Finding similar roles your CV already fits...",
    "interview_prep": "Finding similar roles your CV already fits...",
}


def _run_analysis(
    api_key: str, resume_text: str | None = None, job_description: str | None = None
) -> None:
    """Run the analysis graph on the session's memory with the selected model.

    Given documents it analyses them and remembers them. Without, it re-runs
    the pair already in memory - which is how a newly chosen model takes over.
    """
    memory = session_memory()
    agent = ATSAgent(api_key=api_key, model=selected_model())

    with st.status("Reading your CV...") as status:
        for step in memory.analyze(agent, resume_text, job_description):
            if step in _STEP_LABELS:
                status.update(label=_STEP_LABELS[step])

    error = memory.values.get("error")
    if error:
        st.error(error)
        st.stop()

    # Recording the run reruns the script, which is why a step that fails is
    # kept as a warning in memory rather than shown with st.warning here.
    record_usage(cvs=1)


def _render_model_switch() -> None:
    """After a model change, offer the remembered analysis to the new model."""
    memory = session_memory()
    if not memory.has_documents() or memory.values.get("result") is None:
        return

    current = selected_model()
    if memory.last_scored_model() not in (None, current):
        st.info(
            f"You switched to **{current}**. It has the CV and job description from your "
            "last analysis in memory, so you can re-run it without uploading again."
        )
        if st.button(f"Re-run with {current}", key="js_rerun_model", type="primary"):
            api_key = require_api_key()
            if not api_key:
                st.stop()
            _run_analysis(api_key)

    scores = memory.scores
    if len(scores) > 1:
        st.caption(
            "Scores for this CV and role: "
            + " · ".join(f"{s['model']}: {s['match_percentage']}%" for s in scores)
        )


def _render_last_analysis() -> None:
    state = session_memory().values
    result = state.get("result")
    if result is None:
        return

    st.divider()
    for message in state.get("warnings") or []:
        st.warning(message)

    render_result(result)

    for key, render_section in (
        ("cv_review", render_cv_review),
        ("improvement_plan", render_improvement_plan),
        ("interview_prep", render_interview_prep),
        ("job_suggestions", render_job_suggestions),
    ):
        if state.get(key) is not None:
            st.divider()
            render_section(state[key])
