"""A30: rebuilt market proxy — primary components, lenses, degradation."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402
import fetch_market_proxy as fmp  # noqa: E402


def _mp(n=32, drop_subs_for=None):
    rng = np.random.default_rng(4)
    codes = [f"T{i:02d}" for i in range(n)]
    mp = pd.DataFrame({
        "team_code": codes,
        "metro_population": rng.uniform(8e5, 2e7, n).round(),
        "arena_attendance": rng.uniform(14e3, 21e3, n).round(),
        "attendance_pct_capacity": rng.uniform(0.75, 1.0, n).round(4),
        "team_sub_subscribers": rng.uniform(2e3, 4e5, n).round(),
    })
    if drop_subs_for is not None:
        mp.loc[drop_subs_for, "team_sub_subscribers"] = np.nan
    return mp


def _df(mp):
    return pd.DataFrame({"team_code": mp["team_code"],
                         "player_id": range(len(mp))})


def test_primary_uses_the_a54_weighted_components():
    """A54 replaced A30's equal-weight thirds with 0.40 social / 0.40
    attendance / 0.20 population, and broadened the social block from Reddit
    alone to Reddit + club Instagram + X. Population was carrying almost no
    signal (club-level rho +0.055) while holding a third of the instrument."""
    mp = _mp()
    _, used, _ = co.compute_market_z(_df(mp), mp=mp)
    assert "attendance_pct_capacity" in used
    assert "metro_population" in used
    assert "team_sub_subscribers" in used
    assert co.A54_WEIGHTS == {"social": 0.40, "attendance": 0.40,
                              "population": 0.20}


def test_graceful_degradation_drops_incomplete_component():
    mp = _mp(drop_subs_for=5)
    _, used, _ = co.compute_market_z(_df(mp), mp=mp)
    assert "team_sub_subscribers" not in used
    assert "metro_population" in used          # irreducible floor


def test_lenses_present_and_distinct_from_primary():
    mp = _mp()
    z, _, lenses = co.compute_market_z(_df(mp), mp=mp)
    assert set(lenses) == {"market_z_lockedv1", "market_z_metro_only"}
    assert not np.allclose(z, lenses["market_z_lockedv1"])
    # metro-only lens is exactly the z of metro population.
    metro_z = co.zscore_array(
        mp["metro_population"].to_numpy(dtype=float))
    assert np.allclose(lenses["market_z_metro_only"], metro_z)


def test_lockedv1_is_the_old_pair():
    assert co.MARKET_COMPONENTS_LOCKEDV1 == ["metro_population",
                                             "arena_attendance"]


def test_static_dicts_cover_the_same_32_codes():
    assert set(fmp.METRO_POP) == set(fmp.ARENA_ATTENDANCE) \
        == set(fmp.ARENA_CAPACITY) == set(fmp.TEAM_SUB)
    assert len(fmp.METRO_POP) == 32


def test_attendance_pct_capacity_sane():
    for c in fmp.ARENA_ATTENDANCE:
        pct = fmp.ARENA_ATTENDANCE[c] / fmp.ARENA_CAPACITY[c]
        assert 0.5 < pct < 1.35, (c, pct)   # announced can exceed seating


def test_uta_sums_the_a22_sub_set():
    assert fmp.UTA_EXTRA_SUBS == ["UtahHockey"]
    assert fmp.TEAM_SUB["UTA"] == "utahmammoth"
