"""Market pass-through, estimated on the scale the data actually lives on.

A55's estimator answers "what is lambda in the units lambda is defined in" and
returns ~0, because the A12 composite z-scores raw counts whose skew is 6.9 --
the bottom 90% of players occupy 11.5% of its range, so a proportional change
for an ordinary player cannot register. This script asks the prior question:
**is there a market effect in the attention data at all**, measured on a scale
that can represent one.

DESIGN. Same identification as A55 -- the same player before and after a club
change, so player-level fame differences out -- but every outcome is a change in
LOG attention, making the coefficient a proportional pass-through. Controls are
change in PPG, TOI/G, destination club points percentage, and a transition
indicator.

THREE ESTIMATES, reported together and never separately:

  1. Per component (en-Wikipedia, intl-Wikipedia, Reddit mentions, Reddit
     upvotes). The honesty check: if only one source carries the effect, the
     claim has to narrow to that source.
  2. Averaged across sources, weighted by the A12 composite weights on the LOG
     scale, Trends excluded (the panel stores one season-invariant value, so it
     cannot move in a difference) and the remainder renormalized.
  3. Free club effects. Rather than assuming the market index composition is
     right, every club gets its own parameter, identified in differences by
     coding destination +1 and origin -1. If those effects line up with the
     market index, the index is not doing the work; if they do not, the index
     composition is the finding rather than the market.

Writes: diagnostics/market_passthrough.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import numpy.linalg as la
import pandas as pd

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
sys.path.insert(0, str(PILOT))

from compute_oaq import (RAW_DIR, WEIGHTS, _attach_team_social,  # noqa: E402
                         _market_z_a54)
from diagnostics.estimate_lambda import (TRANSITIONS, MIN_GP,  # noqa: E402
                                         points_pct, season_club, team_alias)

DRAWS = 2000
SEED = 20260526
COMPONENTS = {"wiki_en": ("en-Wikipedia", WEIGHTS["wiki_12mo"]),
              "wiki_intl": ("intl-Wikipedia", WEIGHTS["wiki_intl_12mo"]),
              "reddit_mentions": ("Reddit mentions", WEIGHTS["reddit_mentions_12mo"]),
              "reddit_upvotes": ("Reddit upvotes", WEIGHTS["reddit_upvotes_12mo"])}


def ols(y, X):
    b, *_ = la.lstsq(X, y, rcond=None)
    r = y - X @ b
    dof = max(len(y) - np.linalg.matrix_rank(X), 1)
    se = np.sqrt(np.maximum(np.diag(la.pinv(X.T @ X) * (r @ r / dof)), 0))
    return b, se


def boot_ci(y, X, col=1, draws=DRAWS, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(y)
    out = np.empty(draws)
    for i in range(draws):
        k = rng.integers(0, n, n)
        out[i] = ols(y[k], X[k])[0][col]
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def build() -> pd.DataFrame:
    alias = team_alias()
    att = pd.read_csv(RAW_DIR / "attention_by_season.csv")
    sk = pd.read_csv(RAW_DIR / "nhl_skill.csv")
    sk["season"] = sk["season"].astype(str)
    mp = _attach_team_social(pd.read_csv(PILOT / "market_proxy.csv"))
    z32, _ = _market_z_a54(mp)
    MZ = dict(zip(mp["team_code"], z32))
    PP = points_pct()
    pl = pd.read_csv(PILOT / "players.csv")
    pl["nid"] = pd.to_numeric(pl["nhl_player_id"], errors="coerce")

    rows = []
    for sa, sb, ya, yb in TRANSITIONS:
        ca, cb = season_club(ya, alias), season_club(yb, alias)
        A = att[att["season"].astype(str) == sa].set_index("player_id")
        B = att[att["season"].astype(str) == sb].set_index("player_id")
        ska = sk[sk["season"] == sa].set_index("player_id")
        skb = sk[sk["season"] == sb].set_index("player_id")
        for _, p in pl.iterrows():
            pid, nid = int(p["player_id"]), p["nid"]
            ta, tb = ca.get(nid), cb.get(nid)
            if not isinstance(ta, str) or not isinstance(tb, str) or ta == tb:
                continue
            if ta not in MZ or tb not in MZ:
                continue
            if pid not in A.index or pid not in B.index:
                continue
            try:
                ra, rb = ska.loc[pid], skb.loc[pid]
            except KeyError:
                continue
            if not (pd.to_numeric(ra["games_played"], errors="coerce") >= MIN_GP
                    and pd.to_numeric(rb["games_played"], errors="coerce") >= MIN_GP):
                continue
            rec = {"name": p["full_name"], "trans": sb, "from": ta, "to": tb,
                   "d_mz": MZ[tb] - MZ[ta],
                   "d_ppg": pd.to_numeric(rb["ppg"], errors="coerce")
                            - pd.to_numeric(ra["ppg"], errors="coerce"),
                   "d_toi": pd.to_numeric(rb["toi_per_game"], errors="coerce")
                            - pd.to_numeric(ra["toi_per_game"], errors="coerce"),
                   "d_pp": PP.get((sb, tb), np.nan) - PP.get((sa, ta), np.nan),
                   "late": 1.0 if sb == "20252026" else 0.0}
            for c in COMPONENTS:
                va = pd.to_numeric(A.loc[pid, c], errors="coerce")
                vb = pd.to_numeric(B.loc[pid, c], errors="coerce")
                rec[f"d_{c}"] = np.log1p(vb) - np.log1p(va)
            rows.append(rec)
    return pd.DataFrame(rows)


def main() -> None:
    d = build()
    base = ["d_ppg", "d_toi", "d_pp", "late"]
    d = d.dropna(subset=["d_mz"] + base)
    n = len(d)
    X = np.column_stack([np.ones(n), d["d_mz"].to_numpy(float)]
                        + [d[c].to_numpy(float) for c in base])

    L = ["# Market pass-through on the log scale", "",
         f"Movers pooled over both transitions: **n = {n}**. Every outcome is a "
         "change in log attention, so each coefficient is a proportional "
         "pass-through per 1 SD of market size. Controls: change in PPG, TOI/G, "
         "destination points percentage, transition.", "",
         "## Per component", "",
         "| source | A12 weight | b | 95% CI | t | % per SD |",
         "|---|---|---|---|---|---|"]

    tot = sum(w for _, w in COMPONENTS.values())
    comp_b = {}
    for col, (label, w) in COMPONENTS.items():
        y = d[f"d_{col}"].to_numpy(float)
        ok = np.isfinite(y)
        b, se = ols(y[ok], X[ok])
        lo, hi = boot_ci(y[ok], X[ok])
        comp_b[col] = b[1]
        L.append(f"| {label} | {w:.2f} | {b[1]:+.4f} | [{lo:+.3f}, {hi:+.3f}] | "
                 f"{b[1]/se[1]:+.2f} | {100*(np.exp(b[1])-1):+.1f}% |")

    # averaged across sources, A12 weights renormalised over the four
    yavg = sum((w / tot) * d[f"d_{c}"].to_numpy(float)
               for c, (_, w) in COMPONENTS.items())
    ok = np.isfinite(yavg)
    b, se = ols(yavg[ok], X[ok])
    lo, hi = boot_ci(yavg[ok], X[ok])
    L += ["", "## Averaged across sources (A12 weights, log scale)", "",
          "| outcome | b | 95% CI | t | % per SD |", "|---|---|---|---|---|",
          f"| weighted composite | {b[1]:+.4f} | [{lo:+.3f}, {hi:+.3f}] | "
          f"{b[1]/se[1]:+.2f} | {100*(np.exp(b[1])-1):+.1f}% |"]
    avg_b, avg_lo, avg_hi = b[1], lo, hi

    # free club effects: destination +1, origin -1, one club dropped as reference
    clubs = sorted(set(d["from"]) | set(d["to"]))
    ref = clubs[0]
    use = [c for c in clubs if c != ref]
    D = np.zeros((n, len(use)))
    for i, (fr, to) in enumerate(zip(d["from"], d["to"])):
        if to in use:
            D[i, use.index(to)] += 1
        if fr in use:
            D[i, use.index(fr)] -= 1
    Xc = np.column_stack([np.ones(n)] + [d[c].to_numpy(float) for c in base] + [D])
    bc, _ = ols(yavg[ok], Xc[ok])
    eff = pd.Series(bc[1 + len(base):], index=use)
    eff[ref] = 0.0
    mp = _attach_team_social(pd.read_csv(PILOT / "market_proxy.csv"))
    z32, _ = _market_z_a54(mp)
    MZ = pd.Series(z32, index=mp["team_code"])
    common = eff.index.intersection(MZ.index)
    from scipy.stats import spearmanr, pearsonr
    rs = spearmanr(eff[common], MZ[common])
    rp = pearsonr(eff[common], MZ[common])
    L += ["", "## Free club effects (no market index assumed)", "",
          f"{len(common)} clubs, identified off {n} moves "
          f"(~{n/len(common):.1f} per club -- thin, so these are noisy).", "",
          f"- correlation with the market index: Spearman **{rs.statistic:+.3f}** "
          f"(p={rs.pvalue:.3f}), Pearson {rp.statistic:+.3f}",
          "", "| club | est. attention effect | market index |", "|---|---|---|"]
    for c in eff[common].sort_values(ascending=False).index[:6]:
        L.append(f"| {c} | {eff[c]:+.3f} | {MZ[c]:+.2f} |")
    L.append("| … | | |")
    for c in eff[common].sort_values().index[:4][::-1]:
        L.append(f"| {c} | {eff[c]:+.3f} | {MZ[c]:+.2f} |")

    spread = max(comp_b.values()) - min(comp_b.values())
    L += ["", "## Read", "",
          f"- Component estimates span {min(comp_b.values()):+.3f} to "
          f"{max(comp_b.values()):+.3f} (spread {spread:.3f}).",
          f"- Averaged estimate: **{avg_b:+.4f}** [{avg_lo:+.3f}, {avg_hi:+.3f}] "
          f"= **{100*(np.exp(avg_b)-1):+.1f}% per SD of market**.",
          f"- Averaged CI excludes zero: **{avg_lo > 0 or avg_hi < 0}**."]

    out = "\n".join(L)
    (HERE / "market_passthrough.md").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
