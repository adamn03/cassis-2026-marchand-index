"""Shared utilities for pilot fetch scripts.

Atomic CSV writes per vault convention: `.tmp` -> rename.
Polite HTTP via requests-cache in this directory.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterable, Mapping

import requests_cache

PILOT_DIR = Path(__file__).parent
RAW_DIR = PILOT_DIR / "raw"
CACHE_PATH = PILOT_DIR / "cache" / "http_cache"

PLAYERS_CSV = PILOT_DIR / "players.csv"


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
