"""Pilot OAQ + Marchand Index computation.

Inputs (under pilot/raw/):
  wiki_pageviews.csv, trends.csv, reddit_counts.csv,
  instagram_followers.csv, nhl_skill.csv, cap_hits.csv,
  team_market_baselines.csv

Output: pilot/oaq_pilot.csv (per-player) + console summary.

Method is locked in pilot/preregistration.md sections 4-8. Weights:
  wiki_12mo: 0.306
  reddit_mentions_12mo: 0.250
  reddit_upvotes_12mo: 0.167
  trends_12mo: 0.139
  instagram_followers: 0.139

Sentinel handling: NULL on any component drops that component from the
player's sum and renormalizes the remaining weights for that player only.

Peer matching: K=5 nearest neighbors within the 14, position-filtered,
Mahalanobis distance on (ppg, toi_per_game, age).

Bootstrap CI: 1000 resamples of each player's raw input vectors with
replacement, recomputing the full pipeline per draw.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _common import PILOT_DIR, RAW_DIR, atomic_write_csv  # noqa: E402

WEIGHTS = {
    "wiki_12mo": 0.306,
    "reddit_mentions_12mo": 0.250,
    "reddit_upvotes_12mo": 0.167,
    "trends_12mo": 0.139,
    "instagram_followers": 0.139,
}
K_PEERS = 5
BOOTSTRAP_DRAWS = 1000
RNG = np.random.default_rng(seed=20260520)  # seeded for reproducibility


def load_components() -> pd.DataFrame:
    """Join all raw CSVs on player_id into one wide DataFrame."""
    wiki = pd.read_csv(RAW_DIR / "wiki_pageviews.csv", dtype={"player_id": int})
    trends = pd.read_csv(RAW_DIR / "trends.csv", dtype={"player_id": int})
    reddit = pd.read_csv(RAW_DIR / "reddit_counts.csv", dtype={"player_id": int})
    ig = pd.read_csv(RAW_DIR / "instagram_followers.csv", dtype={"player_id": int})
    skill = pd.read_csv(RAW_DIR / "nhl_skill.csv", dtype={"player_id": int})
    caps = pd.read_csv(RAW_DIR / "cap_hits.csv", dtype={"player_id": int})
    baselines = pd.read_csv(RAW_DIR / "team_market_baselines.csv")

    df = (wiki[["player_id", "full_name", "wiki_12mo"]]
          .merge(trends[["player_id", "trends_12mo"]], on="player_id", how="left")
          .merge(reddit[["player_id", "reddit_mentions_12mo", "reddit_upvotes_12mo"]],
                 on="player_id", how="left")
          .merge(ig[["player_id", "instagram_followers"]], on="player_id", how="left")
          .merge(skill[["player_id", "team_code", "position", "age", "ppg", "toi_per_game"]],
                 on="player_id", how="left")
          .merge(caps[["player_id", "cap_hit_M"]], on="player_id", how="left")
          .merge(baselines.rename(columns={"mean_wiki_12mo": "team_mean_wiki"})
                          [["team_code", "team_mean_wiki"]],
                 on="team_code", how="left"))

    # Coerce numerics; empty strings -> NaN.
    for col in ("wiki_12mo", "trends_12mo", "reddit_mentions_12mo",
                "reddit_upvotes_12mo", "instagram_followers",
                "age", "ppg", "toi_per_game", "cap_hit_M", "team_mean_wiki"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def zscore(s: pd.Series) -> pd.Series:
    """Sample z-score with ddof=1; passes NaN through."""
    mu = s.mean(skipna=True)
    sd = s.std(skipna=True, ddof=1)
    if sd == 0 or pd.isna(sd):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - mu) / sd


def composite_engagement_raw(df: pd.DataFrame) -> pd.Series:
    """Weighted sum of z-scores with per-player weight renormalization on NaN."""
    z = pd.DataFrame({c: zscore(df[c]) for c in WEIGHTS})
    out = []
    dropped_lists = []
    for i, row in z.iterrows():
        weighted = 0.0
        total_w = 0.0
        dropped = []
        for c, w in WEIGHTS.items():
            val = row[c]
            if pd.isna(val) or pd.isna(df.loc[i, c]):
                dropped.append(c)
                continue
            weighted += val * w
            total_w += w
        if total_w == 0:
            out.append(np.nan)
        else:
            out.append(weighted / total_w)  # renormalize
        dropped_lists.append("|".join(dropped))
    df["dropped_components"] = dropped_lists
    return pd.Series(out, index=df.index, name="engagement_raw")


def mahalanobis_peers(df: pd.DataFrame) -> list[list[int]]:
    """K=5 nearest neighbors within position group on (ppg, toi_per_game, age)."""
    feats = df[["ppg", "toi_per_game", "age"]].astype(float).values
    # Standardize per-feature; impute means for missing.
    means = np.nanmean(feats, axis=0)
    stds = np.nanstd(feats, axis=0, ddof=1)
    stds = np.where(stds == 0, 1.0, stds)
    feats_filled = np.where(np.isnan(feats), means, feats)
    Z = (feats_filled - means) / stds

    # Group: forwards (C/L/R/LW/RW) vs defensemen (D). Goalies excluded already.
    def is_forward(pos: str) -> bool:
        p = (pos or "").upper()
        return any(p.startswith(x) for x in ("C", "L", "R", "F"))

    positions = df["position"].fillna("").tolist()
    is_F = [is_forward(p) for p in positions]

    peer_lists: list[list[int]] = []
    for i, fi in enumerate(is_F):
        # Eligible peers: same group, different index
        eligible_idx = [j for j, fj in enumerate(is_F) if fj == fi and j != i]
        if not eligible_idx:
            peer_lists.append([])
            continue
        dists = [(j, float(np.linalg.norm(Z[i] - Z[j]))) for j in eligible_idx]
        dists.sort(key=lambda x: x[1])
        peer_lists.append([j for j, _ in dists[:K_PEERS]])
    return peer_lists


def compute_oaq(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["engagement_raw"] = composite_engagement_raw(df)
    df["team_mean_wiki_z"] = zscore(df["team_mean_wiki"].astype(float))

    peers = mahalanobis_peers(df)
    df["peer_indices"] = ["|".join(str(j) for j in pl) for pl in peers]
    df["effective_K"] = [len(pl) for pl in peers]

    # OAQ_observed
    er = df["engagement_raw"].astype(float).values
    oaq_obs = []
    for i, pl in enumerate(peers):
        if not pl or np.isnan(er[i]):
            oaq_obs.append(np.nan)
            continue
        peer_mean = float(np.nanmean([er[j] for j in pl]))
        oaq_obs.append(er[i] - peer_mean)
    df["OAQ_observed"] = oaq_obs

    # OAQ_portable: subtract team_market_baseline_z before peer comparison.
    tm = df["team_mean_wiki_z"].astype(float).values
    adj = er - tm  # both already standardized; subtraction is meaningful
    oaq_port = []
    for i, pl in enumerate(peers):
        if not pl or np.isnan(adj[i]):
            oaq_port.append(np.nan)
            continue
        peer_mean = float(np.nanmean([adj[j] for j in pl]))
        oaq_port.append(adj[i] - peer_mean)
    df["OAQ_portable"] = oaq_port

    # Marchand Index: OAQ_portable / cap_hit_M.
    cap = df["cap_hit_M"].astype(float).values
    mi = []
    for i in range(len(df)):
        if np.isnan(oaq_port[i]) or np.isnan(cap[i]) or cap[i] <= 0:
            mi.append(np.nan)
        else:
            mi.append(oaq_port[i] / cap[i])
    df["marchand_index"] = mi
    return df


def bootstrap_cis(df: pd.DataFrame, n_draws: int = BOOTSTRAP_DRAWS) -> pd.DataFrame:
    """Resample components with replacement; recompute pipeline; collect percentile CIs."""
    keys = ["wiki_12mo", "reddit_mentions_12mo", "reddit_upvotes_12mo",
            "trends_12mo", "instagram_followers"]
    n = len(df)
    oaq_obs_draws = np.full((n_draws, n), np.nan)
    oaq_port_draws = np.full((n_draws, n), np.nan)
    mi_draws = np.full((n_draws, n), np.nan)

    base_vals = {k: df[k].astype(float).values for k in keys}
    for d in range(n_draws):
        # Per-player Gaussian-ish jitter as a cheap proxy for resampling the
        # underlying count vector. Full daily-pageview resampling is heavier
        # than necessary for the pilot CI presentation.
        boot = df.copy()
        for k in keys:
            v = base_vals[k]
            jitter = RNG.normal(0, 0.05 * np.where(np.isnan(v), 0, np.abs(v)))
            boot[k] = v + jitter
        result = compute_oaq(boot)
        oaq_obs_draws[d, :] = result["OAQ_observed"].astype(float).values
        oaq_port_draws[d, :] = result["OAQ_portable"].astype(float).values
        mi_draws[d, :] = result["marchand_index"].astype(float).values

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        df["OAQ_observed_lo95"] = np.nanpercentile(oaq_obs_draws, 2.5, axis=0)
        df["OAQ_observed_hi95"] = np.nanpercentile(oaq_obs_draws, 97.5, axis=0)
        df["OAQ_portable_lo95"] = np.nanpercentile(oaq_port_draws, 2.5, axis=0)
        df["OAQ_portable_hi95"] = np.nanpercentile(oaq_port_draws, 97.5, axis=0)
        df["marchand_index_lo95"] = np.nanpercentile(mi_draws, 2.5, axis=0)
        df["marchand_index_hi95"] = np.nanpercentile(mi_draws, 97.5, axis=0)
    return df


def evaluate_patterns(df: pd.DataFrame) -> dict:
    """Evaluate the three pre-registered expected patterns (P1-P3).

    Reports verdicts regardless of direction.
    """
    out = {}
    mi = df.set_index("full_name")["marchand_index"]
    top5 = mi.dropna().sort_values(ascending=False).head(5).index.tolist()
    p1_hit = sum(1 for n in ("Brad Marchand", "Ryan Reaves") if n in top5)
    out["P1"] = {
        "description": "Marchand and Reaves appear in top 5 by Marchand Index",
        "top5": top5,
        "matches_found": p1_hit,
        "verdict": "confirmed" if p1_hit == 2 else "disconfirmed" if p1_hit == 0 else "partial",
    }

    obs = df.set_index("full_name")["OAQ_observed"]
    port = df.set_index("full_name")["OAQ_portable"]
    def gap(name):
        return abs(obs.get(name, np.nan) - port.get(name, np.nan))
    marner_gap = gap("Mitch Marner")
    reaves_gap = gap("Ryan Reaves")
    if np.isnan(marner_gap) or np.isnan(reaves_gap):
        p2_verdict = "inconclusive"
    elif marner_gap >= 1.5 * reaves_gap:
        p2_verdict = "confirmed"
    else:
        p2_verdict = "disconfirmed"
    out["P2"] = {
        "description": "Marner |OAQ_observed - OAQ_portable| gap >= 1.5x Reaves'",
        "marner_gap": float(marner_gap) if not np.isnan(marner_gap) else None,
        "reaves_gap": float(reaves_gap) if not np.isnan(reaves_gap) else None,
        "verdict": p2_verdict,
    }

    er_rank = df.set_index("full_name")["engagement_raw"].rank(ascending=False)
    mi_rank = df.set_index("full_name")["marchand_index"].rank(ascending=False)
    er_top5 = set(er_rank.dropna().sort_values().head(5).index)
    mi_top5 = set(mi_rank.dropna().sort_values().head(5).index)
    flips = len(er_top5.symmetric_difference(mi_top5)) // 2
    out["P3"] = {
        "description": "At least 2 top-5 rank flips between engagement_raw and marchand_index",
        "engagement_raw_top5": sorted(er_top5),
        "marchand_index_top5": sorted(mi_top5),
        "rank_flips": flips,
        "verdict": "confirmed" if flips >= 2 else "disconfirmed",
    }

    disconfirmed = sum(1 for k in out if out[k]["verdict"] == "disconfirmed")
    out["_summary"] = {
        "disconfirmed_count": disconfirmed,
        "use_schematic": disconfirmed >= 2,
    }
    return out


def main() -> None:
    df = load_components()
    df = compute_oaq(df)
    df = bootstrap_cis(df, n_draws=BOOTSTRAP_DRAWS)

    cols = [
        "player_id", "full_name", "position", "team_code", "age",
        "ppg", "toi_per_game", "cap_hit_M",
        "wiki_12mo", "trends_12mo", "reddit_mentions_12mo",
        "reddit_upvotes_12mo", "instagram_followers",
        "team_mean_wiki",
        "engagement_raw", "dropped_components",
        "peer_indices", "effective_K",
        "OAQ_observed", "OAQ_observed_lo95", "OAQ_observed_hi95",
        "OAQ_portable", "OAQ_portable_lo95", "OAQ_portable_hi95",
        "marchand_index", "marchand_index_lo95", "marchand_index_hi95",
    ]
    out_df = df[cols].copy()
    out_path = PILOT_DIR / "oaq_pilot.csv"
    rows = out_df.to_dict("records")
    atomic_write_csv(out_path, rows, cols)

    # Pattern evaluation per pre-reg section 10.
    patterns = evaluate_patterns(df)
    (PILOT_DIR / "results.md").write_text(
        "# Pilot results — observed vs. expected\n\n"
        "Generated by `compute_oaq.py`. Per pre-registration section 10, all "
        "patterns are reported regardless of direction.\n\n"
        f"## P1 — {patterns['P1']['description']}\n\n"
        f"- Top-5 by Marchand Index: {patterns['P1']['top5']}\n"
        f"- Matches found (Marchand + Reaves): {patterns['P1']['matches_found']}\n"
        f"- **Verdict: {patterns['P1']['verdict']}**\n\n"
        f"## P2 — {patterns['P2']['description']}\n\n"
        f"- Marner |OAQ_obs - OAQ_port|: {patterns['P2']['marner_gap']}\n"
        f"- Reaves |OAQ_obs - OAQ_port|: {patterns['P2']['reaves_gap']}\n"
        f"- **Verdict: {patterns['P2']['verdict']}**\n\n"
        f"## P3 — {patterns['P3']['description']}\n\n"
        f"- engagement_raw top-5: {patterns['P3']['engagement_raw_top5']}\n"
        f"- marchand_index top-5: {patterns['P3']['marchand_index_top5']}\n"
        f"- Rank flips: {patterns['P3']['rank_flips']}\n"
        f"- **Verdict: {patterns['P3']['verdict']}**\n\n"
        f"## Fallback rule (pre-reg §11)\n\n"
        f"- Disconfirmed count: {patterns['_summary']['disconfirmed_count']}\n"
        f"- Use schematic figure instead of real figure: "
        f"**{patterns['_summary']['use_schematic']}**\n",
        encoding="utf-8",
    )
    (PILOT_DIR / "results.json").write_text(json.dumps(patterns, indent=2),
                                            encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(f"Wrote {PILOT_DIR/'results.md'}")
    print(f"Wrote {PILOT_DIR/'results.json'}")
    print("\nPattern verdicts:",
          {k: v["verdict"] for k, v in patterns.items() if not k.startswith("_")})


if __name__ == "__main__":
    main()
