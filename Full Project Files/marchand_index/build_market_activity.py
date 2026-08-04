"""A46 — derive per-team subreddit submission activity from the local corpus.

Writes `market_activity.csv`. This is a DERIVATION, not a fetch: every input
is already on disk and no network call is made.

Why this exists
---------------
`market_z`'s social component is `team_sub_subscribers` — a stock. Subreddit
submission volume is a flow, and the two barely agree (Spearman 0.299 across
the 32 teams). r/BostonBruins has more subscribers than r/Habs but roughly a
fifth of the submissions. This file makes the flow measurable so the
dependence of `OAQ_portable` on that choice can be reported.

Activity is ENDOGENOUS — a winning team's subreddit posts more, and its
players draw more mentions. It is therefore a reporting lens only and must
never become a `market_z` primary component.

Run from inside `marchand_index/`:

    python build_market_activity.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

PILOT_DIR = Path(__file__).parent
CORPUS_DIR = PILOT_DIR / "cache" / "reddit_corpus"
OUT_PATH = PILOT_DIR / "market_activity.csv"

# Matches the rest of the project (SESSION.md CARRY-FORWARD). Both inclusive.
WINDOW_START = pd.Timestamp("2025-04-18")
WINDOW_END = pd.Timestamp("2026-04-17")

# The Utah franchise was renamed mid-window, splitting its subreddit. Both
# names are the same fanbase and are summed into the canonical one that
# `market_proxy.csv` lists.
SUB_ALIASES = {"utahhockey": "utahmammoth"}

# Belong to no single team; excluded from a per-team activity measure.
NEUTRAL_SUBS = frozenset({"hockey", "nhl", "fantasyhockey"})

# Below this many in-window submissions the activity figure is treated as a
# collection artifact rather than a fanbase signal. Utah sits at 81 against
# 2,171 for the next-lowest team, so the threshold separates one known data
# hole from the real distribution.
ACTIVITY_QUALITY_MIN = 500


def count_window_submissions(corpus_dir: Path) -> dict[str, int]:
    """Canonical lowercased subreddit name -> in-window submission count.

    Neutral subreddits are excluded, aliases are folded, malformed lines are
    skipped rather than aborting the scan.
    """
    counts: dict[str, int] = {}
    start = WINDOW_START.timestamp()
    end = (WINDOW_END + pd.Timedelta(days=1)).timestamp()

    for path in sorted(corpus_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sub = str(rec["subreddit"]).lower()
                if sub in NEUTRAL_SUBS:
                    continue
                sub = SUB_ALIASES.get(sub, sub)
                stamp = int(rec["created_utc"])
                if start <= stamp < end:
                    counts[sub] = counts.get(sub, 0) + 1
    return counts


def build_activity_table(
    counts: dict[str, int], market_proxy: pd.DataFrame
) -> pd.DataFrame:
    """One row per team in `market_proxy`, with activity and a quality flag.

    Raises if any team has no corpus submissions at all — that would mean the
    venue mapping is wrong, and silently emitting a zero would corrupt the
    z-score for all 32 teams.
    """
    records = []
    for row in market_proxy.itertuples(index=False):
        sub = str(row.team_sub).lower()
        sub = SUB_ALIASES.get(sub, sub)
        n = counts.get(sub)
        if n is None:
            raise RuntimeError(
                f"no corpus submissions for team {row.team_code} (sub {row.team_sub})"
            )
        subscribers = float(row.team_sub_subscribers)
        records.append(
            {
                "team_code": row.team_code,
                "team_sub": row.team_sub,
                "sub_submissions_window": int(n),
                "submissions_per_1k_subs": round(n / (subscribers / 1000.0), 2),
                "activity_quality": "ok" if n >= ACTIVITY_QUALITY_MIN else "low",
            }
        )
    return pd.DataFrame.from_records(records)


def main() -> None:
    market = pd.read_csv(PILOT_DIR / "market_proxy.csv")
    counts = count_window_submissions(CORPUS_DIR)
    out = build_activity_table(counts, market)

    tmp = OUT_PATH.with_suffix(".csv.tmp")
    out.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, OUT_PATH)

    low = out[out["activity_quality"] == "low"]["team_code"].tolist()
    print(f"wrote {OUT_PATH} ({len(out)} rows)")
    print(f"  low-quality teams: {low or 'none'}")
    merged = out.merge(market[["team_code", "team_sub_subscribers"]], on="team_code")
    rho = merged[["team_sub_subscribers", "sub_submissions_window"]].corr(
        method="spearman"
    ).iloc[0, 1]
    print(f"  spearman(subscribers, submissions) = {rho:.3f}")


if __name__ == "__main__":
    main()
