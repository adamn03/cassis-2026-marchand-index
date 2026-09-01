"""A28: `onice_status = thin` rows ineligible as peers in sensitivity mode."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


def _pool_df(n=30, n_thin=4, seed=11):
    """One position group; the first `n_thin` rows are A13-thin (their on-ice
    features sit exactly at the group mean, mimicking imputation, which is
    what over-selects them as peers in the primary)."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "player_id": range(1, n + 1),
        "full_name": [f"P{i}" for i in range(n)],
        "group": ["f1"] * n,
        "age": rng.uniform(19, 36, n),
        "ppg": rng.uniform(0.1, 1.4, n),
        "toi_per_game": rng.uniform(8, 22, n),
        "cf_pct": rng.uniform(0.42, 0.58, n),
        "xgf_pct": rng.uniform(0.42, 0.58, n),
        "ozs_pct": rng.uniform(0.35, 0.65, n),
        "onice_status": ["thin"] * n_thin + ["ok"] * (n - n_thin),
    })
    # Imputation mimic: thin rows at the group mean of each on-ice feature.
    for c in ("cf_pct", "xgf_pct", "ozs_pct"):
        df.loc[: n_thin - 1, c] = df[c].iloc[n_thin:].mean()
    return df


def test_thin_rows_in_no_peer_list_in_sensitivity_mode():
    df = _pool_df()
    peers = co.compute_peers(df, exclude_thin_peers=True)
    thin_idx = set(df.index[df["onice_status"] == "thin"])
    for pl in peers:
        assert thin_idx.isdisjoint(pl)


def test_thin_rows_still_scored_themselves():
    df = _pool_df()
    peers = co.compute_peers(df, exclude_thin_peers=True)
    for i in df.index[df["onice_status"] == "thin"]:
        assert len(peers[i]) == min(co.K_PEERS,
                                    int((df["onice_status"] != "thin").sum()))


def test_primary_mode_unchanged_and_can_select_thin():
    df = _pool_df()
    peers_default = co.compute_peers(df)
    peers_explicit = co.compute_peers(df, exclude_thin_peers=False)
    assert peers_default == peers_explicit
    thin_idx = set(df.index[df["onice_status"] == "thin"])
    picked = set(j for pl in peers_default for j in pl)
    # Centroid-sitting thin rows are exactly the over-selection A28 targets.
    assert picked & thin_idx


def test_missing_status_column_means_all_eligible():
    df = _pool_df().drop(columns=["onice_status"])
    assert co.compute_peers(df, exclude_thin_peers=True) == co.compute_peers(df)
