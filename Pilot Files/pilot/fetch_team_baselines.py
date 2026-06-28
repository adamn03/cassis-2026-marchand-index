"""Compute per-team market baseline = mean Wikipedia 12-mo pageviews
across the team's active roster (excluding the pilot player).

Per pre-registration section 7. Inputs: pilot/raw/team_rosters.csv produced
by fetch_nhl_api.py. Output: pilot/raw/team_market_baselines.csv.

This script fetches Wikipedia pageviews for every rostered player on every
team that hosts a pilot player. ~10 teams x ~25 players = ~250 API calls.
At 0.5s each that's ~2 minutes; cached so re-runs are instant.

Resolving each rostered player to a Wikipedia article slug is best-effort:
we try "First_Last", then "First_Last_(ice_hockey)", and skip if neither
returns pageviews. Missing players reduce the per-team N but don't bias the
mean systematically.
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, session  # noqa: E402

USER_AGENT = "marchand-index-pilot/0.1 (https://github.com/adamn03; ana178@sfu.ca)"
BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"


def window_strings() -> tuple[str, str]:
    today = dt.date.today()
    end = today - dt.timedelta(days=1)
    start = end - dt.timedelta(days=365)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def fetch_views(s, slug: str, start: str, end: str) -> int | None:
    url = f"{BASE}/en.wikipedia/all-access/all-agents/{slug}/daily/{start}/{end}"
    r = s.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        return None
    items = r.json().get("items", [])
    return sum(int(it["views"]) for it in items)


def candidate_slugs(first: str, last: str) -> list[str]:
    first_s = first.replace(" ", "_")
    last_s = last.replace(" ", "_")
    return [
        f"{first_s}_{last_s}",
        f"{first_s}_{last_s}_(ice_hockey)",
    ]


def main() -> None:
    start, end = window_strings()
    s = session(expire_hours=48)

    rosters_path = RAW_DIR / "team_rosters.csv"
    if not rosters_path.exists():
        sys.exit(f"Missing {rosters_path}. Run fetch_nhl_api.py first.")

    with rosters_path.open("r", encoding="utf-8") as f:
        rosters = list(csv.DictReader(f))

    # Group by team_code.
    per_team: dict[str, list[dict]] = {}
    for r in rosters:
        per_team.setdefault(r["team_code"], []).append(r)

    out_rows = []
    detail_rows = []
    for team_code, members in per_team.items():
        views_list = []
        for m in members:
            first = m["first_name"]
            last = m["last_name"]
            views = None
            chosen_slug = ""
            for slug in candidate_slugs(first, last):
                v = fetch_views(s, slug, start, end)
                if v is not None and v > 0:
                    views = v
                    chosen_slug = slug
                    break
                time.sleep(0.2)
            detail_rows.append({
                "team_code": team_code,
                "first_name": first,
                "last_name": last,
                "position": m.get("position", ""),
                "wikipedia_slug": chosen_slug,
                "wiki_12mo": "" if views is None else views,
            })
            if views is not None:
                views_list.append(views)
            time.sleep(0.3)
        n = len(views_list)
        mean_views = (sum(views_list) / n) if n else 0
        median_views = sorted(views_list)[n // 2] if n else 0
        print(f"{team_code:>4}  N={n:>3}  mean={mean_views:,.0f}  median={median_views:,.0f}")
        out_rows.append({
            "team_code": team_code,
            "roster_n": n,
            "mean_wiki_12mo": int(mean_views),
            "median_wiki_12mo": int(median_views),
            "window_start": start,
            "window_end": end,
        })

    atomic_write_csv(RAW_DIR / "team_market_baselines.csv", out_rows, [
        "team_code", "roster_n", "mean_wiki_12mo", "median_wiki_12mo",
        "window_start", "window_end",
    ])
    atomic_write_csv(RAW_DIR / "team_market_baselines_detail.csv", detail_rows, [
        "team_code", "first_name", "last_name", "position", "wikipedia_slug", "wiki_12mo",
    ])
    print(f"\nWrote {RAW_DIR/'team_market_baselines.csv'} ({len(out_rows)} teams)")
    print(f"Wrote {RAW_DIR/'team_market_baselines_detail.csv'} ({len(detail_rows)} rows)")


if __name__ == "__main__":
    main()
