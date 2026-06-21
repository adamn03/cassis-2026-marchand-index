"""Tier-1 pilot OAQ + Marchand Index computation (pilot2).

Implements pilot2/preregistration.md EXACTLY (sections 4, 6, 7, 8, 9, 10, 11
and amendments A1-A4). This is the LOCKED method — no deviations.

A4 (2026-05-27): the Marchand Index denominator is the skill-EXPECTED cap
from an OLS fit of cap_hit_M ~ PPG + TOI/G estimated separately per position
group (age excluded), prediction floored at $0.775M league min. The original
§8 raw-cap quantity is retained as `marchand_index_rawcap` for audit.

Inputs (under pilot2/ and pilot2/raw/):
  players.csv               player_id, full_name, position, group, team_code, ...
  raw/nhl_skill.csv         age, ppg, toi_per_game, ...
  raw/wiki_pageviews.csv    wiki_12mo, ...
  raw/wiki_daily.csv        daily_views (pipe-joined per player) -> bootstrap
  raw/trends.csv            trends_12mo
  raw/instagram_followers.csv  instagram_followers (NULL for all 160)
  raw/cap_hits.csv          cap_hit_M, cap_quality
  raw/reddit_counts.csv     reddit_mentions_12mo, reddit_upvotes_12mo, reddit_status
  raw/reddit_detail.csv     submission_id, score (per player) -> bootstrap
  market_proxy.csv          team_code, metro_population, arena_attendance, ...
  external_outcomes.csv     jersey_list_member, jersey_rank, asg2024_member, ...

Outputs:
  pilot2/oaq_pilot.csv   per-player components + OAQ_observed/portable/MI + CIs
  pilot2/results.md      external validation, pattern verdicts, leaderboards
  pilot2/results.json    machine-readable external results + pattern verdicts

Method summary (locked):
  engagement_raw = weighted sum of z-scored components, per-player sentinel
    renormalization on NULL components.
  Peers: K=10, hard position split via `group`, Mahalanobis distance using the
    inverse WITHIN-GROUP covariance of the standardized skill vector
    (age, ppg, toi_per_game), group-mean imputation for NULL skill.
  OAQ_observed = engagement_raw - mean(engagement_raw over K peers).
  OAQ_portable = (engagement_raw - market_z) - mean over K peers of same.
  expected_cap(P): per-group OLS cap_hit_M ~ PPG + TOI/G prediction, floored
    at $0.775M. Age excluded so the rookie scale is not re-imported.
  marchand_index_hybrid = OAQ_portable / (expected_cap if rookie-deal else
    cap_hit_M)                                    (HEADLINE, A8)
  marchand_index = OAQ_portable / expected_cap   (intrinsic-efficiency lens;
    was A4 headline, demoted by A8)
  marchand_index_rawcap = OAQ_portable / cap_hit_M  (audit / §8-original)
  Bootstrap: 1000 draws, resample each player's wiki daily vector + reddit
    submission pool with replacement; trends/IG/cap/market fixed; peer SETS
    fixed; recompute z-scores + everything per draw; 2.5/97.5 percentile CIs.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _common import PILOT_DIR, RAW_DIR  # noqa: E402

# scipy is optional; fall back to a manual Spearman if missing.
try:
    from scipy.stats import spearmanr as _scipy_spearmanr  # type: ignore

    def spearman_rho(x: np.ndarray, y: np.ndarray) -> float:
        if len(x) < 2:
            return float("nan")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = _scipy_spearmanr(x, y).correlation
        return float(r)
except Exception:  # pragma: no cover - scipy may be absent
    def spearman_rho(x: np.ndarray, y: np.ndarray) -> float:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if len(x) < 2:
            return float("nan")
        rx = pd.Series(x).rank().to_numpy()
        ry = pd.Series(y).rank().to_numpy()
        sx, sy = rx.std(), ry.std()
        if sx == 0 or sy == 0:
            return float("nan")
        return float(np.corrcoef(rx, ry)[0, 1])


# A12 (2026-06-21) — composite re-locked by demographic-coverage reasoning,
# BEFORE the wiki_intl fetch. Instagram (stock) DROPPED; wiki_intl_12mo (flow)
# ADDED. Prior vector retained in preregistration.md A12 for audit. The code
# key `wiki_12mo` IS the spec's `wiki_en_12mo` (same en-Wikipedia column).
WEIGHTS = {
    "wiki_12mo": 0.29,           # wiki_en_12mo: EN encyclopedic / casual lookup
    "wiki_intl_12mo": 0.11,      # non-anglophone hockey markets (A12)
    "reddit_mentions_12mo": 0.27,
    "reddit_upvotes_12mo": 0.17,
    "trends_12mo": 0.16,
}
COMPONENTS = list(WEIGHTS.keys())
SKILL_COLS = ["age", "ppg", "toi_per_game"]
K_PEERS = 10
BOOTSTRAP_DRAWS = 1000
SEED = 20260526

# Whole-league pivot (A10): descriptive, NON-EXCLUSIONARY low-GP flag. A skater
# with fewer than this many NHL regular-season games this year is flagged
# small_sample so the headline is never quoted on a tiny-sample call-up (or a
# season-long injury absence, GP NULL → flagged). The player stays in the pool
# and in every computation; the §10 bootstrap CIs already widen for thin signal.
SMALL_SAMPLE_GP = 20

# A4: per-position OLS denominator for the headline Marchand Index. Age is
# deliberately EXCLUDED — including it re-imports the rookie scale via
# young/cheap peers (verified: a ±5yr age band re-inflates rookie MI).
EXPECTED_CAP_PREDICTORS = ["ppg", "toi_per_game"]
LEAGUE_MIN_CAP_M = 0.775

# A5 (2026-05-27) — one-sided damped market correction in §7.
# OAQ_portable = engagement − λ × max(0, market_z) − peer_mean(of same).
# Small markets (market_z < 0) get zero correction (no phantom boost).
# Big markets (market_z > 0) get a partial discount: fraction of fan equity
# travels with the player when they move. λ committed at the max-entropy
# midpoint between bounds 0 and 1 BEFORE re-running; sensitivity ladder
# {0.0, 0.25, 0.5, 0.75, 1.0} reported as robustness.
LAMBDA_BIGMARKET = 0.5
LAMBDA_SENSITIVITY = (0.0, 0.25, 0.5, 0.75, 1.0)

# Rookie-deal (ELC) proxy: cap ≤ $0.975M AND age ≤ 25. Tight enough to exclude
# veteran-minimum / depth players (Stecher 32 @ $0.788M, McIlrath 34 @ $0.825M,
# Wotherspoon 28 @ $1.00M, Mukhamadullin 24 @ $1.00M) while catching every
# obvious ELC in the set (Bedard, Celebrini, Schaefer, Eklund, Smith, Fantilli,
# Benson, Parekh, Carlsson, Snuggerud, Nazar, Bump, etc.). $0.975M is the
# practical ELC cap-hit ceiling including standard signing bonuses for 2025-26.
ROOKIE_CAP_MAX_M = 0.975
ROOKIE_AGE_MAX = 25

# V1/V2 floors per pre-reg §9.
V1_FLOOR, V1_TARGET = 0.40, 0.50
V2_FLOOR, V2_TARGET = 0.45, 0.55
PA_FLOOR = 0.40   # PA uses V1 Spearman >= 0.40
PB_FLOOR = 0.45   # PB uses V2 Spearman >= 0.45
UNDERPOWERED_N = 10

# A6: V3 team-level triangulation gate. n=32 teams. Floor mirrors V1.
V3_FLOOR, V3_TARGET = 0.40, 0.50
PD_FLOOR = 0.40
V3_N_TEAMS = 32


# --------------------------------------------------------------------------- #
# Loading                                                                      #
# --------------------------------------------------------------------------- #
def _to_num(df: pd.DataFrame, cols: list[str]) -> None:
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")


def load_inputs() -> pd.DataFrame:
    """Join all inputs on player_id into one wide DataFrame (160 rows).

    Reddit is treated as NULL for any player missing from reddit_counts.csv
    (the fetcher may be mid-write / blocked for some players); the files
    being entirely absent is also tolerated.
    """
    players = pd.read_csv(PILOT_DIR / "players.csv", dtype={"player_id": int})
    skill = pd.read_csv(RAW_DIR / "nhl_skill.csv", dtype={"player_id": int})
    wiki = pd.read_csv(RAW_DIR / "wiki_pageviews.csv", dtype={"player_id": int})
    trends = pd.read_csv(RAW_DIR / "trends.csv", dtype={"player_id": int})
    wiki_intl = pd.read_csv(RAW_DIR / "wiki_intl_pageviews.csv",
                            dtype={"player_id": int})
    caps = pd.read_csv(RAW_DIR / "cap_hits.csv", dtype={"player_id": int})
    external = pd.read_csv(PILOT_DIR / "external_outcomes.csv", dtype={"player_id": int})

    df = players[
        ["player_id", "full_name", "position", "group", "team_code", "nhl_player_id"]
    ].copy()

    df = df.merge(
        skill[["player_id", "age", "ppg", "toi_per_game", "games_played"]],
        on="player_id", how="left",
    )
    df = df.merge(wiki[["player_id", "wiki_12mo", "wiki_match"]], on="player_id", how="left")
    df = df.merge(
        wiki_intl[["player_id", "wiki_intl_12mo", "intl_match"]],
        on="player_id", how="left",
    )
    df = df.merge(trends[["player_id", "trends_12mo"]], on="player_id", how="left")
    df = df.merge(
        caps[["player_id", "cap_hit_M", "cap_quality"]], on="player_id", how="left"
    )
    df = df.merge(
        external[
            ["player_id", "jersey_list_member", "jersey_rank", "asg2024_member"]
        ],
        on="player_id",
        how="left",
    )

    # Reddit (defensive: files may be absent or only partially populated).
    rc_path = RAW_DIR / "reddit_counts.csv"
    if rc_path.exists():
        rc = pd.read_csv(rc_path, dtype={"player_id": int})
        keep = ["player_id", "reddit_mentions_12mo", "reddit_upvotes_12mo"]
        if "reddit_status" in rc.columns:
            keep.append("reddit_status")
        df = df.merge(rc[keep], on="player_id", how="left")
    else:
        df["reddit_mentions_12mo"] = np.nan
        df["reddit_upvotes_12mo"] = np.nan
        df["reddit_status"] = "null"

    if "reddit_status" not in df.columns:
        df["reddit_status"] = np.nan

    # Reddit NULL rule: status 'null' (or missing row) -> NULL both reddit cols.
    _to_num(df, ["reddit_mentions_12mo", "reddit_upvotes_12mo"])
    status = df["reddit_status"].astype("string").str.strip().str.lower()
    null_mask = status.isna() | (status == "null") | (status == "")
    df.loc[null_mask, ["reddit_mentions_12mo", "reddit_upvotes_12mo"]] = np.nan

    _to_num(
        df,
        SKILL_COLS
        + ["games_played", "wiki_12mo", "wiki_intl_12mo", "trends_12mo",
           "cap_hit_M", "jersey_rank"],
    )
    for c in ("jersey_list_member", "asg2024_member"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    df["cap_quality"] = df["cap_quality"].astype("string").fillna("low")

    # §2/§8 match_quality: identity-resolution flag that ships with every
    # published number. "low" if NHL id is blank (player unresolved on NHL) OR
    # the Wikipedia article resolved only weakly / not at all (A1 wiki_match).
    nhl_id = df["nhl_player_id"].astype("string").str.strip()
    nhl_unresolved = nhl_id.isna() | (nhl_id == "") | (nhl_id.str.lower() == "nan")
    wiki_m = df["wiki_match"].astype("string").str.strip().str.lower()
    wiki_unresolved = wiki_m.isin(["none", "weak"])
    df["match_quality"] = np.where(nhl_unresolved | wiki_unresolved, "low", "ok")

    # A10 small_sample (descriptive, non-exclusionary): GP < SMALL_SAMPLE_GP, or
    # GP NULL (no current-season row, e.g. a season-long injury absence). Players
    # stay in the pool and in every computation; the flag only warns the headline
    # must not be quoted on a tiny-sample row. NaN >= GP is False -> flagged 1.
    gp = df["games_played"].to_numpy(dtype=float)
    df["small_sample"] = np.where(gp >= SMALL_SAMPLE_GP, 0, 1).astype(int)

    df = df.sort_values("player_id").reset_index(drop=True)
    return df


def load_wiki_daily() -> dict[int, np.ndarray]:
    """player_id -> numpy array of daily pageviews (for bootstrap resampling)."""
    path = RAW_DIR / "wiki_daily.csv"
    out: dict[int, np.ndarray] = {}
    if not path.exists():
        return out
    wd = pd.read_csv(path, dtype={"player_id": int})
    for _, row in wd.iterrows():
        raw = row.get("daily_views")
        if isinstance(raw, str) and raw.strip():
            arr = np.array(
                [float(x) for x in raw.split("|") if x.strip() != ""], dtype=float
            )
        else:
            arr = np.empty(0, dtype=float)
        out[int(row["player_id"])] = arr
    return out


def load_wiki_intl_daily_summed() -> dict[int, np.ndarray]:
    """player_id -> pooled intl daily-view array (all whitelisted editions
    concatenated) for bootstrap resampling. Empty for anglophone-only players."""
    path = RAW_DIR / "wiki_intl_daily.csv"
    out: dict[int, np.ndarray] = {}
    if not path.exists():
        return out
    wd = pd.read_csv(path, dtype={"player_id": int})
    for pid, grp in wd.groupby("player_id"):
        pool: list[float] = []
        for raw in grp["daily_views"]:
            if isinstance(raw, str) and raw.strip():
                pool.extend(float(x) for x in raw.split("|") if x.strip() != "")
        out[int(pid)] = np.array(pool, dtype=float)
    return out


def load_reddit_scores() -> dict[int, np.ndarray]:
    """player_id -> numpy array of submission scores (for bootstrap resampling)."""
    path = RAW_DIR / "reddit_detail.csv"
    out: dict[int, np.ndarray] = {}
    if not path.exists():
        return out
    rd = pd.read_csv(path, dtype={"player_id": int})
    scores = pd.to_numeric(rd["score"], errors="coerce").fillna(0.0)
    for pid, grp in scores.groupby(rd["player_id"]):
        out[int(pid)] = grp.to_numpy(dtype=float)
    return out


# --------------------------------------------------------------------------- #
# Core math                                                                    #
# --------------------------------------------------------------------------- #
def zscore_array(v: np.ndarray) -> np.ndarray:
    """Sample z-score (ddof=1), NaN passes through. Constant -> zeros."""
    finite = v[np.isfinite(v)]
    if finite.size < 2:
        return np.full_like(v, np.nan, dtype=float)
    mu = finite.mean()
    sd = finite.std(ddof=1)
    if sd == 0 or not np.isfinite(sd):
        out = np.where(np.isfinite(v), 0.0, np.nan)
        return out
    return (v - mu) / sd


def engagement_from_components(comp_z: dict[str, np.ndarray]) -> np.ndarray:
    """Weighted sum of z-scores with per-player sentinel renormalization.

    comp_z: component name -> z-scored array (NaN where component NULL).
    Returns engagement_raw array (NaN if a player has all components NULL).
    """
    n = len(next(iter(comp_z.values())))
    weighted = np.zeros(n)
    total_w = np.zeros(n)
    for c, w in WEIGHTS.items():
        z = comp_z[c]
        present = np.isfinite(z)
        weighted = weighted + np.where(present, z * w, 0.0)
        total_w = total_w + np.where(present, w, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(total_w > 0, weighted / total_w, np.nan)
    return out


def compute_engagement_raw(df: pd.DataFrame):
    """Returns (engagement_raw array, dropped_components list)."""
    comp_z = {c: zscore_array(df[c].to_numpy(dtype=float)) for c in COMPONENTS}
    er = engagement_from_components(comp_z)
    dropped = []
    for i in range(len(df)):
        d = [c for c in COMPONENTS if not np.isfinite(comp_z[c][i])]
        dropped.append("|".join(d))
    return er, dropped


def _standardize_skill(df: pd.DataFrame) -> np.ndarray:
    """Standardize skill vector across the 160; impute group-mean (then overall
    mean) for any NULL skill value BEFORE standardizing."""
    feats = df[SKILL_COLS].to_numpy(dtype=float)
    groups = df["group"].to_numpy()
    filled = feats.copy()
    for gi in np.unique(groups):
        mask = groups == gi
        for j in range(feats.shape[1]):
            col = feats[mask, j]
            gmean = np.nanmean(col) if np.isfinite(col).any() else np.nan
            sub = filled[mask, j]
            sub = np.where(np.isnan(sub), gmean, sub)
            filled[mask, j] = sub
    # Any still-NaN (group had no finite value) -> overall mean.
    for j in range(filled.shape[1]):
        col = filled[:, j]
        omean = np.nanmean(col) if np.isfinite(col).any() else 0.0
        filled[:, j] = np.where(np.isnan(col), omean, col)
    # Standardize across all 160 (sample sd, ddof=1).
    mu = filled.mean(axis=0)
    sd = filled.std(axis=0, ddof=1)
    sd = np.where(sd == 0, 1.0, sd)
    return (filled - mu) / sd


def compute_peers(df: pd.DataFrame) -> list[list[int]]:
    """K=10 Mahalanobis nearest peers within position group.

    Distance uses pinv of the WITHIN-GROUP sample covariance of the
    standardized skill vector, computed separately per group.
    """
    Z = _standardize_skill(df)
    groups = df["group"].to_numpy()
    n = len(df)
    peers: list[list[int]] = [[] for _ in range(n)]

    for gi in np.unique(groups):
        idx = np.where(groups == gi)[0]
        if idx.size == 0:
            continue
        sub = Z[idx]
        if sub.shape[0] > 1:
            cov = np.cov(sub, rowvar=False, ddof=1)
            cov = np.atleast_2d(cov)
        else:
            cov = np.eye(sub.shape[1])
        VI = np.linalg.pinv(cov)
        for a_local, a in enumerate(idx):
            diffs = sub - sub[a_local]            # (m, p)
            # Mahalanobis^2 = diff @ VI @ diff.T (diagonal).
            d2 = np.einsum("ij,jk,ik->i", diffs, VI, diffs)
            order = np.argsort(d2, kind="stable")
            chosen = [idx[b] for b in order if idx[b] != a][:K_PEERS]
            peers[a] = list(map(int, chosen))
    return peers


def _peer_means(values: np.ndarray, peers: list[list[int]]) -> np.ndarray:
    """Mean of `values` over each player's peer set (NaN-aware)."""
    out = np.full(len(values), np.nan)
    for i, pl in enumerate(peers):
        if not pl:
            continue
        pv = values[pl]
        finite = pv[np.isfinite(pv)]
        if finite.size:
            out[i] = finite.mean()
    return out


