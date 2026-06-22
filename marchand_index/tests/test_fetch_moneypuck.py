"""Unit tests for fetch_moneypuck pure logic (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_moneypuck as fmp  # noqa: E402


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
