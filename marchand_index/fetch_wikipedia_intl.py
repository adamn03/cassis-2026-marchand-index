"""Fetch multi-language Wikipedia pageviews for the 774-skater pool (A12).

Adds a SEPARATE flow component `wiki_intl_12mo` = sum of per-article pageviews
over the locked non-English hockey-market editions {sv,fi,cs,ru,de,sk,fr},
over the FIXED A11 window [2025-04-18, 2026-04-17] (hardcoded — diverges from
the en fetcher's run-time window). Each player's wikidata_qid is REUSED from
raw/wiki_pageviews.csv (A1 occupation-checked resolver); no re-resolution.

Writes:
  pilot2/raw/wiki_intl_pageviews.csv
    player_id, full_name, wikidata_qid, editions_available, editions_fetched,
    wiki_intl_12mo, per_edition_json, window_start, window_end, fetch_date,
    intl_match
  pilot2/raw/wiki_intl_daily.csv
    player_id, edition, n_days, daily_views
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONTACT_UA, RAW_DIR, atomic_write_csv, load_csv, session  # noqa: E402

PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
WD = "https://www.wikidata.org/w/api.php"

# A11 FIXED window, hardcoded (NOT run-time). [2025-04-18 00:00 UTC, 2026-04-18).
WINDOW_START = "20250418"
WINDOW_END = "20260417"

# Locked hockey-market edition whitelist (A12; locked before fetch).
WHITELIST = ("sv", "fi", "cs", "ru", "de", "sk", "fr")


def window_strings() -> tuple[str, str, str]:
    """Return (fixed_start, fixed_end, today_iso). Only fetch_date is dynamic."""
    return WINDOW_START, WINDOW_END, dt.date.today().isoformat()
