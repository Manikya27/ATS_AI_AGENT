# ATS Match Agent

An AI agent that acts as an ATS (Applicant Tracking System), served as a two-view web app:

- **Job Seeker view** - upload your CV and a job description, get a match score, missing
  skills, and concrete edits to improve your chances. If the match scores below 50%, the
  agent also generates a targeted improvement plan (aimed at ~75%) and suggests other job
  titles that better fit your existing CV.
- **Employer view** - paste a job description once, upload multiple candidate CVs, and get a
  ranked shortlist by match percentage.

Both views share the same core agent, packaged as a small, reusable product
([`ats_agent`](./ats_agent), `ATSAgent`) rather than a one-off script.

## Features

- Two role-based views (Job Seeker / Employer) in one Streamlit multipage app
- Upload CVs and job descriptions as PDF, DOCX, or TXT
- Structured, validated output (Pydantic) with:
  - overall match percentage and verdict
  - matched vs. missing skills
  - strengths and gaps
  - actionable suggestions to improve the CV
- Employer view screens up to 20 CVs per run and ranks them by match %
- Below a 50% match, the Job Seeker view adds:
  - a gap analysis + specific, prioritized action items to raise the score toward 75%
  - AI-suggested job titles that better fit the candidate's existing CV, with search keywords
    (these are AI-generated suggestions based on the CV, not live job market listings)
- Runs on **Google Gemini's free tier** (`gemini-2.5-flash` by default) - no paid API required
- Dockerized for hosting as a service (Render, Railway, Fly.io, or any container host)

## Project structure

```
app.py                    Entry point: sidebar + view navigation (st.navigation)
views/
  job_seeker.py            Job Seeker view - single CV vs. one job description
  employer.py               Employer view - bulk CV screening + ranked shortlist
  common.py                  Shared UI helpers (API key handling, result rendering)
ats_agent/
  agent.py                  ATSAgent - the product's core (analyze, suggest_improvement_plan,
                             suggest_jobs)
  models.py                   Pydantic schemas: MatchResult, ImprovementPlan, JobSuggestions
  parsers.py                   PDF/DOCX/TXT text extraction
  prompts.py                   System prompts for each agent capability
Dockerfile                 Container image for hosting the app as a service
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Get a **free** Gemini API key at https://aistudio.google.com/apikey, then set it (or enter it in
the app's sidebar at runtime):

```bash
cp .env.example .env   # then edit .env
export GEMINI_API_KEY=your-gemini-api-key
```

## Run locally

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501). Use the sidebar
navigation to switch between the Job Seeker and Employer views.

## Configuration

| Env var | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | Free Gemini API key from Google AI Studio | none - falls back to the sidebar input |
| `ATS_AGENT_MODEL` | Gemini model to use | `gemini-2.5-flash` |

## Hosting as a service

Build and run the container:

```bash
docker build -t ats-agent .
docker run -p 8501:8501 -e GEMINI_API_KEY=your-gemini-api-key ats-agent
```

Then deploy the image to any container host (Render, Railway, Fly.io, AWS/GCP/Azure container
services, etc.), setting `GEMINI_API_KEY` as an environment variable/secret on the host. Most of
these platforms will build directly from this repo's `Dockerfile` without any extra config.

**Note on the free tier:** Gemini's free tier enforces per-minute request limits. The Employer
view screens CVs one at a time and surfaces per-candidate errors (including rate limits) inline,
but if you expect heavy concurrent traffic, budget for a paid Gemini tier or add request
throttling/queuing in front of the agent.

## Using the agent programmatically

```python
from ats_agent import ATSAgent, LOW_MATCH_THRESHOLD

agent = ATSAgent()  # reads GEMINI_API_KEY from the environment
result = agent.analyze(resume_text, job_description_text)

print(result.match_percentage, result.verdict)
print(result.missing_skills)

if result.match_percentage < LOW_MATCH_THRESHOLD:
    plan = agent.suggest_improvement_plan(resume_text, job_description_text, result)
    print(plan.gap_analysis, plan.action_items)

    jobs = agent.suggest_jobs(resume_text)
    for job in jobs.suggestions:
        print(job.title, job.search_keywords)
```
