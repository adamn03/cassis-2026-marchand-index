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


def test_aggregate_single_team_passthrough():
    df = fmp.filter_5v5(pd.DataFrame([
        _raw_row(1, "5on5", ct=0.55, xt=0.52, ozs=120, dzs=80, ice=1000, gp=20),
    ]))
    agg = fmp.aggregate_traded(df)
    assert len(agg) == 1
    r = agg.iloc[0]
    assert r["n_team_rows"] == 1
    assert r["cf_pct"] == 0.55 and r["xgf_pct"] == 0.52
    assert r["ozs_pct"] == 0.6
    assert r["mp_icetime_5v5"] == 1000 and r["mp_games_played_5v5"] == 20


def test_aggregate_traded_two_team_rows_icetime_weighted():
    # Player 7 traded: 900 min @ cf 0.60 on team A, 100 min @ cf 0.40 on team B.
    # icetime-weighted cf = (0.60*900 + 0.40*100)/1000 = 0.58 (NOT simple 0.50).
    # ozs from summed counts: (180+20)/((180+20)+(120+80)) = 200/400 = 0.5.
    df = fmp.filter_5v5(pd.DataFrame([
        _raw_row(7, "5on5", ct=0.60, xt=0.62, ozs=180, dzs=120, ice=900, gp=45,
                 team="TOR", name="Traded Guy"),
        _raw_row(7, "5on5", ct=0.40, xt=0.42, ozs=20, dzs=80, ice=100, gp=5,
                 team="CGY", name="Traded Guy"),
    ]))
    agg = fmp.aggregate_traded(df)
    assert len(agg) == 1
    r = agg.iloc[0]
    assert r["n_team_rows"] == 2
    assert abs(r["cf_pct"] - 0.58) < 1e-9
    assert abs(r["xgf_pct"] - 0.60) < 1e-9   # (0.62*900+0.42*100)/1000
    assert abs(r["ozs_pct"] - 0.5) < 1e-9    # summed-count ratio, NOT averaged
    assert r["mp_icetime_5v5"] == 1000 and r["mp_games_played_5v5"] == 50
    assert r["team"] == "TOR"   # max-icetime (primary) team


def test_aggregate_one_row_per_player():
    df = fmp.filter_5v5(pd.DataFrame([
        _raw_row(1, "5on5", ice=500), _raw_row(1, "5on5", ice=400),
        _raw_row(2, "5on5", ice=900),
    ]))
    agg = fmp.aggregate_traded(df)
    assert sorted(agg["playerId"].tolist()) == [1, 2]
    assert agg["playerId"].is_unique


def test_apply_thin_floor_nulls_below_150():
    row = {"cf_pct": 0.65, "xgf_pct": 0.60, "ozs_pct": 0.7,
           "mp_icetime_5v5": 120.0}
    out = fmp.apply_thin_floor(row)
    assert out["onice_status"] == "thin"
    assert np.isnan(out["cf_pct"]) and np.isnan(out["xgf_pct"])
    assert np.isnan(out["ozs_pct"])


def test_apply_thin_floor_keeps_above_floor():
    row = {"cf_pct": 0.55, "xgf_pct": 0.52, "ozs_pct": 0.6,
           "mp_icetime_5v5": 800.0}
    out = fmp.apply_thin_floor(row)
    assert out["onice_status"] == "ok"
    assert out["cf_pct"] == 0.55 and out["ozs_pct"] == 0.6


def test_apply_thin_floor_nan_icetime_is_thin():
    out = fmp.apply_thin_floor(
        {"cf_pct": 0.5, "xgf_pct": 0.5, "ozs_pct": 0.5,
         "mp_icetime_5v5": float("nan")})
    assert out["onice_status"] == "thin"
    assert np.isnan(out["cf_pct"])


def _agg_df(rows):
    # rows already aggregated/floored; supply the post-aggregate columns.
    return pd.DataFrame(rows)


def test_join_pool_id_match_and_status():
    players = [
        {"player_id": "1", "full_name": "Leo Carlsson", "team_code": "ANA",
         "nhl_player_id": "8484153"},
        {"player_id": "2", "full_name": "No Match Guy", "team_code": "BOS",
         "nhl_player_id": "9999999"},
    ]
    mp = _agg_df([
        {"playerId": 8484153, "name": "Leo Carlsson", "team": "ANA",
         "cf_pct": 0.55, "xgf_pct": 0.52, "ozs_pct": 0.6,
         "mp_icetime_5v5": 800.0, "mp_games_played_5v5": 40.0,
         "n_team_rows": 1, "onice_status": "ok"},
    ])
    out = fmp.join_pool(players, mp, "2026-06-20")
    assert len(out) == 2
    leo = next(r for r in out if r["player_id"] == "1")
    assert leo["cf_pct"] == 0.55 and leo["onice_status"] == "ok"
    assert leo["team_code"] == "ANA" and leo["situation"] == "5on5"
    miss = next(r for r in out if r["player_id"] == "2")
    assert miss["onice_status"] == "missing"
    assert miss["cf_pct"] == "" and miss["n_team_rows"] == 0


def test_join_pool_name_fallback_only_when_id_blank():
    players = [
        {"player_id": "3", "full_name": "Michael Benning", "team_code": "FLA",
         "nhl_player_id": ""},  # blank id -> name fallback allowed
    ]
    mp = _agg_df([
        {"playerId": 8480000, "name": "michael  benning", "team": "FLA",
         "cf_pct": 0.50, "xgf_pct": 0.49, "ozs_pct": 0.45,
         "mp_icetime_5v5": 600.0, "mp_games_played_5v5": 30.0,
         "n_team_rows": 1, "onice_status": "ok"},
    ])
    out = fmp.join_pool(players, mp, "2026-06-20")
    assert out[0]["cf_pct"] == 0.50  # matched by normalized name


def test_join_pool_never_drops_player():
    players = [{"player_id": str(i), "full_name": f"P{i}", "team_code": "BOS",
                "nhl_player_id": str(8000000 + i)} for i in range(5)]
    out = fmp.join_pool(players, _agg_df([]), "2026-06-20")
    assert len(out) == 5
    assert all(r["onice_status"] == "missing" for r in out)


def test_load_raw_uses_cache_when_present(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "moneypuck_skaters_2025.csv").write_text(
        "playerId,name,team,situation,icetime,games_played,"
        "onIce_corsiPercentage,onIce_xGoalsPercentage,"
        "I_F_oZoneShiftStarts,I_F_dZoneShiftStarts\n"
        "8484153,Leo Carlsson,ANA,5on5,800,40,0.55,0.52,120,80\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(fmp, "RAW_DIR", raw)
    monkeypatch.setattr(fmp, "CACHE_CSV", raw / "moneypuck_skaters_2025.csv")

    class _NoNet:
        def get(self, *a, **k):
            raise AssertionError("network hit despite cache present")

    df = fmp.load_raw(_NoNet())
    assert int(df.iloc[0]["playerId"]) == 8484153
    assert df.iloc[0]["situation"] == "5on5"


def test_empirical_group_report_flags_traded():
    df = fmp.filter_5v5(pd.DataFrame([
        _raw_row(7, "5on5", ice=900), _raw_row(7, "5on5", ice=100),
        _raw_row(9, "5on5", ice=800),
    ]))
    rep = fmp.empirical_group_report(df)
    assert rep[7] == 2 and rep[9] == 1
