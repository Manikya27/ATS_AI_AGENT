"""Helpers shared by the Job Seeker and Employer views."""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from ats_agent.models import CVReview, ImprovementPlan, InterviewPrep, JobSuggestions, MatchResult
from ats_agent.stats import record_run
from views.theme import ACCENT_NEUTRAL, ACCENT_POSITIVE, keyword_chips, section_label

# Brand orange + blue, validated against the dark chart surface (lightness band,
# chroma floor, CVD separation, contrast).
COLOR_MATCHED = "#e8641f"
COLOR_MISSING = "#3987e5"


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


def record_usage(cvs: int) -> None:
    """Record a completed run, then rerun so the header stats show it immediately."""
    if cvs <= 0:
        return
    new_session = not st.session_state.get("counted_session", False)
    st.session_state["counted_session"] = True
    st.session_state["usage_stats"] = record_run(cvs=cvs, new_session=new_session)
    st.rerun()


def render_result(result: MatchResult) -> None:
    score = result.match_percentage

    # Blue rather than red at the low end: a weak match is "not there yet",
    # not an error, and red undercuts the encouraging tone of the guidance.
    if score >= 75:
        color = "green"
    elif score >= 50:
        color = "orange"
    else:
        color = "blue"

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Match score", f"{score}%")
        st.progress(score / 100)
        st.markdown(f":{color}[**{result.verdict}**]")
    with col2:
        section_label("Summary")
        st.write(result.summary)

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        section_label("Matched skills", ACCENT_POSITIVE)
        if result.matched_skills:
            for skill in result.matched_skills:
                st.markdown(f"- {skill}")
        else:
            st.caption("None identified.")

        section_label("Strengths", ACCENT_POSITIVE)
        if result.strengths:
            for item in result.strengths:
                st.markdown(f"- {item}")
        else:
            st.caption("None identified.")

    with col_b:
        section_label("Missing skills", ACCENT_NEUTRAL)
        if result.missing_skills:
            for skill in result.missing_skills:
                st.markdown(f"- {skill}")
        else:
            st.caption("None identified.")

        section_label("Gaps", ACCENT_NEUTRAL)
        if result.gaps:
            for item in result.gaps:
                st.markdown(f"- {item}")
        else:
            st.caption("None identified.")

    if result.matched_skills or result.missing_skills:
        section_label("Skill match breakdown")
        chart_df = pd.DataFrame(
            {
                "Matched": [len(result.matched_skills)],
                "Missing": [len(result.missing_skills)],
            }
        )
        st.bar_chart(chart_df, color=[COLOR_MATCHED, COLOR_MISSING], stack=False, height=220)

    st.divider()
    section_label("Suggestions to improve the match")
    if result.suggestions:
        for suggestion in result.suggestions:
            st.markdown(f"- {suggestion}")
    else:
        st.caption("No suggestions.")


def render_improvement_plan(plan: ImprovementPlan) -> None:
    st.markdown(f"#### How to reach ~{plan.target_match_percentage}% match")
    st.write(plan.gap_analysis)
    for item in plan.action_items:
        st.markdown(f"- {item}")

    if plan.recommended_courses:
        section_label("Courses worth exploring", ACCENT_POSITIVE)
        st.caption(
            "A little upskilling here goes a long way - these are AI-suggested learning "
            "paths for your biggest gaps, not specific real courses or providers."
        )
        for course in plan.recommended_courses:
            with st.expander(course.skill_or_topic):
                st.write(course.course_suggestion)
                st.caption(course.why_it_helps)


