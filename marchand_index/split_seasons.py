"""A52: collapse the 921-day attention window into a per-player-per-season panel.

WHY. After A51 widened the window to three seasons, the dataset was split
between two shapes. The NHL-side files (`nhl_skill.csv`, `nhl_onice.csv`,
`cap_hits.csv`) carry one row per player per season — 2,919 rows each. The
attention files carried one row per player covering the whole 921-day window.
Nothing could be joined on `(player_id, season)` without a slice step written
by hand each time, and `compute_oaq.py` — which still assumes one row per
player — silently triple-counts when handed the new NHL files.

This script writes the missing side of that join: `raw/attention_by_season.csv`,
one row per player per season, same shape and same season keys as
`nhl_skill.csv`.

WHAT IS AND IS NOT SLICEABLE. Three of the five OAQ components are stored as
daily series and slice exactly. Two are not, and the difference is a property
of the source, not of this code:

  SLICEABLE (exact)
    wiki_en        raw/wiki_daily.csv        921 daily counts per player
    wiki_intl      raw/wiki_intl_daily.csv   921 daily counts per player-edition
    reddit_*       raw/reddit_detail.csv joined to the corpus `created_utc`

  NOT SLICEABLE (season-invariant, carried forward unchanged with a flag)
    trends_12mo    Google Trends was fetched as ONE window-level index per
                   player. The weekly series was never retained, and re-fetching
                   per season would re-scale every value against a different
                   window maximum, so the three seasons would not be comparable
                   to each other OR to the existing column. Repeated per season
                   and flagged `trends_season_invariant=1`.
    social         Follower counts are a STOCK observed once at fetch time, not
                   a flow. There is no historical series to slice.

A season-invariant column repeated across three rows is NOT evidence about that
season. Any model consuming this file must either drop those columns or absorb
them in a player-level term — treating them as season-varying would attribute a
career-level constant to a single year. The flag column exists so that mistake
has to be made deliberately.

SEASON BOUNDS are the regular season only (first to last regular-season game),
taken from raw/game_attendance.csv, NOT the calendar year and NOT the playoffs.
Off-season days fall outside every season and are deliberately dropped: they
belong to no season's on-ice production and would otherwise be double-counted
or arbitrarily assigned.

Writes: marchand_index/raw/attention_by_season.csv
  player_id, full_name, season, wiki_en, wiki_intl, wiki_intl_editions,
  reddit_mentions, reddit_upvotes, trends_12mo, trends_season_invariant,
  season_start, season_end, season_days, fetch_date
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (RAW_DIR, WINDOW_START_DATE, atomic_write_csv,  # noqa: E402
                     load_csv, load_players)

csv.field_size_limit(10 ** 9)

OUT_CSV = RAW_DIR / "attention_by_season.csv"
OUT_FIELDS = [
    "player_id", "full_name", "season", "wiki_en", "wiki_intl",
    "wiki_intl_editions", "reddit_mentions", "reddit_upvotes", "trends_12mo",
    "trends_season_invariant", "season_start", "season_end", "season_days",
    "fetch_date",
]
CORPUS_DIR = Path(__file__).parent / "cache" / "reddit_corpus"


def season_bounds() -> dict[str, tuple[dt.date, dt.date]]:
    """{season: (first, last)} regular-season game dates, read from the
    attendance table so the bounds always match the games actually played."""
    days: dict[str, list[str]] = collections.defaultdict(list)
    for r in load_csv(RAW_DIR / "game_attendance.csv"):
        if r.get("game_type") == "regular" and r.get("game_date"):
            days[r["season"]].append(r["game_date"])
    return {s: (dt.date.fromisoformat(min(v)), dt.date.fromisoformat(max(v)))
            for s, v in sorted(days.items())}


def slice_daily(vec: list[int], a: dt.date, b: dt.date) -> int:
    """Inclusive sum of a 921-day window vector between two dates."""
    lo = (a - WINDOW_START_DATE).days
    hi = (b - WINDOW_START_DATE).days + 1
    return sum(vec[max(0, lo):max(0, hi)])


def load_daily(path: Path, key: str) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for r in load_csv(path):
        vec = [int(x or 0) for x in r["daily_views"].split("|")]
        out.setdefault(r[key], [0] * len(vec))
        acc = out[r[key]]
        for i, v in enumerate(vec):
            acc[i] += v
    return out


def load_reddit_dates() -> dict[str, int]:
    """submission_id -> created_utc, from the Arctic Shift corpus."""
    out: dict[str, int] = {}
    for p in glob.glob(str(CORPUS_DIR / "*.jsonl")):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                    out[o["id"]] = int(o["created_utc"])
                except Exception:
                    continue
    return out


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    bounds = season_bounds()
    print(f"season bounds (regular season only):")
    for s, (a, b) in bounds.items():
        print(f"  {s}  {a} -> {b}  ({(b - a).days + 1} days)")

    en = load_daily(RAW_DIR / "wiki_daily.csv", "player_id")
    intl = load_daily(RAW_DIR / "wiki_intl_daily.csv", "player_id")
    n_ed: collections.Counter = collections.Counter()
    for r in load_csv(RAW_DIR / "wiki_intl_daily.csv"):
        n_ed[r["player_id"]] += 1

    sub_ts = load_reddit_dates()
    print(f"corpus submissions dated: {len(sub_ts):,}")

    men: dict[tuple[str, str], int] = collections.Counter()
    upv: dict[tuple[str, str], int] = collections.Counter()
    unmatched = 0
    epoch = {s: (int(dt.datetime.combine(a, dt.time(), dt.timezone.utc).timestamp()),
                 int(dt.datetime.combine(b, dt.time(23, 59, 59),
                                         dt.timezone.utc).timestamp()))
             for s, (a, b) in bounds.items()}
    for r in load_csv(RAW_DIR / "reddit_detail.csv"):
        ts = sub_ts.get(r["submission_id"])
        if ts is None:
            unmatched += 1
            continue
        for s, (lo, hi) in epoch.items():
            if lo <= ts <= hi:
                men[(r["player_id"], s)] += 1
                try:
                    upv[(r["player_id"], s)] += max(0, int(float(r["score"])))
                except (TypeError, ValueError):
                    pass
                break
    print(f"reddit rows unmatched to a corpus date: {unmatched}")

    trends = {r["player_id"]: r.get("trends_12mo", "")
              for r in load_csv(RAW_DIR / "trends.csv")}

    rows = []
    for p in load_players():
        pid = p["player_id"]
        for s, (a, b) in bounds.items():
            rows.append({
                "player_id": pid,
                "full_name": p["full_name"],
                "season": s,
                "wiki_en": slice_daily(en[pid], a, b) if pid in en else "",
                "wiki_intl": slice_daily(intl[pid], a, b) if pid in intl else "",
                "wiki_intl_editions": n_ed.get(pid, 0),
                "reddit_mentions": men.get((pid, s), 0),
                "reddit_upvotes": upv.get((pid, s), 0),
                "trends_12mo": trends.get(pid, ""),
                "trends_season_invariant": 1,
                "season_start": a.isoformat(),
                "season_end": b.isoformat(),
                "season_days": (b - a).days + 1,
                "fetch_date": fetch_date,
            })

    atomic_write_csv(OUT_CSV, rows, OUT_FIELDS)

    print(f"\nWrote {OUT_CSV}  ({len(rows)} rows = "
          f"{len(rows)//len(bounds)} players x {len(bounds)} seasons)")
    for s in bounds:
        sub = [r for r in rows if r["season"] == s]
        we = sum(int(r["wiki_en"] or 0) for r in sub)
        wi = sum(int(r["wiki_intl"] or 0) for r in sub)
        rm = sum(r["reddit_mentions"] for r in sub)
        ru = sum(r["reddit_upvotes"] for r in sub)
        nz = sum(1 for r in sub if int(r["wiki_en"] or 0) > 0)
        print(f"  {s}  wiki_en={we:>10,}  wiki_intl={wi:>9,}  "
              f"reddit_men={rm:>7,}  reddit_upv={ru:>9,}  players_nonzero={nz}")

    # Reconciliation: sliced season totals must not exceed the window totals.
    tot_en = sum(sum(v) for v in en.values())
    got_en = sum(int(r["wiki_en"] or 0) for r in rows)
    print(f"\n  wiki_en: {got_en:,} of {tot_en:,} window views inside a regular "
          f"season ({100*got_en/tot_en:.1f}%; remainder is off-season/playoff)")


if __name__ == "__main__":
    main()
