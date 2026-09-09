"""Persistent usage counters behind the product's headline stats.

These are real counters, incremented only when a run actually succeeds - the
numbers shown in the UI reflect genuine usage, never a seeded marketing figure.
The file lives at ATS_STATS_PATH; on an ephemeral container mount a volume
there, or the counts reset when the container is replaced.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

STATS_PATH = Path(os.environ.get("ATS_STATS_PATH", "data/usage_stats.json"))

_LOCK = threading.Lock()


@dataclass(frozen=True)
class UsageStats:
    """Counters shown in the header."""

    people_helped: int = 0
    cvs_analyzed: int = 0
    roles_matched: int = 0


def load_stats() -> UsageStats:
    try:
        raw = json.loads(STATS_PATH.read_text())
    except (OSError, ValueError):
        return UsageStats()

    fields = UsageStats.__dataclass_fields__
    return UsageStats(**{k: int(v) for k, v in raw.items() if k in fields})


def record_run(*, cvs: int, new_person: bool) -> UsageStats:
    """Record one successful run: `cvs` CVs analysed against one role."""
    with _LOCK:
        current = load_stats()
        updated = UsageStats(
            people_helped=current.people_helped + (1 if new_person else 0),
            cvs_analyzed=current.cvs_analyzed + cvs,
            roles_matched=current.roles_matched + 1,
        )
        _write(updated)
        return updated


def _write(stats: UsageStats) -> None:
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file in the same directory, then replace atomically, so a
    # crash mid-write can't leave a truncated stats file behind.
    with tempfile.NamedTemporaryFile(
        "w", dir=STATS_PATH.parent, delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(asdict(stats), tmp)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, STATS_PATH)


def format_count(value: int) -> str:
    """Compact display form: 1240 -> '1.2K', 15300 -> '15.3K'."""
    if value < 1_000:
        return str(value)
    if value < 1_000_000:
        return f"{value / 1_000:.1f}K".replace(".0K", "K")
    return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
