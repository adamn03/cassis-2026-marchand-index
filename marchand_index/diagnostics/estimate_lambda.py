"""A55: estimate the §7/A5 market damping constant lambda from club changes.

lambda is the only headline parameter in this project that was never measured.
A5 set it to 0.5 as the midpoint between its bounds because the pass-through was
unknown; A55 replaces that assumption with an estimate.

IDENTIFICATION. A club change is the natural experiment. The same player, one
season later, in a different market: if market size supplies attention, a move to
a larger market raises attention beyond what the player's own change in
production explains. lambda is exactly that pass-through, so it is the
coefficient on the change in market size -- not a quantity that has to be assumed.

UNITS ARE THE WHOLE TRICK. lambda multiplies `market_z` and is subtracted from
the engagement composite, so the estimate is only interpretable as lambda if the
outcome is in the same units the composite is in. Each season's components are
therefore standardized WITHIN that season's pool before weighting, making the
outcome a change in league standard deviations. `trends_12mo` is dropped: the
A52 panel stores one season-invariant value per player, so it contributes
exactly zero to any difference. The remaining four A12 weights are renormalized
per the section 4 sentinel rule.

CONTROLS. Change in PPG and TOI/G absorb the player's own trajectory. Change in
destination club points percentage absorbs the contender effect, so that moving
to a good team is not credited to its market. A transition indicator absorbs
anything common to a season pair.

The adoption rule is fixed in A55 and is NOT decided here: this script reports
lambda-hat and its interval, and prints which branch of that rule applies.

Reads:  raw/attention_by_season.csv, raw/nhl_skill.csv, raw/moneypuck_skaters_*.csv,
        raw/game_attendance.csv, raw/teams.csv, market_proxy.csv, players.csv
Writes: diagnostics/estimate_lambda.md   (the result, for the record)
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
                         _market_z_a54, zscore_array)

TRANSITIONS = [("20232024", "20242025", 2023, 2024),
               ("20242025", "20252026", 2024, 2025)]
MIN_GP = 20
DRAWS = 2000
SEED = 20260526
# A55: Trends is season-invariant in the A52 panel, so it cannot move in a
# difference. Dropped, remaining weights renormalized (section 4 sentinel rule).
DELTA_COMPONENTS = {k: v for k, v in WEIGHTS.items() if k != "trends_12mo"}
PANEL_COL = {"wiki_12mo": "wiki_en", "wiki_intl_12mo": "wiki_intl",
             "reddit_mentions_12mo": "reddit_mentions",
             "reddit_upvotes_12mo": "reddit_upvotes"}


def team_alias() -> dict[str, str]:
    """MoneyPuck uses its own club codes; map them onto the pool's."""
    t = pd.read_csv(RAW_DIR / "teams.csv")
    out = {}
    for _, r in t.iterrows():
        for c in [c for c in t.columns if "code" in c.lower()]:
            v = str(r[c]).strip()
            if v and v.lower() != "nan":
                out[v] = r["team_code"]
    return out


def season_club(year: int, alias: dict) -> pd.Series:
    """Club of maximum ice time in that season -- a played-for club, not a
    roster snapshot. `nhl_skill.csv` carries the snapshot club for every season
    and therefore reports zero movers; using it here would silently produce an
    empty sample."""
    d = pd.read_csv(RAW_DIR / f"moneypuck_skaters_{year}.csv",
                    usecols=["playerId", "team", "situation", "icetime"])
    d = d[d["situation"] == "all"]
    d = d.sort_values("icetime", ascending=False).drop_duplicates("playerId")
    return d.set_index("playerId")["team"].map(
        lambda t: alias.get(str(t).strip(), str(t).strip()))


def points_pct() -> dict[tuple[str, str], float]:
    """Regular-season points percentage per (season, club): 2 for a win, 1 for
    an overtime or shootout loss."""
    g = pd.read_csv(RAW_DIR / "game_attendance.csv")
    g = g[g["game_type"].astype(str) == "regular"]
    pts: dict[tuple[str, str], list[int]] = {}
    for _, r in g.iterrows():
        s = str(r["season"])
        hg, vg = r["home_goals"], r["visitor_goals"]
        extra = str(r.get("overtime") or "") != ""
        hw = hg > vg
        for club, won in ((r["home_code"], hw), (r["visitor_code"], not hw)):
            p = 2 if won else (1 if extra else 0)
            pts.setdefault((s, str(club)), [0, 0])
            pts[(s, str(club))][0] += p
            pts[(s, str(club))][1] += 2
    return {k: v[0] / v[1] for k, v in pts.items() if v[1]}


def season_composite(att: pd.DataFrame, season: str) -> pd.Series:
    """A12 composite for one season, standardized within that season's pool so
    the result is in league standard deviations."""
    g = att[att["season"].astype(str) == season].set_index("player_id")
    w = DELTA_COMPONENTS
    tot = sum(w.values())
    acc = None
    for key, weight in w.items():
        v = pd.to_numeric(g[PANEL_COL[key]], errors="coerce").to_numpy(float)
        z = zscore_array(np.where(np.isfinite(v), v, np.nan))
        part = (weight / tot) * pd.Series(z, index=g.index)
        acc = part if acc is None else acc.add(part, fill_value=0.0)
    return acc