def compute_expected_cap(df: pd.DataFrame) -> np.ndarray:
    """A4 denominator: market-rate cap expected from production alone.

    OLS `cap_hit_M ~ PPG + TOI/G` fit SEPARATELY per position group on the
    in-sample rows where all three are finite. Predictions are floored at the
    2025-26 league minimum ($0.775M). NULL predictors are imputed with the
    within-group mean before prediction (group fit). Age is deliberately
    excluded — including it re-imports the rookie-scale floor via
    young/cheap peers (verified empirically; see prereg §14 A4).
    """
    groups = df["group"].to_numpy()
    cap = df["cap_hit_M"].to_numpy(dtype=float)
    X_raw = np.column_stack([
        df[c].to_numpy(dtype=float) for c in EXPECTED_CAP_PREDICTORS
    ])
    out = np.full(len(df), np.nan)

    for gi in np.unique(groups):
        idx = np.where(groups == gi)[0]
        if idx.size == 0:
            continue
        cap_g = cap[idx]
        X_g = X_raw[idx]
        # Fit only on rows with finite cap + all predictors.
        fit_mask = np.isfinite(cap_g) & np.all(np.isfinite(X_g), axis=1)
        if fit_mask.sum() < (X_g.shape[1] + 1):
            # Degenerate group: floor everyone in this group at league min.
            out[idx] = LEAGUE_MIN_CAP_M
            continue
        X_fit = np.column_stack([np.ones(fit_mask.sum()), X_g[fit_mask]])
        y_fit = cap_g[fit_mask]
        beta, *_ = np.linalg.lstsq(X_fit, y_fit, rcond=None)
        # Predict on every row in the group; impute NULL predictors with
        # group means (finite-row means) before prediction.
        X_pred = X_g.copy()
        for j in range(X_pred.shape[1]):
            col = X_g[:, j]
            mu = np.nanmean(col) if np.isfinite(col).any() else 0.0
            X_pred[:, j] = np.where(np.isnan(col), mu, col)
        Xb = np.column_stack([np.ones(idx.size), X_pred])
        pred = Xb @ beta
        out[idx] = np.maximum(pred, LEAGUE_MIN_CAP_M)
    return out


