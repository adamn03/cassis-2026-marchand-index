"""Fetch 12-month Wikipedia pageview totals for each pilot player.

Per pre-registration section 3.1, this is the primary engagement signal
(weight 0.306 in the composite). Source: Wikimedia REST API, no auth.

Writes: pilot/raw/wiki_pageviews.csv with columns
  player_id, full_name, wikipedia_slug, wiki_12mo, fetch_date, window_start, window_end
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

# Make the pilot dir importable when this is run directly.
sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_players, session  # noqa: E402

USER_AGENT = "marchand-index-pilot/0.1 (https://github.com/adamn03; ana178@sfu.ca)"
BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"


def window_strings() -> tuple[str, str, str]:
    """Return (window_start, window_end, fetch_date) as YYYYMMDD / ISO date."""
    today = dt.date.today()
    end = today - dt.timedelta(days=1)        # API has 1-day lag
    start = end - dt.timedelta(days=365)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), today.isoformat()


def fetch_player(s, slug: str, start: str, end: str) -> int | None:
    url = f"{BASE}/en.wikipedia/all-access/all-agents/{slug}/daily/{start}/{end}"
    r = s.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    items = r.json().get("items", [])
    return sum(int(it["views"]) for it in items)


def main() -> None:
    start, end, fetch_date = window_strings()
    s = session(expire_hours=24)
    rows = []
    players = load_players()
    for p in players:
        slug = p["wikipedia_slug"]
        try:
            total = fetch_player(s, slug, start, end)
            print(f"{p['full_name']:<22} {slug:<40} {total}")
        except Exception as e:
            print(f"{p['full_name']}: FAILED {e!r}", file=sys.stderr)
            total = None
        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "wikipedia_slug": slug,
            "wiki_12mo": "" if total is None else total,
            "fetch_date": fetch_date,
            "window_start": start,
            "window_end": end,
        })
        time.sleep(0.5)  # be polite even with cache

    out = RAW_DIR / "wiki_pageviews.csv"
    atomic_write_csv(out, rows, [
        "player_id", "full_name", "wikipedia_slug",
        "wiki_12mo", "fetch_date", "window_start", "window_end",
    ])
    print(f"\nWrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