def ols(y: np.ndarray, X: np.ndarray):
    b, *_ = la.lstsq(X, y, rcond=None)
    r = y - X @ b
    dof = max(len(y) - X.shape[1], 1)
    se = np.sqrt(np.diag(la.pinv(X.T @ X) * (r @ r / dof)))
    return b, se


def main() -> None:
    alias = team_alias()
    att = pd.read_csv(RAW_DIR / "attention_by_season.csv")
    sk = pd.read_csv(RAW_DIR / "nhl_skill.csv")
    sk["season"] = sk["season"].astype(str)
    mp = _attach_team_social(pd.read_csv(PILOT / "market_proxy.csv"))
    mz32, _ = _market_z_a54(mp)
    MZ = dict(zip(mp["team_code"], mz32))
    PP = points_pct()
    pl = pd.read_csv(PILOT / "players.csv")
    pl["nid"] = pd.to_numeric(pl["nhl_player_id"], errors="coerce")

    rows = []
    for sa, sb, ya, yb in TRANSITIONS:
        ca, cb = season_club(ya, alias), season_club(yb, alias)
        comp_a, comp_b = season_composite(att, sa), season_composite(att, sb)
        ska = sk[sk["season"] == sa].set_index("player_id")
        skb = sk[sk["season"] == sb].set_index("player_id")
        for _, p in pl.iterrows():
            pid, nid = int(p["player_id"]), p["nid"]
            ta, tb = ca.get(nid), cb.get(nid)
            if not isinstance(ta, str) or not isinstance(tb, str) or ta == tb:
                continue
            if ta not in MZ or tb not in MZ:
                continue
            try:
                ra, rb = ska.loc[pid], skb.loc[pid]
            except KeyError:
                continue
            gpa = pd.to_numeric(ra["games_played"], errors="coerce")
            gpb = pd.to_numeric(rb["games_played"], errors="coerce")
            if not (gpa >= MIN_GP and gpb >= MIN_GP):
                continue
            if pid not in comp_a.index or pid not in comp_b.index:
                continue
            rows.append({
                "player_id": pid, "name": p["full_name"], "trans": sb,
                "from": ta, "to": tb,
                "d_comp": comp_b[pid] - comp_a[pid],
                "d_mz": MZ[tb] - MZ[ta],
                "d_ppg": pd.to_numeric(rb["ppg"], errors="coerce")
                         - pd.to_numeric(ra["ppg"], errors="coerce"),
                "d_toi": pd.to_numeric(rb["toi_per_game"], errors="coerce")
                         - pd.to_numeric(ra["toi_per_game"], errors="coerce"),
                "d_pp": PP.get((sb, tb), np.nan) - PP.get((sa, ta), np.nan),
            })

    d = pd.DataFrame(rows).dropna(
        subset=["d_comp", "d_mz", "d_ppg", "d_toi", "d_pp"])
    n = len(d)
    late = (d["trans"] == "20252026").to_numpy(float)
    X = np.c_[np.ones(n), d["d_mz"], d["d_ppg"], d["d_toi"], d["d_pp"], late]
    y = d["d_comp"].to_numpy(float)
    b, se = ols(y, X)
    lam = float(b[1])

    rng = np.random.default_rng(SEED)
    draws = np.empty(DRAWS)
    for i in range(DRAWS):
        idx = rng.integers(0, n, n)
        draws[i] = ols(y[idx], X[idx])[0][1]
    lo, hi = float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))

    excludes_zero = lo > 0
    adopt = excludes_zero and lam > 0
    new_lambda = float(np.clip(lam, 0.0, 1.0)) if adopt else 0.5

    names = ["intercept", "D market_z", "D ppg", "D toi/g", "D points%",
             "transition"]
    L = ["# A55 - lambda estimated from club changes", "",
         f"Movers pooled over both transitions: **n = {n}** "
         f"({int((d['trans'] == '20242025').sum())} + "
         f"{int((d['trans'] == '20252026').sum())}). "
         f"Outcome is the A12 composite in within-season standard deviations.",
         "", "| term | b | se | t |", "|---|---|---|---|"]
    for nm, c, s in zip(names, b, se):
        L.append(f"| {nm} | {c:+.4f} | {s:.4f} | {c / s:+.2f} |")
    L += ["",
          f"**lambda-hat = {lam:.4f}**, 95% bootstrap interval "
          f"[{lo:.4f}, {hi:.4f}] ({DRAWS} draws, seed {SEED}).", "",
          f"Interval excludes zero: **{excludes_zero}**.", "",
          f"A55 adoption rule -> primary lambda = **{new_lambda:.4f}** "
          + ("(estimate adopted)." if adopt else
             "(estimate not distinguishable from zero; pre-registered 0.5 retained)."),
          "", "Pre-registered comparison lambda = 0.5 is retained and reported "
          "either way, with the {0, 0.25, 0.5, 0.75, 1.0} ladder unchanged."]
    out = "\n".join(L)
    (HERE / "estimate_lambda.md").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
