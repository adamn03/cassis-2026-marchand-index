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

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _common as _C  # noqa: E402

# Subreddits in the corpus that belong to no single team. r/hockey alone is
# ~37% of all mention pairs, so this bucket is large and must be reported.
NEUTRAL_SUBS = frozenset({"hockey", "nhl", "fantasyhockey"})

# The corpus holds THREE subreddits for this franchise because it changed
# identity twice inside the window: Arizona Coyotes (r/Coyotes, 2023-24) ->
# Utah Hockey Club (r/UtahHockey, 2024-25) -> Utah Mammoth (r/utahmammoth,
# 2025-26). `market_proxy.csv` lists only the current one, so the two earlier
# names are added by hand. A51 brought r/Coyotes in-window; without it, every
# Arizona-era mention is scored as neither own-fanbase nor rival.
EXTRA_SUB_ALIASES = {"utahhockey": "UTA", "coyotes": "UTA"}


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


# `mover_dates.csv` originally named teams by nickname; everything else uses the
# project's own team codes (LA not LAK, NAS not NSH, MON not MTL, VEG not VGK).
# Both Utah names map to UTA because the franchise was renamed mid-window.
#
# A38's move to dated game logs changed that file to carry NHL team codes
# instead (build_mover_list.canon_team). Identity entries for every code are
# appended below the nickname block, so the map resolves either vintage and a
# re-generated mover file cannot silently drop every row.
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
    "Coyotes": "UTA",            # A51: 2023-24 franchise name, now in-window
    "Canucks": "VAN",
    "Golden Knights": "VEG",
    "Capitals": "WAS",
    "Jets": "WPG",
}
# Game-log vintage: NHL codes, plus the project-code aliases they differ on.
NICKNAME_TO_CODE.update({c: c for c in set(NICKNAME_TO_CODE.values())})
NICKNAME_TO_CODE.update({
    "LAK": "LA", "NSH": "NAS", "MTL": "MON", "VGK": "VEG",
    "SJS": "SJ", "TBL": "TB", "NJD": "NJ", "WSH": "WAS",
    "ARI": "UTA", "UTA": "UTA",
})



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


# Measurement window, matching the rest of the project (SESSION.md
# CARRY-FORWARD). Both bounds inclusive.
# A51: window sourced from _common (2023-24 opener start, unchanged end day).
WINDOW_START = pd.Timestamp(_C.WINDOW_START_DATE)
WINDOW_END = pd.Timestamp(_C.WINDOW_END_DATE)


def label_mentions(
    detail: pd.DataFrame,
    submissions: pd.DataFrame,
    players: pd.DataFrame,
    venue_map: dict[str, str],
    timeline: dict[int, list[tuple[pd.Timestamp, str]]],
) -> pd.DataFrame:
    """Attach a own/other/neutral bucket to every mention pair.

    `detail`      : player_id, submission_id, score
    `submissions` : submission_id, subreddit, created_at
    `players`     : player_id, team_code (team at end of window)

    Returns player_id, subreddit, bucket, score. Mentions whose submission is
    absent from the index, or which fall outside the window, are dropped.
    """
    df = detail.merge(submissions, on="submission_id", how="inner")
    df = df[
        (df["created_at"] >= WINDOW_START) & (df["created_at"] <= WINDOW_END)
    ].copy()

    end_team = dict(
        zip(players["player_id"].astype(int), players["team_code"].astype(str))
    )

    buckets = []
    for row in df.itertuples(index=False):
        owner = venue_team(row.subreddit, venue_map)
        if owner is None:
            buckets.append("neutral")
            continue
        player_team = team_at(
            int(row.player_id),
            row.created_at,
            end_team.get(int(row.player_id), ""),
            timeline,
        )
        buckets.append("own" if owner == player_team else "other")

    df["bucket"] = buckets
    return df[["player_id", "subreddit", "bucket", "score"]].reset_index(drop=True)


# Minimum attributed (own + other) mentions before own_share is trustworthy.
# Median pool player has 165 total mentions and ~63% are attributable, so this
# keeps roughly the top three quartiles. Pre-registered in A45; do not tune it
# after seeing results.
LOW_N_MIN = 30


def _rates(group: pd.DataFrame, sub_volume: dict[str, int], weight: str) -> pd.Series:
    """Per-subreddit rate for one player: weight summed, divided by volume."""
    summed = group.groupby("subreddit")[weight].sum()
    volumes = pd.Series(
        {sub: sub_volume.get(sub, 0) for sub in summed.index}, dtype=float
    )
    return (summed / volumes.replace(0, np.nan)).dropna()


def aggregate_players(
    labelled: pd.DataFrame,
    sub_volume: dict[str, int],
    players: pd.DataFrame,
) -> pd.DataFrame:
    """One row per player in `players`, with volume-normalized shares.

    `sub_volume` maps subreddit name -> number of submissions collected for it.
    Dividing by it is what makes a Bruin comparable to a Hab: r/Habs carries
    ~5x r/BostonBruins' submissions despite a smaller subscriber base, so raw
    mention counts encode venue activity rather than player attention.
    """
    work = labelled.copy()
    work["unit"] = 1.0
    work["weight"] = work["score"].clip(lower=0).astype(float) + 1.0

    records = []
    by_player = dict(tuple(work.groupby("player_id")))

    for row in players.itertuples(index=False):
        pid = int(row.player_id)
        group = by_player.get(pid)
        if group is None:
            group = work.iloc[0:0]

        counts = group["bucket"].value_counts()
        own_n = int(counts.get("own", 0))
        other_n = int(counts.get("other", 0))
        neutral_n = int(counts.get("neutral", 0))
        attributed = own_n + other_n

        intensity = {}
        scored = {}
        for bucket in ("own", "other", "neutral"):
            sub = group[group["bucket"] == bucket]
            intensity[bucket] = float(_rates(sub, sub_volume, "unit").sum())
            scored[bucket] = float(_rates(sub, sub_volume, "weight").sum())

        denom = intensity["own"] + intensity["other"]
        own_share = intensity["own"] / denom if denom > 0 else np.nan

        denom_s = scored["own"] + scored["other"]
        own_share_scored = scored["own"] / denom_s if denom_s > 0 else np.nan

        rivals = group[group["bucket"] == "other"]
        rival_rates = _rates(rivals, sub_volume, "unit")
        top_rival = str(rival_rates.idxmax()) if len(rival_rates) else ""

        records.append(
            {
                "player_id": pid,
                "full_name": row.full_name,
                "team_code": row.team_code,
                "own_mentions": own_n,
                "other_mentions": other_n,
                "neutral_mentions": neutral_n,
                "attributed_mentions": attributed,
                "own_intensity": intensity["own"],
                "other_intensity": intensity["other"],
                "neutral_intensity": intensity["neutral"],
                "own_share": own_share,
                "own_share_scored": own_share_scored,
                "rival_reach": int(len(rival_rates)),
                "top_rival": top_rival,
                "low_n": attributed < LOW_N_MIN,
            }
        )

    return pd.DataFrame.from_records(records)
