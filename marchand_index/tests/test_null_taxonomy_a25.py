"""A25: missingness taxonomy — no_entity_exists imputes raw 0, fetch_failed renorms."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


def _base_df(n=10, seed=3):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "player_id": range(1, n + 1),
        "full_name": [f"P{i}" for i in range(n)],
        "wiki_12mo": rng.uniform(1e3, 1e6, n),
        "wiki_intl_12mo": rng.uniform(0, 1e4, n),
        "reddit_mentions_12mo": rng.integers(0, 400, n).astype(float),
        "reddit_upvotes_12mo": rng.integers(0, 9000, n).astype(float),
        "trends_12mo": rng.uniform(0, 30, n),
        "wiki_match": ["occupation"] * n,
        "intl_match": ["ok"] * n,
        "query_mid": ["/m/x"] * n,
    })
    return df


def test_no_page_classified_no_entity_and_imputed_zero():
    df = _base_df()
    df.loc[0, "wiki_12mo"] = np.nan
    df.loc[0, "wiki_match"] = "none"
    reasons = co.classify_null_reasons(df)
    assert reasons["wiki_12mo"][0] == co.NULL_NO_ENTITY
    out = co.apply_null_taxonomy(df)
    assert out.loc[0, "wiki_12mo"] == 0.0
    assert "wiki_12mo=no_entity_exists" in out.loc[0, "null_reasons"]


def test_fetch_failure_classified_fetch_failed_and_stays_nan():
    df = _base_df()
    df.loc[1, "wiki_12mo"] = np.nan          # match ok -> HTTP-class failure
    reasons = co.classify_null_reasons(df)
    assert reasons["wiki_12mo"][1] == co.NULL_FETCH_FAILED
    out = co.apply_null_taxonomy(df)
    assert np.isnan(out.loc[1, "wiki_12mo"])


def test_trends_no_mid_is_fetch_failed_since_a47():
    """SUPERSEDED BY A47. A25 read a blank query_mid as "no Google entity" and
    imputed raw 0. After A47 every Trends refusal blanks the MID — including a
    429 — and a missing Trends entity is namesake/coverage-driven rather than
    evidence of zero interest. All NULL trends now renormalize. The wiki and
    wiki_intl clauses of A25 are unchanged (tested above)."""
    df = _base_df()
    df.loc[2, "trends_12mo"] = np.nan
    df.loc[2, "query_mid"] = ""
    reasons = co.classify_null_reasons(df)
    assert reasons["trends_12mo"][2] == co.NULL_FETCH_FAILED
    # With a MID present it was already a fetch failure.
    df.loc[3, "trends_12mo"] = np.nan
    reasons = co.classify_null_reasons(df)
    assert reasons["trends_12mo"][3] == co.NULL_FETCH_FAILED


def test_no_entity_scores_strictly_lower_than_renorm():
    """The E3 defect: renorm hid the no-page signal. A25 must score the
    no-page player strictly lower than the pre-A25 renorm treatment."""
    df = _base_df(n=12)
    df.loc[0, "wiki_12mo"] = np.nan
    df.loc[0, "wiki_match"] = "none"

    # Pre-A25 behavior: NULL stays NaN -> renorm over surviving components.
    er_old, _ = co.compute_engagement_raw(df)
    # A25: raw 0 imputed before z-scoring.
    er_new, _ = co.compute_engagement_raw(co.apply_null_taxonomy(df))

    assert er_new[0] < er_old[0]
    # Everyone else's engagement is not perturbed upward/downward by more than
    # the z-shift the imputed 0 introduces (their values stay finite).
    assert np.isfinite(er_new).all()


def test_fetch_failed_player_unchanged_vs_current_behavior():
    df = _base_df(n=12)
    df.loc[4, "trends_12mo"] = np.nan        # MID present -> fetch_failed
    er_old, dropped_old = co.compute_engagement_raw(df)
    er_new, dropped_new = co.compute_engagement_raw(co.apply_null_taxonomy(df))
    np.testing.assert_allclose(er_new, er_old, equal_nan=True)
    assert dropped_new == dropped_old


def test_defensive_default_without_verdict_columns():
    # Synthetic fixtures without wiki_match/query_mid: all nulls fetch_failed,
    # pre-A25 behavior preserved bit-for-bit.
    df = _base_df().drop(columns=["wiki_match", "intl_match", "query_mid"])
    df.loc[0, "wiki_12mo"] = np.nan
    reasons = co.classify_null_reasons(df)
    assert reasons["wiki_12mo"][0] == co.NULL_FETCH_FAILED
    out = co.apply_null_taxonomy(df)
    assert np.isnan(out.loc[0, "wiki_12mo"])
