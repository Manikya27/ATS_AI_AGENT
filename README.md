# Employee 360

An AI agent that acts as an ATS (Applicant Tracking System), served as a small website: a
landing page explains the product, and visitors choose which of the two views to enter. Each
view has its own URL (`/`, `?view=job-seeker`, `?view=employer`), so links are shareable and
the browser's back button works.

- **Job Seeker** - upload your CV and a job description, get a match score, missing skills,
  and concrete edits to improve your chances, delivered in a professional, encouraging tone.
  Every run also tells you which of the role's own words your CV never says, how to
  restructure the document so it survives a skim, and which similar roles your CV already
  supports. Below 75% the agent adds a targeted improvement plan for reaching that bar, with
  upskilling course suggestions; at 75% or above it switches to interview preparation - the
  questions this role and your CV are likely to produce, and what to bring to each answer.
- **Employer** - paste a job description once, upload multiple candidate CVs, and get a ranked
  shortlist by match percentage. Candidates at 75% or above get a one-click "Schedule Google
  Meet interview" action, pre-filled with the candidate's email (extracted from their CV).
  An optional talent pool keeps screened CVs so a role you post later surfaces the candidates
  you have already seen.
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
- **Keyword screen** (Job Seeker, every run): the terms the job description screens on,
  each marked *present*, *worded differently*, or *missing*, split into required and
  preferred, with a note on what to do about each and a covered-vs-missing chart. Keyword
  filters match on the words themselves, so a CV can hold exactly the right experience under
  the wrong label and never be read - "worded differently" is the cheapest fix on the page.
  The prompt refuses to recommend keyword stuffing or hidden keyword blocks, and tells the
  candidate to add only terms their real experience supports.
- **Format review** (Job Seeker, every run): how the CV reads today, the section order that
  would suit this particular role, and specific layout/phrasing changes ranked high, medium
  or low impact. It judges the cleaned text, so it comments on structure and wording rather
  than fonts or margins it cannot see.
- **Interview prep** (Job Seeker, at 75%+): once the CV clears the bar it has done its job,
  so the view switches from fixing the CV to preparing for the conversation. 8-12 questions
  this pairing of role and CV is likely to produce, ordered by how reliably each comes up,
  each with why it's expected, what a strong answer covers, and which things already on the
  CV are the best material for it - plus a few questions to ask the interviewer. It
  deliberately includes the awkward ones (a half-met requirement, a short stint, a gap
  between roles), because an interviewer will ask and a prepared candidate answers calmly.
  These are **predicted from the job description and the CV** - nothing here has seen an
  employer's real interview or question bank - and the prompt gives the shape of a good
  answer rather than a script to memorise.
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
- **Talent pool** (Employer, opt-in): tick a box to save a screening run's CVs, and every
  job description screened afterwards is also matched against them. Saved candidates scoring
  75%+ appear in their own section below the shortlist, and a CV in the current upload that
  is already in the pool is flagged as screened before. At most 10 saved CVs are re-scored
  per run, picked by plain word overlap with the role (no model call) because each actual
  scoring costs a request. Entries are deleted automatically 90 days after they were last
  screened, and the whole pool can be cleared from the view.
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
                             review_cv, suggest_improvement_plan, prepare_interview,
                             suggest_jobs)
  models.py                   Pydantic schemas: MatchResult, CVReview, ImprovementPlan, ...
  parsers.py                   PDF/DOCX/TXT text extraction
  prompts.py                   System prompts for each agent capability (tone included)
  knowledge.py                  Product reference + rules behind the in-app assistant
  scheduling.py                 CV email extraction + Google Calendar meeting link builder
  talent_pool.py                 Opt-in storage of screened CVs + the lexical pre-ranker
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
| `ATS_TALENT_POOL_PATH` | Where opt-in saved CVs are stored | `data/talent_pool.json` |
| `ATS_TALENT_POOL_RETENTION_DAYS` | How long a saved CV survives after it was last screened | `90` |

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

### What is and isn't stored

A CV uploaded in the **Job Seeker** view is read in memory, sent to Gemini for analysis, and
forgotten. It is never written to disk.

The **Employer** view's talent pool is the one exception in the product, and it is opt-in per
screening run. When the box is ticked, each screened CV is saved as:

- the cleaned Markdown text of the CV (truncated to 20,000 characters)
- the filename it was uploaded under
- the email address extracted from it

The original uploaded file is not kept. Entries are keyed by email where the CV has one, so a
re-upload updates that candidate instead of duplicating them, and they are deleted
automatically `ATS_TALENT_POOL_RETENTION_DAYS` days after they were last screened. The whole
pool can be cleared from the Employer view.

Two things to be clear about before enabling it:

- **There are no user accounts.** The pool belongs to the deployment, so everyone using the
  Employer view of the same instance sees the same saved candidates. If you host this for more
  than one employer, add authentication and scope the pool per account first.
- **Saved CVs are personal data.** Retaining a candidate's details needs a lawful basis under
  GDPR and equivalent regimes, and candidates generally have a right to see and delete what you
  hold. The retention window and the delete button exist to help with that; they are not by
  themselves a compliance programme.

Like the counters, the pool lives on the container filesystem, so mount a volume at
`ATS_TALENT_POOL_PATH` if it should survive a redeploy.

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
run makes several calls.

| Run | Calls |
| --- | --- |
| Job Seeker, CV at 75%+ | 5 - conversion, analysis, keyword/format review, similar roles, interview prep |
| Job Seeker, CV below 75% | 5 - the same, with the improvement plan in place of interview prep |
| Employer, per uploaded CV | 2 - conversion, then analysis |
| Employer, per talent-pool CV re-screened | 1 - already stored as clean Markdown |

Bulk screening therefore burns through the per-minute quota quickly. It screens CVs one at a
time and surfaces per-candidate errors (including rate limits) inline rather than aborting the
batch, and the talent pool is capped at 10 re-screens per run for the same reason. For heavy
traffic, budget for a paid Gemini tier or add request throttling/queuing in front of the
agent.

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
else:
    # The CV already clears the bar, so the useful help is the interview.
    prep = agent.prepare_interview(resume_md, job_description_text, result)
    for q in prep.questions:
        print(f"[{q.likelihood}] {q.question}")
        print("   ", q.how_to_answer)

# Which of the role's own terms the CV never says, plus how to lay the CV out.
review = agent.review_cv(resume_md, job_description_text)
for hit in review.keywords:
    if hit.status != "present":
        print(hit.importance, hit.status, hit.keyword, "->", hit.advice)
print(review.suggested_structure)

# Pass the job description to get similar roles of the same kind; omit it for the
# best overall fits for the CV.
jobs = agent.suggest_jobs(resume_md, job_description_text)
for job in jobs.suggestions:
    print(job.title, job.search_keywords)
```
