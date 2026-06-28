"""Render the pilot figure for §4 of the CASSIS abstract.

Per pre-registration section 9, layout is two vertical columns:
  LEFT  — ranked by engagement_raw (raw popularity)
  RIGHT — ranked by marchand_index (cap-adjusted, market-controlled)
Grey lines link each player across the two columns so rank-flip is visible.

If pre-reg fallback rule (§11) triggers (>=2 of P1/P2/P3 disconfirmed),
this script renders a schematic instead of the real figure, using
synthetic numbers to illustrate the method. The schematic carries an
explicit "Schematic illustration" label so reviewers cannot mistake it
for real results.

Output: pilot/figure.png (300 dpi)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _common import PILOT_DIR  # noqa: E402

OUT_PATH = PILOT_DIR / "figure.png"


def load_results() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(PILOT_DIR / "oaq_pilot.csv")
    patterns = json.loads((PILOT_DIR / "results.json").read_text(encoding="utf-8"))
    return df, patterns


def render_real_figure(df: pd.DataFrame) -> None:
    real = df.dropna(subset=["engagement_raw", "marchand_index"]).copy()
    real = real.sort_values("engagement_raw", ascending=False).reset_index(drop=True)
    real["rank_engagement"] = real["engagement_raw"].rank(ascending=False, method="min").astype(int)
    real["rank_mi"] = real["marchand_index"].rank(ascending=False, method="min").astype(int)

    n = len(real)
    fig, ax = plt.subplots(figsize=(8.5, max(5.0, 0.45 * n + 1)), dpi=300)

    left_x, right_x = 0.0, 1.0
    name_pad = 0.04

    name_to_left_rank = dict(zip(real["full_name"], real["rank_engagement"]))
    name_to_right_rank = dict(zip(real["full_name"], real["rank_mi"]))

    for name in real["full_name"]:
        y_left = n - name_to_left_rank[name] + 1
        y_right = n - name_to_right_rank[name] + 1
        ax.plot([left_x + name_pad, right_x - name_pad],
                [y_left, y_right],
                color="#bbbbbb", linewidth=0.8, zorder=1)

    for _, r in real.iterrows():
        y_left = n - r["rank_engagement"] + 1
        y_right = n - r["rank_mi"] + 1
        ax.text(left_x, y_left, r["full_name"], ha="right", va="center", fontsize=9, zorder=3)
        cap_str = (f"  ${r['cap_hit_M']:.1f}M" if pd.notna(r["cap_hit_M"]) else "")
        ax.text(right_x, y_right, r["full_name"] + cap_str,
                ha="left", va="center", fontsize=9, zorder=3)

    ax.axvline(left_x - 0.001, color="#444444", linewidth=1)
    ax.axvline(right_x + 0.001, color="#444444", linewidth=1)

    ax.set_xlim(-0.55, 1.55)
    ax.set_ylim(0.3, n + 0.7)
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.text(left_x, n + 0.45, "Rank by engagement_raw\n(raw popularity)",
            ha="right", va="bottom", fontsize=10, fontweight="bold")
    ax.text(right_x, n + 0.45, "Rank by Marchand Index\n(cap-adjusted, market-controlled)",
            ha="left", va="bottom", fontsize=10, fontweight="bold")

    fig.suptitle("The Marchand Index — worked example (N=14, K=5 restricted peers)",
                 fontsize=11, y=0.99)
    fig.text(0.5, 0.01,
             "Cross-overs between the two rankings indicate that cap- and "
             "market-adjusted attention diverges from raw popularity. "
             "Pre-registered: pilot/preregistration.md @ 9774a68.",
             ha="center", fontsize=8, style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def render_schematic() -> None:
    """Synthetic, clearly-labeled illustration of the method.

    Used when the pre-reg fallback rule triggers. The schematic shows
    8 hypothetical players where the method would, in principle,
    re-order raw popularity into cap-adjusted Marchand Index.
    """
    schematic = pd.DataFrame([
        {"full_name": "Star_A",      "engagement_raw": 2.5, "marchand_index": 0.21, "cap": 12.0},
        {"full_name": "Star_B",      "engagement_raw": 2.0, "marchand_index": 0.27, "cap": 9.0},
        {"full_name": "Polariz_C",   "engagement_raw": 1.0, "marchand_index": 0.95, "cap": 1.5},
        {"full_name": "Role_D",      "engagement_raw": 0.5, "marchand_index": 0.80, "cap": 0.9},
        {"full_name": "MidStar_E",   "engagement_raw": 0.2, "marchand_index": 0.45, "cap": 3.0},
        {"full_name": "Veteran_F",   "engagement_raw": 0.0, "marchand_index": 0.12, "cap": 4.5},
        {"full_name": "Quiet_G",     "engagement_raw": -0.5, "marchand_index": 0.05, "cap": 2.0},
        {"full_name": "Bottom_H",    "engagement_raw": -1.0, "marchand_index": -0.30, "cap": 6.0},
    ])
    schematic["rank_engagement"] = schematic["engagement_raw"].rank(ascending=False).astype(int)
    schematic["rank_mi"] = schematic["marchand_index"].rank(ascending=False).astype(int)
    n = len(schematic)

    fig, ax = plt.subplots(figsize=(8.5, 5.5), dpi=300)
    left_x, right_x = 0.0, 1.0
    name_pad = 0.04

    name_to_left = dict(zip(schematic["full_name"], schematic["rank_engagement"]))
    name_to_right = dict(zip(schematic["full_name"], schematic["rank_mi"]))
    for name in schematic["full_name"]:
        y_l = n - name_to_left[name] + 1
        y_r = n - name_to_right[name] + 1
        ax.plot([left_x + name_pad, right_x - name_pad], [y_l, y_r],
                color="#bbbbbb", linewidth=0.8, zorder=1)

    for _, r in schematic.iterrows():
        y_l = n - r["rank_engagement"] + 1
        y_r = n - r["rank_mi"] + 1
        ax.text(left_x, y_l, r["full_name"], ha="right", va="center", fontsize=9)
        ax.text(right_x, y_r, r["full_name"] + f"  ${r['cap']:.1f}M",
                ha="left", va="center", fontsize=9)

    ax.set_xlim(-0.55, 1.55)
    ax.set_ylim(0.3, n + 0.7)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)

    ax.text(left_x, n + 0.45, "Rank by engagement_raw\n(raw popularity)",
            ha="right", va="bottom", fontsize=10, fontweight="bold")
    ax.text(right_x, n + 0.45, "Rank by Marchand Index\n(cap-adjusted, market-controlled)",
            ha="left", va="bottom", fontsize=10, fontweight="bold")

    fig.suptitle("Schematic illustration — method only; synthetic data", fontsize=11, y=0.99)
    fig.text(0.5, 0.02,
             "Pilot triggered the pre-registered fallback rule "
             "(2+ of 3 expected patterns disconfirmed). Pre-reg: "
             "pilot/preregistration.md @ 9774a68. Real pilot data shown in pilot/results.md.",
             ha="center", fontsize=8, style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df, patterns = load_results()
    if patterns.get("_summary", {}).get("use_schematic"):
        print("Pre-registered fallback triggered — rendering schematic.")
        render_schematic()
    else:
        print("All / most patterns held — rendering real figure.")
        render_real_figure(df)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
