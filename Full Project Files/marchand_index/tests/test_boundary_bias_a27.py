"""A27: peer_skill_gap diagnostic + bias-corrected lens on a convex fixture."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


def _convex_df(n=40, seed=9):
    """One position group on a 1-D skill ladder (ppg drives everything);
    attention is CONVEX in skill with zero noise, so every player's OAQ is a
    pure boundary artifact: interior players' convexity bonus is small, the
    frontier player's is large."""
    rng = np.random.default_rng(seed)
    ppg = np.linspace(0.2, 1.6, n)
    df = pd.DataFrame({
        "player_id": range(1, n + 1),
        "full_name": [f"P{i}" for i in range(n)],
        "group": ["f1"] * n,
        "age": np.full(n, 25.0) + rng.normal(0, 0.01, n),
        "ppg": ppg,
        "toi_per_game": np.full(n, 17.0) + rng.normal(0, 0.01, n),
        "cf_pct": np.full(n, 0.5) + rng.normal(0, 0.001, n),
        "xgf_pct": np.full(n, 0.5) + rng.normal(0, 0.001, n),
        "ozs_pct": np.full(n, 0.5) + rng.normal(0, 0.001, n),
    })
    # Convex attention-in-skill; no idiosyncratic attention at all.
    df["engagement_raw"] = np.exp(2.5 * ppg)
    return df


def _wire(df):
    peers = co.compute_peers(df)
    er = df["engagement_raw"].to_numpy(dtype=float)
    peer_eng = co._peer_means(er, peers)
    df["OAQ_observed"] = er - peer_eng
    df["OAQ_portable"] = df["OAQ_observed"]     # no market side in fixture
    return co.compute_boundary_bias(df, peers), peers


def _linear_df(n=40, seed=9):
    """Same ladder but attention LINEAR in skill: the linear Abadie–Imbens
    correction is exact here, so the frontier artifact must vanish."""
    df = _convex_df(n=n, seed=seed)
    df["engagement_raw"] = 10.0 * df["ppg"].to_numpy()
    return df


def test_frontier_artifact_removed_exactly_on_linear_surface():
    df, _ = _wire(_linear_df())
    top = df["ppg"].idxmax()
    # Mechanical boundary positivity: frontier OAQ > 0 despite zero
    # idiosyncratic attention...
    assert df.loc[top, "OAQ_observed"] > 0
    # ...and the linear correction removes it (≈ 0).
    assert abs(df.loc[top, "OAQ_bc"]) < 0.05 * df.loc[top, "OAQ_observed"]


def test_frontier_artifact_attenuated_on_convex_surface():
    # On a truly convex (exponential) surface the LINEAR correction cannot
    # zero the artifact, but it must attenuate it substantially and keep sign.
    df, _ = _wire(_convex_df())
    top = df["ppg"].idxmax()
    assert df.loc[top, "OAQ_observed"] > 0
    assert df.loc[top, "OAQ_bc"] < 0.6 * df.loc[top, "OAQ_observed"]


def test_peer_skill_gap_largest_at_the_boundary():
    df, _ = _wire(_convex_df())
    top = df["ppg"].idxmax()
    interior = df["peer_skill_gap"].iloc[10:30].mean()
    assert df.loc[top, "peer_skill_gap"] > interior


def test_gap_columns_present_and_finite():
    df, peers = _wire(_convex_df())
    for c in co.SKILL_COLS:
        assert f"peer_skill_gap_{c}" in df.columns
    assert np.isfinite(df["peer_skill_gap"]).all()


def test_portable_bc_uses_same_correction():
    df, _ = _wire(_convex_df())
    corr_obs = df["OAQ_observed"] - df["OAQ_bc"]
    corr_port = df["OAQ_portable"] - df["OAQ_portable_bc"]
    np.testing.assert_allclose(corr_obs, corr_port)
