"""The employer's opt-in talent pool: CVs kept so a later role can find them.

This is the one place in Employee 360 that stores a person's CV. Everything
else processes uploads in memory and forgets them, and the privacy copy the
product shows job seekers says so - which is why saving here is opt-in per
screening run, capped, and expires on its own.

What is kept: the cleaned Markdown of the CV, the label it was uploaded under,
and the email extracted from it. What is not: the original file. Entries older
than the retention window are dropped whenever the pool is read, so an employer
who stops using the app stops holding the data.

The file lives at ATS_TALENT_POOL_PATH. On an ephemeral container mount a
volume there, or the pool empties when the container is replaced.

Writes are serialised with an in-process lock and land atomically, which covers
the Streamlit sessions of one server. Two replicas sharing one file could still
interleave a read-modify-write and lose an entry - run a single instance, or put
the pool behind a real database, before scaling this out.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

POOL_PATH = Path(os.environ.get("ATS_TALENT_POOL_PATH", "data/talent_pool.json"))

# How long a saved CV survives without being seen again. Personal data with no
# expiry is a liability, not a feature.
RETENTION_DAYS = int(os.environ.get("ATS_TALENT_POOL_RETENTION_DAYS", "90"))

# Ceilings on what one deployment holds. The oldest entries fall out first.
MAX_POOL_ENTRIES = 200
MAX_STORED_CHARS = 20_000

# How many saved CVs get re-scored against a new job description. Every one of
# them is a Gemini call, so the pool is pre-ranked lexically and only the most
# promising few are actually screened.
MAX_RESCREEN = 10

_LOCK = threading.Lock()

_WORD_RE = re.compile(r"[a-z0-9+#.]{2,}")

# Words too common to say anything about whether a CV suits a role. Trimming
# them keeps the pre-ranking from scoring every CV identically on "and the for".
_STOPWORDS = frozenset(
    """a an and are as at be but by for from has have in into is it its of on or that the to
    with will you your we our their they this these those role job work team experience
    years year strong ability able across including etc via using use used must should would
    who whom which while within without over under about
    """.split()
)


@dataclass(frozen=True)
class PooledCandidate:
    """One CV an employer chose to keep."""

    id: str
    label: str
    email: str | None
    resume_md: str
    added_at: str
    last_seen_at: str
    times_seen: int = 1

    @property
    def added_on(self) -> str:
        """Just the date, for display."""
        return self.added_at[:10]


def candidate_id(resume_md: str, email: str | None) -> str:
    """A stable id for one person.

    Keyed on the email when the CV has one, so an updated CV from the same
    person replaces their entry instead of creating a second. Without an email
    there is nothing better than the document itself, so a re-upload of the same
    file matches and a revised file does not.
    """
    basis = email.strip().lower() if email else " ".join(resume_md.split()).lower()
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def load_pool() -> list[PooledCandidate]:
    """Every saved candidate that hasn't expired, most recently seen first."""
    try:
        raw = json.loads(POOL_PATH.read_text())
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []

    cutoff = (_now() - timedelta(days=RETENTION_DAYS)).isoformat()
    fields = PooledCandidate.__dataclass_fields__
    entries = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            entry = PooledCandidate(**{k: v for k, v in item.items() if k in fields})
        except TypeError:
            continue
        if entry.last_seen_at >= cutoff:
            entries.append(entry)

    entries.sort(key=lambda c: c.last_seen_at, reverse=True)
    return entries


def remember(label: str, resume_md: str, email: str | None) -> PooledCandidate:
    """Add a CV to the pool, or refresh the entry that person already has."""
    now = _now().isoformat()
    entry_id = candidate_id(resume_md, email)

    with _LOCK:
        pool = load_pool()
        existing = next((c for c in pool if c.id == entry_id), None)
        entry = PooledCandidate(
            id=entry_id,
            label=label,
            email=email,
            resume_md=resume_md[:MAX_STORED_CHARS],
            added_at=existing.added_at if existing else now,
            last_seen_at=now,
            times_seen=(existing.times_seen + 1) if existing else 1,
        )
        pool = [c for c in pool if c.id != entry_id]
        pool.insert(0, entry)
        _write(pool[:MAX_POOL_ENTRIES])
    return entry


def forget(entry_id: str) -> None:
    """Delete one candidate from the pool."""
    with _LOCK:
        _write([c for c in load_pool() if c.id != entry_id])


def clear_pool() -> None:
    """Delete every saved candidate."""
    with _LOCK:
        _write([])


def rank_for_role(
    job_description: str,
    pool: list[PooledCandidate],
    *,
    exclude_ids: frozenset[str] = frozenset(),
    limit: int = MAX_RESCREEN,
) -> list[PooledCandidate]:
    """Pick which saved CVs are worth spending a model call on for this role.

    Pure word overlap - no model, no cost. It is a coarse filter and it is
    supposed to be: its only job is to put plausible candidates ahead of
    unrelated ones before the real scoring runs on the top few.
    """
    wanted = _terms(job_description)
    if not wanted:
        return []

    scored = []
    for candidate in pool:
        if candidate.id in exclude_ids:
            continue
        overlap = wanted & _terms(candidate.resume_md)
        if overlap:
            scored.append((len(overlap) / len(wanted), candidate))

    # Ties broken by recency, which load_pool has already established.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [candidate for _, candidate in scored[:limit]]


def _terms(text: str) -> frozenset[str]:
    return frozenset(w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _write(pool: list[PooledCandidate]) -> None:
    POOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Same atomic replace as the usage counters: a crash mid-write must not
    # leave a half-written pool that then reads back as empty.
    with tempfile.NamedTemporaryFile(
        "w", dir=POOL_PATH.parent, delete=False, encoding="utf-8"
    ) as tmp:
        json.dump([asdict(c) for c in pool], tmp)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, POOL_PATH)