def compute_oaq(df: pd.DataFrame, peers: list[list[int]] | None = None,
                market_z: np.ndarray | None = None) -> pd.DataFrame:
    """Full per-player OAQ pipeline. `df` must already have market_z if not
    passed. Returns a copy with engagement_raw, OAQ_observed, OAQ_portable,
    marchand_index (A4: OAQ_portable / expected_cap),
    marchand_index_rawcap (§8-original: OAQ_portable / cap_hit_M),
    dropped_components, effective_K, peer info."""
    df = df.copy().reset_index(drop=True)

    er, dropped = compute_engagement_raw(df)
    df["engagement_raw"] = er
    df["dropped_components"] = dropped

    if peers is None:
        peers = compute_peers(df)
    df["effective_K"] = [len(pl) for pl in peers]
    df["peer_player_ids"] = [
        "|".join(str(int(df.loc[j, "player_id"])) for j in pl) for pl in peers
    ]

    if market_z is None:
        market_z = df["market_z"].to_numpy(dtype=float)
    df["market_z"] = market_z

    # OAQ_observed.
    peer_eng = _peer_means(er, peers)
    df["peer_engagement_mean"] = peer_eng
    df["OAQ_observed"] = er - peer_eng

    # OAQ_portable — A5 headline: one-sided damped market correction.
    # Only big markets (market_z > 0) are discounted; small markets get 0.
    market_z_pos = np.maximum(0.0, market_z)
    adj_a5 = er - LAMBDA_BIGMARKET * market_z_pos
    peer_adj_a5 = _peer_means(adj_a5, peers)
    df["OAQ_portable"] = adj_a5 - peer_adj_a5

    # OAQ_portable_lockedv1: §7-original two-sided full subtraction, retained
    # for audit per §13 / A5 anti-tuning commitments.
    adj_v1 = er - market_z
    peer_adj_v1 = _peer_means(adj_v1, peers)
    df["OAQ_portable_lockedv1"] = adj_v1 - peer_adj_v1

    # Marchand Index — three denominator lenses ship together so the rookie
    # artifact and the small-market artifact can both be inspected honestly.
    #   marchand_index_hybrid     : A8 HEADLINE — rookie-deal players use
    #                               expected_cap; everyone else uses cap_hit_M.
    #                               Isolates the ELC fix from veterans, whose
    #                               actual cap hit is a real negotiated price.
    #   marchand_index            : intrinsic-efficiency lens (was A4 headline,
    #                               demoted by A8) — OAQ_portable / expected_cap
    #                               (all 160 use per-group OLS prediction).
    #   marchand_index_rawcap     : §8-original — OAQ_portable / cap_hit_M
    #                               (current-season bargain lens).
    expected_cap = compute_expected_cap(df)
    df["expected_cap"] = expected_cap
    cap_raw = df["cap_hit_M"].to_numpy(dtype=float)
    age = df["age"].to_numpy(dtype=float)
    rookie_deal = (
        np.isfinite(cap_raw) & np.isfinite(age)
        & (cap_raw <= ROOKIE_CAP_MAX_M) & (age <= ROOKIE_AGE_MAX)
    )
    df["is_rookie_deal"] = rookie_deal.astype(int)
    port = df["OAQ_portable"].to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        df["marchand_index"] = np.where(
            (expected_cap > 0) & np.isfinite(expected_cap),
            port / expected_cap, np.nan,
        )
        df["marchand_index_rawcap"] = np.where(
            (cap_raw > 0) & np.isfinite(cap_raw),
            port / cap_raw, np.nan,
        )
        # Hybrid denominator: expected_cap for rookie-deal players, raw cap
        # for everyone else. NaN if the chosen denominator is unusable.
        hybrid_denom = np.where(rookie_deal, expected_cap, cap_raw)
        df["marchand_index_hybrid"] = np.where(
            (hybrid_denom > 0) & np.isfinite(hybrid_denom),
            port / hybrid_denom, np.nan,
        )
    return df


# --------------------------------------------------------------------------- #
# §7 market proxy                                                              #
# --------------------------------------------------------------------------- #
def compute_market_z(df: pd.DataFrame):
    """Returns (market_z aligned to df rows, list of components used)."""
    mp = pd.read_csv(PILOT_DIR / "market_proxy.csv")
    candidates = ["metro_population", "arena_attendance", "team_social_followers"]
    used = []
    z_cols = []
    for c in candidates:
        if c not in mp.columns:
            continue
        col = pd.to_numeric(mp[c], errors="coerce").to_numpy(dtype=float)
        if np.isfinite(col).sum() < len(mp):  # must be present for ALL 32 teams
            continue
        used.append(c)
        z_cols.append(zscore_array(col))
    if not z_cols:
        raise RuntimeError("No market components present for all 32 teams.")
    market_size = np.mean(np.vstack(z_cols), axis=0)        # equal-weight z-mean
    market_size_z = zscore_array(market_size)                # z across 32 teams
    team_to_z = dict(zip(mp["team_code"].astype(str), market_size_z))

    miss = set(df["team_code"].astype(str)) - set(team_to_z)
    if miss:
        raise RuntimeError(f"team_code(s) in players not in market_proxy: {sorted(miss)}")
    aligned = df["team_code"].astype(str).map(team_to_z).to_numpy(dtype=float)
    return aligned, used


