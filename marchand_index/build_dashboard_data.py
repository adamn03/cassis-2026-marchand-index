"""Build the JSON the public dashboard reads (one row per pooled player, three
peer vectors, bootstrap intervals on every published figure).

WHY THIS EXISTS. `oaq_pilot.csv` carries the pre-registered primary only, and
`diagnostics/peer_vector_lenses.py` recomputes the A53 lenses WITHOUT
bootstrapping. Publishing a lens ranking with no interval would break the
project's own bar ("every headline number carries a CI"), so this script runs
the same `bootstrap_player_cis` the primary uses, once per peer vector, and
emits everything the page needs in one file.

DISPLAY NAMES (owner decision 2026-08-31; display layer only, no computation
changes). The dashboard renames two published quantities:

    Marchand Index                  = OAQ_observed
    Marchand Index, salary adjusted = marchand_index_rawcap

`OAQ_observed` is the attention residual against skill-matched peers with **no
market correction**. A56 set lambda to 0 after the market pass-through was
estimated on 170 club changes and its components disagreed in sign
(en-Wikipedia +0.147 [+0.082, +0.211], Reddit mentions -0.082 [-0.161, -0.007]);
the weighted average, +0.043 [-0.021, +0.108], contains zero. That makes
`OAQ_portable` identical to `OAQ_observed`, and the published figure points at
the uncorrected column so its name does not imply an adjustment that is no
longer applied. The identity is asserted at build time.

`marchand_index_rawcap` is `HEADLINE_MI_COL` and is the A49.2 headline
(`OAQ_portable / cap_hit_M`, hence now `OAQ_observed / cap_hit_M`). The column
literally named `marchand_index` is the A4 `expected_cap` lens, which A49.2
DEMOTED to an audit lens -- it is deliberately NOT the salary-adjusted figure
here, and the mapping is restated on the page so a reader can reconcile the
dashboard against `preregistration.md`.

PUBLICATION RULES applied as per-row flags rather than by dropping rows, so the
page can disclose the excluded counts instead of silently hiding players:
  A49.2  entry-level contracts never share a table with non-ELC players
  A34    `small_sample` or null current-season GP excluded from published panels
  A49.2  `cap_quality == "low"` excluded from every salary-adjusted ranking

Every one of the 771 is emitted regardless, so the page's search can reach a
player who appears in no top-N table.

Reads:  the same inputs as compute_oaq.py, plus raw/player_stock.csv (A53 Lens B)
Writes: marchand_index/dashboard/data.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from compute_oaq import (  # noqa: E402
    BOOTSTRAP_DRAWS, HEADLINE_MI_COL, K_PEERS, LAMBDA_BIGMARKET, RAW_DIR,
    SKILL_COLS, bootstrap_player_cis, compute_market_z, compute_oaq,
    compute_peers, load_inputs, load_reddit_scores, load_wiki_daily,
    load_wiki_intl_daily_by_edition,
)
from diagnostics.peer_vector_lenses import (  # noqa: E402
    LENS_A_ADD, LENS_B_ADD, SHRINK_DELTA, build_lens_a, build_lens_b,
    build_peers,
)

OUT_DIR = HERE / "dashboard"
# A56 set lambda to 0, which makes `OAQ_portable` identical to `OAQ_observed`
# by construction. The published residual points at `OAQ_observed` directly, so
# the column name carries no implication of a market term that is no longer
# applied. `marchand_index_rawcap` is `OAQ_portable / cap_hit_M` and is
# therefore now `OAQ_observed / cap_hit_M`; the identity is asserted at build
# time rather than assumed, so a future lambda change cannot silently
# reintroduce a correction under the old name.
MI_COL = HEADLINE_MI_COL              # "marchand_index_rawcap"
RESID_COL = "OAQ_observed"


def _rank(series: pd.Series, eligible: pd.Series) -> pd.Series:
    """Dense rank within the eligible subset only; NaN elsewhere.

    Ranking over the whole pool and then hiding rows would leave visible gaps
    ("#3, #7, #11") that imply the hidden players were beaten rather than
    excluded by a publication rule."""
    s = series.where(eligible)
    return s.rank(ascending=False, method="min")


def _num(v):
    """JSON-safe float, or None for NaN/inf."""
    if v is None:
        return None
    f = float(v)
    return None if not np.isfinite(f) else round(f, 4)


def run_vector(name: str, df_inputs: pd.DataFrame, peers, market_z,
               wiki_daily, reddit_scores, wiki_intl_daily) -> pd.DataFrame:
    """compute_oaq + bootstrap under one peer vector. Everything except the
    peer sets is identical across vectors by construction -- same inputs, same
    market_z, same seed -- so differences are attributable to peer choice."""
    print(f"  [{name}] compute_oaq ...", flush=True)
    df = compute_oaq(df_inputs.copy(), peers=peers, market_z=market_z)
    print(f"  [{name}] bootstrap {BOOTSTRAP_DRAWS} draws ...", flush=True)
    ci = bootstrap_player_cis(df, peers, market_z, wiki_daily, reddit_scores,
                              wiki_intl_daily)
    for k, v in ci.items():
        df[k] = v
    return df


def tier_width(frames: dict, col: str, eligible: pd.Series) -> float:
    """How wide a tier has to be before two players in adjacent tiers are
    actually distinguishable.

    The published bootstrap interval is NOT the right input. It resamples the
    attention series while holding peer sets FIXED (§10), so it captures
    sampling noise and nothing about the choice of comparison group -- and that
    choice turns out to be the larger term by roughly 2.4x. Ignoring it would
    produce tiers far too narrow to defend and would reintroduce, in banded
    form, exactly the false precision that ranking positions gave.

    Total uncertainty combines the two independent sources, and a tier is the
    width at which adjacent tiers separate at 95%:

        sd_total = sqrt( sd_peer_choice^2 + (CI_width / 3.92)^2 )
        width    = 2 * 1.96 * sd_total

    The result is rounded UP to a readable step so the published boundaries are
    round numbers a reader can hold in their head; rounding up never makes a
    tier narrower than the evidence supports.
    """
    base = frames["primary"]
    shifts = pd.concat([
        (frames[k][col] - base[col])[eligible]
        for k in ("lensA", "lensB")
    ])
    sd_peer = float(shifts.std())
    lo, hi = f"{col}_lo95", f"{col}_hi95"
    ci = float((base[hi] - base[lo])[eligible].median()) if hi in base else 0.0
    sd_tot = float(np.sqrt(sd_peer ** 2 + (ci / 3.92) ** 2))
    raw = 2 * 1.96 * sd_tot
    step = 0.25 if raw < 0.75 else 0.5
    return float(np.ceil(raw / step) * step)


def social_validation(df: pd.DataFrame, market_z: np.ndarray) -> dict:
    """Independent, off-platform check on the attention measure, plus the
    player-level market-size null A54 disclosed.

    Followers are the LARGER of the player's Instagram and X counts. Two
    platforms with different adoption by cohort measure the same underlying
    thing badly in different directions; taking the max avoids scoring a player
    as unknown merely for being absent from one of them. It is a validation
    input only -- it never enters the index, and A12 deliberately dropped
    follower stocks from the composite for exactly that reason.
    """
    path = RAW_DIR / "player_social.csv"
    if not path.exists():
        return {}
    ps = pd.read_csv(path, dtype={"player_id": int})
    m = df[["player_id", "engagement_raw", "OAQ_observed", "OAQ_portable",
            "small_sample"]].merge(
        ps[["player_id", "ig_followers", "x_followers"]], on="player_id",
        how="left")
    m = m[m["small_sample"].astype(int) == 0]
    fol = m[["ig_followers", "x_followers"]].max(axis=1)
    lf = np.log1p(pd.to_numeric(fol, errors="coerce"))
    ok = lf.notna().to_numpy()

    out = {"n": int(ok.sum()), "coverage": f"{int(ok.sum())}/{len(m)}"}
    for c in ("engagement_raw", "OAQ_observed", "OAQ_portable"):
        r = spearmanr(m[c].to_numpy()[ok], lf.to_numpy()[ok])
        out[c] = {"rho": round(float(r.statistic), 3),
                  "p": float(r.pvalue)}
    mz = market_z[df["small_sample"].astype(int).to_numpy() == 0]
    r = spearmanr(m["engagement_raw"].to_numpy(), mz)
    out["market_z_vs_attention"] = {"rho": round(float(r.statistic), 3),
                                    "p": round(float(r.pvalue), 3)}
    return out


def main() -> None:
    df_inputs = load_inputs()
    wiki_daily = load_wiki_daily()
    reddit_scores = load_reddit_scores()
    wiki_intl_daily = load_wiki_intl_daily_by_edition()

    market_z, market_used, _lenses = compute_market_z(df_inputs)
    df_inputs["market_z"] = market_z
    print(f"pool={len(df_inputs)}  market components={market_used}", flush=True)

    # Lens features are attached to the INPUT frame so all three vectors are
    # built from one identical set of rows.
    df_inputs[[c for c in LENS_A_ADD if c != "games_played"]] = build_lens_a(
        df_inputs)
    df_inputs[LENS_B_ADD] = build_lens_b(df_inputs)

    vectors = {
        "primary": compute_peers(df_inputs),
        "lensA": build_peers(df_inputs, SKILL_COLS + LENS_A_ADD, SHRINK_DELTA),
        "lensB": build_peers(df_inputs, SKILL_COLS + LENS_B_ADD, SHRINK_DELTA),
    }

    frames = {
        k: run_vector(k, df_inputs, p, market_z, wiki_daily, reddit_scores,
                      wiki_intl_daily)
        for k, p in vectors.items()
    }

    base = frames["primary"]
    n = len(base)

    # A56 identity check: with lambda = 0 the market-corrected and uncorrected
    # residuals must agree exactly. If they ever diverge, a market term has been
    # reintroduced upstream and every published figure would be mislabelled.
    both = base[["OAQ_observed", "OAQ_portable"]].to_numpy(dtype=float)
    ok = np.isfinite(both).all(axis=1)
    gap = float(np.max(np.abs(both[ok, 0] - both[ok, 1]))) if ok.any() else 0.0
    if gap > 1e-9:
        raise SystemExit(
            f"lambda is not 0: OAQ_observed and OAQ_portable differ by {gap:.3e}. "
            "Either restore LAMBDA_BIGMARKET = 0.0 or stop labelling the "
            "published residual as uncorrected.")
    print(f"  lambda=0 identity verified (max |diff| = {gap:.1e})", flush=True)

    # ---- publication eligibility (flags, not drops) ----------------------
    gp = pd.to_numeric(base.get("games_played"), errors="coerce")
    small = base["small_sample"].astype(int) == 1
    absent = gp.isna()
    cap_low = base["cap_quality"].astype(str).str.lower() == "low"
    elc = base["is_rookie_deal"].astype(int) == 1

    shown = ~(small | absent)                    # A34
    elig_resid = shown                           # residual needs no cap
    elig_mi = shown & ~cap_low                   # A49.2 cap_quality rule

    excluded = {
        "small_sample_or_absent": int((small | absent).sum()),
        "cap_quality_low": int(cap_low.sum()),
        "entry_level": int(elc.sum()),
        "pool": n,
        "published_non_elc": int((elig_mi & ~elc).sum()),
        "published_elc": int((elig_mi & elc).sum()),
    }
    print("eligibility:", excluded, flush=True)

    players = []
    for i in range(n):
        r = base.iloc[i]
        rec = {
            "id": int(r["player_id"]),
            "name": str(r["full_name"]),
            "pos": str(r["position"]),
            "team": str(r["team_code"]),
            "cap": _num(r["cap_hit_M"]),
            "elc": bool(elc.iloc[i]),
            "shown": bool(shown.iloc[i]),
            "capLow": bool(cap_low.iloc[i]),
            "v": {},
        }
        for key, f in frames.items():
            row = f.iloc[i]
            rec["v"][key] = {
                "mi": _num(row[RESID_COL]),
                "miLo": _num(row[f"{RESID_COL}_lo95"]),
                "miHi": _num(row[f"{RESID_COL}_hi95"]),
                "sa": _num(row[MI_COL]),
                "saLo": _num(row[f"{MI_COL}_lo95"]),
                "saHi": _num(row[f"{MI_COL}_hi95"]),
            }
        players.append(rec)

    # ---- ranks, computed per vector x metric x panel ---------------------
    for key, f in frames.items():
        panels = {
            "miOpen": (f[RESID_COL], elig_resid & ~elc),
            "miElc": (f[RESID_COL], elig_resid & elc),
            "saOpen": (f[MI_COL], elig_mi & ~elc),
            "saElc": (f[MI_COL], elig_mi & elc),
        }
        for pname, (series, mask) in panels.items():
            ranks = _rank(series, mask)
            for i, rk in enumerate(ranks):
                players[i]["v"][key][pname] = (
                    None if not np.isfinite(rk) else int(rk))

    # ---- tiers: the published unit, replacing rank positions ------------
    # Peer choice moves a player further than sampling noise does, so an exact
    # position is not a claim the data supports. Tiers are sized so that two
    # players in ADJACENT tiers are separated at 95%; within a tier, order is
    # explicitly not claimed. Examples are picked mechanically -- the
    # highest-attention players in the tier -- so the choice is not editorial.
    tier_meta = {}
    for metric, col, mask in (("mi", RESID_COL, elig_resid & ~elc),
                              ("sa", MI_COL, elig_mi & ~elc)):
        w = tier_width(frames, col, mask)
        bounds = [w, 0.0, -w]
        labels = ["Far above peers", "Above peers", "Below peers",
                  "Far below peers"]
        v = base[col]
        idx = np.full(n, 3)
        idx = np.where(v >= -w, 2, idx)
        idx = np.where(v >= 0.0, 1, idx)
        idx = np.where(v >= w, 0, idx)
        idx = np.where(v.isna().to_numpy(), -1, idx)
        for i in range(n):
            players[i]["v"]["lensA"].setdefault("tier", {})
            players[i]["v"]["lensA"]["tier"][metric] = (
                None if idx[i] < 0 else int(idx[i]))
        rows = []
        for t, lab in enumerate(labels):
            sel = (idx == t) & mask.to_numpy()
            ex = (base.loc[sel, ["full_name", "engagement_raw"]]
                  .nlargest(6, "engagement_raw")["full_name"].tolist())
            ids = (base.loc[sel, ["player_id", "engagement_raw"]]
                   .nlargest(6, "engagement_raw")["player_id"].astype(int).tolist())
            rows.append({"label": lab, "n": int(sel.sum()),
                         "share": round(100 * sel.sum() / max(mask.sum(), 1), 1),
                         "examples": ex, "exampleIds": ids})
        elc_rows = []
        for t, lab in enumerate(labels):
            sel = (idx == t) & (elig_resid & elc).to_numpy()
            ex = (base.loc[sel, ["full_name", "engagement_raw"]]
                  .nlargest(4, "engagement_raw")["full_name"].tolist())
            ids = (base.loc[sel, ["player_id", "engagement_raw"]]
                   .nlargest(4, "engagement_raw")["player_id"].astype(int).tolist())
            elc_rows.append({"n": int(sel.sum()), "examples": ex,
                             "exampleIds": ids})
        tier_meta[metric] = {"width": w, "bounds": bounds, "tiers": rows,
                             "elc": elc_rows}
        print(f"  tiers[{metric}] width={w} -> "
              f"{[r['n'] for r in rows]}", flush=True)

    payload = {
        "meta": {
            "pool": n,
            "k": K_PEERS,
            "lambda": LAMBDA_BIGMARKET,
            "shrinkage": SHRINK_DELTA,
            "draws": BOOTSTRAP_DRAWS,
            "window": "2025-04-18 to 2026-04-17",
            "marketComponents": list(market_used),
            "excluded": excluded,
            "tiers": tier_meta,
            "validation": social_validation(base, market_z),
            "columns": {
                "Marchand Index": RESID_COL,
                "Marchand Index, salary adjusted": MI_COL,
            },
            "vectors": {
                "primary": {"p": len(SKILL_COLS), "feats": SKILL_COLS},
                "lensA": {"p": len(SKILL_COLS) + len(LENS_A_ADD),
                          "feats": SKILL_COLS + LENS_A_ADD},
                "lensB": {"p": len(SKILL_COLS) + len(LENS_B_ADD),
                          "feats": SKILL_COLS + LENS_B_ADD},
            },
        },
        "players": players,
    }

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / "data.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":")),
                   encoding="utf-8")
    tmp.replace(out)
    print(f"\nwrote {out}  players={len(players)}  "
          f"{out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
