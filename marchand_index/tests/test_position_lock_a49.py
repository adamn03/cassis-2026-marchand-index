"""A49: position-locked peer matching (A49.1) + raw-cap MI headline with the
entry-level-contract pool reported separately (A49.2)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


def _synthetic(n_c=14, n_l=8, n_r=8, n_d=14, seed=49):
    """Forwards (C/L/R) in group f1, defence in d1 — the production shape."""
    rng = np.random.default_rng(seed)
    pos = ["C"] * n_c + ["L"] * n_l + ["R"] * n_r + ["D"] * n_d
    n = len(pos)
    return pd.DataFrame({
        "player_id": range(1, n + 1),
        "full_name": [f"P{i}" for i in range(n)],
        "position": pos,
        "group": ["f1"] * (n_c + n_l + n_r) + ["d1"] * n_d,
        "age": rng.uniform(19, 36, n),
        "ppg": rng.uniform(0.1, 1.4, n),
        "toi_per_game": rng.uniform(8, 22, n),
        "cf_pct": rng.uniform(0.42, 0.58, n),
        "xgf_pct": rng.uniform(0.42, 0.58, n),
        "ozs_pct": rng.uniform(0.35, 0.65, n),
        "onice_status": ["ok"] * n,
    })


def _peers_unrestricted(df, exclude_thin_peers=False):
    """Pre-A49 matcher: identical distance, no position-class filter."""
    Z = co._standardize_skill(df)
    groups = df["group"].to_numpy()
    n = len(df)
    out = [[] for _ in range(n)]
    if exclude_thin_peers and "onice_status" in df.columns:
        eligible = (df["onice_status"].astype(str) != "thin").to_numpy()
    else:
        eligible = np.ones(n, dtype=bool)
    for gi in np.unique(groups):
        idx = np.where(groups == gi)[0]
        sub = Z[idx]
        cov = (np.atleast_2d(np.cov(sub, rowvar=False, ddof=1))
               if sub.shape[0] > 1 else np.eye(sub.shape[1]))
        VI = np.linalg.pinv(cov)
        for a_local, a in enumerate(idx):
            diffs = sub - sub[a_local]
            d2 = np.einsum("ij,jk,ik->i", diffs, VI, diffs)
            order = np.argsort(d2, kind="stable")
            out[a] = [int(idx[b]) for b in order
                      if idx[b] != a and eligible[idx[b]]][:co.K_PEERS]
    return out


# --------------------------------------------------------------------- #
# A49.1 — position class                                                 #
# --------------------------------------------------------------------- #
def test_position_class_maps_wings_together():
    df = pd.DataFrame({"position": ["C", "L", "R", "D", "G"]})
    assert list(co.position_class(df)) == ["C", "W", "W", "D", "G"]


def test_position_class_unknown_falls_to_g_bucket():
    df = pd.DataFrame({"position": ["", "F", None]})
    assert set(co.position_class(df)) == {"G"}


def test_position_class_missing_column_is_single_class():
    """Synthetic fixtures without `position` must keep pre-A49 behaviour."""
    df = pd.DataFrame({"group": ["f1"] * 5})
    assert set(co.position_class(df)) == {"ALL"}


def test_production_inputs_carry_position():
    """The fallback above must never fire on real data."""
    df = co.load_inputs()
    assert "position" in df.columns
    assert df["position"].notna().all()
    assert set(co.position_class(df)) <= {"C", "W", "D", "G"}


def test_peers_never_cross_position_class_synthetic():
    df = _synthetic()
    cls = co.position_class(df)
    for i, pl in enumerate(co.compute_peers(df)):
        assert all(cls[j] == cls[i] for j in pl)


def test_peers_never_cross_position_class_production():
    df = co.load_inputs()
    cls = co.position_class(df)
    for i, pl in enumerate(co.compute_peers(df)):
        assert all(cls[j] == cls[i] for j in pl), df["full_name"].iloc[i]


def test_centre_never_gets_a_winger_peer():
    df = _synthetic()
    cls = co.position_class(df)
    peers = co.compute_peers(df)
    for i in np.where(cls == "C")[0]:
        assert not any(cls[j] == "W" for j in peers[i])


def test_left_and_right_wings_are_mutual_candidates():
    """W is ONE class — an L must be able to draw an R as a peer."""
    df = _synthetic()
    pos = df["position"].to_numpy()
    peers = co.compute_peers(df)
    cross = [
        (i, j) for i in np.where(pos == "L")[0] for j in peers[i]
        if pos[j] == "R"
    ]
    assert cross, "no L drew an R peer — wings were split"


def test_defence_peer_sets_identical_to_pre_a49():
    """Group d1 is already all-D, so the filter is a no-op there."""
    df = co.load_inputs()
    locked = co.compute_peers(df)
    unrestricted = _peers_unrestricted(df)
    d_idx = np.where(df["group"].to_numpy() == "d1")[0]
    assert d_idx.size > 0
    for i in d_idx:
        assert locked[i] == unrestricted[i]


def test_forward_peer_sets_actually_changed():
    """A49.1 must bite on forwards, or the amendment is a no-op."""
    df = co.load_inputs()
    locked = co.compute_peers(df)
    unrestricted = _peers_unrestricted(df)
    f_idx = np.where(df["group"].to_numpy() == "f1")[0]
    assert any(locked[i] != unrestricted[i] for i in f_idx)


def test_chosen_peers_are_the_nearest_within_class():
    """Only the candidate filter narrows — the distance ordering is intact."""
    df = _synthetic()
    cls = co.position_class(df)
    locked = co.compute_peers(df)
    unrestricted_order = _peers_unrestricted(df)
    for i, pl in enumerate(locked):
        same_class_in_order = [j for j in unrestricted_order[i]
                               if cls[j] == cls[i]]
        assert pl[:len(same_class_in_order)] == same_class_in_order


def test_every_production_row_keeps_full_k():
    df = co.load_inputs()
    assert all(len(pl) == co.K_PEERS for pl in co.compute_peers(df))


def test_position_class_pools_support_k_peers():
    df = co.load_inputs()
    counts = pd.Series(co.position_class(df)).value_counts()
    for cls_name in ("C", "W", "D"):
        assert counts[cls_name] > co.K_PEERS


def test_thin_sensitivity_mode_still_position_locked():
    """A28 mode composes with A49.1 rather than bypassing it."""
    df = _synthetic()
    df.loc[:3, "onice_status"] = "thin"
    cls = co.position_class(df)
    for i, pl in enumerate(co.compute_peers(df, exclude_thin_peers=True)):
        assert all(cls[j] == cls[i] for j in pl)


# --------------------------------------------------------------------- #
# A49.2 — raw-cap headline, ELC separated                                #
# --------------------------------------------------------------------- #
def test_headline_column_is_rawcap():
    assert co.HEADLINE_MI_COL == "marchand_index_rawcap"


def test_split_elc_partitions_exactly():
    df = pd.DataFrame({
        "player_id": [1, 2, 3, 4],
        "is_rookie_deal": [0, 1, 0, 1],
    })
    non_elc, elc = co.split_elc(df)
    assert list(non_elc["player_id"]) == [1, 3]
    assert list(elc["player_id"]) == [2, 4]
    assert len(non_elc) + len(elc) == len(df)


def test_split_elc_is_a_view_free_copy():
    """Callers mutate the returned frames; they must not touch the source."""
    df = pd.DataFrame({"is_rookie_deal": [0, 1], "x": [1.0, 2.0]})
    non_elc, _ = co.split_elc(df)
    non_elc["x"] = 99.0
    assert df["x"].tolist() == [1.0, 2.0]


@pytest.fixture(scope="module")
def scored():
    df = co.load_inputs()
    peers = co.compute_peers(df)
    market_z, _, _ = co.compute_market_z(df)
    return co.compute_oaq(df, peers=peers, market_z=market_z)


def test_headline_is_portable_over_raw_cap(scored):
    port = scored["OAQ_portable"].to_numpy(float)
    cap = scored["cap_hit_M"].to_numpy(float)
    mi = scored[co.HEADLINE_MI_COL].to_numpy(float)
    ok = np.isfinite(cap) & (cap > 0)
    assert np.allclose(mi[ok], port[ok] / cap[ok], equal_nan=True)


def test_demoted_lenses_still_computed(scored):
    """A49.2 demotes; it does not delete the audit trail."""
    for col in ("marchand_index_hybrid", "marchand_index", "expected_cap"):
        assert col in scored.columns
        assert np.isfinite(scored[col].to_numpy(float)).any()


def test_headline_and_hybrid_differ_on_elc_rows(scored):
    """If they agreed everywhere the denominator swap would be cosmetic."""
    elc = scored[scored["is_rookie_deal"] == 1]
    a = elc["marchand_index_rawcap"].to_numpy(float)
    b = elc["marchand_index_hybrid"].to_numpy(float)
    ok = np.isfinite(a) & np.isfinite(b)
    assert ok.sum() > 0
    assert not np.allclose(a[ok], b[ok])


def test_headline_and_hybrid_agree_on_non_elc_rows(scored):
    """Off ELC the hybrid denominator IS the raw cap."""
    non_elc = scored[scored["is_rookie_deal"] == 0]
    a = non_elc["marchand_index_rawcap"].to_numpy(float)
    b = non_elc["marchand_index_hybrid"].to_numpy(float)
    ok = np.isfinite(a) & np.isfinite(b)
    assert np.allclose(a[ok], b[ok])


def test_pc_pattern_runs_on_rawcap_and_excludes_elc(scored):
    out = co.evaluate_patterns(scored, co.external_validation(scored))
    pc = out["PC"]
    assert "top10_marchand_index_rawcap" in pc
    assert "top10_marchand_index_hybrid" not in pc
    assert "marchand_index_rawcap" in pc["description"]
    elc_names = set(scored.loc[scored["is_rookie_deal"] == 1, "full_name"])
    assert not (set(pc["top10_marchand_index_rawcap"]) & elc_names)
    assert not (set(pc["top10_engagement_raw"]) & elc_names)


def test_log_lens_covers_the_headline(scored):
    peers = co.compute_peers(co.load_inputs())
    mz = scored["market_z"].to_numpy(float)
    lens = co.compute_log_lens(scored, peers, mz)
    assert "marchand_index_rawcap_log1p" in lens
    cap = scored["cap_hit_M"].to_numpy(float)
    ok = np.isfinite(cap) & (cap > 0)
    expect = lens["OAQ_portable_log1p"][ok] / cap[ok]
    assert np.allclose(lens["marchand_index_rawcap_log1p"][ok], expect)


def test_out_cols_carry_headline_and_audit_lenses():
    for col in ("marchand_index_rawcap", "marchand_index_rawcap_log1p",
                "marchand_index_hybrid", "marchand_index"):
        assert col in co.OUT_COLS
