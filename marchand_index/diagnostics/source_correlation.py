"""A12 diagnostic (a): pairwise Spearman across z-scored composite components.

Pairwise-complete, per-cell n reported. Descriptive ONLY — never feeds back
into weights. Output: diagnostics/source_correlation.csv + heatmap PNG.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from _common import PILOT_DIR, atomic_write_csv  # noqa: E402
import compute_oaq as co  # noqa: E402

DIAG_COMPONENTS = [
    "wiki_12mo", "wiki_intl_12mo", "reddit_mentions_12mo",
    "reddit_upvotes_12mo", "trends_12mo",
]
DIAG_DIR = PILOT_DIR / "diagnostics"


def pairwise_spearman(z_by_comp: dict[str, np.ndarray],
                      components: list[str]):
    k = len(components)
    rho = np.full((k, k), np.nan)
    n = np.zeros((k, k), dtype=int)
    for i in range(k):
        zi = z_by_comp[components[i]]
        for j in range(k):
            zj = z_by_comp[components[j]]
            mask = np.isfinite(zi) & np.isfinite(zj)
            n[i, j] = int(mask.sum())
            if i == j:
                rho[i, j] = 1.0 if mask.sum() else np.nan
            elif mask.sum() >= 2:
                rho[i, j] = co.spearman_rho(zi[mask], zj[mask])
    return rho, n


def main() -> None:
    df = co.load_inputs()
    z_by_comp = {
        c: co.zscore_array(df[c].to_numpy(dtype=float)) for c in DIAG_COMPONENTS
    }
    rho, n = pairwise_spearman(z_by_comp, DIAG_COMPONENTS)

    rows = []
    for i, a in enumerate(DIAG_COMPONENTS):
        for j, b in enumerate(DIAG_COMPONENTS):
            rows.append({"comp_a": a, "comp_b": b,
                         "spearman_rho": rho[i, j], "n": n[i, j]})
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(DIAG_DIR / "source_correlation.csv", rows,
                     ["comp_a", "comp_b", "spearman_rho", "n"])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(rho, vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(DIAG_COMPONENTS)))
    ax.set_yticks(range(len(DIAG_COMPONENTS)))
    ax.set_xticklabels(DIAG_COMPONENTS, rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels(DIAG_COMPONENTS, fontsize=7)
    for i in range(len(DIAG_COMPONENTS)):
        for j in range(len(DIAG_COMPONENTS)):
            if np.isfinite(rho[i, j]):
                ax.text(j, i, f"{rho[i, j]:.2f}\nn={n[i, j]}",
                        ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=ax, label="Spearman rho")
    ax.set_title("Source-correlation matrix (z-scored components)")
    fig.tight_layout()
    fig.savefig(DIAG_DIR / "figure_source_correlation.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {DIAG_DIR / 'source_correlation.csv'}")
    print(f"Wrote {DIAG_DIR / 'figure_source_correlation.png'}")


if __name__ == "__main__":
    main()
