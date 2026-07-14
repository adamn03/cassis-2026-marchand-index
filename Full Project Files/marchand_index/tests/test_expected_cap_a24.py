"""A24: contract-type rookie flag + non-rookie log-scale expected_cap fit."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402
from fetch_cap_hits import find_2025_26_caphit  # noqa: E402


# --------------------------------------------------------------------------- #
# Rookie flag                                                                  #
# --------------------------------------------------------------------------- #
def _flag_df(rows):
    df = pd.DataFrame(rows)
    df["player_id"] = range(1, len(df) + 1)
    return df


def test_flag_keys_on_contract_type_when_present():
    df = _flag_df([
        # Bonus-laden ELC above the proxy ceiling: proxy would say market,
        # contract type says rookie -> A24 kills misclassification direction 1.
        {"contract_type": "Entry-Level Contract", "cap_hit_M": 1.85, "age": 20},
        # Cheap post-ELC RFA deal below the ceiling: proxy would say rookie,
        # contract type says market -> misclassification direction 2.
        {"contract_type": "Standard Contract", "cap_hit_M": 0.85, "age": 23},
        {"contract_type": "Standard Contract (Extension)", "cap_hit_M": 12.6, "age": 30},
        {"contract_type": "35+ Contract (Extension)", "cap_hit_M": 8.7, "age": 38},
    ])
    flag, source = co.rookie_flags(df)
    assert flag.tolist() == [True, False, False, False]
    assert all(s == "contract_type" for s in source)


def test_flag_proxy_fallback_when_field_missing():
    df = _flag_df([
        {"contract_type": "", "cap_hit_M": 0.95, "age": 19},     # proxy rookie
        {"contract_type": None, "cap_hit_M": 0.85, "age": 32},   # vet-min: not rookie
        {"contract_type": pd.NA, "cap_hit_M": 5.0, "age": 24},   # market: not rookie
    ])
    flag, source = co.rookie_flags(df)
    assert flag.tolist() == [True, False, False]
    assert all(s == "price_age_proxy" for s in source)


def test_flag_no_contract_type_column_at_all():
    df = _flag_df([{"cap_hit_M": 0.95, "age": 20}])
    flag, source = co.rookie_flags(df)
    assert flag.tolist() == [True]
    assert source[0] == "price_age_proxy"


# --------------------------------------------------------------------------- #
# Governing-contract extraction (fetch side)                                   #
# --------------------------------------------------------------------------- #
def test_governing_contract_type_not_future_extension():
    # Hutson case: extension listed first, ELC governs 2025-26.
    player = {"contracts": [
        {"type": "Standard Contract (Extension)",
         "details": [{"season": "2026-27", "capHit": "$8,850,000"}]},
        {"type": "Entry-Level Contract",
         "details": [{"season": "2025-26", "capHit": "$950,000"}]},
    ]}
    cap_m, note, ctype = find_2025_26_caphit(player)
    assert cap_m == pytest.approx(0.95)
    assert ctype == "Entry-Level Contract"
    assert note == ""


# --------------------------------------------------------------------------- #
# Log-scale non-rookie fit + Duan                                              #
# --------------------------------------------------------------------------- #
def _elc_contaminated_df(seed=7):
    """One group: 40 market deals priced log-linearly in PPG+TOI, plus 10
    CBA-priced ELC rows at $0.95M whose production says they should cost more.
    """
    rng = np.random.default_rng(seed)
    n_mkt = 40
    ppg = rng.uniform(0.2, 1.3, n_mkt)
    toi = rng.uniform(12, 22, n_mkt)
    log_cap = 0.2 + 1.6 * ppg + 0.05 * toi + rng.normal(0, 0.05, n_mkt)
    rows = [{"group": "f", "ppg": p, "toi_per_game": t,
             "cap_hit_M": float(np.exp(lc)), "contract_type": "Standard Contract",
             "age": 27}
            for p, t, lc in zip(ppg, toi, log_cap)]
    for k in range(10):
        rows.append({"group": "f", "ppg": 1.0 + 0.02 * k, "toi_per_game": 19.0,
                     "cap_hit_M": 0.95, "contract_type": "Entry-Level Contract",
                     "age": 20})
    df = pd.DataFrame(rows)
    df["player_id"] = range(1, len(df) + 1)
    return df


def test_nonrookie_log_fit_recovers_market_slope():
    df = _elc_contaminated_df()
    rookie, _ = co.rookie_flags(df)
    exp_cap, _lin = co.compute_expected_cap(df, rookie)
    # Every ELC's expected market rate must far exceed its CBA price: with
    # PPG=1.0/TOI=19 the true market log-cap is 0.2+1.6+0.95=2.75 -> ~$15.6M.
    assert (exp_cap[rookie] > 5.0).all()
    # Market rows: prediction close to actual (fit recovered the surface).
    mkt = ~rookie
    rel_err = np.abs(exp_cap[mkt] - df.loc[mkt, "cap_hit_M"].to_numpy()) \
        / df.loc[mkt, "cap_hit_M"].to_numpy()
    assert np.median(rel_err) < 0.10


def test_elc_contamination_would_have_depressed_linear_fit():
    # The linear ALL-ROWS audit lens (pre-A24 behavior) is dragged down by the
    # CBA-priced rows; the A24 fit must exceed it for the rookies.
    df = _elc_contaminated_df()
    rookie, _ = co.rookie_flags(df)
    exp_cap, exp_lin = co.compute_expected_cap(df, rookie)
    assert (exp_cap[rookie] > exp_lin[rookie]).all()


def test_degenerate_group_floors_at_league_min():
    df = pd.DataFrame([
        {"group": "d", "ppg": 0.3, "toi_per_game": 18.0, "cap_hit_M": 4.0,
         "contract_type": "Standard Contract", "age": 28, "player_id": 1},
        {"group": "d", "ppg": 0.2, "toi_per_game": 16.0, "cap_hit_M": np.nan,
         "contract_type": "", "age": 22, "player_id": 2},
    ])
    rookie, _ = co.rookie_flags(df)
    exp_cap, _ = co.compute_expected_cap(df, rookie)
    assert (exp_cap == co.LEAGUE_MIN_CAP_M).all()


def test_floor_applies_to_low_production_rows():
    df = _elc_contaminated_df()
    df.loc[len(df)] = {"group": "f", "ppg": 0.0, "toi_per_game": 0.0,
                       "cap_hit_M": 0.8, "contract_type": "Standard Contract",
                       "age": 30, "player_id": len(df) + 1}
    rookie, _ = co.rookie_flags(df)
    exp_cap, _ = co.compute_expected_cap(df, rookie)
    assert exp_cap[-1] >= co.LEAGUE_MIN_CAP_M
