# Employee 360

An AI agent that acts as an ATS (Applicant Tracking System), served as a small website: a
landing page explains the product, and visitors choose which of the two views to enter. Each
view has its own URL (`/`, `?view=job-seeker`, `?view=employer`), so links are shareable and
the browser's back button works.

- **Job Seeker** - upload your CV and a job description, get a match score, missing skills,
  and concrete edits to improve your chances, delivered in a professional, encouraging tone.
  Below 75% the agent adds a targeted improvement plan for reaching that bar, with upskilling
  course suggestions. Every run also suggests similar roles of the same kind that your CV
  already supports, so you know what else to search for alongside the application.
- **Employer** - paste a job description once, upload multiple candidate CVs, and get a ranked
  shortlist by match percentage. Candidates at 75% or above get a one-click "Schedule Google
  Meet interview" action, pre-filled with the candidate's email (extracted from their CV).
- **Assistant** - a chat that answers questions about how the product works, grounded in a
  product reference rather than the model's own guesses.

Both views share the same core agent, packaged as a small, reusable product
([`ats_agent`](./ats_agent), `ATSAgent`) rather than a one-off script.

The API key and model are **server-side configuration only** - visitors never see or enter
either; there's no key input and no model name anywhere in the UI.

## Demo

![Employee 360 walkthrough](docs/demo.gif)

Starting from the landing page: a job seeker picks their view and checks a CV against a Data
Engineer role. It comes back at 62% - short of the 75% bar, so the view adds a plan for
reaching it and courses for the biggest gaps, then similar roles in the same family as the
role being applied for, each with search keywords. The nav bar then switches to the employer
view, which bulk-screens three CVs into a ranked shortlist and schedules an interview with the
top candidate.

*Animation not playing?* GitHub puts a play control on animated images and holds them still if
your system prefers reduced motion. The same walkthrough is in
**[`docs/demo.mp4`](docs/demo.mp4)** (1.1 MB), which plays with normal video controls.

> Recorded with sample CVs. The analysis text in the recording comes from a stubbed model so
> the walkthrough is reproducible without an API key - the interface, charts and usage
> counters are the real app.

## Features

- Landing page with the product overview, how-it-works, an embedded demo and an FAQ, plus
  two cards for choosing a view - the whole card is the link
- URL-routed views with a persistent nav bar; back/forward and shareable links both work
- In-app assistant: a conversational view for questions about the product, answering only
  from a curated reference whose numbers are interpolated from the app's own constants, so
  it can't drift out of date or invent features
- Premium black-and-orange dark theme, set via `.streamlit/config.toml` plus a small
  brand stylesheet (`views/theme.py`) - simple system sans throughout
- Live usage stats in the header (CVs analysed, roles matched, sessions helped)
- Upload CVs and job descriptions as PDF, DOCX, or TXT
- Every CV is first converted to clean, structured Markdown by the model, and that version is
  reused across every subsequent call for the same CV - cuts noise from PDF/DOCX extraction
  (headers, page numbers, stray line breaks) and keeps token usage predictable
- Professional, cordial tone throughout - findings and gaps are stated honestly but framed
  constructively, never bluntly
- Structured, validated output (Pydantic) with:
  - overall match percentage and verdict
  - matched vs. missing skills, with a bar-chart breakdown
  - strengths and gaps
  - actionable suggestions to improve the CV
- Employer view screens up to 20 CVs per run, ranks them by match %, and charts the ranked
  scores
- At 75%+ match, the Employer view offers a "Schedule Google Meet interview" action: the
  candidate's email is extracted from their CV (editable if missed or wrong), and the button
  opens a pre-filled Google Calendar event - no Google account/OAuth setup required. The
  employer picks the final time and adds Google Meet video conferencing from Calendar.
- Below a 75% match, the Job Seeker view adds:
  - a gap analysis + specific, prioritized action items to reach 75%, written to encourage the
    candidate to keep going and upskill rather than to discourage them
  - upskilling suggestions - course/certification *types* (not specific real courses) aimed
    at the biggest skill gaps versus the role
- On every Job Seeker run, whatever the score, the view also suggests **similar roles** of the
  same kind as the job description the candidate supplied - roles their CV already supports -
  with search keywords for each. These are AI-inferred role suggestions from the CV, **not live
  vacancies**: the agent has no job-board access, so it never names a company that is hiring or
  claims a specific opening exists.
- Runs on **Google Gemini's free tier** (`gemini-2.5-flash` by default) - no paid API required
- Dockerized for hosting as a service (Render, Railway, Fly.io, or any container host)

## Project structure

