"""A12 diagnostic (b): Reddit-downweight robustness sensitivity analysis.

Re-runs the OAQ pipeline at a pre-declared Reddit-weight ladder {1.0,0.5,0.0}x
the A12 Reddit family weight, redistributing the freed weight PROPORTIONALLY
across non-Reddit flows. Compares each variant's OAQ_portable to the locked
A12 headline (factor=1.0) via Spearman + top-20 overlap. Sensitivity analysis
ONLY — the headline stays the locked A12 vector; never a weight search.

Output: diagnostics/reddit_robustness.csv + figure_reddit_robustness.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from _common import PILOT_DIR, atomic_write_csv  # noqa: E402
import compute_oaq as co  # noqa: E402

REDDIT_KEYS = ("reddit_mentions_12mo", "reddit_upvotes_12mo")
LADDER = (1.0, 0.5, 0.0)
DIAG_DIR = PILOT_DIR / "diagnostics"


def scaled_weights(base: dict[str, float], factor: float) -> dict[str, float]:
    """Scale Reddit family by `factor`; redistribute freed weight to non-Reddit
    components proportionally so the vector re-sums to 1.0."""
    reddit_base = sum(base[k] for k in REDDIT_KEYS)
    nonreddit = {k: v for k, v in base.items() if k not in REDDIT_KEYS}
    nonreddit_sum = sum(nonreddit.values())
    freed = reddit_base * (1.0 - factor)
    out: dict[str, float] = {}
    for k, v in base.items():
        if k in REDDIT_KEYS:
            out[k] = v * factor
        else:
            share = (v / nonreddit_sum) if nonreddit_sum > 0 else 0.0
            out[k] = v + freed * share
    return out


def top_overlap(a_names: list[str], b_names: list[str], k: int = 20) -> int:
    return len(set(a_names[:k]) & set(b_names[:k]))


def _portable_for_weights(df, peers, market_z, weights):
    """Recompute OAQ_portable under a temporary WEIGHTS vector."""
    old_w, old_c = co.WEIGHTS, co.COMPONENTS
    try:
        co.WEIGHTS = weights
        co.COMPONENTS = list(weights.keys())
        out = co.compute_oaq(df, peers=peers, market_z=market_z)
    finally:
        co.WEIGHTS, co.COMPONENTS = old_w, old_c
    return out


def main() -> None:
    df = co.load_inputs()
    market_z, _, _ = co.compute_market_z(df)
    df["market_z"] = market_z
    peers = co.compute_peers(df)

    base = dict(co.WEIGHTS)
    headline = _portable_for_weights(df, peers, market_z, base)
    head_port = headline["OAQ_portable"].to_numpy(dtype=float)
    head_top = (headline.dropna(subset=["OAQ_portable"])
                .sort_values("OAQ_portable", ascending=False)["full_name"].tolist())

    rows = []
    for factor in LADDER:
        w = scaled_weights(base, factor)
        variant = _portable_for_weights(df, peers, market_z, w)
        v_port = variant["OAQ_portable"].to_numpy(dtype=float)
        mask = np.isfinite(head_port) & np.isfinite(v_port)
        rho = co.spearman_rho(head_port[mask], v_port[mask])
        v_top = (variant.dropna(subset=["OAQ_portable"])
                 .sort_values("OAQ_portable", ascending=False)["full_name"].tolist())
        rows.append({
            "reddit_factor": factor,
            "reddit_weight": round(sum(w[k] for k in REDDIT_KEYS), 6),
            "spearman_vs_headline": rho,
            "top20_overlap": top_overlap(head_top, v_top, 20),
            "n": int(mask.sum()),
        })

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(DIAG_DIR / "reddit_robustness.csv", rows,
                     ["reddit_factor", "reddit_weight",
                      "spearman_vs_headline", "top20_overlap", "n"])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    factors = [r["reddit_factor"] for r in rows]
    rhos = [r["spearman_vs_headline"] for r in rows]
    overlaps = [r["top20_overlap"] for r in rows]
    fig, ax1 = plt.subplots(figsize=(6, 4))
    ax1.plot(factors, rhos, "o-", color="C0", label="Spearman vs headline")
    ax1.set_xlabel("Reddit weight factor")
    ax1.set_ylabel("Spearman rho vs A12 headline", color="C0")
    ax1.set_ylim(0, 1.02)
    ax2 = ax1.twinx()
    ax2.plot(factors, overlaps, "s--", color="C1", label="top-20 overlap")
    ax2.set_ylabel("top-20 overlap (of 20)", color="C1")
    ax1.set_title("Reddit-downweight robustness")
    fig.tight_layout()
    fig.savefig(DIAG_DIR / "figure_reddit_robustness.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {DIAG_DIR / 'reddit_robustness.csv'}")
    print(f"Wrote {DIAG_DIR / 'figure_reddit_robustness.png'}")


if __name__ == "__main__":
    main()
