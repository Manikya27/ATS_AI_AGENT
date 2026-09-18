"""Employer view - screen multiple candidates against one job description."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from ats_agent import ATSAgent, ATSAgentError
from ats_agent.models import MatchResult
from ats_agent.parsers import SUPPORTED_EXTENSIONS, UnsupportedFileType, extract_text
from ats_agent.scheduling import MEETING_ELIGIBLE_THRESHOLD, extract_email, google_calendar_meeting_link
from views.common import COLOR_MATCHED, record_usage, render_result, require_api_key
from views.theme import ACCENT_POSITIVE, section_label, step_label, view_header

MAX_CANDIDATES = 20


@dataclass
class CandidateResult:
    filename: str
    result: MatchResult | None
    error: str | None = None
    email: str | None = None


def render() -> None:
    view_header(
        "Screen candidates against a role",
        "Provide the job description once, upload multiple candidate CVs, and get a ranked "
        "shortlist by match percentage.",
    )

    step_label("01", "Job description")
    jd_file = st.file_uploader(
        "Upload JD (optional)", type=list(SUPPORTED_EXTENSIONS), key="em_jd_file"
    )
    jd_text_input = st.text_area(
        "...or paste the job description here", height=200, key="em_jd_text"
    )

    step_label("02", "Candidate CVs")
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
        "Screen candidates", type="primary", width="stretch", key="em_screen"
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
                resume_md = agent.cv_to_markdown(resume_text)
                result = agent.analyze(resume_md, job_description)
                candidates.append(
                    CandidateResult(
                        filename=resume_file.name,
                        result=result,
                        email=extract_email(resume_md),
                    )
                )
            except (UnsupportedFileType, ATSAgentError) as e:
                candidates.append(
                    CandidateResult(filename=resume_file.name, result=None, error=str(e))
                )
            progress.progress(
                (i + 1) / len(resume_files), text=f"Screened {i + 1}/{len(resume_files)}"
            )

        progress.empty()
        st.session_state["em_last_candidates"] = candidates
        record_usage(cvs=sum(1 for c in candidates if c.result is not None))

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
                "Verdict": c.result.verdict if c.result else f"Failed: {c.error}",
            }
            for i, c in enumerate(ranked)
        ]
        st.dataframe(table_rows, width="stretch", hide_index=True)

        scored = [c for c in ranked if c.result is not None]
        if scored:
            section_label("Match score by candidate")
            chart_df = pd.DataFrame(
                {"Match %": [c.result.match_percentage for c in scored]},
                index=[c.filename for c in scored],
            )
            st.bar_chart(chart_df, y="Match %", color=COLOR_MATCHED, sort=False, height=280)

        st.subheader("Candidate details")
        for i, c in enumerate(ranked):
            if c.result is None:
                st.markdown(f"**{c.filename}** — could not be screened: {c.error}")
                continue
            with st.expander(f"{c.filename} — {c.result.match_percentage}% match"):
                render_result(c.result)
                if c.result.match_percentage >= MEETING_ELIGIBLE_THRESHOLD:
                    _render_scheduling(c, i)


def _render_scheduling(candidate: CandidateResult, index: int) -> None:
    st.divider()
    section_label("Schedule an interview", ACCENT_POSITIVE)
    st.caption(
        "This candidate cleared the shortlist threshold. Confirm their email, then open a "
        "pre-filled Google Calendar invite - add Google Meet video conferencing there."
    )
    email = st.text_input(
        "Candidate email",
        value=candidate.email or "",
        placeholder="Not found in CV - enter manually",
        key=f"em_email_{index}",
    )

    candidate_label = Path(candidate.filename).stem
    url = google_calendar_meeting_link(
        candidate_label, email or None, candidate.result.match_percentage
    )
    st.link_button("Schedule Google Meet interview", url, width="content")
