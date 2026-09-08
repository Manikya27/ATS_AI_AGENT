"""Job Seeker view - check your own CV against a job description."""
from __future__ import annotations

import streamlit as st

from ats_agent import ATSAgent, ATSAgentError
from ats_agent.parsers import SUPPORTED_EXTENSIONS, UnsupportedFileType, extract_text
from views.common import render_result, require_api_key

st.title("🧑‍💻 Job Seeker: Check Your CV")
st.write(
    "Upload your CV and the job description you're applying to. Get a match score, "
    "see what's missing, and get concrete edits to improve your chances."
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Your CV")
    resume_file = st.file_uploader(
        "Upload CV", type=list(SUPPORTED_EXTENSIONS), key="js_resume_file"
    )

with col2:
    st.subheader("2. Job Description")
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

    with st.spinner("Analyzing match..."):
        try:
            agent = ATSAgent(api_key=api_key)
            result = agent.analyze(resume_text, job_description)
        except ATSAgentError as e:
            st.error(str(e))
            st.stop()

    st.session_state["js_last_result"] = result

if "js_last_result" in st.session_state:
    st.divider()
    render_result(st.session_state["js_last_result"])