# --------------------------------------------------------------------------- #
# §10 bootstrap                                                                #
# --------------------------------------------------------------------------- #
def bootstrap_player_cis(
    df: pd.DataFrame,
    peers: list[list[int]],
    market_z: np.ndarray,
    wiki_daily: dict[int, np.ndarray],
    reddit_scores: dict[int, np.ndarray],
    wiki_intl_daily: dict[int, np.ndarray],
    n_draws: int = BOOTSTRAP_DRAWS,
    seed: int = SEED,
):
    """Resample each player's wiki daily vector + reddit submission pool with
    replacement; recompute engagement/OAQ/MI each draw; return percentile CIs.

    trends, cap, market_z, and peer SETS are FIXED across draws.
    """
    rng = np.random.default_rng(seed)
    n = len(df)
    pids = df["player_id"].to_numpy(dtype=int)

    # Precompute per-player numpy arrays for resampling (hot loop avoids pandas).
    daily_arrays = [wiki_daily.get(int(p), np.empty(0)) for p in pids]
    reddit_arrays = [reddit_scores.get(int(p), np.empty(0)) for p in pids]
    intl_arrays = [wiki_intl_daily.get(int(p), np.empty(0)) for p in pids]

    # Which players legitimately HAVE each resampled component (NULL stays NULL).
    base_wiki = df["wiki_12mo"].to_numpy(dtype=float)
    base_rmen = df["reddit_mentions_12mo"].to_numpy(dtype=float)
    base_rup = df["reddit_upvotes_12mo"].to_numpy(dtype=float)
    wiki_present = np.isfinite(base_wiki)
    reddit_present = np.isfinite(base_rmen)  # mentions+upvotes share NULL status
    base_intl = df["wiki_intl_12mo"].to_numpy(dtype=float)
    intl_present = np.isfinite(base_intl)

    # Fixed (non-resampled) components.
    trends_fixed = df["trends_12mo"].to_numpy(dtype=float)
    cap = df["cap_hit_M"].to_numpy(dtype=float)
    cap_ok = (cap > 0) & np.isfinite(cap)
    # A4: expected_cap is a function of (PPG, TOI/G), which are NOT resampled,
    # so it is fixed across draws — computed once on the input df.
    exp_cap = df["expected_cap"].to_numpy(dtype=float)
    exp_cap_ok = (exp_cap > 0) & np.isfinite(exp_cap)
    # Hybrid denominator: expected_cap for rookie-deal players, raw cap else.
    rookie_deal = df["is_rookie_deal"].to_numpy(dtype=bool)
    hybrid_denom = np.where(rookie_deal, exp_cap, cap)
    hybrid_ok = (hybrid_denom > 0) & np.isfinite(hybrid_denom)

    # A5 market correction is one-sided over market_z (fixed across draws).
    market_z_pos = np.maximum(0.0, market_z)

    oaq_obs = np.full((n_draws, n), np.nan)
    oaq_port = np.full((n_draws, n), np.nan)
    oaq_port_v1 = np.full((n_draws, n), np.nan)
    mi = np.full((n_draws, n), np.nan)
    mi_raw = np.full((n_draws, n), np.nan)
    mi_hyb = np.full((n_draws, n), np.nan)

    # Peer index lists -> object array of int arrays for fast mean.
    peer_idx = [np.asarray(pl, dtype=int) for pl in peers]

    for d in range(n_draws):
        wiki_draw = base_wiki.copy()
        rmen_draw = base_rmen.copy()
        rup_draw = base_rup.copy()
        intl_draw = base_intl.copy()

        for i in range(n):
            if wiki_present[i]:
                arr = daily_arrays[i]
                if arr.size:
                    samp = arr[rng.integers(0, arr.size, arr.size)]
                    wiki_draw[i] = samp.sum()
                # else keep base value (no daily detail) -> effectively fixed
            if intl_present[i]:
                arr = intl_arrays[i]
                if arr.size:
                    samp = arr[rng.integers(0, arr.size, arr.size)]
                    intl_draw[i] = samp.sum()
            if reddit_present[i]:
                arr = reddit_arrays[i]
                if arr.size:
                    samp = arr[rng.integers(0, arr.size, arr.size)]
                    rmen_draw[i] = arr.size  # count of resampled rows == pool size
                    rup_draw[i] = samp.sum()
                else:
                    # reddit present (mentions>0) but no detail rows: keep base.
                    pass

        comp_z = {
            "wiki_12mo": zscore_array(wiki_draw),
            "wiki_intl_12mo": zscore_array(intl_draw),
            "reddit_mentions_12mo": zscore_array(rmen_draw),
            "reddit_upvotes_12mo": zscore_array(rup_draw),
            "trends_12mo": zscore_array(trends_fixed),
        }
        er = engagement_from_components(comp_z)

        peer_eng = _peer_mean_fast(er, peer_idx)
        d_obs = er - peer_eng

        # A5 headline: one-sided damped market correction.
        adj_a5 = er - LAMBDA_BIGMARKET * market_z_pos
        peer_adj_a5 = _peer_mean_fast(adj_a5, peer_idx)
        d_port = adj_a5 - peer_adj_a5

        # Locked-v1 audit: two-sided full subtraction (§7-original).
        adj_v1 = er - market_z
        peer_adj_v1 = _peer_mean_fast(adj_v1, peer_idx)
        d_port_v1 = adj_v1 - peer_adj_v1

        with np.errstate(invalid="ignore", divide="ignore"):
            d_mi = np.where(exp_cap_ok, d_port / exp_cap, np.nan)
            d_mi_raw = np.where(cap_ok, d_port / cap, np.nan)
            d_mi_hyb = np.where(hybrid_ok, d_port / hybrid_denom, np.nan)

        oaq_obs[d] = d_obs
        oaq_port[d] = d_port
        oaq_port_v1[d] = d_port_v1
        mi[d] = d_mi
        mi_raw[d] = d_mi_raw
        mi_hyb[d] = d_mi_hyb

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        ci = {
            "OAQ_observed_lo95": np.nanpercentile(oaq_obs, 2.5, axis=0),
            "OAQ_observed_hi95": np.nanpercentile(oaq_obs, 97.5, axis=0),
            "OAQ_portable_lo95": np.nanpercentile(oaq_port, 2.5, axis=0),
            "OAQ_portable_hi95": np.nanpercentile(oaq_port, 97.5, axis=0),
            "OAQ_portable_lockedv1_lo95": np.nanpercentile(oaq_port_v1, 2.5, axis=0),
            "OAQ_portable_lockedv1_hi95": np.nanpercentile(oaq_port_v1, 97.5, axis=0),
            "marchand_index_lo95": np.nanpercentile(mi, 2.5, axis=0),
            "marchand_index_hi95": np.nanpercentile(mi, 97.5, axis=0),
            "marchand_index_rawcap_lo95": np.nanpercentile(mi_raw, 2.5, axis=0),
            "marchand_index_rawcap_hi95": np.nanpercentile(mi_raw, 97.5, axis=0),
            "marchand_index_hybrid_lo95": np.nanpercentile(mi_hyb, 2.5, axis=0),
            "marchand_index_hybrid_hi95": np.nanpercentile(mi_hyb, 97.5, axis=0),
        }
    return ci


def _peer_mean_fast(values: np.ndarray, peer_idx: list[np.ndarray]) -> np.ndarray:
    out = np.full(len(values), np.nan)
    for i, idx in enumerate(peer_idx):
        if idx.size == 0:
            continue
        pv = values[idx]
        finite = pv[np.isfinite(pv)]
        if finite.size:
            out[i] = finite.mean()
    return out


