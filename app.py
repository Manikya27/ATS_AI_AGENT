"""ATS Match Agent - Streamlit product front-end."""
from __future__ import annotations

import os

import streamlit as st

from ats_agent import ATSAgent, ATSAgentError
from ats_agent.models import MatchResult
from ats_agent.parsers import SUPPORTED_EXTENSIONS, UnsupportedFileType, extract_text

st.set_page_config(page_title="ATS Match Agent", page_icon="🎯", layout="wide")


def get_api_key() -> str | None:
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return env_key
    return st.session_state.get("api_key") or None


def render_sidebar() -> None:
    with st.sidebar:
        st.header("🎯 ATS Match Agent")
        st.caption("Upload a CV and a job description to get an AI-scored match.")

        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.text_input(
                "Anthropic API key",
                type="password",
                key="api_key",
                help="Not stored anywhere - only kept for this browser session.",
            )
        else:
            st.success("API key loaded from environment.", icon="✅")

        st.divider()
        st.caption(f"Model: `{os.environ.get('ATS_AGENT_MODEL', 'claude-opus-5')}`")
        st.caption("Supported files: PDF, DOCX, TXT")


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


def main() -> None:
    render_sidebar()

    st.title("ATS Resume ↔ Job Description Matcher")
    st.write(
        "Upload a candidate's CV and paste (or upload) the job description. "
        "The agent scores how well the CV matches the role and explains why."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Candidate CV")
        resume_file = st.file_uploader(
            "Upload CV", type=list(SUPPORTED_EXTENSIONS), key="resume_file"
        )

    with col2:
        st.subheader("2. Job Description")
        jd_file = st.file_uploader(
            "Upload JD (optional)", type=list(SUPPORTED_EXTENSIONS), key="jd_file"
        )
        jd_text_input = st.text_area(
            "...or paste the job description here", height=200, key="jd_text"
        )

    analyze_clicked = st.button("Analyze match", type="primary", use_container_width=True)

    if analyze_clicked:
        api_key = get_api_key()
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
            return
        if resume_file is None:
            st.error("Please upload a CV.")
            return

        try:
            resume_text = extract_text(resume_file.getvalue(), resume_file.name)
        except UnsupportedFileType as e:
            st.error(str(e))
            return

        if jd_file is not None:
            try:
                job_description = extract_text(jd_file.getvalue(), jd_file.name)
            except UnsupportedFileType as e:
                st.error(str(e))
                return
        else:
            job_description = jd_text_input

        if not job_description.strip():
            st.error("Please provide a job description (upload a file or paste text).")
            return

        with st.spinner("Analyzing match..."):
            try:
                agent = ATSAgent(api_key=api_key)
                result = agent.analyze(resume_text, job_description)
            except ATSAgentError as e:
                st.error(str(e))
                return

        st.session_state["last_result"] = result

    if "last_result" in st.session_state:
        st.divider()
        render_result(st.session_state["last_result"])


if __name__ == "__main__":
    main()