def render_job_suggestions(jobs: JobSuggestions) -> None:
    st.markdown("#### Similar roles worth searching for")
    st.caption(
        "Roles of the same kind your CV already supports, so you can widen the search around "
        "this application. These are AI-generated suggestions from your CV - not live "
        "vacancies, and no company here is known to be hiring."
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


# Status order for the keyword report: the two the candidate can act on come
# first, and "present" last as reassurance rather than as the headline.
_KEYWORD_GROUPS = (
    (
        "missing",
        "Missing from your CV",
        ACCENT_NEUTRAL,
        "The role asks for these and your CV never says them. Add the ones you can back up "
        "with real experience; treat the rest as what to build next.",
    ),
    (
        "partial",
        "You have this - you just don't say it",
        ACCENT_POSITIVE,
        "Your experience is here, worded differently. These are the cheapest points on the "
        "page: reword the bullet you already have so it uses the role's term.",
    ),
    (
        "present",
        "Already covered",
        ACCENT_POSITIVE,
        "Your CV uses these terms. Keep them where a skim will find them.",
    ),
)


def render_cv_review(review: CVReview) -> None:
    """The keyword screen and the layout advice - what to change before applying."""
    st.markdown("#### Keywords this role screens for")
    st.caption(
        "Recruiters and keyword filters match on the words themselves, so a CV can hold the "
        "right experience under the wrong label and never be read. These terms are taken "
        "from the job description you supplied."
    )
    st.write(review.keyword_summary)

    by_status = {status: [] for status, _, _, _ in _KEYWORD_GROUPS}
    for hit in review.keywords:
        by_status.setdefault(hit.status, []).append(hit)

    if review.keywords:
        counts = {status: len(hits) for status, hits in by_status.items()}
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Missing", counts.get("missing", 0))
        col_b.metric("Worded differently", counts.get("partial", 0))
        col_c.metric("Already covered", counts.get("present", 0))

        covered = counts.get("present", 0) + counts.get("partial", 0)
        chart_df = pd.DataFrame(
            {"Covered": [covered], "Missing": [counts.get("missing", 0)]}
        )
        st.bar_chart(chart_df, color=[COLOR_MATCHED, COLOR_MISSING], stack=False, height=170)

    for status, heading, accent, blurb in _KEYWORD_GROUPS:
        hits = by_status.get(status) or []
        if not hits:
            continue
        section_label(heading, accent)
        st.caption(blurb)
        # Core requirements are the ones that decide the screen, so they are
        # chipped separately from the nice-to-haves rather than mixed in.
        for importance, label in (("core", "Required"), ("preferred", "Preferred")):
            group = [h for h in hits if h.importance == importance]
            if not group:
                continue
            st.markdown(f"**{label}**")
            keyword_chips([h.keyword for h in group], status)

        if status != "present":
            with st.expander(f"What to do about each ({len(hits)})"):
                for hit in hits:
                    st.markdown(f"**{hit.keyword}** - {hit.advice}")

    st.caption(
        "Only add a keyword your experience genuinely supports. Padding a CV with terms you "
        "can't speak to in an interview costs you the interview, and hidden keyword blocks "
        "are filtered out by every modern screen."
    )

    st.divider()
    st.markdown("#### Make the CV itself land harder")
    st.write(review.format_summary)

    if review.suggested_structure:
        section_label("Suggested running order for this role")
        for i, section in enumerate(review.suggested_structure, start=1):
            st.markdown(f"{i}. {section}")

    if review.format_tips:
        section_label("Specific changes")
        for tip in review.format_tips:
            with st.expander(f"{tip.area} - {tip.impact} impact"):
                st.markdown(f"**Today:** {tip.issue}")
                st.markdown(f"**Change to:** {tip.fix}")


# Read as a label in the expander title, so the candidate can triage the list
# without opening anything.
_CATEGORY_LABELS = {
    "technical": "Technical",
    "experience": "Your experience",
    "behavioural": "Behavioural",
    "gap": "The awkward one",
    "motivation": "Motivation",
}


def render_interview_prep(prep: InterviewPrep) -> None:
    """What a strong candidate is likely to be asked, and what to bring to each answer."""
    st.markdown("#### Prepare for the interview")
    st.caption(
        "Your CV clears the bar for this role, so the next thing worth your time is the "
        "conversation. These questions are predicted from this job description and your CV - "
        "nobody here has seen the employer's actual interview or question list."
    )
    st.write(prep.readiness_summary)

    if prep.questions:
        section_label(f"{len(prep.questions)} questions worth rehearsing")
        st.caption("Most likely first. Prepare from the top down if you are short of time.")
        for i, q in enumerate(prep.questions, start=1):
            category = _CATEGORY_LABELS.get(q.category, q.category.title())
            # Likelihood goes in the collapsed label: the point of the list is
            # knowing what to rehearse first, which is useless if you have to
            # open every question to find out.
            with st.expander(f"{i}. {q.question}  ·  {q.likelihood}"):
                st.caption(category)
                st.markdown(f"**Why it comes up:** {q.why_it_comes_up}")
                st.markdown(f"**A strong answer:** {q.how_to_answer}")
                if q.draw_on:
                    st.markdown("**Draw on:**")
                    for item in q.draw_on:
                        st.markdown(f"- {item}")

    if prep.questions_to_ask:
        section_label("Ask them this", ACCENT_POSITIVE)
        st.caption(
            "Interviews run both ways, and a specific question lands better than a polite one."
        )
        for question in prep.questions_to_ask:
            st.markdown(f"- {question}")

    st.caption(
        "Answer from your own experience rather than a script - these are the shape of a good "
        "answer, not words to memorise."
    )
