"""A46 — how much does OAQ_portable depend on the market_z social component?

`market_z` currently uses `team_sub_subscribers` (a stock). Subreddit
submission volume (a flow) is a nearly independent measure — Spearman 0.299
across the 32 teams. This report quantifies the consequence.

Answers open item #3B: is Montreal's 16-of-100 showing in the OAQ_portable top
100 real over-indexing, or a market strip that under-corrects because Reddit
subscriber counts understate a francophone fanbase?

IN-MEMORY ONLY. Writes one markdown report and no CSV. Does not constitute a
production `compute_oaq` run and does not touch any sacred CSV.

Run from inside `marchand_index/`:

    python -m diagnostics.market_sensitivity
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

import compute_oaq as co

PILOT_DIR = Path(__file__).parent.parent
REPORT_PATH = Path(__file__).parent / "market_sensitivity_report.md"


def team_z_table(
    mp: pd.DataFrame,
    activity: pd.DataFrame,
    primary: np.ndarray,
    lenses: dict[str, np.ndarray],
    team_codes: pd.Series,
) -> pd.DataFrame:
    """One row per team: market_z under the primary and each A46 lens."""
    frame = pd.DataFrame({"team_code": team_codes, "market_z_a30": primary})
    for name in ("market_z_activity", "market_z_social_blend"):
        if name in lenses:
            frame[name] = lenses[name]
    per_team = frame.groupby("team_code").first().reset_index()
    per_team = per_team.merge(
        activity[["team_code", "sub_submissions_window", "activity_quality"]],
        on="team_code",
        how="left",
    ).merge(
        mp[["team_code", "team_sub_subscribers"]], on="team_code", how="left"
    )
    if "market_z_activity" in per_team.columns:
        per_team["delta"] = per_team["market_z_activity"] - per_team["market_z_a30"]
        per_team = per_team.sort_values("delta", ascending=False)
    return per_team.reset_index(drop=True)


def top_n_composition(
    df: pd.DataFrame, score_col: str, n: int = 100
) -> pd.DataFrame:
    """Team counts among the top `n` rows by `score_col`, highest first."""
    ranked = df.dropna(subset=[score_col]).nlargest(n, score_col)
    counts = (
        ranked.groupby("team_code").size().reset_index(name="n_in_top")
    )
    return counts.sort_values("n_in_top", ascending=False).reset_index(drop=True)


def main() -> None:
    mp = pd.read_csv(PILOT_DIR / "market_proxy.csv")
    activity = co.load_market_activity()
    if activity is None:
        raise SystemExit(
            "market_activity.csv not found — run `python build_market_activity.py` first"
        )

    players = pd.read_csv(PILOT_DIR / "players.csv")
    primary, used, lenses = co.compute_market_z(players, mp, activity=activity)

    per_team = team_z_table(
        mp, activity, primary, lenses, players["team_code"].astype(str)
    )

    lines: list[str] = []
    lines.append("# A46 — market_z social-component sensitivity\n")
    lines.append(f"Primary (A30) components used: `{used}`\n")

    merged = activity.merge(
        mp[["team_code", "team_sub_subscribers"]], on="team_code"
    )
    rho = merged[["team_sub_subscribers", "sub_submissions_window"]].corr(
        method="spearman"
    ).iloc[0, 1]
    lines.append(
        f"Spearman(subscribers, submissions) across 32 teams: **{rho:.3f}**\n"
    )

    if "market_z_activity" in lenses:
        z_rho = pd.Series(primary).corr(
            pd.Series(lenses["market_z_activity"]), method="spearman"
        )
        lines.append(
            f"Spearman(market_z A30, market_z activity) across players: "
            f"**{z_rho:.3f}**\n"
        )

    lines.append("\n## Per-team market_z\n")
    # to_string, not to_markdown: the latter needs the tabulate package,
    # which is not installed ($0 stack); a fenced block renders fine.
    lines.append("```\n" + per_team.to_string(index=False) + "\n```")

    low = activity[activity["activity_quality"] == "low"]["team_code"].tolist()
    lines.append(
        f"\n**Low-quality activity teams (excluded from conclusions): "
        f"{low or 'none'}**\n"
    )

    report = "\n".join(lines)
    tmp = REPORT_PATH.with_suffix(".md.tmp")
    tmp.write_text(report, encoding="utf-8")
    os.replace(tmp, REPORT_PATH)

    print(report)
    print(f"\nwrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
