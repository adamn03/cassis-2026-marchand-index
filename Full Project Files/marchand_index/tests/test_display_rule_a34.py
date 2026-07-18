"""A34: published-leaderboard display rule — small_sample / season-absent
rows excluded from every published table, retained in data, count disclosed."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


def test_display_pool_excludes_flagged_and_absent_rows():
    df = pd.DataFrame({
        "full_name": ["A", "B", "C", "D"],
        "small_sample": [1, 0, 0, 0],
        "games_played": [30.0, np.nan, 40.0, 50.0],
    })
    disp, n_excl = co._a34_display_pool(df)
    assert n_excl == 2
    assert list(disp["full_name"]) == ["C", "D"]


def _pipeline_df(n=24, seed=13):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "player_id": range(1, n + 1),
        "full_name": [f"Player{i}" for i in range(n)],
        "position": ["C"] * n,
        "group": ["f1"] * n,
        "team_code": [f"T{i % 6}" for i in range(n)],
        "age": rng.uniform(19, 36, n),
        "ppg": rng.uniform(0.1, 1.4, n),
        "toi_per_game": rng.uniform(8, 22, n),
        "cf_pct": rng.uniform(0.42, 0.58, n),
        "xgf_pct": rng.uniform(0.42, 0.58, n),
        "ozs_pct": rng.uniform(0.35, 0.65, n),
        "wiki_12mo": rng.uniform(100, 1000, n),
        "trends_12mo": rng.uniform(1, 100, n),
        "reddit_mentions_12mo": rng.uniform(0, 50, n),
        "reddit_upvotes_12mo": rng.uniform(0, 500, n),
        "wiki_intl_12mo": np.nan,
        "cap_hit_M": rng.uniform(0.8, 12.0, n),
        "market_z": rng.normal(size=n),
    })
    # FlaggedStar: engagement leader who is small_sample -> must vanish
    # from every published table while keeping computed values in the data.
    df.loc[0, "full_name"] = "FlaggedStar"
    df.loc[0, "wiki_12mo"] = 50_000
    df.loc[0, "trends_12mo"] = 500
    df.loc[1, "full_name"] = "AbsentGuy"
    df["market_z_lockedv1"] = df["market_z"]
    out = co.compute_oaq(df)
    out["cap_quality"] = "ok"
    out["match_quality"] = "ok"
    out["small_sample"] = 0
    out.loc[out["full_name"] == "FlaggedStar", "small_sample"] = 1
    out["games_played"] = 40.0
    out.loc[out["full_name"] == "AbsentGuy", "games_played"] = np.nan
    # external-validation columns
    port = out["OAQ_portable"].to_numpy(dtype=float)
    order = np.argsort(-port)
    jr = np.full(len(out), np.nan)
    for r, i in enumerate(order[:8], 1):
        jr[i] = r
    out["jersey_rank"] = jr
    mem = np.zeros(len(out))
    mem[order[:3]] = 1
    out["jersey_list_member"] = mem
    asg = np.zeros(len(out))
    asg[order[:3]] = 1
    out["asg2024_member"] = asg
    return out


def test_flagged_rows_absent_from_published_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    df = _pipeline_df()
    external = co.external_validation(df, n_draws=50, seed=9, n_perm=200)
    patterns = co.evaluate_patterns(df, external)
    md = tmp_path / "results.md"
    co.write_results_md(md, df, external, patterns,
                        market_used=["metro_population"],
                        reddit_note="test", a32_panel=None)
    text = md.read_text(encoding="utf-8")
    leaderboards = text.split("## Leaderboards", 1)[1]
    assert "FlaggedStar" not in leaderboards
    assert "AbsentGuy" not in leaderboards
    # Count disclosed alongside the tables.
    assert "A34" in leaderboards
    assert "2 " in leaderboards.split("\n", 6)[2] or "2 row" in leaderboards
    # Retained in the data with computed values (CSV source).
    row = df[df["full_name"] == "FlaggedStar"].iloc[0]
    assert np.isfinite(row["OAQ_portable"])


def test_flagged_rows_still_in_validation_cohort(tmp_path, monkeypatch):
    # A34 is display-only: external validation runs on the FULL pool.
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    df = _pipeline_df()
    external = co.external_validation(df, n_draws=50, seed=9, n_perm=200)
    assert external["V1b"]["n_total"] == len(df)
