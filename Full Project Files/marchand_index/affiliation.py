"""A45 — Phase A: reddit attention affiliation split (own / other / neutral).

Pure functions only. No file I/O, no network. The driver is
`compute_affiliation.py`.

Terminology
-----------
venue      the subreddit a mention appeared in
own        venue belongs to a team the player was on at mention time
other      venue belongs to some other team
neutral    venue belongs to no team (r/hockey, r/nhl, r/fantasyhockey)
rate       mentions in a venue divided by that venue's submission count
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Subreddits in the corpus that belong to no single team. r/hockey alone is
# ~37% of all mention pairs, so this bucket is large and must be reported.
NEUTRAL_SUBS = frozenset({"hockey", "nhl", "fantasyhockey"})

# The corpus holds both Utah subreddits because the franchise was renamed
# mid-window (Utah Hockey Club -> Utah Mammoth). `market_proxy.csv` lists only
# the current one, so the old name is added by hand.
EXTRA_SUB_ALIASES = {"utahhockey": "UTA"}


def build_venue_map(market_proxy: pd.DataFrame) -> dict[str, str]:
    """Map lowercased subreddit name -> team code.

    `market_proxy` must have `team_code` and `team_sub` columns.
    """
    venue_map = {
        str(sub).lower(): str(code)
        for sub, code in zip(market_proxy["team_sub"], market_proxy["team_code"])
    }
    venue_map.update(EXTRA_SUB_ALIASES)
    return venue_map


def venue_team(subreddit: str, venue_map: dict[str, str]) -> str | None:
    """Team code owning `subreddit`, or None if neutral or unrecognised."""
    key = str(subreddit).lower()
    if key in NEUTRAL_SUBS:
        return None
    return venue_map.get(key)
