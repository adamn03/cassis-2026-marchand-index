"""A47 x A25: an unresolved Trends row must be classified by WHY it is null.

The A25 rule inferred "no Google entity exists" from a blank query_mid. Once
A47 stops publishing raw-string values, that inference imputes RAW 0 to every
player whose suggestions() call was merely throttled — Alex Ovechkin would be
scored as having zero search interest. The refusal reason has to decide.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


def _base_df(n=10, seed=3):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
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
        "trends_method": ["topic"] * n,
    })


def _null_trends(df, i, method):
    df.loc[i, "trends_12mo"] = np.nan
    df.loc[i, "query_mid"] = ""
    df.loc[i, "trends_method"] = method
    return df


def test_no_hockey_topic_is_fetch_failed_not_no_entity():
    """A missing Google Trends ENTITY reflects knowledge-graph coverage and
    namesake crowding, not absence of public interest. Will Smith (SJ, 4th
    overall 2023) has no hockey MID because the actor owns the name — imputing
    raw 0 would assert nobody searches for him. Renormalize instead; his other
    four components carry him. (Wikipedia keeps the raw-0 rule: a missing
    ARTICLE really does mean no encyclopedic salience.)"""
    df = _null_trends(_base_df(), 0, "no_hockey_topic")
    assert co.classify_null_reasons(df)["trends_12mo"][0] == co.NULL_FETCH_FAILED
    assert np.isnan(co.apply_null_taxonomy(df).loc[0, "trends_12mo"])


def test_no_trends_refusal_is_ever_imputed_zero():
    df = _base_df()
    for i, method in enumerate(("no_hockey_topic", "ambiguous_topic",
                                "resolve_failed")):
        df = _null_trends(df, i, method)
    out = co.apply_null_taxonomy(df)
    reasons = co.classify_null_reasons(df)
    for i in range(3):
        assert reasons["trends_12mo"][i] == co.NULL_FETCH_FAILED
        assert np.isnan(out.loc[i, "trends_12mo"])


def test_wiki_keeps_the_raw_zero_rule():
    """The A47 change is scoped to Trends only."""
    df = _base_df()
    df.loc[7, "wiki_12mo"] = np.nan
    df.loc[7, "wiki_match"] = "none"
    assert co.classify_null_reasons(df)["wiki_12mo"][7] == co.NULL_NO_ENTITY
    assert co.apply_null_taxonomy(df).loc[7, "wiki_12mo"] == 0.0


def test_resolve_failed_is_fetch_failed_not_no_entity():
    """A 429 says nothing about the player's search interest. Imputing 0 here
    would score a throttled Ovechkin as league-minimum attention."""
    df = _null_trends(_base_df(), 1, "resolve_failed")
    assert co.classify_null_reasons(df)["trends_12mo"][1] == co.NULL_FETCH_FAILED
    assert np.isnan(co.apply_null_taxonomy(df).loc[1, "trends_12mo"])


def test_ambiguous_topic_is_fetch_failed_not_no_entity():
    """Two candidate entities is an excess of signal, not an absence of one."""
    df = _null_trends(_base_df(), 2, "ambiguous_topic")
    assert co.classify_null_reasons(df)["trends_12mo"][2] == co.NULL_FETCH_FAILED
    assert np.isnan(co.apply_null_taxonomy(df).loc[2, "trends_12mo"])


def test_every_refusal_reason_scores_identically():
    """No refusal reason is privileged: all three renormalize, so a player's
    engagement does not depend on WHY Trends could not measure him."""
    df = _base_df(n=12)
    ers = []
    for method in ("no_hockey_topic", "ambiguous_topic", "resolve_failed"):
        out = co.apply_null_taxonomy(_null_trends(df.copy(), 3, method))
        er, _ = co.compute_engagement_raw(out)
        ers.append(er[3])
    assert ers[0] == ers[1] == ers[2]


def test_renorm_equals_imputing_the_weighted_mean_of_the_present_components():
    """Renormalization IS "use his average from the other components": with
    weights summing to 0.84 over the four survivors, 0.84m + 0.16m = m."""
    df = _base_df(n=12)
    nulled = co.apply_null_taxonomy(_null_trends(df.copy(), 3, "no_hockey_topic"))
    er_renorm, _ = co.compute_engagement_raw(nulled)

    # A57: the composite stabilises each component before standardising,
    # so the hand-computed comparison has to apply the same transform or
    # it is checking the renorm identity on a different scale.
    comp_z = {c: co.zscore_array(co.stabilize(nulled[c].to_numpy(dtype=float)))
              for c in co.COMPONENTS}
    present = [c for c in co.COMPONENTS if c != "trends_12mo"]
    w = sum(co.WEIGHTS[c] for c in present)
    m = sum(co.WEIGHTS[c] * comp_z[c][3] for c in present) / w
    assert abs(er_renorm[3] - m) < 1e-12


def test_a_null_trends_row_is_never_imputed_zero_whatever_the_vintage():
    """Pre-A47 CSVs carry no trends_method column. They must not fall back to
    the superseded blank-MID rule that imputed raw 0."""
    df = _base_df().drop(columns=["trends_method"])
    df.loc[5, "trends_12mo"] = np.nan
    df.loc[5, "query_mid"] = ""
    assert co.classify_null_reasons(df)["trends_12mo"][5] == co.NULL_FETCH_FAILED
    assert np.isnan(co.apply_null_taxonomy(df).loc[5, "trends_12mo"])
