# ATS Match Agent

An AI agent that acts as an ATS (Applicant Tracking System): give it a job description and a
candidate's CV (PDF, DOCX, or TXT), and it scores the match percentage, lists matched/missing
skills, and suggests concrete CV improvements. Built as a Streamlit app on top of the
[`ats_agent`](./ats_agent) package, which packages the agent as a small, reusable product
(`ATSAgent`) rather than a one-off script.

## Features

- Upload a CV as PDF, DOCX, or TXT
- Provide a job description by upload or paste
- Structured, validated output (Pydantic) with:
  - overall match percentage and verdict
  - matched vs. missing skills
  - strengths and gaps
  - actionable suggestions to improve the CV
- Runs on Claude via the Anthropic API

## Project structure

```
app.py                 Streamlit UI
ats_agent/
  agent.py             ATSAgent - the product: analyze(resume_text, jd_text) -> MatchResult
  models.py             MatchResult schema (Pydantic)
  parsers.py             PDF/DOCX/TXT text extraction
  prompts.py             System prompt for the matching agent
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your Anthropic API key (or enter it in the app's sidebar at runtime):

```bash
cp .env.example .env   # then edit .env
export ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

## Configuration

| Env var | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | none - falls back to the sidebar input |
| `ATS_AGENT_MODEL` | Claude model to use | `claude-opus-5` |

## Using the agent programmatically

```python
from ats_agent import ATSAgent

agent = ATSAgent()  # reads ANTHROPIC_API_KEY from the environment
result = agent.analyze(resume_text, job_description_text)

print(result.match_percentage, result.verdict)
print(result.missing_skills)
```
