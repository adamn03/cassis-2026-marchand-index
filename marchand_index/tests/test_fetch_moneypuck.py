"""Unit tests for fetch_moneypuck pure logic (no network)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_moneypuck as fmp  # noqa: E402


def _raw_row(pid, sit, ct=0.0, xt=0.0, ozs=0.0, dzs=0.0, ice=1000.0, gp=10,
             name="X", team="BOS"):
    return {
        "playerId": pid, "name": name, "team": team, "situation": sit,
        "icetime": ice, "games_played": gp,
        "onIce_corsiPercentage": ct, "onIce_xGoalsPercentage": xt,
        "I_F_oZoneShiftStarts": ozs, "I_F_dZoneShiftStarts": dzs,
    }


def test_url_and_locked_constants():
    assert fmp.MP_URL == (
        "https://moneypuck.com/moneypuck/playerData/seasonSummary/"
        "2025/regular/skaters.csv"
    )
    assert fmp.START_YEAR == "2025"
    assert fmp.LOCKED_SITUATION == "5on5"
    assert fmp.ONICE_MIN_ICETIME_5V5 == 150


def test_out_fields_match_spec_schema():
    assert fmp.OUT_FIELDS == [
        "player_id", "nhl_player_id", "full_name", "team_code", "situation",
        "cf_pct", "xgf_pct", "ozs_pct", "mp_icetime_5v5",
        "mp_games_played_5v5", "n_team_rows", "onice_status", "fetch_date",
    ]


def test_filter_5v5_keeps_only_5on5_and_renames():
    raw = pd.DataFrame([
        _raw_row(1, "all", ct=0.9),
        _raw_row(1, "5on5", ct=0.55, xt=0.52, ozs=120, dzs=80),
        _raw_row(1, "5on4", ct=0.99),
        _raw_row(2, "5on5", ct=0.48),
    ])
    out = fmp.filter_5v5(raw)
    assert set(out["situation"]) == {"5on5"}
    assert len(out) == 2
    r = out[out["playerId"] == 1].iloc[0]
    assert r["cf_pct"] == 0.55 and r["xgf_pct"] == 0.52
    assert r["ozs_raw"] == 120 and r["dzs_raw"] == 80


def test_ozs_pct_formula():
    assert fmp.ozs_pct(120.0, 80.0) == 0.6
    assert fmp.ozs_pct(0.0, 0.0) != fmp.ozs_pct(0.0, 0.0)  # NaN != NaN
    assert np.isnan(fmp.ozs_pct(np.nan, 5.0))