```
app.py                    Entry point: routes ?view= to the landing page or a view
.streamlit/config.toml    Black/orange theme (colours, fonts, radii, chart palette)
views/
  landing.py               Landing page: overview, view chooser, demo, FAQ
  assistant.py              Assistant view - grounded chat about the product
  router.py                  Query-param routing (one URL per view)
  theme.py                   Brand chrome: stylesheet, nav bar, stat tiles
  job_seeker.py             Job Seeker view - single CV vs. one job description
  employer.py                Employer view - bulk CV screening + ranked shortlist
  common.py                   Shared UI helpers (API key lookup, result rendering, counters)
ats_agent/
  agent.py                  ATSAgent - the product's core (cv_to_markdown, analyze,
                             suggest_improvement_plan, suggest_jobs)
  models.py                   Pydantic schemas: MatchResult, ImprovementPlan, JobSuggestions
  parsers.py                   PDF/DOCX/TXT text extraction
  prompts.py                   System prompts for each agent capability (tone included)
  knowledge.py                  Product reference + rules behind the in-app assistant
  scheduling.py                 CV email extraction + Google Calendar meeting link builder
  stats.py                       Persistent usage counters behind the header stats
Dockerfile                 Container image for hosting the app as a service
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Get a **free** Gemini API key at https://aistudio.google.com/apikey and set it as a server-side
environment variable - this is the only place it's ever configured:

```bash
cp .env.example .env   # then edit .env
export GEMINI_API_KEY=your-gemini-api-key
```

## Run locally

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501). You'll land on the
overview page; pick a view from there, or go straight to one with `?view=job-seeker`,
`?view=employer` or `?view=assistant`.

### The assistant

`?view=assistant` is a chat for questions about the product. It answers only from the
reference in `ats_agent/knowledge.py`, which interpolates the app's real constants (score
thresholds, the CV-per-run limit, accepted formats, meeting length), so the numbers it quotes
are the ones the code enforces. It is told to say it doesn't know rather than invent an answer,
never to disclose the model or any server configuration, and it cannot see anyone's CV or
results - those live in the view that produced them, which is a separate session.

## Configuration

| Env var | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | Gemini API key (server-side only, required) | none - the app shows a "not configured" error until set |
| `ATS_AGENT_MODEL` | Gemini model to use (server-side only) | `gemini-2.5-flash` |
| `ATS_STATS_PATH` | Where the usage counters are stored | `data/usage_stats.json` |

### Usage stats

The three figures in the header are **real counters**, incremented only when a run actually
succeeds - they start at zero on a fresh deployment and are not seeded with a marketing
number. `cvs_analyzed` counts CVs processed, `roles_matched` counts job descriptions matched
against, and `sessions_helped` counts visits that completed at least one run.

`sessions_helped` deliberately says *sessions*, not people: moving between views is a full
page load and therefore a new Streamlit session, and nothing stable identifies a browser
across loads, so one person who uses both views counts twice. Counting sessions is the
honest description of what the number actually measures.

They live in a JSON file at `ATS_STATS_PATH`. Container filesystems are ephemeral, so **mount a
volume at that path** (or point it at one) if you want the counts to survive a redeploy.

## Hosting as a service

Build and run the container:

```bash
docker build -t employee360 .
docker run -p 8501:8501 -e GEMINI_API_KEY=your-gemini-api-key employee360
```

Then deploy the image to any container host (Render, Railway, Fly.io, AWS/GCP/Azure container
services, etc.), setting `GEMINI_API_KEY` as an environment variable/secret on the host - never
in client-visible config. Most of these platforms will build directly from this repo's
`Dockerfile` without any extra config.

**Note on the free tier:** Gemini's free tier enforces per-minute request limits, and a single
run makes several calls. Screening one CV in the Employer view costs two (Markdown conversion,
then analysis), so bulk screening burns through the per-minute quota quickly - it screens CVs
one at a time and surfaces per-candidate errors (including rate limits) inline rather than
aborting the batch. A Job Seeker run costs three when the CV clears 75% (conversion, analysis,
similar roles) and four when it doesn't (plus the improvement plan). For heavy traffic, budget
for a paid Gemini tier or add request throttling/queuing in front of the agent.

## Using the agent programmatically

```python
from ats_agent import ATSAgent, STRONG_MATCH_THRESHOLD

agent = ATSAgent()  # reads GEMINI_API_KEY from the environment

resume_md = agent.cv_to_markdown(resume_text)  # clean once, reuse across every call below
result = agent.analyze(resume_md, job_description_text)

print(result.match_percentage, result.verdict)
print(result.missing_skills)

if result.match_percentage < STRONG_MATCH_THRESHOLD:
    plan = agent.suggest_improvement_plan(resume_md, job_description_text, result)
    print(plan.gap_analysis, plan.action_items)
    for course in plan.recommended_courses:
        print(course.skill_or_topic, "->", course.course_suggestion)

# Pass the job description to get similar roles of the same kind; omit it for the
# best overall fits for the CV.
jobs = agent.suggest_jobs(resume_md, job_description_text)
for job in jobs.suggestions:
    print(job.title, job.search_keywords)
```
