"""Unit tests for diagnostic pure helpers (no network, no figure render)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from diagnostics import source_correlation as sc  # noqa: E402


# --- Task 11: source-correlation matrix ---

def test_diag_components_are_the_five_zscored_components():
    assert sc.DIAG_COMPONENTS == [
        "wiki_12mo", "wiki_intl_12mo", "reddit_mentions_12mo",
        "reddit_upvotes_12mo", "trends_12mo",
    ]


def test_pairwise_spearman_pairwise_complete_per_cell_n():
    comps = ["a", "b"]
    z = {
        "a": np.array([1.0, 2.0, 3.0, 4.0]),
        "b": np.array([1.0, 2.0, np.nan, 4.0]),  # one NULL -> pair drops to n=3
    }
    rho, n = sc.pairwise_spearman(z, comps)
    assert rho.shape == (2, 2) and n.shape == (2, 2)
    assert n[0, 1] == 3            # pairwise-complete excludes the NaN row
    assert abs(rho[0, 1] - 1.0) < 1e-9   # perfectly monotone on the 3 shared
    assert rho[0, 0] == 1.0 and rho[1, 1] == 1.0
    assert n[0, 0] == 4 and n[1, 1] == 3


# --- Task 12: Reddit-downweight robustness ---

from diagnostics import reddit_robustness as rr  # noqa: E402


def test_ladder_and_keys_locked():
    assert rr.LADDER == (1.0, 0.5, 0.0)
    assert rr.REDDIT_KEYS == ("reddit_mentions_12mo", "reddit_upvotes_12mo")


def test_scaled_weights_sum_to_one_and_halve_reddit():
    base = {
        "wiki_12mo": 0.29, "wiki_intl_12mo": 0.11,
        "reddit_mentions_12mo": 0.27, "reddit_upvotes_12mo": 0.17,
        "trends_12mo": 0.16,
    }
    half = rr.scaled_weights(base, 0.5)
    assert abs(sum(half.values()) - 1.0) < 1e-9
    assert half["reddit_mentions_12mo"] < base["reddit_mentions_12mo"]
    assert (half["wiki_12mo"] / half["wiki_intl_12mo"]) == \
           (base["wiki_12mo"] / base["wiki_intl_12mo"])


def test_scaled_weights_zero_drops_reddit_entirely():
    base = {
        "wiki_12mo": 0.29, "wiki_intl_12mo": 0.11,
        "reddit_mentions_12mo": 0.27, "reddit_upvotes_12mo": 0.17,
        "trends_12mo": 0.16,
    }
    zero = rr.scaled_weights(base, 0.0)
    assert zero["reddit_mentions_12mo"] == 0.0
    assert zero["reddit_upvotes_12mo"] == 0.0
    assert abs(sum(zero.values()) - 1.0) < 1e-9


def test_top_overlap_counts_intersection():
    a = ["A", "B", "C", "D"]
    b = ["C", "D", "E", "F"]
    assert rr.top_overlap(a, b, k=4) == 2
    assert rr.top_overlap(a, b, k=2) == 0


# --- Task 13: A12 amendment in preregistration ---

def test_a12_amendment_appended_to_prereg():
    txt = (Path(__file__).resolve().parents[1] / "preregistration.md").read_text(
        encoding="utf-8")
    assert "A12 (2026-06-" in txt
    assert "multi-language Wikipedia" in txt
    assert "wiki_en 0.29, wiki_intl 0.11" in txt
    assert "Instagram follower count" in txt
    assert txt.index("A11 (2026-06-19)") < txt.index("A12 (2026-06-")
