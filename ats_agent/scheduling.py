"""Interview scheduling helpers - email extraction and a Google Calendar link.

No Google account, API credentials, or OAuth flow required: the "Schedule
meeting" action just opens a pre-filled Google Calendar event-creation page
in a new tab, with the candidate already added as a guest. The employer
picks the final time and adds Google Meet video conferencing from there.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from urllib.parse import urlencode

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

DEFAULT_MEETING_HOUR = 10
DEFAULT_MEETING_DURATION_MINUTES = 30

# A CV/JD match at or above this score is considered strong enough for an
# employer to schedule an interview directly from the shortlist.
MEETING_ELIGIBLE_THRESHOLD = 75

_SATURDAY = 5


def extract_email(text: str) -> str | None:
    """Best-effort extraction of the candidate's email address from CV text."""
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def _next_business_day(from_date: datetime) -> datetime:
    next_day = from_date + timedelta(days=1)
    while next_day.weekday() >= _SATURDAY:
        next_day += timedelta(days=1)
    return next_day


def google_calendar_meeting_link(
    candidate_label: str,
    guest_email: str | None,
    match_percentage: int,
    *,
    now: datetime | None = None,
) -> str:
    """Build a pre-filled 'Add to Google Calendar' link for an interview slot.

    Defaults to a 30-minute slot at 10:00 on the next business day. The
    `dates` value carries no UTC suffix, so Calendar interprets it in the
    viewer's own timezone rather than a server-assumed one.
    """
    start = _next_business_day(now or datetime.now()).replace(
        hour=DEFAULT_MEETING_HOUR, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(minutes=DEFAULT_MEETING_DURATION_MINUTES)
    date_fmt = "%Y%m%dT%H%M%S"

    details = (
        f"Interview invite for {candidate_label} - CV/job description match: "
        f"{match_percentage}%.\n\n"
        "Scheduled via Employee 360. Click \"Add Google Meet video conferencing\" "
        "in Calendar to include a video call link before sending the invite."
    )

    params = {
        "action": "TEMPLATE",
        "text": f"Interview: {candidate_label}",
        "dates": f"{start.strftime(date_fmt)}/{end.strftime(date_fmt)}",
        "details": details,
    }
    if guest_email:
        params["add"] = guest_email

    return "https://calendar.google.com/calendar/render?" + urlencode(params)
