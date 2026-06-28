"""Render the §4 pilot figure showing the confirmed P3 result with real names.

Top-5 by raw engagement (left) vs. top-5 by Marchand Index (right). Connecting
lines mark players who hold position; (out) / (in) annotations mark movers.
Cap hits are shown on both sides for context.

Per pre-registration §11, only the confirmed P3 portion of the pilot is
visualized; P1 / P2 disconfirmation diagnosis is in §2 of the abstract, and
the full ranked pilot table is in pilot/oaq_pilot.csv.

Output: pilot/figure.png (300 dpi).
"""
from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PILOT_DIR = Path(__file__).parent
OUT_PATH = PILOT_DIR / "figure.png"

NAME_SHORTEN = {
    "Brady Tkachuk": "B. Tkachuk",
    "Matthew Tkachuk": "M. Tkachuk",
    "Nikita Kucherov": "Kucherov",
    "Connor McDavid": "McDavid",
    "Connor Bedard": "Bedard",
    "Jack Hughes": "J. Hughes",
    "Sidney Crosby": "Crosby",
    "Brad Marchand": "Marchand",
    "Nathan MacKinnon": "MacKinnon",
    "Leon Draisaitl": "Draisaitl",
    "Auston Matthews": "Matthews",
    "Cale Makar": "Makar",
    "Mitch Marner": "Marner",
    "Ryan Reaves": "Reaves",
}


def main() -> None:
    df = pd.read_csv(PILOT_DIR / "oaq_pilot.csv")
    df = df.dropna(subset=["engagement_raw", "marchand_index"]).copy()

    top5_eng = df.nlargest(5, "engagement_raw").reset_index(drop=True)
    top5_mi = df.nlargest(5, "marchand_index").reset_index(drop=True)

    left_names = top5_eng["full_name"].tolist()
    right_names = top5_mi["full_name"].tolist()
    caps = pd.read_csv(PILOT_DIR / "raw" / "cap_hits.csv")
    caps_all = dict(zip(caps["full_name"], caps["cap_hit_M"]))

    left_rank = {name: i + 1 for i, name in enumerate(left_names)}
    right_rank = {name: i + 1 for i, name in enumerate(right_names)}

    stayers = set(left_names) & set(right_names)

    n = 5
    fig, ax = plt.subplots(figsize=(7.6, 4.0), dpi=300)
    left_x, right_x = 0.0, 1.0

    def yof(rank: int) -> float:
        return n - rank + 1

    # Connecting lines for stayers
    for name in stayers:
        ax.plot(
            [left_x + 0.05, right_x - 0.05],
            [yof(left_rank[name]), yof(right_rank[name])],
            color="#555555", linewidth=1.3, zorder=1,
        )

    # Left column
    for name in left_names:
        is_stayer = name in stayers
        weight = "bold" if is_stayer else "normal"
        short = NAME_SHORTEN.get(name, name)
        cap = caps_all.get(name)
        cap_str = f"  (${cap:.2f}M)" if pd.notna(cap) else ""
        suffix = "" if is_stayer else "   (out)"
        ax.text(
            left_x - 0.015, yof(left_rank[name]),
            f"{left_rank[name]}.  {short}{cap_str}{suffix}",
            ha="right", va="center", fontsize=10.2, fontweight=weight,
        )

    # Right column
    for name in right_names:
        is_stayer = name in stayers
        weight = "bold" if is_stayer else "normal"
        short = NAME_SHORTEN.get(name, name)
        cap = caps_all.get(name)
        cap_str = f"  (${cap:.2f}M)" if pd.notna(cap) else ""
        prefix = "" if is_stayer else "(in)   "
        ax.text(
            right_x + 0.015, yof(right_rank[name]),
            f"{prefix}{right_rank[name]}.  {short}{cap_str}",
            ha="left", va="center", fontsize=10.2, fontweight=weight,
        )

    # Column dividers
    ax.axvline(left_x - 0.005, color="#444444", linewidth=0.9)
    ax.axvline(right_x + 0.005, color="#444444", linewidth=0.9)

    # Headers
    ax.text(left_x, n + 0.60, "Top 5 by raw engagement",
            ha="right", va="bottom", fontsize=11, fontweight="bold")
    ax.text(right_x, n + 0.60, "Top 5 by Marchand Index",
            ha="left", va="bottom", fontsize=11, fontweight="bold")
    ax.text(left_x, n + 0.22, "Wikipedia + Google Trends z-composite",
            ha="right", va="bottom", fontsize=8, color="#555555", style="italic")
    ax.text(right_x, n + 0.22, "cap- and market-adjusted attention surplus",
            ha="left", va="bottom", fontsize=8, color="#555555", style="italic")

    ax.set_xlim(-1.05, 2.05)
    ax.set_ylim(0.3, n + 1.15)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)

    fig.suptitle(
        "Pilot top 5 — cap- and market-adjustment reorders the leaderboard",
        fontsize=11.5, y=0.985,
    )
    fig.text(
        0.5, 0.025,
        "Bedard, J. Hughes, and Crosby hold position (bold, connected). Marchand and McDavid "
        "drop out of the top 5; B. Tkachuk and Kucherov enter — driven by their lower cap hits. "
        "Only the confirmed top-5 reordering is shown; the lower-ranking values reflect the "
        "market-baseline proxy flaw described in §2.",
        ha="center", fontsize=7.6, style="italic", wrap=True,
    )

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
