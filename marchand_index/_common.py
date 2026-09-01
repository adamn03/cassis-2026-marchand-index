"""Shared utilities for pilot2 fetch scripts.

Atomic CSV writes per vault convention: `.tmp` -> rename.
Polite HTTP via requests-cache in this directory.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable, Mapping

import requests_cache

# Console here is cp1252; canonical Wikipedia titles (Fehérváry) and other
# accented names crash print(). Force UTF-8 stdout/stderr for all fetchers.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

PILOT_DIR = Path(__file__).parent
RAW_DIR = PILOT_DIR / "raw"
CACHE_PATH = PILOT_DIR / "cache" / "http_cache"

PLAYERS_CSV = PILOT_DIR / "players.csv"

# ---------------------------------------------------------------------------
# Attention window (amendment A51 — see preregistration.md).
#
# Was the fixed 365-day A11/A14 window [2025-04-18, 2026-04-17]. Extended
# BACKWARD to the 2023-24 NHL regular-season opener so the mover panel spans
# three seasons; the END DAY IS UNCHANGED, so every previously collected
# observation stays inside the new window and remains valid.
#
# All fetchers import these instead of hardcoding dates. WINDOW_DAYS is derived,
# never a literal — daily vectors are zero-filled to exactly this length.
# ---------------------------------------------------------------------------
import datetime as _dt

WINDOW_START_DATE = _dt.date(2023, 10, 10)   # 2023-24 NHL regular-season opener
WINDOW_END_DATE = _dt.date(2026, 4, 17)      # unchanged: 2025-26 reg-season end
WINDOW_DAYS = (WINDOW_END_DATE - WINDOW_START_DATE).days + 1   # 921, inclusive

WINDOW_START = WINDOW_START_DATE.strftime("%Y%m%d")   # "20231010"
WINDOW_END = WINDOW_END_DATE.strftime("%Y%m%d")       # "20260417"

# Seasons overlapping the window (A22 season-filter rule, widened by A51).
WINDOW_SEASONS = {"20232024", "20242025", "20252026"}

# The window the COMPOSITE is defined on: a fixed 365 days ending the last day
# of the 2025-26 regular season, locked by A11 (Reddit) and A14 (en-Wikipedia).
#
# This is NOT a legacy value. WINDOW_START_DATE above governs COLLECTION, which
# A51/A52 widened to 2023-10-10 so the three-season panel could be built from one
# pass; the composite's own window never moved. Calling this constant "LEGACY"
# is what allowed every *_12mo total to drift onto the 921-day collection window
# unnoticed -- see V-A11-Window in preregistration.md. The old name is kept as an
# alias so existing imports still resolve.
COMPOSITE_WINDOW_START_DATE = _dt.date(2025, 4, 18)
COMPOSITE_WINDOW_DAYS = (WINDOW_END_DATE - COMPOSITE_WINDOW_START_DATE).days + 1  # 365
LEGACY_WINDOW_START_DATE = COMPOSITE_WINDOW_START_DATE   # deprecated alias


def window_epoch_bounds() -> tuple[int, int]:
    """[lower, upper) UTC epoch seconds for the full window, end-day inclusive."""
    lower = _dt.datetime(WINDOW_START_DATE.year, WINDOW_START_DATE.month,
                         WINDOW_START_DATE.day, tzinfo=_dt.timezone.utc).timestamp()
    upper = _dt.datetime(WINDOW_END_DATE.year, WINDOW_END_DATE.month,
                         WINDOW_END_DATE.day,
                         tzinfo=_dt.timezone.utc).timestamp() + 86400.0
    return int(lower), int(upper)


def day_index(d: _dt.date) -> int:
    """0-based index of a date inside the window (0 == WINDOW_START_DATE)."""
    return (d - WINDOW_START_DATE).days

# A browser-like UA is required for DailyFaceoff / CapWages (Next.js sites that
# 403 generic agents). NHL + Wikimedia accept any UA.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CONTACT_UA = "marchand-index/0.1 (research; ana178@sfu.ca)"

_NEXT_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)


def session(expire_hours: int = 24):
    """requests_cache session with on-disk persistence."""
    ensure_dirs()
    return requests_cache.CachedSession(
        str(CACHE_PATH),
        backend="sqlite",
        expire_after=expire_hours * 3600,
        allowable_methods=("GET",),
    )


def next_data(html: str):
    """Extract and parse the Next.js __NEXT_DATA__ JSON blob, or None."""
    m = _NEXT_RE.search(html)
    return json.loads(m.group(1)) if m else None


def atomic_write_csv(path: Path, rows: Iterable[Mapping], fieldnames: list[str]) -> None:
    """Write CSV via .tmp -> rename so partial writes never appear on disk."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(tmp, path)


def atomic_write_text(path: Path, text: str) -> None:
    """Write text via .tmp -> rename so partial writes never appear on disk."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_players() -> list[dict]:
    with PLAYERS_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))
