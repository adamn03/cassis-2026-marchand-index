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


# `mover_dates.csv` names teams by nickname; everything else uses the project's
# own team codes (LA not LAK, NAS not NSH, MON not MTL, VEG not VGK). Both Utah
# names map to UTA because the franchise was renamed mid-window.
NICKNAME_TO_CODE = {
    "Ducks": "ANA",
    "Bruins": "BOS",
    "Sabres": "BUF",
    "Hurricanes": "CAR",
    "Blue Jackets": "CBJ",
    "Flames": "CGY",
    "Blackhawks": "CHI",
    "Avalanche": "COL",
    "Stars": "DAL",
    "Red Wings": "DET",
    "Oilers": "EDM",
    "Panthers": "FLA",
    "Kings": "LA",
    "Wild": "MIN",
    "Canadiens": "MON",
    "Predators": "NAS",
    "Devils": "NJ",
    "Islanders": "NYI",
    "Rangers": "NYR",
    "Senators": "OTT",
    "Flyers": "PHI",
    "Penguins": "PIT",
    "Kraken": "SEA",
    "Sharks": "SJ",
    "Blues": "STL",
    "Lightning": "TB",
    "Maple Leafs": "TOR",
    "Mammoth": "UTA",
    "Utah Hockey Club": "UTA",
    "Canucks": "VAN",
    "Golden Knights": "VEG",
    "Capitals": "WAS",
    "Jets": "WPG",
}


def build_move_timeline(
    movers: pd.DataFrame,
) -> dict[int, list[tuple[pd.Timestamp, str]]]:
    """Map player_id -> chronological [(event_date, old_team_code), ...].

    Rows whose `status` is not `"dated"` are dropped: 19 of them are Utah
    rename artifacts, not real transactions. Rows naming a team absent from
    NICKNAME_TO_CODE are dropped too; `test_nickname_map_covers_every_mover_team`
    guards against that silently hiding a real gap.
    """
    dated = movers[movers["status"] == "dated"]
    timeline: dict[int, list[tuple[pd.Timestamp, str]]] = {}
    for row in dated.itertuples(index=False):
        code = NICKNAME_TO_CODE.get(row.old_team)
        if code is None:
            continue
        timeline.setdefault(int(row.player_id), []).append(
            (pd.Timestamp(row.event_date), code)
        )
    for moves in timeline.values():
        moves.sort(key=lambda pair: pair[0])
    return timeline


def team_at(
    player_id: int,
    when: pd.Timestamp,
    end_team: str,
    timeline: dict[int, list[tuple[pd.Timestamp, str]]],
) -> str:
    """Team code the player was on at `when`.

    `end_team` is their team in `players.csv` (end of window). Walk the moves
    newest-first; every move dated strictly after `when` is undone by reverting
    to that move's `old_team`. The oldest such move wins, which is why the
    loop runs in reverse. A move dated exactly `when` has already happened.
    """
    team = end_team
    for event_date, old_team in reversed(timeline.get(int(player_id), [])):
        if event_date > when:
            team = old_team
    return team