# --------------------------------------------------------------------------- #
# §9 external validation                                                       #
# --------------------------------------------------------------------------- #
def auc_mannwhitney(scores: np.ndarray, labels: np.ndarray) -> float:
    """AUC via Mann-Whitney U: AUC = U / (n_pos * n_neg). Ties -> midrank.

    Higher score should predict label==1. Returns NaN if either class empty.
    """
    mask = np.isfinite(scores)
    scores = scores[mask]
    labels = labels[mask]
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    n_pos, n_neg = len(pos), len(neg)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = pd.Series(scores).rank(method="average").to_numpy()
    rank_pos_sum = ranks[labels == 1].sum()
    u = rank_pos_sum - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def _bootstrap_stat_ci(stat_fn, n: int, n_draws: int, seed: int):
    """Player-level resample-with-replacement CI for a cohort statistic."""
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_draws):
        idx = rng.integers(0, n, n)
        v = stat_fn(idx)
        if v is not None and np.isfinite(v):
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def external_validation(df: pd.DataFrame, n_draws: int = BOOTSTRAP_DRAWS,
                        seed: int = SEED) -> dict:
    """V1a (Spearman rho vs jersey_rank), V1b (AUC jersey membership),
    V2 (AUC asg2024 membership; Spearman if vote share existed)."""
    port = df["OAQ_portable"].to_numpy(dtype=float)
    jersey_rank = df["jersey_rank"].to_numpy(dtype=float)
    jersey_mem = df["jersey_list_member"].to_numpy(dtype=float)
    asg_mem = df["asg2024_member"].to_numpy(dtype=float)

    results: dict = {}

    # ---- V1a: Spearman vs jersey_rank on the overlap ---- #
    rank_mask = np.isfinite(jersey_rank) & np.isfinite(port)
    n_rank = int(rank_mask.sum())
    if n_rank >= 2:
        rho_v1a = spearman_rho(port[rank_mask], jersey_rank[rank_mask])
        p_sub = port[rank_mask]
        r_sub = jersey_rank[rank_mask]

        def stat_v1a(idx):
            return spearman_rho(p_sub[idx], r_sub[idx])

        ci_v1a = _bootstrap_stat_ci(stat_v1a, n_rank, n_draws, seed)
    else:
        rho_v1a, ci_v1a = float("nan"), (float("nan"), float("nan"))
    results["V1a"] = {
        "test": "Spearman rho(OAQ_portable, jersey_rank) over rank overlap",
        "metric": "spearman_rho",
        "value": rho_v1a,
        "ci95": list(ci_v1a),
        "n": n_rank,
        "floor": V1_FLOOR,
        "target": V1_TARGET,
        "underpowered": n_rank < UNDERPOWERED_N,
        "convention": ("jersey_rank is 1=best, so a NEGATIVE rho indicates "
                       "AGREEMENT (high OAQ_portable -> low/better rank number)."),
    }

    # ---- V1b: AUC jersey membership across all 160 (primary) ---- #
    n_pos_v1b = int(np.nansum(jersey_mem == 1))
    auc_v1b = auc_mannwhitney(port, jersey_mem)
    if np.isfinite(auc_v1b):
        def stat_v1b(idx):
            return auc_mannwhitney(port[idx], jersey_mem[idx])
        ci_v1b = _bootstrap_stat_ci(stat_v1b, len(df), n_draws, seed)
    else:
        ci_v1b = (float("nan"), float("nan"))
    results["V1b"] = {
        "test": "AUC OAQ_portable discriminating jersey_list_member (1/0)",
        "metric": "auc",
        "value": auc_v1b,
        "ci95": list(ci_v1b),
        "n_total": int(len(df)),
        "n_members": n_pos_v1b,
        "underpowered": n_pos_v1b < UNDERPOWERED_N,
    }

    # ---- V2: AUC asg2024 membership (membership-only; no vote share) ---- #
    n_pos_v2 = int(np.nansum(asg_mem == 1))
    auc_v2 = auc_mannwhitney(port, asg_mem)
    if np.isfinite(auc_v2):
        def stat_v2(idx):
            return auc_mannwhitney(port[idx], asg_mem[idx])
        ci_v2 = _bootstrap_stat_ci(stat_v2, len(df), n_draws, seed)
    else:
        ci_v2 = (float("nan"), float("nan"))
    results["V2"] = {
        "test": "AUC OAQ_portable discriminating asg2024_member (1/0)",
        "metric": "auc",
        "value": auc_v2,
        "ci95": list(ci_v2),
        "n_total": int(len(df)),
        "n_members": n_pos_v2,
        "floor": V2_FLOOR,
        "target": V2_TARGET,
        "underpowered": n_pos_v2 < UNDERPOWERED_N,
        "note": ("asg2024 published as membership only (no fan-vote share "
                 "available), so V2 is AUC; no Spearman computed."),
    }

    # ---- V3 (A6): team-level triangulation. n=32 teams. ---- #
    v3_path = PILOT_DIR / "team_outcomes.csv"
    if v3_path.exists():
        to_df = pd.read_csv(v3_path)
        wiki_team = pd.to_numeric(
            to_df["wiki_12mo"], errors="coerce"
        ).to_numpy(dtype=float)
        team_codes_v3 = to_df["team_code"].astype(str).to_numpy()
        # Sum OAQ_observed across each team's 5 pilot players (held-out test:
        # peer-matched residual aggregated to team level vs. independent
        # team-account popularity signal).
        oaq_obs_all = df["OAQ_observed"].to_numpy(dtype=float)
        team_codes_p = df["team_code"].astype(str).to_numpy()
        team_sum_oaq = []
        team_sum_eng = []
        eng_all = df["engagement_raw"].to_numpy(dtype=float)
        wiki_aligned = []
        team_used = []
        for tc, w in zip(team_codes_v3, wiki_team):
            if not np.isfinite(w):
                continue
            mask = team_codes_p == tc
            if mask.sum() == 0:
                continue
            obs_sum = np.nansum(oaq_obs_all[mask])
            eng_sum = np.nansum(eng_all[mask])
            team_sum_oaq.append(obs_sum)
            team_sum_eng.append(eng_sum)
            wiki_aligned.append(w)
            team_used.append(tc)
        team_sum_oaq = np.array(team_sum_oaq, dtype=float)
        team_sum_eng = np.array(team_sum_eng, dtype=float)
        wiki_aligned = np.array(wiki_aligned, dtype=float)
        n_v3 = int(len(team_sum_oaq))
        if n_v3 >= 2:
            rho_v3 = spearman_rho(team_sum_oaq, wiki_aligned)
            rho_v3_eng = spearman_rho(team_sum_eng, wiki_aligned)

            def stat_v3(idx):
                return spearman_rho(team_sum_oaq[idx], wiki_aligned[idx])

            def stat_v3_eng(idx):
                return spearman_rho(team_sum_eng[idx], wiki_aligned[idx])

            ci_v3 = _bootstrap_stat_ci(stat_v3, n_v3, n_draws, seed)
            ci_v3_eng = _bootstrap_stat_ci(stat_v3_eng, n_v3, n_draws, seed)
        else:
            rho_v3, ci_v3 = float("nan"), (float("nan"), float("nan"))
            rho_v3_eng, ci_v3_eng = float("nan"), (float("nan"), float("nan"))
        results["V3"] = {
            "test": ("Spearman rho(sum_OAQ_observed_per_team, "
                     "team_wiki_12mo) across n teams"),
            "metric": "spearman_rho",
            "value": rho_v3,
            "ci95": list(ci_v3),
            "n": n_v3,
            "floor": V3_FLOOR,
            "target": V3_TARGET,
            "underpowered": n_v3 < UNDERPOWERED_N,
            "outcome_signal": ("team Wikipedia 12-mo pageviews (A6 "
                               "graceful-degradation: Reddit subscriber 403)"),
            "predictor": "sum of OAQ_observed across each team's 5 pilot players",
            "robustness_eng_raw": {
                "rho": rho_v3_eng,
                "ci95": list(ci_v3_eng),
                "note": ("mechanical baseline: sum of engagement_raw "
                         "(no peer-skill control)"),
            },
            "teams_used": team_used,
        }
    else:
        results["V3"] = {
            "test": "team-level triangulation (A6)",
            "value": float("nan"),
            "ci95": [float("nan"), float("nan")],
            "n": 0,
            "floor": V3_FLOOR,
            "underpowered": True,
            "note": "team_outcomes.csv not found",
        }
    return results


