"""A53 peer-vector robustness lenses: Lens A (production detail) vs Lens B
(attention stock), each compared separately against the shipped §6/A13 primary.

WHY: §6/A13 matches peers on (age, PPG, TOI/G, CF%, xGF%, OZS%). Two objections
survive that vector. (A) The skill match is too coarse -- PPG hides shooters vs.
playmakers and ignores power-play deployment. (B) The residual is accumulated
fame, because every control is a single-season FLOW while attention is a STOCK.
A53 answers them with two additional peer constructions, reported alongside the
primary and never promoted to headline.

FIDELITY. `value_propositions.md` records the earlier in-memory "peer-stack v2"
run as only 87.1% faithful to the stored `peer_player_ids`, so ~13 points of its
reported churn was the re-implementation's own drift rather than the feature
set. This script removes that ambiguity two ways: the primary is taken from the
STORED `peer_player_ids` in `oaq_pilot.csv` (not re-derived), and a re-derived
primary is scored against it as a published fidelity check before any lens
number is believed.

DENOMINATORS are not re-derived either. A53 leaves the A4/A8/A24/A49.2 headline
denominator unchanged, so it is backed out per row as
`cap_denom = OAQ_portable_shipped / marchand_index_shipped` and reused for every
lens. That is exact, and it makes denominator drift structurally impossible.

Reads:  marchand_index/oaq_pilot.csv                    (the current build; primary)
        marchand_index/players.csv                      (nhl_player_id join)
        marchand_index/raw/moneypuck_skaters_2025.csv   (Lens A)
        marchand_index/raw/player_stock.csv             (Lens B; fetch_player_stock.py)
Writes: marchand_index/diagnostics/peer_vector_lenses.csv   per-player, all lenses
        marchand_index/diagnostics/peer_vector_lenses.md    the comparison tables
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
sys.path.insert(0, str(PILOT))

from compute_oaq import (K_PEERS, LAMBDA_BIGMARKET, SKILL_COLS,  # noqa: E402
                         position_class, spearman_rho)

RAW = PILOT / "raw"
SHRINK_DELTA = 0.10          # A53
UNDRAFTED_PICK = 225         # A53: one past the last pick of a 7x32 draft

LENS_A_ADD = ["pp_toi_per_game", "ixg_per60", "shots_per60",
              "points_per60", "goal_share", "games_played"]
LENS_B_ADD = ["career_gp_log", "career_points_log", "nhl_seasons",
              "draft_overall_log"]


# --------------------------------------------------------------------------
# feature construction
# --------------------------------------------------------------------------
def build_lens_a(df: pd.DataFrame) -> pd.DataFrame:
    """A53 Lens A features from the MoneyPuck season-summary CSV.

    Rates use 5v5 icetime, preserving A13's locked-situation rule.
    `pp_toi_per_game` is A53's one deliberate exception (power-play deployment
    cannot be measured at 5v5) and `goal_share` uses all situations because a
    5v5-only points denominator is too thin to be a stable ratio.
    """
    mp = pd.read_csv(RAW / "moneypuck_skaters_2025.csv", usecols=[
        "playerId", "situation", "games_played", "icetime",
        "I_F_xGoals", "I_F_shotsOnGoal", "I_F_points", "I_F_goals"])
    for c in ("games_played", "icetime", "I_F_xGoals", "I_F_shotsOnGoal",
              "I_F_points", "I_F_goals"):
        mp[c] = pd.to_numeric(mp[c], errors="coerce")

    ev = mp[mp.situation == "5on5"].set_index("playerId")
    pp = mp[mp.situation == "5on4"].set_index("playerId")
    al = mp[mp.situation == "all"].set_index("playerId")

    def per60(num: pd.Series, ice: pd.Series) -> np.ndarray:
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(ice > 0, num * 3600.0 / ice, np.nan)

    feat = pd.DataFrame(index=ev.index)
    feat["ixg_per60"] = per60(ev["I_F_xGoals"], ev["icetime"])
    feat["shots_per60"] = per60(ev["I_F_shotsOnGoal"], ev["icetime"])
    feat["points_per60"] = per60(ev["I_F_points"], ev["icetime"])
    # GP denominator from the all-situations row: stable for players with
    # near-zero special-teams ice, where the 5on4 row's own GP is unreliable.
    gp_all = al["games_played"].reindex(feat.index)
    pp_min = pp["icetime"].reindex(feat.index) / 60.0
    with np.errstate(invalid="ignore", divide="ignore"):
        feat["pp_toi_per_game"] = np.where(gp_all > 0, pp_min / gp_all, np.nan)
    pts_all = al["I_F_points"].reindex(feat.index)
    gls_all = al["I_F_goals"].reindex(feat.index)
    with np.errstate(invalid="ignore", divide="ignore"):
        feat["goal_share"] = np.where(pts_all > 0, gls_all / pts_all, np.nan)

    nid = pd.to_numeric(df["nhl_player_id"], errors="coerce")
    joined = feat.reindex(nid.to_numpy())
    joined.index = df.index
    # `games_played` (NHL API, 2025-26 RS) already rides on oaq_pilot.csv.
    return joined[[c for c in LENS_A_ADD if c != "games_played"]]


def build_lens_b(df: pd.DataFrame) -> pd.DataFrame:
    """A53 Lens B features from raw/player_stock.csv, with the locked log1p
    transforms and the undrafted -> 225 sentinel applied here, so the stored
    file keeps the raw auditable quantities."""
    path = RAW / "player_stock.csv"
    if not path.exists():
        raise SystemExit(f"missing {path} -- run fetch_player_stock.py first")
    st = pd.read_csv(path, dtype={"player_id": int}).set_index("player_id")
    st = st.reindex(df["player_id"].to_numpy())
    st.index = df.index

    out = pd.DataFrame(index=df.index)
    out["career_gp_log"] = np.log1p(
        pd.to_numeric(st["career_gp"], errors="coerce"))
    out["career_points_log"] = np.log1p(
        pd.to_numeric(st["career_points"], errors="coerce"))
    out["nhl_seasons"] = pd.to_numeric(st["nhl_seasons"], errors="coerce")
    pick = pd.to_numeric(st["draft_overall"], errors="coerce")
    out["draft_overall_log"] = np.log1p(pick.fillna(UNDRAFTED_PICK))
    return out


# --------------------------------------------------------------------------
# peer construction (generalized from compute_oaq._standardize_skill /
# compute_peers -- identical logic, arbitrary column list, optional shrinkage)
# --------------------------------------------------------------------------
def standardize(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """Group-mean then overall-mean imputation, then z across the pool
    (ddof=1). Mirrors compute_oaq._standardize_skill exactly."""
    feats = df[cols].to_numpy(dtype=float)
    groups = df["group"].to_numpy()
    filled = feats.copy()
    for gi in np.unique(groups):
        mask = groups == gi
        for j in range(feats.shape[1]):
            col = feats[mask, j]
            gmean = np.nanmean(col) if np.isfinite(col).any() else np.nan
            filled[mask, j] = np.where(np.isnan(filled[mask, j]), gmean,
                                       filled[mask, j])
    for j in range(filled.shape[1]):
        col = filled[:, j]
        omean = np.nanmean(col) if np.isfinite(col).any() else 0.0
        filled[:, j] = np.where(np.isnan(col), omean, col)
    mu = filled.mean(axis=0)
    sd = filled.std(axis=0, ddof=1)
    sd = np.where(sd == 0, 1.0, sd)
    return (filled - mu) / sd


def build_peers(df: pd.DataFrame, cols: list[str],
                delta: float = 0.0) -> list[list[int]]:
    """K=10 Mahalanobis peers within `group`, candidates filtered to the A49.1
    position class. `delta` > 0 applies A53's ridge shrinkage
    Sigma_hat = (1-d)*Sigma + d*(tr Sigma / p)*I before inversion."""
    Z = standardize(df, cols)
    groups = df["group"].to_numpy()
    pclass = position_class(df)
    peers: list[list[int]] = [[] for _ in range(len(df))]
    for gi in np.unique(groups):
        idx = np.where(groups == gi)[0]
        sub = Z[idx]
        if sub.shape[0] > 1:
            cov = np.atleast_2d(np.cov(sub, rowvar=False, ddof=1))
        else:
            cov = np.eye(sub.shape[1])
        if delta > 0:
            p = cov.shape[0]
            cov = (1 - delta) * cov + delta * (np.trace(cov) / p) * np.eye(p)
        VI = np.linalg.pinv(cov)
        for a_local, a in enumerate(idx):
            diffs = sub - sub[a_local]
            d2 = np.einsum("ij,jk,ik->i", diffs, VI, diffs)
            order = np.argsort(d2, kind="stable")
            peers[a] = [int(idx[b]) for b in order
                        if idx[b] != a and pclass[idx[b]] == pclass[a]
                        ][:K_PEERS]
    return peers


def peer_means(values: np.ndarray, peers: list[list[int]]) -> np.ndarray:
    out = np.full(len(peers), np.nan)
    for i, pl in enumerate(peers):
        if pl:
            v = values[np.asarray(pl, dtype=int)]
            if np.isfinite(v).any():
                out[i] = np.nanmean(v)
    return out


def recompute(df: pd.DataFrame, peers: list[list[int]]) -> pd.DataFrame:
    """OAQ + headline MI under one peer set. Everything except the peer sets is
    held at its shipped value, per A53."""
    er = df["engagement_raw"].to_numpy(dtype=float)
    mz = df["market_z"].to_numpy(dtype=float)
    adj = er - LAMBDA_BIGMARKET * np.maximum(0.0, mz)
    out = pd.DataFrame(index=df.index)
    out["OAQ_observed"] = er - peer_means(er, peers)
    out["OAQ_portable"] = adj - peer_means(adj, peers)
    out["marchand_index"] = out["OAQ_portable"] / df["cap_denom"].to_numpy()
    return out


# --------------------------------------------------------------------------
# comparison metrics (all fixed in A53 before this ran)
# --------------------------------------------------------------------------
def overlap_stats(base: list[list[int]], other: list[list[int]]) -> dict:
    ov = np.array([len(set(a) & set(b)) for a, b in zip(base, other)],
                  dtype=float)
    k = np.array([max(len(a), 1) for a in base], dtype=float)
    frac = ov / k
    return {
        "mean_overlap": float(np.mean(frac)),
        "pct_lost_half": float(np.mean(frac < 0.5) * 100.0),
        "pct_identical": float(np.mean(frac == 1.0) * 100.0),
    }


def retention(base_rank: pd.Series, new_rank: pd.Series, n: int,
              tail: str) -> float:
    b = set(base_rank.nsmallest(n).index if tail == "top"
            else base_rank.nlargest(n).index)
    o = set(new_rank.nsmallest(n).index if tail == "top"
            else new_rank.nlargest(n).index)
    return len(b & o) / n * 100.0


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 2 else float("nan")


def main() -> None:
    df = pd.read_csv(PILOT / "oaq_pilot.csv", dtype={"player_id": int})
    pl = pd.read_csv(PILOT / "players.csv", dtype={"player_id": int})
    df = df.merge(pl[["player_id", "nhl_player_id"]], on="player_id",
                  how="left")
    df = df.sort_values("player_id").reset_index(drop=True)
    n = len(df)

    # Back out the shipped headline denominator (A53: denominators unchanged).
    with np.errstate(invalid="ignore", divide="ignore"):
        denom = df["OAQ_portable"] / df["marchand_index"]
    df["cap_denom"] = denom.replace([np.inf, -np.inf], np.nan)

    df[LENS_A_ADD[:-1]] = build_lens_a(df)
    df[LENS_B_ADD] = build_lens_b(df)

    cols_a = SKILL_COLS + LENS_A_ADD
    cols_b = SKILL_COLS + LENS_B_ADD

    # Stored primary = ground truth for every comparison below.
    pid_to_row = {int(p): i for i, p in enumerate(df["player_id"])}
    stored = [[pid_to_row[int(x)] for x in str(s).split("|")
               if x != "" and int(x) in pid_to_row]
              for s in df["peer_player_ids"]]

    builds = {
        "primary_pinv (fidelity check)": build_peers(df, SKILL_COLS, 0.0),
        "primary_shrunk (estimator effect)": build_peers(df, SKILL_COLS,
                                                         SHRINK_DELTA),
        "lensA_production_detail": build_peers(df, cols_a, SHRINK_DELTA),
        "lensB_attention_stock": build_peers(df, cols_b, SHRINK_DELTA),
    }

    base_mi = df["marchand_index"]
    base_oaq = df["OAQ_portable"].to_numpy(dtype=float)
    base_rank_mi = base_mi.rank(ascending=False)
    top25 = base_rank_mi.nsmallest(25).index

    import datetime as _dt
    vintage = _dt.date.fromtimestamp(
        (PILOT / "oaq_pilot.csv").stat().st_mtime).isoformat()

    lines = [
        "# A53 peer-vector lenses - Lens A vs Lens B",
        "",
        f"Pool {n} (`oaq_pilot.csv`, build of {vintage}). "
        f"K={K_PEERS}, shrinkage delta={SHRINK_DELTA}, "
        f"lambda={LAMBDA_BIGMARKET}. Primary = STORED `peer_player_ids`; "
        "every quantity except the peer sets is held at its build value.",
        "",
        "| lens | p | peer overlap | lost >=half | identical | Pearson OAQ | "
        "Spearman OAQ | top-25 | bottom-25 | max move (top-25) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    per_player = df[["player_id", "full_name", "position", "group",
                     "marchand_index", "OAQ_portable"]].copy()

    for name, peers in builds.items():
        res = recompute(df, peers)
        ov = overlap_stats(stored, peers)
        new_rank = res["marchand_index"].rank(ascending=False)
        p_dim = (len(SKILL_COLS) if name.startswith("primary")
                 else len(cols_a) if "lensA" in name else len(cols_b))
        moved = (new_rank - base_rank_mi).abs()
        lines.append(
            f"| {name} | {p_dim} | {ov['mean_overlap'] * 100:.1f}% | "
            f"{ov['pct_lost_half']:.1f}% | {ov['pct_identical']:.1f}% | "
            f"{pearson(base_oaq, res['OAQ_portable'].to_numpy()):.4f} | "
            f"{spearman_rho(base_oaq, res['OAQ_portable'].to_numpy()):.4f} | "
            f"{retention(base_rank_mi, new_rank, 25, 'top'):.0f}% | "
            f"{retention(base_rank_mi, new_rank, 25, 'bottom'):.0f}% | "
            f"{moved.loc[top25].max():.0f} |")
        tag = name.split()[0]
        per_player[f"MI_{tag}"] = res["marchand_index"]
        per_player[f"OAQport_{tag}"] = res["OAQ_portable"]
        per_player[f"rankmove_{tag}"] = new_rank - base_rank_mi

    lines += ["", "## Largest headline rank moves, by lens", ""]
    for tag in ("lensA_production_detail", "lensB_attention_stock"):
        col = f"rankmove_{tag}"
        sel = per_player[col].abs().nlargest(10).index
        lines += [f"### {tag}", "",
                  "| player | pos | primary rank | lens rank | move |",
                  "|---|---|---|---|---|"]
        for i in sel:
            br = base_rank_mi.loc[i]
            lines.append(
                f"| {per_player.loc[i, 'full_name']} | "
                f"{per_player.loc[i, 'position']} | {br:.0f} | "
                f"{br + per_player.loc[i, col]:.0f} | "
                f"{per_player.loc[i, col]:+.0f} |")
        lines.append("")

    out_csv = HERE / "peer_vector_lenses.csv"
    out_md = HERE / "peer_vector_lenses.md"
    per_player.to_csv(out_csv, index=False)
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out_csv}\nwrote {out_md}")


if __name__ == "__main__":
    main()
