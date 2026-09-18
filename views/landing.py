"""Landing page - product overview and the choice of which view to enter."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from ats_agent.agent import STRONG_MATCH_THRESHOLD
from ats_agent.knowledge import MAX_CANDIDATES
from ats_agent.scheduling import MEETING_ELIGIBLE_THRESHOLD
from ats_agent.talent_pool import RETENTION_DAYS as TALENT_POOL_RETENTION_DAYS
from ats_agent.stats import UsageStats
from views.router import ASSISTANT, EMPLOYER, JOB_SEEKER, href
from views.theme import render_stat_tiles

DEMO_GIF = Path(__file__).resolve().parent.parent / "docs" / "demo.gif"

_CHOICES = (
    {
        "view": JOB_SEEKER,
        "kicker": "For job seekers",
        "title": "Check your CV against a role",
        "points": [
            "A match score with the skills you hit and the ones you miss",
            "The exact words this role screens for that your CV never says",
            "How to restructure the CV so it lands in an eight-second skim",
            f"Under {STRONG_MATCH_THRESHOLD}%? A plan to get there, plus courses to close "
            "the gap",
            f"Over {STRONG_MATCH_THRESHOLD}%? The questions you're likely to be asked, and what "
            "to bring to each",
            "Similar roles your CV already fits, to widen the search",
        ],
        "cta": "Check my CV",
    },
    {
        "view": EMPLOYER,
        "kicker": "For employers",
        "title": "Screen a stack of CVs in minutes",
        "points": [
            f"Up to {MAX_CANDIDATES} CVs against one job description per run",
            "A ranked shortlist with a score chart",
            "Per-candidate strengths, gaps and matched skills",
            f"Candidates you saved earlier who also clear {MEETING_ELIGIBLE_THRESHOLD}%, surfaced automatically",
            f"One-click Google Meet invite for {MEETING_ELIGIBLE_THRESHOLD}%+ matches",
        ],
        "cta": "Screen candidates",
    },
)

_STEPS = (
    ("Step 01", "Upload", "Drop in a CV and the job description - PDF, DOCX or plain text."),
    ("Step 02", "Analyse", "Each CV is cleaned into structured Markdown, then scored against every requirement in the role."),
    ("Step 03", "Act", "Fix the CV with a concrete plan, prepare for the interview you're about to get, or shortlist the candidate and book one."),
)

_FEATURES = (
    ("Explainable scores", "Every score comes with the matched skills, the missing ones and the reasoning behind it."),
    ("Structured output", "Results are validated against typed schemas, so the UI never renders a half-parsed answer."),
    ("Nothing is kept unless asked", "Job seekers' CVs are processed in memory and never stored. An employer can opt in to a talent pool, which expires on its own."),
    ("Self-hostable", "One container, one API key. Runs on Gemini's free tier."),
)

_FAQ = (
    (
        "What file formats can I upload?",
        "PDF, DOCX and TXT, for both CVs and job descriptions. You can also paste a job "
        "description straight into the box instead of uploading it.",
    ),
    (
        "What happens to my CV?",
        "It's read in memory, converted to clean Markdown, and sent to Google Gemini to be "
        "analysed - so it does leave this server and is processed under Google's API terms. "
        "A CV you upload in the Job Seeker view is never written to disk here. The one "
        "exception anywhere in the product is the Employer view's talent pool: an employer "
        "can tick a box to save the CVs in a screening run so a later role can be matched "
        "against them. That box is off by default, and saved CVs are deleted "
        f"{TALENT_POOL_RETENTION_DAYS} days after they were last screened.",
    ),
    (
        "What is the keyword check?",
        "Keyword filters and skim-reading recruiters match on the words themselves, so a CV "
        "can hold exactly the right experience under the wrong label and never get read. The "
        "Job Seeker view lists the terms the job description screens on and marks each one "
        "present, worded differently, or missing. Only add the ones your experience genuinely "
        "supports - stuffing a CV with terms you can't discuss costs you the interview.",
    ),
    (
        "Are the interview questions the real ones?",
        "No - and nothing here has seen an employer's actual interview. They are predicted "
        "from the job description and your CV: what the role is built around, what on your CV "
        "an interviewer will want to open up, and where the two don't quite line up. Each one "
        "says why it's expected, so you can judge the reasoning rather than trust the list.",
    ),
    (
        "How accurate is the score?",
        "Treat it as structured, well-reasoned guidance rather than a verdict. It reflects what "
        "the CV text evidences against what the job description asks for - it can't know the "
        "context a human reviewer would, and it is not a hiring decision.",
    ),
    (
        "Is there a cost?",
        "The app runs on Google Gemini's free tier by default. Free-tier rate limits apply, so "
        "screening a large batch of CVs may need to be paced.",
    ),
)


def _choice_card(choice: dict) -> str:
    # Spans only, no block-level tags: Streamlit runs this through a markdown
    # parser, which would hoist a <div>/<ul> out of the inline <a> and split the
    # card into separate boxes. CSS gives these spans their block layout.
    points = "".join(f'<span class="e360-choice-point">{p}</span>' for p in choice["points"])
    return (
        f'<a class="e360-choice" href="{href(choice["view"])}" target="_self">'
        f'<span class="e360-choice-kicker">{choice["kicker"]}</span>'
        f'<span class="e360-choice-title">{choice["title"]}</span>'
        f"{points}"
        f'<span class="e360-choice-cta">{choice["cta"]} <span>&rarr;</span></span>'
        "</a>"
    )


def render(stats: UsageStats) -> None:
    # --- Hero ---------------------------------------------------------
    st.markdown(
        '<div class="e360-eyebrow">ATS intelligence</div>'
        '<h1 class="e360-h1">See the match <em>before</em> anyone else does.</h1>'
        '<p class="e360-lede">Employee 360 scores any CV against any job description, '
        "explains the gap in plain language, and tells both sides what to do next - "
        "whether you are applying for the role or filling it.</p>",
        unsafe_allow_html=True,
    )

    render_stat_tiles(stats, note="Live counts from completed runs on this deployment.")

    # --- Choose a view ------------------------------------------------
    st.markdown('<hr class="e360-rule">', unsafe_allow_html=True)
    st.markdown(
        '<div class="e360-section-title">Where would you like to start?</div>'
        '<p class="e360-section-sub">Two views, one engine. Pick the side of the table '
        "you're sitting on - you can switch at any time.</p>",
        unsafe_allow_html=True,
    )
    left, right = st.columns(2, gap="medium")
    for column, choice in zip((left, right), _CHOICES):
        with column:
            st.markdown(_choice_card(choice), unsafe_allow_html=True)

    # --- How it works -------------------------------------------------
    st.markdown('<hr class="e360-rule">', unsafe_allow_html=True)
    st.markdown('<div class="e360-section-title">How it works</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="e360-section-sub">The same three steps whichever view you use.</p>',
        unsafe_allow_html=True,
    )
    steps = "".join(
        '<div class="e360-step-card">'
        f'<div class="e360-step-num">{num.upper()}</div>'
        f'<div class="e360-card-title">{title}</div>'
        f'<div class="e360-card-body">{body}</div>'
        "</div>"
        for num, title, body in _STEPS
    )
    st.markdown(f'<div class="e360-grid">{steps}</div>', unsafe_allow_html=True)

    # --- Demo ---------------------------------------------------------
    if DEMO_GIF.exists():
        st.markdown('<hr class="e360-rule">', unsafe_allow_html=True)
        st.markdown(
            '<div class="e360-section-title">See it run</div>'
            '<p class="e360-section-sub">A job seeker checking their CV: a score, a plan for '
            "reaching 75%, and similar roles worth searching for - then an employer screening "
            "a stack of CVs into a ranked shortlist.</p>",
            unsafe_allow_html=True,
        )
        st.image(str(DEMO_GIF), width="stretch")
        st.caption(
            "Recorded with sample CVs and a stubbed model so the walkthrough runs without "
            "an API key - the interface, charts and counters are the real app."
        )

    # --- What you get -------------------------------------------------
    st.markdown('<hr class="e360-rule">', unsafe_allow_html=True)
    st.markdown(
        '<div class="e360-section-title">What you get</div>', unsafe_allow_html=True
    )
    features = "".join(
        '<div class="e360-feature">'
        f'<div class="e360-card-title">{title}</div>'
        f'<div class="e360-card-body">{body}</div>'
        "</div>"
        for title, body in _FEATURES
    )
    st.markdown(f'<div class="e360-grid">{features}</div>', unsafe_allow_html=True)

    # --- FAQ ----------------------------------------------------------
    st.markdown('<hr class="e360-rule">', unsafe_allow_html=True)
    st.markdown(
        '<div class="e360-section-title">Good to know</div>', unsafe_allow_html=True
    )
    for question, answer in _FAQ:
        with st.expander(question):
            st.write(answer)

    st.markdown(
        '<p class="e360-section-sub" style="margin-top:1.1rem">Something else on your mind? '
        f'<a href="{href(ASSISTANT)}" target="_self" class="e360-inline-link">Ask the assistant</a> '
        "- it answers questions about how the product works.</p>",
        unsafe_allow_html=True,
    )

    # --- Footer -------------------------------------------------------
    st.markdown(
        '<div class="e360-footer">Employee 360 - AI-assisted CV and job-description '
        "matching. Scores and suggestions are generated by a language model and are meant "
        "to inform a decision, not to make one.</div>",
        unsafe_allow_html=True,
    )
