"""Employer view - screen multiple candidates against one job description."""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from ats_agent import ATSAgent, ATSAgentError
from ats_agent.models import MatchResult
from ats_agent.parsers import SUPPORTED_EXTENSIONS, UnsupportedFileType, extract_text
from views.common import render_result, require_api_key

MAX_CANDIDATES = 20


@dataclass
class CandidateResult:
    filename: str
    result: MatchResult | None
    error: str | None = None


def render() -> None:
    st.header("🏢 Employer: Screen Candidates")
    st.write(
        "Provide the job description once, upload multiple candidate CVs, and get a ranked "
        "shortlist by match percentage."
    )

    st.subheader("1. Job Description")
    jd_file = st.file_uploader(
        "Upload JD (optional)", type=list(SUPPORTED_EXTENSIONS), key="em_jd_file"
    )
    jd_text_input = st.text_area(
        "...or paste the job description here", height=200, key="em_jd_text"
    )

    st.subheader("2. Candidate CVs")
    resume_files = st.file_uploader(
        "Upload CVs (multiple)",
        type=list(SUPPORTED_EXTENSIONS),
        accept_multiple_files=True,
        key="em_resume_files",
    )
    if resume_files and len(resume_files) > MAX_CANDIDATES:
        st.warning(f"Only the first {MAX_CANDIDATES} CVs will be screened in this run.")
        resume_files = resume_files[:MAX_CANDIDATES]

    screen_clicked = st.button(
        "Screen candidates", type="primary", use_container_width=True, key="em_screen"
    )

    if screen_clicked:
        api_key = require_api_key()
        if not api_key:
            st.stop()
        if not resume_files:
            st.error("Please upload at least one candidate CV.")
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
        candidates: list[CandidateResult] = []
        progress = st.progress(0.0, text="Screening candidates...")

        for i, resume_file in enumerate(resume_files):
            try:
                resume_text = extract_text(resume_file.getvalue(), resume_file.name)
                result = agent.analyze(resume_text, job_description)
                candidates.append(CandidateResult(filename=resume_file.name, result=result))
            except (UnsupportedFileType, ATSAgentError) as e:
                candidates.append(
                    CandidateResult(filename=resume_file.name, result=None, error=str(e))
                )
            progress.progress(
                (i + 1) / len(resume_files), text=f"Screened {i + 1}/{len(resume_files)}"
            )

        progress.empty()
        st.session_state["em_last_candidates"] = candidates

    if "em_last_candidates" in st.session_state:
        candidates: list[CandidateResult] = st.session_state["em_last_candidates"]
        ranked = sorted(
            candidates,
            key=lambda c: c.result.match_percentage if c.result else -1,
            reverse=True,
        )

        st.divider()
        st.subheader("Ranked shortlist")

        table_rows = [
            {
                "Rank": i + 1,
                "Candidate": c.filename,
                "Match %": c.result.match_percentage if c.result else None,
                "Verdict": c.result.verdict if c.result else f"⚠️ {c.error}",
            }
            for i, c in enumerate(ranked)
        ]
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        st.subheader("Candidate details")
        for c in ranked:
            if c.result is None:
                st.markdown(f"**{c.filename}** — ⚠️ {c.error}")
                continue
            with st.expander(f"{c.filename} — {c.result.match_percentage}% match"):
                render_result(c.result)
