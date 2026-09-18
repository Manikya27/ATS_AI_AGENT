"""Employer view - screen multiple candidates against one job description."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from ats_agent import ATSAgent, ATSAgentError
from ats_agent.knowledge import MAX_CANDIDATES
from ats_agent.models import MatchResult
from ats_agent.parsers import SUPPORTED_EXTENSIONS, UnsupportedFileType, extract_text
from ats_agent.scheduling import MEETING_ELIGIBLE_THRESHOLD, extract_email, google_calendar_meeting_link
from ats_agent.talent_pool import (
    MAX_RESCREEN,
    RETENTION_DAYS,
    PooledCandidate,
    candidate_id,
    clear_pool,
    load_pool,
    rank_for_role,
    remember,
)
from views.common import COLOR_MATCHED, record_usage, render_result, require_api_key
from views.theme import ACCENT_POSITIVE, badge, section_label, step_label, view_header


# How many saved candidates the pool panel lists before it stops naming them.
POOL_PREVIEW = 10


@dataclass
class CandidateResult:
    filename: str
    result: MatchResult | None
    error: str | None = None
    email: str | None = None
    resume_md: str | None = None
    # Set when this exact person is already in the talent pool from an earlier
    # run. Captured before this run saves anything, or every CV would look
    # like a returning one.
    seen_before: PooledCandidate | None = None


@dataclass
class PoolMatch:
    """A candidate from an earlier run whose saved CV fits the role posted now."""

    candidate: PooledCandidate
    result: MatchResult


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

    step_label("03", "Talent pool")
    _render_pool_controls()

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
        save_to_pool = st.session_state.get("em_save_pool", False)
        # Read once, before this run writes anything: a CV saved a moment ago
        # would otherwise report itself as a returning candidate.
        pool_before = load_pool()
        known_ids = {c.id: c for c in pool_before}

        candidates: list[CandidateResult] = []
        progress = st.progress(0.0, text="Screening candidates...")

        for i, resume_file in enumerate(resume_files):
            try:
                resume_text = extract_text(resume_file.getvalue(), resume_file.name)
                resume_md = agent.cv_to_markdown(resume_text)
                result = agent.analyze(resume_md, job_description)
                email = extract_email(resume_md)
                candidates.append(
                    CandidateResult(
                        filename=resume_file.name,
                        result=result,
                        email=email,
                        resume_md=resume_md,
                        seen_before=known_ids.get(candidate_id(resume_md, email)),
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

        uploaded_ids = frozenset(
            candidate_id(c.resume_md, c.email) for c in candidates if c.resume_md
        )
        pool_matches, pool_screened = _screen_talent_pool(
            agent, job_description, pool_before, uploaded_ids
        )
        st.session_state["em_last_pool_matches"] = pool_matches

        if save_to_pool:
            for candidate in candidates:
                if candidate.resume_md:
                    remember(
                        Path(candidate.filename).stem, candidate.resume_md, candidate.email
                    )

        # Every saved CV that was re-scored is a CV analysed, not just the ones
        # that cleared the bar - the counter says "CVs analysed" and has to mean it.
        screened = sum(1 for c in candidates if c.result is not None)
        record_usage(cvs=screened + pool_screened)

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
                "Seen before": "Yes" if c.seen_before else "",
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

        _render_pool_matches(st.session_state.get("em_last_pool_matches") or [])

        st.subheader("Candidate details")
        for i, c in enumerate(ranked):
            if c.result is None:
                st.markdown(f"**{c.filename}** — could not be screened: {c.error}")
                continue
            title = f"{c.filename} — {c.result.match_percentage}% match"
            if c.seen_before:
                title += "  ·  in your talent pool"
            with st.expander(title):
                if c.seen_before:
                    st.markdown(
                        badge("Screened before")
                        + f"&nbsp; First saved {c.seen_before.added_on}, "
                        f"screened {c.seen_before.times_seen}× in total.",
                        unsafe_allow_html=True,
                    )
                render_result(c.result)
                if c.result.match_percentage >= MEETING_ELIGIBLE_THRESHOLD:
                    _render_scheduling(c, i)



def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _render_pool_controls() -> None:
    """The consent checkbox and the state of what is currently stored."""
    pool = load_pool()
    st.checkbox(
        "Save these CVs to the talent pool",
        value=False,
        key="em_save_pool",
        help=(
            "Keeps each CV's cleaned text, its filename and the email found in it, so a job "
            "description you post later can be matched against candidates you have already "
            "seen. Off by default."
        ),
    )
    st.caption(
        f"Saved CVs are kept for {RETENTION_DAYS} days after they were last screened, then "
        "deleted automatically. Candidates you upload are always matched against whatever is "
        "already in the pool, whether or not you add this batch to it. Only tick this if you "
        "have a lawful basis to retain these candidates' details."
    )
    if not pool:
        return

    with st.expander(f"Talent pool: {_plural(len(pool), 'saved candidate')}"):
        for candidate in pool[:POOL_PREVIEW]:
            st.markdown(
                f"- **{candidate.label}** - saved {candidate.added_on}, "
                f"screened {candidate.times_seen}×"
            )
        if len(pool) > POOL_PREVIEW:
            st.caption(f"...and {len(pool) - POOL_PREVIEW} more.")
        if st.button("Delete every saved CV", key="em_clear_pool"):
            clear_pool()
            st.success("Talent pool cleared.")
            st.rerun()


def _screen_talent_pool(
    agent: ATSAgent,
    job_description: str,
    pool: list[PooledCandidate],
    uploaded_ids: frozenset[str],
) -> tuple[list[PoolMatch], int]:
    """Score saved CVs against the role just posted, and keep the strong ones.

    Returns the matches worth showing and how many saved CVs were actually
    scored, which is the larger number and the one the usage counter wants.

    Only the lexically most promising few are sent to the model: every one is a
    request, and a pool of two hundred would exhaust a free-tier quota on its
    own. Saved CVs are already cleaned Markdown, so they skip the conversion
    step the uploads need.
    """
    shortlist = rank_for_role(job_description, pool, exclude_ids=uploaded_ids)
    if not shortlist:
        return [], 0

    scored = 0
    matches: list[PoolMatch] = []
    progress = st.progress(0.0, text="Checking your talent pool...")
    for i, candidate in enumerate(shortlist):
        try:
            result = agent.analyze(candidate.resume_md, job_description)
            scored += 1
            if result.match_percentage >= MEETING_ELIGIBLE_THRESHOLD:
                matches.append(PoolMatch(candidate=candidate, result=result))
        except ATSAgentError:
            # One unscreenable saved CV shouldn't cost the employer the rest of
            # the pool, and it isn't a candidate they uploaded just now.
            pass
        progress.progress((i + 1) / len(shortlist), text=f"Checked {i + 1}/{len(shortlist)}")
    progress.empty()

    matches.sort(key=lambda m: m.result.match_percentage, reverse=True)
    return matches, scored


def _render_pool_matches(matches: list[PoolMatch]) -> None:
    if not matches:
        return

    st.divider()
    section_label("Already in your talent pool", ACCENT_POSITIVE)
    st.subheader(f"{_plural(len(matches), 'earlier candidate')} also fit this role")
    st.caption(
        f"These CVs were saved from previous screenings, not uploaded just now. Each scored "
        f"{MEETING_ELIGIBLE_THRESHOLD}% or above against this job description. At most "
        f"{MAX_RESCREEN} saved CVs are re-scored per run, chosen by word overlap with the role."
    )

    for i, match in enumerate(matches):
        candidate = match.candidate
        with st.expander(
            f"{candidate.label} — {match.result.match_percentage}% match  ·  saved {candidate.added_on}"
        ):
            st.markdown(
                badge("From talent pool")
                + f"&nbsp; Saved {candidate.added_on}, screened {candidate.times_seen}× in total.",
                unsafe_allow_html=True,
            )
            render_result(match.result)
            _render_scheduling(
                CandidateResult(
                    filename=candidate.label,
                    result=match.result,
                    email=candidate.email,
                ),
                index=1000 + i,
            )


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
