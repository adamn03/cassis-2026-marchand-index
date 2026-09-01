"""Restore the pre-registered A11/A14 attention window in the composite inputs.

THE DEFECT. A11 and A14 lock the attention window at a fixed 365 days ending
2026-04-17, the last day of the 2025-26 regular season. A51/A52 widened
`_common.WINDOW_START_DATE` to 2023-10-10 so the three-season panel could be
built from one pass of collection. Every fetcher imports that constant, so the
`*_12mo` totals silently became 921-day totals -- 2.5 seasons, including two
offseasons -- while still carrying `12mo` in the column name and still being
matched against a SINGLE season of production.

Measured on the first pooled player: `wiki_12mo` read 166,992 against a true
365-day total of 71,385. Across the pool the stored value equalled the full
921-day sum for 956 of 973 rows.

This is a bug against a locked rule, not a design change, so the fix restores
A11 rather than amending it. No re-fetch is needed: the daily vectors already
hold all 921 days, and the A11 window is their last 365 entries. Reddit carries
no date in `reddit_detail.csv`, but the cached corpus retains `created_utc` per
submission and joins on `submission_id`.

WHAT IS AND IS NOT REPAIRED
  wiki_12mo          recomputed  (last 365 of wiki_daily)
  wiki_intl_12mo     recomputed  (last 365 of wiki_intl_daily, summed
                                  across editions)
  reddit_*_12mo      recomputed  (corpus created_utc inside the A11 window)
  trends_12mo        LEFT AS IS -- it is a MEAN of a weekly index normalised to
                     a fixed anchor, not a sum, so it does not scale with window
                     length the way a total does; and the weekly series was not
                     retained, so a 365-day mean cannot be recovered without a
                     re-fetch. Disclosed rather than silently mixed.

Originals are written alongside as `*.pre_a11repair.csv` before anything is
overwritten.

Writes (in place, atomically): raw/wiki_pageviews.csv,
raw/wiki_intl_pageviews.csv, raw/reddit_counts.csv
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _common import (LEGACY_WINDOW_START_DATE, RAW_DIR,  # noqa: E402
                     WINDOW_END_DATE, atomic_write_csv)

A11_DAYS = (WINDOW_END_DATE - LEGACY_WINDOW_START_DATE).days + 1   # 365
LOWER = dt.datetime(LEGACY_WINDOW_START_DATE.year, LEGACY_WINDOW_START_DATE.month,
                    LEGACY_WINDOW_START_DATE.day,
                    tzinfo=dt.timezone.utc).timestamp()
UPPER = dt.datetime(WINDOW_END_DATE.year, WINDOW_END_DATE.month,
                    WINDOW_END_DATE.day,
                    tzinfo=dt.timezone.utc).timestamp() + 86400.0


def tail_sum(vec: str, n: int = A11_DAYS) -> float | None:
    """Sum the last `n` daily values. A vector shorter than the window is left
    alone -- a partial series summed as though complete would understate that
    player against everyone else."""
    if not isinstance(vec, str) or not vec:
        return None
    vals = [float(x) for x in vec.split("|") if x != ""]
    if len(vals) < n:
        return None
    return float(sum(vals[-n:]))


def backup(path: Path) -> None:
    dest = path.with_suffix(".pre_a11repair.csv")
    if not dest.exists():
        shutil.copy2(path, dest)


def repair_wiki() -> None:
    pv_path, wd_path = RAW_DIR / "wiki_pageviews.csv", RAW_DIR / "wiki_daily.csv"
    pv = pd.read_csv(pv_path)
    wd = pd.read_csv(wd_path)
    daily = dict(zip(wd["player_id"], wd["daily_views"]))
    before = pd.to_numeric(pv["wiki_12mo"], errors="coerce")
    pv["wiki_12mo"] = [
        "" if (s := tail_sum(daily.get(p))) is None else int(round(s))
        for p in pv["player_id"]
    ]
    pv["window_start"] = LEGACY_WINDOW_START_DATE.strftime("%Y%m%d")
    after = pd.to_numeric(pv["wiki_12mo"], errors="coerce")
    ok = before.notna() & after.notna()
    backup(pv_path)
    atomic_write_csv(pv_path, pv.to_dict("records"), list(pv.columns))
    print(f"  wiki_12mo       repaired {int(after.notna().sum())} rows; "
          f"median {before[ok].median():,.0f} -> {after[ok].median():,.0f}")


def repair_intl() -> None:
    iv_path, id_path = (RAW_DIR / "wiki_intl_pageviews.csv",
                        RAW_DIR / "wiki_intl_daily.csv")
    iv = pd.read_csv(iv_path)
    idl = pd.read_csv(id_path)
    idl["a11"] = idl["daily_views"].map(tail_sum)
    per = idl.groupby("player_id")["a11"].sum(min_count=1)
    before = pd.to_numeric(iv["wiki_intl_12mo"], errors="coerce")
    iv["wiki_intl_12mo"] = [
        "" if pd.isna(v := per.get(p)) else float(v) for p in iv["player_id"]
    ]
    iv["window_start"] = LEGACY_WINDOW_START_DATE.strftime("%Y%m%d")
    after = pd.to_numeric(iv["wiki_intl_12mo"], errors="coerce")
    ok = before.notna() & after.notna()
    backup(iv_path)
    atomic_write_csv(iv_path, iv.to_dict("records"), list(iv.columns))
    print(f"  wiki_intl_12mo  repaired {int(after.notna().sum())} rows; "
          f"median {before[ok].median():,.0f} -> {after[ok].median():,.0f}")


def repair_reddit() -> None:
    rc_path, rd_path = RAW_DIR / "reddit_counts.csv", RAW_DIR / "reddit_detail.csv"
    files = glob.glob(str(Path(__file__).parent / "cache" / "reddit_corpus" / "*.jsonl"))
    if not files:
        print("  reddit          SKIPPED - no cached corpus, dates unrecoverable")
        return
    created: dict[str, float] = {}
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if "id" in d and "created_utc" in d:
                    created[str(d["id"])] = float(d["created_utc"])
    rd = pd.read_csv(rd_path)
    rd["ts"] = rd["submission_id"].astype(str).map(created)
    matched = rd["ts"].notna().mean()
    inwin = rd[(rd["ts"] >= LOWER) & (rd["ts"] < UPPER)]
    men = inwin.groupby("player_id").size()
    ups = inwin.groupby("player_id")["score"].sum()
    rc = pd.read_csv(rc_path)
    b_m = pd.to_numeric(rc["reddit_mentions_12mo"], errors="coerce")
    have = rc["player_id"].isin(rd["player_id"].unique())
    rc["reddit_mentions_12mo"] = [
        int(men.get(p, 0)) if h else v
        for p, v, h in zip(rc["player_id"], rc["reddit_mentions_12mo"], have)
    ]
    rc["reddit_upvotes_12mo"] = [
        int(ups.get(p, 0)) if h else v
        for p, v, h in zip(rc["player_id"], rc["reddit_upvotes_12mo"], have)
    ]
    a_m = pd.to_numeric(rc["reddit_mentions_12mo"], errors="coerce")
    ok = b_m.notna() & a_m.notna()
    backup(rc_path)
    atomic_write_csv(rc_path, rc.to_dict("records"), list(rc.columns))
    print(f"  reddit          submission_id -> created_utc match "
          f"{matched * 100:.1f}%; mentions median "
          f"{b_m[ok].median():,.0f} -> {a_m[ok].median():,.0f}")


def main() -> None:
    print(f"Restoring the A11 window: {LEGACY_WINDOW_START_DATE} -> "
          f"{WINDOW_END_DATE} ({A11_DAYS} days)\n")
    repair_wiki()
    repair_intl()
    repair_reddit()
    print("\ntrends_12mo left unchanged (a normalised mean, not a window sum) "
          "- disclosed, not silently mixed.")
    print("Originals saved as raw/*.pre_a11repair.csv")


if __name__ == "__main__":
    main()
