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


def load_players() -> list[dict]:
    with PLAYERS_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))
