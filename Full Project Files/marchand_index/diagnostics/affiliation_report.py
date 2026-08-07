"""A45 — Phase A diagnostics.

Two questions this answers:

1. Open item #3B — Montreal holds 16 of the OAQ_portable top-100. If MON
   players also show unusually high `own_share`, their attention is
   fanbase-captive and `market_z` is under-correcting for fanbase intensity
   rather than MON genuinely over-indexing.

2. Whether `OAQ_portable` earns the name "portable". Attention concentrated
   in a player's own subreddit does not travel with him.

Run from inside `marchand_index/`:

    python -m diagnostics.affiliation_report
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

AFFIL_PATH = Path(__file__).parent.parent / "attention_affiliation.csv"


def team_own_share(affil: pd.DataFrame) -> pd.DataFrame:
    """Median own_share per team, `low_n` players excluded, highest first."""
    usable = affil[~affil["low_n"].astype(bool)]
    grouped = (
        usable.groupby("team_code")["own_share"]
        .agg(median_own_share="median", n_players="count")
        .reset_index()
    )
    return grouped.sort_values(
        "median_own_share", ascending=False
    ).reset_index(drop=True)


def main() -> None:
    affil = pd.read_csv(AFFIL_PATH)

    print("=== median own_share by team (low_n excluded) ===")
    print(team_own_share(affil).to_string(index=False))

    usable = affil[~affil["low_n"].astype(bool)]
    print()
    print("=== most road-followed players (lowest own_share) ===")
    cols = ["full_name", "team_code", "own_share", "rival_reach", "top_rival"]
    print(usable.nsmallest(20, "own_share")[cols].to_string(index=False))

    print()
    print("=== widest rival reach ===")
    print(usable.nlargest(20, "rival_reach")[cols].to_string(index=False))

    print()
    print(f"league median own_share: {usable['own_share'].median():.3f}")
    print(f"league median rival_reach: {usable['rival_reach'].median():.1f}")


if __name__ == "__main__":
    main()