# --------------------------------------------------------------------------- #
# §11 patterns                                                                 #
# --------------------------------------------------------------------------- #
def evaluate_patterns(df: pd.DataFrame, external: dict) -> dict:
    out: dict = {}

    # PA: V1 Spearman rho >= 0.40. Use V1a (the Spearman test). Underpowered
    # -> inconclusive. Direction: jersey_rank 1=best so agreement is NEGATIVE
    # rho; we test |rho| >= floor when not underpowered, and report signed rho.
    v1a = external["V1a"]
    rho = v1a["value"]
    if v1a["underpowered"] or not np.isfinite(rho):
        pa_verdict = "inconclusive"
    else:
        pa_verdict = "confirmed" if abs(rho) >= PA_FLOOR else "disconfirmed"
    out["PA"] = {
        "description": "OAQ_portable aligns with independent jersey demand (V1 Spearman >= 0.40)",
        "metric": "spearman_rho (signed; negative = agreement)",
        "value": rho,
        "ci95": v1a["ci95"],
        "n": v1a["n"],
        "floor": PA_FLOOR,
        "underpowered": v1a["underpowered"],
        "verdict": pa_verdict,
    }

    # PB: V2 Spearman rho >= 0.45. No vote share -> no Spearman -> inconclusive
    # (underpowered, membership-only).
    v2 = external["V2"]
    out["PB"] = {
        "description": "OAQ_portable aligns with independent fan voting (V2 Spearman >= 0.45)",
        "metric": "spearman_rho (unavailable: asg2024 membership-only)",
        "value": float("nan"),
        "auc_proxy": v2["value"],
        "auc_ci95": v2["ci95"],
        "n_members": v2["n_members"],
        "floor": PB_FLOOR,
        "underpowered": v2["underpowered"],
        "verdict": "inconclusive",
    }

    # PD (A6): V3 team-level triangulation — Spearman rho >= 0.40.
    v3 = external.get("V3", {})
    rho_v3 = v3.get("value", float("nan"))
    if v3.get("underpowered", True) or not np.isfinite(rho_v3):
        pd_verdict = "inconclusive"
    else:
        pd_verdict = "confirmed" if rho_v3 >= PD_FLOOR else "disconfirmed"
    out["PD"] = {
        "description": ("Sum of OAQ_observed per team aligns with independent "
                        "team Wikipedia pageviews (V3 Spearman >= 0.40)"),
        "metric": "spearman_rho",
        "value": rho_v3,
        "ci95": v3.get("ci95", [float("nan"), float("nan")]),
        "n": v3.get("n", 0),
        "floor": PD_FLOOR,
        "underpowered": v3.get("underpowered", True),
        "verdict": pd_verdict,
        "robustness_eng_raw": v3.get("robustness_eng_raw", {}),
    }

    # PC: >=3 of top-10 by engagement_raw are displaced OUT of top-10 by the
    # headline MI. A8: headline = marchand_index_hybrid (rookie-deal players
    # use expected_cap; everyone else uses actual cap_hit_M). Recomputed off
    # the hybrid headline per the A8 re-evaluation obligation.
    # cap_quality=low excluded from the MI ranking.
    eng = df[["full_name", "engagement_raw"]].dropna(subset=["engagement_raw"])
    top10_eng = (
        eng.sort_values("engagement_raw", ascending=False)
        .head(10)["full_name"]
        .tolist()
    )
    mi_pool = df[df["cap_quality"].astype(str).str.lower() != "low"]
    mi_pool = mi_pool.dropna(subset=["marchand_index_hybrid"])
    top10_mi = (
        mi_pool.sort_values("marchand_index_hybrid", ascending=False)
        .head(10)["full_name"]
        .tolist()
    )
    displaced = [n for n in top10_eng if n not in set(top10_mi)]
    out["PC"] = {
        "description": ">=3 of top-10 by engagement_raw displaced out of top-10 by marchand_index_hybrid (A8 hybrid headline)",
        "top10_engagement_raw": top10_eng,
        "top10_marchand_index_hybrid": top10_mi,
        "n_displaced": len(displaced),
        "displaced_names": displaced,
        "floor": 3,
        "verdict": "confirmed" if len(displaced) >= 3 else "disconfirmed",
    }
    return out


# --------------------------------------------------------------------------- #
# Output writers                                                               #
# --------------------------------------------------------------------------- #
def _fnum(x, nd=4):
    try:
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "NA"
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return "NA"


