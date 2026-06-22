"""Fetch MoneyPuck 5v5 on-ice play-driving features for the 774 pool (A13).

Adds three on-ice features to the §6 peer (skill) vector:
  cf_pct  = onIce_corsiPercentage   (5v5 territorial play-driving share, 0-1)
  xgf_pct = onIce_xGoalsPercentage  (5v5 shot-quality-weighted share, 0-1)
  ozs_pct = I_F_oZoneShiftStarts / (I_F_oZoneShiftStarts + I_F_dZoneShiftStarts)
            (offensive-zone-start share; neutral starts excluded, standard
            convention)

Source: MoneyPuck free season-summary skater CSV (2025-26 regular season),
downloaded once and cached in raw/. The CSV is stratified by `situation` in
{all, 5on5, 5on4, 4on5, other}; A13 LOCKS situation == '5on5' (even-strength;
all-situations re-imports the special-teams confound). Join key is
`nhl_player_id` (players.csv) == MoneyPuck `playerId` (identical NHL id space);
name-fallback only where nhl_player_id is blank.

Traded players have ONE 5v5 row per team and NO aggregate row, so rows are
collapsed per playerId by icetime-weighted mean (cf_pct, xgf_pct) and
summed-count ratio (ozs_pct). Skaters below ONICE_MIN_ICETIME_5V5 = 150 min
5v5 have the three features NULLed (onice_status=thin); compute_oaq.py's
existing group-mean imputation fills them to position-group neutral before
standardizing. No player is ever dropped (A10 774-pool preserved). MoneyPuck
credited on the poster per its non-commercial terms.

Writes:
  marchand_index/raw/moneypuck_skaters_2025.csv   raw download cache
  marchand_index/raw/nhl_onice.csv                774 rows, schema = OUT_FIELDS
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONTACT_UA, RAW_DIR, atomic_write_csv, load_players, session  # noqa: E402

START_YEAR = "2025"  # pre-reg locks the 2025-26 regular season
MP_URL = (
    "https://moneypuck.com/moneypuck/playerData/seasonSummary/"
    f"{START_YEAR}/regular/skaters.csv"
)
LOCKED_SITUATION = "5on5"            # A13 locked situation (NOT a default)
ONICE_MIN_ICETIME_5V5 = 150         # minutes 5v5 thin floor (locked, A13)

CACHE_CSV = RAW_DIR / "moneypuck_skaters_2025.csv"
OUT_CSV = RAW_DIR / "nhl_onice.csv"

OUT_FIELDS = [
    "player_id", "nhl_player_id", "full_name", "team_code", "situation",
    "cf_pct", "xgf_pct", "ozs_pct", "mp_icetime_5v5",
    "mp_games_played_5v5", "n_team_rows", "onice_status", "fetch_date",
]
