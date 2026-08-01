"""A45 — Phase A driver: write attention_affiliation.csv.

Reads the existing reddit corpus and project CSVs, labels every mention pair
as own / other / neutral relative to the player's team at that moment,
normalizes by each subreddit's submission volume, and writes one row per pool
player. No network calls, no LLM, no sentiment.

Canonical output lives in `marchand_index/` (code reads from there); a
deliverable copy is mirrored into `final_dataset/affiliation/` per the
convention in `final_dataset/README.md`.

Run from inside `marchand_index/`:

    python compute_affiliation.py
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pandas as pd

import affiliation as aff

PILOT_DIR = Path(__file__).parent
RAW_DIR = PILOT_DIR / "raw"
CORPUS_DIR = PILOT_DIR / "cache" / "reddit_corpus"
OUT_PATH = PILOT_DIR / "attention_affiliation.csv"
DELIVERABLE_DIR = PILOT_DIR.parent / "final_dataset" / "affiliation"

# BLOCKED — do not publish to final_dataset/ yet.
#
# `raw/reddit_detail.csv` was built by fetch_reddit.py under the A22 rule:
# each player was searched ONLY in r/hockey, r/nhl, r/fantasyhockey, and the
# team subreddit(s) they were rostered on inside the window. Rival subreddits
# were never scanned for that player.
#
# The `own` and `neutral` buckets are therefore valid, but `other` is empty by
# construction: 551 of 771 players have rival_reach 0, and `rival_reach` maxes
# out at 3 because it can only count a player's own FORMER team subs. The
# `other_*`, `own_share`, `rival_reach`, and `top_rival` columns measure trade
# history, not rival-fanbase attention.
#
# Fix requires re-matching all 771 players against all 36 corpus subreddits
# (the corpus itself holds all 250,004 submissions — only the matching was
# scoped). Flip this to True once that re-scan lands.
PUBLISH_DELIVERABLE = False


def build_submission_index(corpus_dir: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    """Scan the JSONL corpus once into (submission frame, sub_volume).

    The corpus is ~125MB over 38 files, so this runs once and everything
    downstream works off the returned frame. Malformed lines are skipped
    rather than aborting the run.
    """
    ids: list[str] = []
    subs: list[str] = []
    times: list[int] = []
    volume: dict[str, int] = {}

    for path in sorted(corpus_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sub = str(rec["subreddit"])
                ids.append(str(rec["id"]))
                subs.append(sub)
                times.append(int(rec["created_utc"]))
                volume[sub] = volume.get(sub, 0) + 1

    index = pd.DataFrame(
        {
            "submission_id": ids,
            "subreddit": subs,
            "created_at": pd.to_datetime(times, unit="s"),
        }
    )
    return index, volume


def main() -> None:
    players = pd.read_csv(PILOT_DIR / "players.csv")
    movers = pd.read_csv(PILOT_DIR / "mover_dates.csv")
    market = pd.read_csv(PILOT_DIR / "market_proxy.csv")
    detail = pd.read_csv(RAW_DIR / "reddit_detail.csv")

    print(f"corpus scan: {CORPUS_DIR}")
    index, sub_volume = build_submission_index(CORPUS_DIR)
    print(f"  {len(index):,} submissions across {len(sub_volume)} subreddits")

    venue_map = aff.build_venue_map(market)
    timeline = aff.build_move_timeline(movers)
    print(f"  {len(timeline)} players carry at least one dated move")

    # Any corpus subreddit that is neither a known team venue nor explicitly
    # neutral would be silently bucketed as neutral, inflating the
    # unattributable share. Surface it instead.
    unmapped = [
        s
        for s in sub_volume
        if s.lower() not in aff.NEUTRAL_SUBS and aff.venue_team(s, venue_map) is None
    ]
    if unmapped:
        print(f"  WARNING unmapped subreddits: {sorted(unmapped)}")

    labelled = aff.label_mentions(detail, index, players, venue_map, timeline)
    counts = labelled["bucket"].value_counts()
    total = len(labelled)
    print(f"  {total:,} in-window mention pairs")
    for bucket in ("own", "other", "neutral"):
        n = int(counts.get(bucket, 0))
        print(f"    {bucket:8} {n:>8,}  ({n / total:.1%})")

    out = aff.aggregate_players(labelled, sub_volume, players)

    tmp = OUT_PATH.with_suffix(".csv.tmp")
    out.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, OUT_PATH)
    print(f"wrote {OUT_PATH} ({len(out)} rows, {int(out['low_n'].sum())} low_n)")

    if PUBLISH_DELIVERABLE:
        DELIVERABLE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OUT_PATH, DELIVERABLE_DIR / OUT_PATH.name)
        print(f"copied to {DELIVERABLE_DIR / OUT_PATH.name}")
    else:
        print(
            "NOT copied to final_dataset/ — the other/rival columns are not yet "
            "valid; see PUBLISH_DELIVERABLE above."
        )


if __name__ == "__main__":
    main()
