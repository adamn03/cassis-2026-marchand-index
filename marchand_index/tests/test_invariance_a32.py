"""A32: invariance panel across locked-original variants + verbatim
disclosure sentence + proxy-swap OAQ column."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


def _df(seed=7, n=22):
    rng = np.random.default_rng(seed)
    port = np.concatenate([np.full(3, 20.0) + [0, 1, 2],
                           np.arange(n - 3, dtype=float) * 0.4])
    order = np.argsort(-port)
    jersey_rank = np.full(n, np.nan)
    for r, i in enumerate(order[:8], 1):
        jersey_rank[i] = r
    mem = np.zeros(n)
    mem[:3] = 1
    asg = np.zeros(n)
    asg[order[:3]] = 1
    return pd.DataFrame({
        "full_name": [f"P{i}" for i in range(n)],
        "team_code": [f"T{i % 6}" for i in range(n)],
        "OAQ_portable": port,
        "OAQ_observed": port + rng.normal(0, 0.1, n),
        "engagement_raw": rng.normal(size=n),
        "ppg": rng.uniform(0.2, 1.4, n),
        "jersey_rank": jersey_rank,
        "jersey_list_member": mem,
        "asg2024_member": asg,
        # locked-original variant score columns
        "marchand_index_rawcap": port + rng.normal(0, 2.0, n),
        "OAQ_portable_lockedv1": port + rng.normal(0, 1.0, n),
        "OAQ_portable_market_lockedv1": port.copy(),  # == primary
    })


def test_disclosure_sentence_matches_prereg_verbatim():
    prereg = (Path(co.__file__).parent / "preregistration.md").read_text(
        encoding="utf-8")
    assert co.A32_DISCLOSURE in prereg


def test_compute_oaq_emits_proxy_swap_column():
    # When market_z_lockedv1 equals the primary market_z, the proxy-swap
    # variant must reproduce OAQ_portable exactly (same A5 rule, same input).
    rng = np.random.default_rng(11)
    n = 30
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
        "wiki_12mo": rng.uniform(0, 1000, n),
        "trends_12mo": rng.uniform(0, 100, n),
        "reddit_mentions_12mo": rng.uniform(0, 50, n),
        "reddit_upvotes_12mo": rng.uniform(0, 500, n),
        "wiki_intl_12mo": np.nan,
        "cap_hit_M": rng.uniform(0.8, 12.0, n),
        "market_z": rng.normal(size=n),
    })
    df["market_z_lockedv1"] = df["market_z"]
    out = co.compute_oaq(df)
    assert "OAQ_portable_market_lockedv1" in out.columns
    np.testing.assert_allclose(
        out["OAQ_portable_market_lockedv1"].to_numpy(dtype=float),
        out["OAQ_portable"].to_numpy(dtype=float), atol=1e-12)


def test_proxy_swap_column_in_out_cols():
    assert "OAQ_portable_market_lockedv1" in co.OUT_COLS


def test_invariance_panel_points_and_deltas(tmp_path, monkeypatch):
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    df = _df()
    external = co.external_validation(df, n_draws=50, seed=9, n_perm=200)
    panel = co.invariance_panel(df, external)
    variants = panel["variants"]
    assert set(variants) == {
        "marchand_index_rawcap", "OAQ_portable_lockedv1",
        "OAQ_portable_market_lockedv1",
    }
    # Variant identical to the primary -> all deltas exactly 0.
    same = variants["OAQ_portable_market_lockedv1"]
    for test in ("V1a", "V1b", "V2"):
        assert same[test]["delta"] == 0.0
    # Deltas are point - primary for every variant x test.
    for name, v in variants.items():
        for test in ("V1a", "V1b", "V2"):
            expected = v[test]["value"] - external[test]["value"]
            assert abs(v[test]["delta"] - expected) < 1e-12
    assert "V3" in panel["v3_note"] or "OAQ_observed" in panel["v3_note"]


def test_invariance_panel_missing_column_flagged(tmp_path, monkeypatch):
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    df = _df().drop(columns=["marchand_index_rawcap"])
    external = co.external_validation(df, n_draws=50, seed=9, n_perm=200)
    panel = co.invariance_panel(df, external)
    assert panel["variants"]["marchand_index_rawcap"].get("missing") is True


def test_a32_results_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    df = _df()
    external = co.external_validation(df, n_draws=50, seed=9, n_perm=200)
    panel = co.invariance_panel(df, external)
    txt = "\n".join(co._a32_results_lines(panel))
    assert "## A32 invariance panel (locked-original variants)" in txt
    assert co.A32_DISCLOSURE in txt
    # One row per variant x test, delta vs primary.
    assert txt.count("| V1b |") == 3
    assert txt.count("| V1a |") == 3
    assert txt.count("| V2 |") == 3
    assert "invariant by construction" in txt


def test_write_results_md_calls_a32_section():
    import inspect
    assert "_a32_results_lines" in inspect.getsource(co.write_results_md)
