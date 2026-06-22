"""Unit tests for the A13 6-feature peer (skill) vector."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


def test_skill_cols_are_the_six_feature_vector():
    assert co.SKILL_COLS == [
        "age", "ppg", "toi_per_game", "cf_pct", "xgf_pct", "ozs_pct",
    ]


def test_expected_cap_predictors_unchanged_ppg_toi_only():
    # A13 must NOT add on-ice features to the A4 market-price regression.
    assert co.EXPECTED_CAP_PREDICTORS == ["ppg", "toi_per_game"]
    assert "cf_pct" not in co.EXPECTED_CAP_PREDICTORS
    assert "xgf_pct" not in co.EXPECTED_CAP_PREDICTORS
    assert "ozs_pct" not in co.EXPECTED_CAP_PREDICTORS


def _skill_df():
    # 6 forwards (group f1) + 6 defense (group d1). Player idx 2 (a forward)
    # and idx 8 (a defenseman) have NULL on-ice features (thin/missing) and
    # must be imputed to their group mean before standardizing.
    n_each = 6
    rows = []
    for g, base in (("f1", 0.50), ("d1", 0.48)):
        for k in range(n_each):
            cf = base + 0.01 * k
            rows.append({
                "group": g,
                "age": 24 + k, "ppg": 0.5 + 0.1 * k,
                "toi_per_game": 15 + k,
                "cf_pct": cf, "xgf_pct": cf - 0.02, "ozs_pct": 0.45 + 0.01 * k,
            })
    df = pd.DataFrame(rows)
    df.loc[2, ["cf_pct", "xgf_pct", "ozs_pct"]] = np.nan   # thin forward
    df.loc[8, ["cf_pct", "xgf_pct", "ozs_pct"]] = np.nan   # thin defenseman
    df["player_id"] = range(1, len(df) + 1)
    return df


def test_standardize_skill_is_six_dim_and_imputes_nulls():
    df = _skill_df()
    Z = co._standardize_skill(df)
    assert Z.shape == (12, 6)              # 6 features now, not 3
    assert np.isfinite(Z).all()           # NULL on-ice features were imputed
    # Each column standardized: ddof=1 sd == 1 (within the all-rows standardize).
    sds = Z.std(axis=0, ddof=1)
    assert np.allclose(sds, 1.0, atol=1e-6)


def test_imputed_player_sits_at_group_mean_on_onice_axes():
    # The thin forward (idx 2) imputed to the f1 group mean on cf/xgf/ozs:
    # after standardizing it equals the standardized group-mean on those axes.
    df = _skill_df()
    Z = co._standardize_skill(df)
    f1_mask = (df["group"] == "f1").to_numpy()
    cf_col = Z[:, 3]                       # cf_pct is index 3 in SKILL_COLS
    # idx 2's standardized cf equals the mean of the OTHER f1 members' raw-mean
    # imputation -> close to the f1 standardized centroid on that axis.
    f1_cf_mean = cf_col[f1_mask].mean()
    assert abs(cf_col[2] - f1_cf_mean) < 0.30  # near group centroid, not extreme


def test_compute_peers_runs_with_six_features():
    df = _skill_df()
    peers = co.compute_peers(df)
    assert len(peers) == 12
    # K capped by group size-1 (6 per group -> at most 5 peers each here).
    assert all(len(pl) <= 5 for pl in peers)
    # Hard position split: a forward's peers are all forwards.
    groups = df["group"].to_numpy()
    for i, pl in enumerate(peers):
        assert all(groups[j] == groups[i] for j in pl)