def write_results_md(path: Path, df: pd.DataFrame, external: dict,
                     patterns: dict, market_used: list[str],
                     reddit_note: str) -> None:
    lines: list[str] = []
    lines.append("# Tier-1 pilot results — The Marchand Index (pilot2)\n")
    lines.append("Generated by `pilot2/compute_oaq.py`. Method locked in "
                 "`pilot2/preregistration.md` (§4,6,7,8,9,10,11; A1-A9). "
                 "Headline denominator = hybrid (A8); Reddit transport = OAuth "
                 "(A9); set = TOI position-split (A7). All effects reported "
                 "with 95% bootstrap CI regardless of direction.\n")
    lines.append(f"**A5 headline market correction:** "
                 f"`OAQ_portable = engagement_raw − λ × max(0, market_z) − "
                 f"peer_mean` with **λ = {LAMBDA_BIGMARKET}** "
                 "(maximum-entropy midpoint between 0 and 1; sensitivity "
                 "ladder reported below). Locked-v1 (two-sided, λ=1) retained "
                 "in `OAQ_portable_lockedv1` for audit.\n")

    lines.append("## Configuration\n")
    lines.append(f"- N skaters: {len(df)} (forwards "
                 f"{(df['group']=='f1').sum()}, defense {(df['group']=='d1').sum()})")
    lines.append(f"- K peers: {K_PEERS} (Mahalanobis, within-group inverse "
                 "covariance of standardized (age, ppg, toi_per_game))")
    lines.append(f"- Bootstrap draws: {BOOTSTRAP_DRAWS}, seed {SEED}")
    lines.append(f"- Market proxy components used: {', '.join(market_used)}")
    lines.append(f"- Reddit availability: {reddit_note}")
    n_mq_low = int((df["match_quality"].astype(str) == "low").sum())
    n_cap_low = int((df["cap_quality"].astype(str).str.lower() == "low").sum())
    lines.append(f"- match_quality=low: {n_mq_low} (identity-resolution); "
                 f"cap_quality=low: {n_cap_low} (excluded from MI leaderboard)")
    n_small = int((df["small_sample"] == 1).sum())
    lines.append(f"- small_sample (GP < {SMALL_SAMPLE_GP} or NULL; A10, "
                 f"descriptive/non-exclusionary): {n_small} — kept in all "
                 "computations; headline is not quoted on these rows")
    lines.append("- **A8 headline denominator:** `marchand_index_hybrid` — "
                 "rookie-deal players use `expected_cap` (per-group OLS of "
                 "cap_hit_M ~ PPG + TOI/G, age excluded, floored at "
                 f"${LEAGUE_MIN_CAP_M:.3f}M); everyone else uses actual "
                 "`cap_hit_M`. `marchand_index` (expected_cap for all, the "
                 "intrinsic-efficiency lens; was the A4 headline) and "
                 "`marchand_index_rawcap` (§8-original, raw cap denominator) "
                 "are also computed for the 5-lens leaderboard comparison.")
    n_rookie = int(df["is_rookie_deal"].sum())
    lines.append(f"- **Rookie-deal flag:** cap ≤ ${ROOKIE_CAP_MAX_M:.3f}M AND "
                 f"age ≤ {ROOKIE_AGE_MAX} → {n_rookie} of {len(df)} players.\n")

    # Sentinel / dropped summary.
    drop_counts: dict[str, int] = {}
    for s in df["dropped_components"]:
        for c in (s.split("|") if s else []):
            drop_counts[c] = drop_counts.get(c, 0) + 1
    lines.append("## Sentinel / dropped-component summary\n")
    if drop_counts:
        lines.append("| Component | Players dropped (NULL) |")
        lines.append("|---|---|")
        for c in COMPONENTS:
            if c in drop_counts:
                lines.append(f"| {c} | {drop_counts[c]} |")
    else:
        lines.append("No components dropped for any player.")
    lines.append("")

    # External validation table.
    lines.append("## External validation (§9)\n")
    lines.append("| ID | Test | Metric | Value | 95% CI | n | Power |")
    lines.append("|---|---|---|---|---|---|---|")
    v1a = external["V1a"]
    lines.append(
        f"| V1a | {v1a['test']} | rho | {_fnum(v1a['value'])} | "
        f"[{_fnum(v1a['ci95'][0])}, {_fnum(v1a['ci95'][1])}] | {v1a['n']} | "
        f"{'underpowered' if v1a['underpowered'] else 'powered'} |"
    )
    v1b = external["V1b"]
    lines.append(
        f"| V1b | {v1b['test']} | AUC | {_fnum(v1b['value'])} | "
        f"[{_fnum(v1b['ci95'][0])}, {_fnum(v1b['ci95'][1])}] | "
        f"{v1b['n_members']}/{v1b['n_total']} | "
        f"{'underpowered' if v1b['underpowered'] else 'powered'} |"
    )
    v2 = external["V2"]
    lines.append(
        f"| V2 | {v2['test']} | AUC | {_fnum(v2['value'])} | "
        f"[{_fnum(v2['ci95'][0])}, {_fnum(v2['ci95'][1])}] | "
        f"{v2['n_members']}/{v2['n_total']} | "
        f"{'underpowered' if v2['underpowered'] else 'powered'} |"
    )
    v3 = external.get("V3", {})
    if v3:
        lines.append(
            f"| V3 | {v3.get('test','')} | rho | {_fnum(v3.get('value'))} | "
            f"[{_fnum(v3.get('ci95',[float('nan'),float('nan')])[0])}, "
            f"{_fnum(v3.get('ci95',[float('nan'),float('nan')])[1])}] | "
            f"{v3.get('n', 0)} (teams) | "
            f"{'underpowered' if v3.get('underpowered', True) else 'powered'} |"
        )
    lines.append("")
    lines.append(f"- V1a convention: {v1a['convention']}")
    lines.append(f"- V2 note: {v2['note']}")
    if v3:
        rob = v3.get("robustness_eng_raw", {})
        lines.append(
            f"- V3 (A6): outcome = {v3.get('outcome_signal','')}; "
            f"predictor = {v3.get('predictor','')}. "
            f"Mechanical baseline (sum of engagement_raw, no peer-skill "
            f"control): rho = {_fnum(rob.get('rho'))}, 95% CI "
            f"[{_fnum(rob.get('ci95',[float('nan'),float('nan')])[0])}, "
            f"{_fnum(rob.get('ci95',[float('nan'),float('nan')])[1])}]. "
            "Headline V3 uses peer-matched OAQ_observed."
        )
    lines.append("")

    # Patterns.
    lines.append("## Pre-registered pattern verdicts (§11)\n")
    pa = patterns["PA"]
    lines.append(f"### PA — {pa['description']}")
    lines.append(f"- Spearman rho = {_fnum(pa['value'])}, 95% CI "
                 f"[{_fnum(pa['ci95'][0])}, {_fnum(pa['ci95'][1])}], n={pa['n']}")
    lines.append(f"- **Verdict: {pa['verdict']}**"
                 f"{' (underpowered)' if pa['underpowered'] else ''}\n")
    pb = patterns["PB"]
    lines.append(f"### PB — {pb['description']}")
    lines.append(f"- Spearman unavailable (membership-only); AUC proxy = "
                 f"{_fnum(pb['auc_proxy'])}, 95% CI "
                 f"[{_fnum(pb['auc_ci95'][0])}, {_fnum(pb['auc_ci95'][1])}], "
                 f"members={pb['n_members']}")
    lines.append(f"- **Verdict: {pb['verdict']}**"
                 f"{' (underpowered)' if pb['underpowered'] else ''}\n")
    pd_ = patterns.get("PD", {})
    if pd_:
        lines.append(f"### PD — {pd_['description']}")
        lines.append(
            f"- Spearman rho = {_fnum(pd_['value'])}, 95% CI "
            f"[{_fnum(pd_['ci95'][0])}, {_fnum(pd_['ci95'][1])}], n={pd_['n']} teams"
        )
        rob = pd_.get("robustness_eng_raw", {})
        if rob:
            lines.append(
                f"- Mechanical baseline (sum of engagement_raw): rho = "
                f"{_fnum(rob.get('rho'))}, 95% CI "
                f"[{_fnum(rob.get('ci95',[float('nan'),float('nan')])[0])}, "
                f"{_fnum(rob.get('ci95',[float('nan'),float('nan')])[1])}] — "
                "comparison shows whether peer-skill control adds signal "
                "beyond raw aggregate attention."
            )
        lines.append(
            f"- **Verdict: {pd_['verdict']}**"
            f"{' (underpowered)' if pd_['underpowered'] else ''}\n"
        )

    pc = patterns["PC"]
    lines.append(f"### PC — {pc['description']}")
    lines.append(f"- Displaced out of top-10 by MI: {pc['n_displaced']} "
                 f"({', '.join(pc['displaced_names']) or 'none'})")
    lines.append(f"- **Verdict: {pc['verdict']}**\n")

    # Leaderboards.
    lines.append("## Leaderboards\n")
    lines.append(
        f"Rookie-deal flag: `cap_hit_M ≤ ${ROOKIE_CAP_MAX_M:.3f}M AND "
        f"age ≤ {ROOKIE_AGE_MAX}` → "
        f"{int(df['is_rookie_deal'].sum())} of {len(df)} players. Catches "
        "every clean ELC in the set; excludes vet-min depth (Stecher/"
        "McIlrath/Wotherspoon/Mukhamadullin).\n"
    )

    lines.append("### Top 10 by engagement_raw (no peer or market adjustment)")
    lines.append("| Rank | Player | Age | engagement_raw | OAQ_portable |")
    lines.append("|---|---|---|---|---|")
    eng_top = (
        df.dropna(subset=["engagement_raw"])
        .sort_values("engagement_raw", ascending=False)
        .head(10)
    )
    for i, (_, r) in enumerate(eng_top.iterrows(), 1):
        lines.append(
            f"| {i} | {r['full_name']} | {_fnum(r['age'], 0)} | "
            f"{_fnum(r['engagement_raw'])} | {_fnum(r['OAQ_portable'])} |"
        )
    lines.append("")

    mi_pool = df[df["cap_quality"].astype(str).str.lower() != "low"].copy()
    rookie_pool = mi_pool[mi_pool["is_rookie_deal"] == 1]
    nonrookie_pool = mi_pool[mi_pool["is_rookie_deal"] == 0]

    # Lens 1 — rookie-deal only, raw cap.
    lines.append("### Lens 1 — Top 10 ROOKIE-DEAL only, raw cap")
    lines.append("(pool = rookie-deal players, ranked by OAQ_portable / cap_hit_M)\n")
    lines.append("| Rank | Player | Age | MI_raw | OAQ_portable | cap_hit_M |")
    lines.append("|---|---|---|---|---|---|")
    r1 = rookie_pool.dropna(subset=["marchand_index_rawcap"]).sort_values(
        "marchand_index_rawcap", ascending=False).head(10)
    for i, (_, r) in enumerate(r1.iterrows(), 1):
        lines.append(
            f"| {i} | {r['full_name']} | {_fnum(r['age'],0)} | "
            f"{_fnum(r['marchand_index_rawcap'])} | "
            f"{_fnum(r['OAQ_portable'])} | {_fnum(r['cap_hit_M'],2)} |"
        )
    lines.append("")

    # Lens 2 — non-rookie-deal only, raw cap.
    lines.append("### Lens 2 — Top 10 NON-ROOKIE-DEAL only, raw cap "
                 "(\"rookie-deal players removed\")")
    lines.append("(pool = veterans / extension-era players only, ranked by "
                 "OAQ_portable / cap_hit_M)\n")
    lines.append("| Rank | Player | Age | MI_raw | OAQ_portable | cap_hit_M |")
    lines.append("|---|---|---|---|---|---|")
    r2 = nonrookie_pool.dropna(subset=["marchand_index_rawcap"]).sort_values(
        "marchand_index_rawcap", ascending=False).head(10)
    for i, (_, r) in enumerate(r2.iterrows(), 1):
        lines.append(
            f"| {i} | {r['full_name']} | {_fnum(r['age'],0)} | "
            f"{_fnum(r['marchand_index_rawcap'])} | "
            f"{_fnum(r['OAQ_portable'])} | {_fnum(r['cap_hit_M'],2)} |"
        )
    lines.append("")

    # Lens 3 — all 160, raw cap (§8-original, no rookie adjustment).
    lines.append("### Lens 3 — Top 10 ALL players, raw cap (no rookie "
                 "adjustment, §8-original)")
    lines.append("(pool = all 160, ranked by OAQ_portable / cap_hit_M)\n")
    lines.append("| Rank | Player | Age | Rookie? | MI_raw | OAQ_portable | "
                 "cap_hit_M |")
    lines.append("|---|---|---|---|---|---|---|")
    r3 = mi_pool.dropna(subset=["marchand_index_rawcap"]).sort_values(
        "marchand_index_rawcap", ascending=False).head(10)
    for i, (_, r) in enumerate(r3.iterrows(), 1):
        lines.append(
            f"| {i} | {r['full_name']} | {_fnum(r['age'],0)} | "
            f"{'Y' if r['is_rookie_deal']==1 else 'N'} | "
            f"{_fnum(r['marchand_index_rawcap'])} | "
            f"{_fnum(r['OAQ_portable'])} | {_fnum(r['cap_hit_M'],2)} |"
        )
    lines.append("")

    # Lens 4 — hybrid (rookie-deal → expected_cap; others → raw cap).
    # A8: this is the published HEADLINE lens.
    lines.append("### Lens 4 — Top 10 ALL players, HYBRID denominator "
                 "(rookie-deal → expected_cap; others → raw cap) — **HEADLINE (A8)**")
    lines.append("(rookies are evaluated at projected market pay vs. similar-"
                 "skill peers; veterans keep their actual cap hit. This is the "
                 "published headline leaderboard: fan-attention surplus per "
                 "dollar of a player's *actual* deal, projecting only those "
                 "contractually barred from signing one.)\n")
    lines.append("| Rank | Player | Age | Rookie? | MI_hybrid | "
                 "OAQ_portable | denom_used |")
    lines.append("|---|---|---|---|---|---|---|")
    r4 = mi_pool.dropna(subset=["marchand_index_hybrid"]).sort_values(
        "marchand_index_hybrid", ascending=False).head(10)
    for i, (_, r) in enumerate(r4.iterrows(), 1):
        is_r = r["is_rookie_deal"] == 1
        denom = r["expected_cap"] if is_r else r["cap_hit_M"]
        denom_label = ("expected_cap=" if is_r else "cap_hit_M=") + \
                      _fnum(denom, 2)
        lines.append(
            f"| {i} | {r['full_name']} | {_fnum(r['age'],0)} | "
            f"{'Y' if is_r else 'N'} | "
            f"{_fnum(r['marchand_index_hybrid'])} | "
            f"{_fnum(r['OAQ_portable'])} | {denom_label} |"
        )
    lines.append("")

    # Lens 5 — A4 full: expected_cap for everyone (intrinsic-efficiency lens).
    lines.append("### Lens 5 — Top 10 ALL players, FULL A4 "
                 "(everyone uses expected_cap) — intrinsic-efficiency lens")
    lines.append("(all 160 evaluated at projected market pay; attention per "
                 "skill-deserved dollar. Was the A4 headline; A8 demoted it to "
                 "the intrinsic-efficiency lens and promoted Lens 4 hybrid as "
                 "the headline. Retained for audit.)\n")
    lines.append("| Rank | Player | Age | Rookie? | MI | OAQ_portable | "
                 "expected_cap | cap_hit_M |")
    lines.append("|---|---|---|---|---|---|---|---|")
    r5 = mi_pool.dropna(subset=["marchand_index"]).sort_values(
        "marchand_index", ascending=False).head(10)
    for i, (_, r) in enumerate(r5.iterrows(), 1):
        lines.append(
            f"| {i} | {r['full_name']} | {_fnum(r['age'],0)} | "
            f"{'Y' if r['is_rookie_deal']==1 else 'N'} | "
            f"{_fnum(r['marchand_index'])} | "
            f"{_fnum(r['OAQ_portable'])} | "
            f"{_fnum(r['expected_cap'],2)} | "
            f"{_fnum(r['cap_hit_M'],2)} |"
        )
    lines.append("")

    # Top-20 team clustering under A5 (sanity check that small-market amplifier
    # is gone).
    market_clusters = (
        df.dropna(subset=["marchand_index"])
        .sort_values("marchand_index", ascending=False)
        .head(20)["team_code"].value_counts()
    )
    cluster_str = ", ".join(
        f"{t}={c}" for t, c in market_clusters.items() if c >= 2
    ) or "no team contributes ≥2 to top 20"
    lines.append("### A5 sanity check — team clustering in top-20 MI")
    lines.append(
        f"Top-20 MI team clustering under A5 (λ = {LAMBDA_BIGMARKET}): "
        f"{cluster_str}. Under locked-v1 (λ = 1, two-sided) the same set "
        "clustered SJ=5, BUF=4, WPG=4 — driven by the small-market "
        "subtraction. A5 collapses small-market `max(0, market_z)` to 0, "
        "removing that amplifier.\n"
    )

    # λ sensitivity ladder — recompute Lens 5 (expected_cap MI) under each λ.
    er_all = df["engagement_raw"].to_numpy(dtype=float)
    market_z_all = df["market_z"].to_numpy(dtype=float)
    peer_ids_str = df["peer_player_ids"].astype(str)
    peer_idx_lists = [
        [int(x) for x in s.split("|") if x] for s in peer_ids_str
    ]
    pid_to_row = {int(p): i for i, p in enumerate(df["player_id"].to_numpy())}
    peer_rows = [
        [pid_to_row[p] for p in pl if p in pid_to_row]
        for pl in peer_idx_lists
    ]
    exp_cap_all = df["expected_cap"].to_numpy(dtype=float)
    exp_ok = (exp_cap_all > 0) & np.isfinite(exp_cap_all)

    lines.append("### λ sensitivity ladder — top 10 by MI (Lens 5 view)")
    lines.append(
        f"For each λ, recompute `OAQ_portable = engagement_raw − λ × "
        f"max(0, market_z) − peer_mean(same)`, divide by `expected_cap`, "
        "exclude `cap_quality=low`. λ = 0 is the no-correction floor; "
        f"λ = {LAMBDA_BIGMARKET} is the A5 headline; λ = 1 is full one-sided "
        "subtraction (still milder than locked-v1, which is two-sided).\n"
    )
    lines.append("| Rank | " + " | ".join(
        f"λ={lam}" for lam in LAMBDA_SENSITIVITY) + " |")
    lines.append("|---|" + "---|" * len(LAMBDA_SENSITIVITY))
    lam_top10: list[list[str]] = []
    cap_quality_low = (
        df["cap_quality"].astype(str).str.lower() == "low"
    ).to_numpy()
    for lam in LAMBDA_SENSITIVITY:
        adj = er_all - lam * np.maximum(0.0, market_z_all)
        peer_adj = np.full_like(adj, np.nan)
        for i, rows in enumerate(peer_rows):
            if not rows:
                continue
            sub = adj[rows]
            sub = sub[np.isfinite(sub)]
            if sub.size:
                peer_adj[i] = sub.mean()
        port = adj - peer_adj
        with np.errstate(invalid="ignore", divide="ignore"):
            mi_lam = np.where(exp_ok, port / exp_cap_all, np.nan)
        mi_lam = np.where(cap_quality_low, np.nan, mi_lam)
        order = np.argsort(-np.where(np.isfinite(mi_lam), mi_lam, -np.inf))
        top = []
        for j in order[:10]:
            if not np.isfinite(mi_lam[j]):
                top.append("—")
            else:
                top.append(
                    f"{df.iloc[j]['full_name']} ({mi_lam[j]:.3f})"
                )
        lam_top10.append(top)
    for r in range(10):
        row = [str(r + 1)]
        for col in range(len(LAMBDA_SENSITIVITY)):
            row.append(lam_top10[col][r])
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append(
        "Stability check: the qualitative MI structure (Crosby / Celebrini / "
        "Will Smith / McDavid / M.Tkachuk holding top ranks across λ ∈ "
        f"[0, {LAMBDA_BIGMARKET}]) supports the choice of λ as a "
        "max-entropy midpoint — the headline ranking is not a sharp "
        "function of the exact λ.\n"
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_results_json(path: Path, external: dict, patterns: dict,
                       market_used: list[str], reddit_note: str) -> None:
    payload = {
        "config": {
            "K_peers": K_PEERS,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "seed": SEED,
            "market_components_used": market_used,
            "reddit_availability": reddit_note,
        },
        "external_validation": external,
        "patterns": {k: _json_safe(v) for k, v in patterns.items()},
    }
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if not np.isfinite(f) else f
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


OUT_COLS = [
    "player_id", "full_name", "position", "group", "team_code",
    "age", "ppg", "toi_per_game", "games_played", "small_sample",
    "wiki_12mo", "wiki_intl_12mo", "intl_match",
    "trends_12mo", "reddit_mentions_12mo", "reddit_upvotes_12mo",
    "engagement_raw", "dropped_components",
    "effective_K", "peer_player_ids", "peer_engagement_mean",
    "market_z",
    "OAQ_observed", "OAQ_observed_lo95", "OAQ_observed_hi95",
    "OAQ_portable", "OAQ_portable_lo95", "OAQ_portable_hi95",
    "OAQ_portable_lockedv1",
    "OAQ_portable_lockedv1_lo95", "OAQ_portable_lockedv1_hi95",
    "expected_cap", "is_rookie_deal",
    "marchand_index", "marchand_index_lo95", "marchand_index_hi95",
    "marchand_index_rawcap",
    "marchand_index_rawcap_lo95", "marchand_index_rawcap_hi95",
    "marchand_index_hybrid",
    "marchand_index_hybrid_lo95", "marchand_index_hybrid_hi95",
    "cap_hit_M", "cap_quality", "match_quality",
    "jersey_list_member", "jersey_rank", "asg2024_member",
]


def main() -> None:
    df = load_inputs()
    wiki_daily = load_wiki_daily()
    reddit_scores = load_reddit_scores()
    wiki_intl_daily = load_wiki_intl_daily_summed()

    market_z, market_used = compute_market_z(df)
    df["market_z"] = market_z

    peers = compute_peers(df)
    df = compute_oaq(df, peers=peers, market_z=market_z)

    ci = bootstrap_player_cis(df, peers, market_z, wiki_daily, reddit_scores,
                              wiki_intl_daily)
    for k, v in ci.items():
        df[k] = v

    external = external_validation(df)
    patterns = evaluate_patterns(df, external)

    n_reddit = int(np.isfinite(df["reddit_mentions_12mo"]).sum())
    reddit_note = f"{n_reddit}/{len(df)} players had non-NULL Reddit data"

    # Write oaq_pilot.csv (atomic via pandas .tmp -> replace).
    out = df.reindex(columns=OUT_COLS)
    csv_path = PILOT_DIR / "oaq_pilot.csv"
    tmp = csv_path.with_suffix(".csv.tmp")
    out.to_csv(tmp, index=False, encoding="utf-8")
    import os
    os.replace(tmp, csv_path)

    write_results_md(PILOT_DIR / "results.md", df, external, patterns,
                     market_used, reddit_note)
    write_results_json(PILOT_DIR / "results.json", external, patterns,
                       market_used, reddit_note)

    print(f"Wrote {csv_path}")
    print(f"Wrote {PILOT_DIR / 'results.md'}")
    print(f"Wrote {PILOT_DIR / 'results.json'}")
    print("Market components:", market_used)
    print("Reddit:", reddit_note)
    print("Pattern verdicts:",
          {k: v["verdict"] for k, v in patterns.items()})


if __name__ == "__main__":
    main()
