"""A35 small-items batch: secondary Trends anchor (clause 1), log-lens ban
(clause 2), goals-rate robustness (clause 3), disclosure emit (clauses 4/5)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402
import fetch_trends as ft  # noqa: E402


# ---- clause 1: secondary anchor for the anchor player's own row ---- #
def test_secondary_anchor_is_crosby():
    assert ft.SECONDARY_ANCHOR_NAME == "Sidney Crosby"


def test_chain_secondary_ratio_math_and_guards():
    # (M/C measured) x (C/M stored) puts Marchand's row on the common scale.
    assert abs(ft.chain_secondary_ratio(1.3, 0.8) - 1.04) < 1e-12
    assert ft.chain_secondary_ratio(None, 0.8) is None
    assert ft.chain_secondary_ratio(1.3, None) is None
    assert ft.chain_secondary_ratio(1.3, 0.0) is None


def test_remeasure_anchor_row_uses_secondary_anchor():
    rows = {
        "1": {"player_id": "1", "full_name": "Brad Marchand",
              "query_mid": "/m/mar", "trends_method": "topic",
              "trends_12mo": "1.000000", "player_mean_scaled": "10.0",
              "anchor_mean_scaled": "10.0", "n_weeks": 53,
              "fetch_date": "2026-07-03"},
        "2": {"player_id": "2", "full_name": "Sidney Crosby",
              "query_mid": "/m/cro", "trends_method": "topic",
              "trends_12mo": "0.800000", "player_mean_scaled": "8.0",
              "anchor_mean_scaled": "10.0", "n_weeks": 53,
              "fetch_date": "2026-07-03"},
    }

    def fake_pair(anchor_kw, player_kw):
        assert anchor_kw == "/m/cro"          # Crosby MID is the anchor
        return 13.0, 10.0, 53                 # M/C = 1.3

    updated = ft.a35_remeasure_anchor_row(rows, fake_pair,
                                          secondary_kw="/m/cro")
    assert updated is True
    m = rows["1"]
    assert m["trends_method"] == "topic_secondary_anchor"
    assert abs(float(m["trends_12mo"]) - 1.04) < 1e-9


def test_remeasure_without_crosby_row_is_refused():
    rows = {"1": {"player_id": "1", "full_name": "Brad Marchand",
                  "trends_12mo": "1.0", "trends_method": "topic"}}
    updated = ft.a35_remeasure_anchor_row(rows, lambda a, p: (1, 1, 1),
                                          secondary_kw="/m/cro")
    assert updated is False
    assert rows["1"]["trends_12mo"] == "1.0"  # untouched


# ---- clause 2: verbatim ban pinned against the prereg ---- #
def test_log_lens_ban_verbatim_in_prereg():
    prereg = (Path(co.__file__).parent / "preregistration.md").read_text(
        encoding="utf-8")
    assert co.A35_LOG_LENS_BAN in prereg


# ---- clause 3: goals-rate robustness (rank agreement only) ---- #
def _inputs_df(n=24, seed=17):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "player_id": range(1, n + 1),
        "full_name": [f"P{i}" for i in range(n)],
        "group": ["f1"] * n,
        "team_code": [f"T{i % 6}" for i in range(n)],
        "age": rng.uniform(19, 36, n),
        "ppg": rng.uniform(0.1, 1.4, n),
        "toi_per_game": rng.uniform(8, 22, n),
        "cf_pct": rng.uniform(0.42, 0.58, n),
        "xgf_pct": rng.uniform(0.42, 0.58, n),
        "ozs_pct": rng.uniform(0.35, 0.65, n),
        "wiki_12mo": rng.uniform(100, 1000, n),
        "trends_12mo": rng.uniform(0.01, 2, n),
        "reddit_mentions_12mo": rng.uniform(0, 50, n),
        "reddit_upvotes_12mo": rng.uniform(0, 500, n),
        "wiki_intl_12mo": np.nan,
        "cap_hit_M": rng.uniform(0.8, 12.0, n),
        "market_z": rng.normal(size=n),
    })


def test_goalsrate_identical_to_ppg_gives_perfect_agreement():
    df_in = _inputs_df()
    df_in["goals_per60"] = df_in["ppg"]     # identical feature -> same ranks
    market_z = df_in["market_z"].to_numpy(dtype=float)
    df_primary = co.compute_oaq(df_in.copy(), market_z=market_z)
    out = co.a35_goalsrate_agreement(df_primary, df_in, market_z)
    assert out["available"] is True
    for col in ("OAQ_observed", "OAQ_portable", "marchand_index_hybrid"):
        assert abs(out["agreement"][col] - 1.0) < 1e-9


def test_goalsrate_unavailable_without_column():
    df_in = _inputs_df()
    market_z = df_in["market_z"].to_numpy(dtype=float)
    df_primary = co.compute_oaq(df_in.copy(), market_z=market_z)
    out = co.a35_goalsrate_agreement(df_primary, df_in, market_z)
    assert out["available"] is False


# ---- emit: disclosures + zero-quantization + agreement table ---- #
def test_a35_results_lines():
    a35 = {
        "goalsrate": {"available": True,
                      "agreement": {"OAQ_observed": 0.97,
                                    "OAQ_portable": 0.96,
                                    "marchand_index_hybrid": 0.95}},
        "trends_zero_count": 41,
    }
    txt = "\n".join(co._a35_results_lines(a35))
    assert co.A35_LOG_LENS_BAN in txt
    assert "41" in txt                        # zero-quantization count
    assert "secondary anchor" in txt.lower()  # clause 1 disclosure
    assert "submissions" in txt.lower()       # clause 4a
    assert "nationality" in txt.lower()       # clause 5
    assert "| OAQ_portable | 0.96" in txt     # agreement table, not a ranking
    assert "injury" in txt.lower()            # A34 limitations line


def test_write_results_md_calls_a35_section():
    import inspect
    assert "_a35_results_lines" in inspect.getsource(co.write_results_md)
