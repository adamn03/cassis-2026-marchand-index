"""Unit tests for the A17 log1p robustness lens (no data files needed)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


def test_signed_log1p_handles_negatives_and_nan():
    v = np.array([-10.0, -1.0, 0.0, 10.0, np.nan])
    out = co.signed_log1p(v)
    assert out[0] == -np.log1p(10.0)
    assert out[1] == -np.log1p(1.0)
    assert out[2] == 0.0
    assert out[3] == np.log1p(10.0)
    assert np.isnan(out[4])


def test_signed_log1p_is_monotone():
    v = np.array([-5.0, -1.0, 0.0, 2.0, 100.0, 10000.0])
    out = co.signed_log1p(v)
    assert np.all(np.diff(out) > 0)


def _toy_df(n=12):
    rng = np.random.default_rng(7)
    df = pd.DataFrame({
        "player_id": np.arange(1, n + 1),
        "full_name": [f"P{i}" for i in range(n)],
        "group": ["f1"] * n,
        # Heavy-tailed component so raw vs log lenses genuinely differ.
        "wiki_12mo": rng.pareto(1.5, n) * 1000,
        "wiki_intl_12mo": rng.pareto(1.5, n) * 100,
        "reddit_mentions_12mo": rng.integers(0, 500, n).astype(float),
        "reddit_upvotes_12mo": rng.integers(-50, 5000, n).astype(float),
        "trends_12mo": rng.pareto(1.5, n),
        "expected_cap": np.full(n, 2.0),
        "cap_hit_M": np.full(n, 4.0),
        "is_rookie_deal": np.zeros(n, dtype=int),
    })
    return df


def test_compute_log_lens_shapes_and_finiteness():
    df = _toy_df()
    peers = [[j for j in range(len(df)) if j != i][:3] for i in range(len(df))]
    market_z = np.zeros(len(df))
    lens = co.compute_log_lens(df, peers, market_z)
    for key in ("engagement_raw_log1p", "OAQ_observed_log1p",
                "OAQ_portable_log1p", "marchand_index_hybrid_log1p"):
        assert key in lens
        assert lens[key].shape == (len(df),)
        assert np.isfinite(lens[key]).all()


def test_log_lens_compresses_star_dominance():
    # z-of-raw lets one mega-outlier dominate; z-of-log must shrink its lead.
    df = _toy_df()
    df.loc[0, ["wiki_12mo", "wiki_intl_12mo", "reddit_mentions_12mo",
               "reddit_upvotes_12mo", "trends_12mo"]] = [1e7, 1e6, 5e4, 1e6, 50]
    peers = [[j for j in range(len(df)) if j != i][:3] for i in range(len(df))]
    market_z = np.zeros(len(df))
    er_raw, _ = co.compute_engagement_raw(df)
    lens = co.compute_log_lens(df, peers, market_z)
    er_log = lens["engagement_raw_log1p"]

    def lead(v):  # top value minus runner-up, in that lens's own sd units
        s = np.sort(v)[::-1]
        return (s[0] - s[1]) / np.nanstd(v)

    assert lead(er_log) < lead(er_raw)


def test_rank_agreement_perfect_and_reversed():
    a = np.array([1.0, 2.0, 3.0, 4.0])
    assert co.rank_agreement(a, a * 10) == 1.0
    assert co.rank_agreement(a, -a) == -1.0


def test_rank_agreement_ignores_nan_rows():
    a = np.array([1.0, 2.0, np.nan, 4.0])
    b = np.array([2.0, 4.0, 9.0, 8.0])
    assert co.rank_agreement(a, b) == 1.0


def test_out_cols_include_log_lens_columns():
    for col in ("engagement_raw_log1p", "OAQ_portable_log1p",
                "marchand_index_hybrid_log1p"):
        assert col in co.OUT_COLS
