"""Fetch MoneyPuck 5v5 on-ice play-driving features for the 774 pool (A13).

Adds three on-ice features to the §6 peer (skill) vector:
  cf_pct  = onIce_corsiPercentage   (5v5 territorial play-driving share, 0-1)
  xgf_pct = onIce_xGoalsPercentage  (5v5 shot-quality-weighted share, 0-1)
  ozs_pct = I_F_oZoneShiftStarts / (I_F_oZoneShiftStarts + I_F_dZoneShiftStarts)
            (offensive-zone-start share; neutral starts excluded, standard
            convention)

Source: MoneyPuck free season-summary skater CSV (2025-26 regular season),
downloaded once and cached in raw/. The CSV is stratified by `situation` in
{all, 5on5, 5on4, 4on5, other}; A13 LOCKS situation == '5on5' (even-strength;
all-situations re-imports the special-teams confound). Join key is
`nhl_player_id` (players.csv) == MoneyPuck `playerId` (identical NHL id space);
name-fallback only where nhl_player_id is blank.

Traded players have ONE 5v5 row per team and NO aggregate row, so rows are
collapsed per playerId by icetime-weighted mean (cf_pct, xgf_pct) and
summed-count ratio (ozs_pct). Skaters below ONICE_MIN_ICETIME_5V5 = 150 min
5v5 have the three features NULLed (onice_status=thin); compute_oaq.py's
existing group-mean imputation fills them to position-group neutral before
standardizing. No player is ever dropped (A10 774-pool preserved). MoneyPuck
credited on the poster per its non-commercial terms.

Writes:
  marchand_index/raw/moneypuck_skaters_2025.csv   raw download cache
  marchand_index/raw/nhl_onice.csv                774 rows, schema = OUT_FIELDS
"""
from __future__ import annotations

import datetime as dt
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONTACT_UA, RAW_DIR, atomic_write_csv, load_players, session  # noqa: E402

START_YEAR = "2025"  # pre-reg locks the 2025-26 regular season
MP_URL = (
    "https://moneypuck.com/moneypuck/playerData/seasonSummary/"
    f"{START_YEAR}/regular/skaters.csv"
)
LOCKED_SITUATION = "5on5"            # A13 locked situation (NOT a default)
ONICE_MIN_ICETIME_5V5 = 150         # minutes 5v5 thin floor (locked, A13)

CACHE_CSV = RAW_DIR / "moneypuck_skaters_2025.csv"
OUT_CSV = RAW_DIR / "nhl_onice.csv"

OUT_FIELDS = [
    "player_id", "nhl_player_id", "full_name", "team_code", "situation",
    "cf_pct", "xgf_pct", "ozs_pct", "mp_icetime_5v5",
    "mp_games_played_5v5", "n_team_rows", "onice_status", "fetch_date",
]


def ozs_pct(ozs: float, dzs: float) -> float:
    """Offensive-zone-start share (neutral starts excluded). NaN if no starts."""
    if not (np.isfinite(ozs) and np.isfinite(dzs)):
        return float("nan")
    denom = ozs + dzs
    if denom == 0:
        return float("nan")
    return ozs / denom


def filter_5v5(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep only situation == '5on5'; coerce numerics; rename to feature cols.

    A13 LOCKED situation. The MoneyPuck CSV stratifies every player by
    situation; the aggregate 'all' row re-imports the special-teams confound,
    so it is dropped here before any aggregation.
    """
    df = raw[raw["situation"].astype(str) == LOCKED_SITUATION].copy()
    for src in ("icetime", "onIce_corsiPercentage", "onIce_xGoalsPercentage",
                "I_F_oZoneShiftStarts", "I_F_dZoneShiftStarts", "games_played"):
        df[src] = pd.to_numeric(df[src], errors="coerce")
    df = df.rename(columns={
        "onIce_corsiPercentage": "cf_pct",
        "onIce_xGoalsPercentage": "xgf_pct",
        "I_F_oZoneShiftStarts": "ozs_raw",
        "I_F_dZoneShiftStarts": "dzs_raw",
    })
    return df[["playerId", "name", "team", "situation", "icetime",
               "games_played", "cf_pct", "xgf_pct", "ozs_raw", "dzs_raw"]]


def _wmean(vals: np.ndarray, weights: np.ndarray) -> float:
    """Icetime-weighted mean; falls back to simple nanmean if all weight is 0."""
    m = np.isfinite(vals) & np.isfinite(weights)
    if not m.any():
        return float("nan")
    v, w = vals[m], weights[m]
    if w.sum() <= 0:
        return float(np.nanmean(v))
    return float((v * w).sum() / w.sum())


def aggregate_traded(df5v5: pd.DataFrame) -> pd.DataFrame:
    """Collapse 5v5 rows to one row per playerId (trade aggregation).

    cf_pct/xgf_pct -> icetime-weighted mean across the player's team-rows;
    ozs_pct -> recomputed from SUMMED zone-start counts (sum then divide);
    icetime/games summed; n_team_rows records the team-row count (>=2 = traded).
    """
    out_rows = []
    for pid, grp in df5v5.groupby("playerId", sort=True):
        ice = grp["icetime"].to_numpy(dtype=float)
        cf = _wmean(grp["cf_pct"].to_numpy(dtype=float), ice)
        xgf = _wmean(grp["xgf_pct"].to_numpy(dtype=float), ice)
        sum_ozs = np.nansum(grp["ozs_raw"].to_numpy(dtype=float))
        sum_dzs = np.nansum(grp["dzs_raw"].to_numpy(dtype=float))
        primary = grp.sort_values("icetime", ascending=False).iloc[0]
        out_rows.append({
            "playerId": int(pid),
            "name": primary["name"],
            "team": primary["team"],
            "cf_pct": cf,
            "xgf_pct": xgf,
            "ozs_pct": ozs_pct(sum_ozs, sum_dzs),
            "mp_icetime_5v5": float(np.nansum(ice)),
            "mp_games_played_5v5": float(
                np.nansum(grp["games_played"].to_numpy(dtype=float))),
            "n_team_rows": int(len(grp)),
        })
    return pd.DataFrame(out_rows)


def apply_thin_floor(row: dict) -> dict:
    """NULL the three on-ice features below ONICE_MIN_ICETIME_5V5 (thin sample).

    Rate stats are unstable at low ice (a 5-game callup can post 65% CF% on
    noise). Below the floor the features are NULLed and onice_status='thin';
    compute_oaq.py's existing group-mean imputation then fills them to
    position-group neutral before standardizing, so the player is matched on
    his stable box-score stats. The player is NEVER dropped (A10 pool).
    """
    out = dict(row)
    ice = out.get("mp_icetime_5v5")
    if ice is None or not np.isfinite(ice) or ice < ONICE_MIN_ICETIME_5V5:
        out["cf_pct"] = float("nan")
        out["xgf_pct"] = float("nan")
        out["ozs_pct"] = float("nan")
        out["onice_status"] = "thin"
    else:
        out["onice_status"] = "ok"
    return out


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _blank(s) -> str:
    return "" if (s is None or (isinstance(s, float) and not np.isfinite(s))) else s


def join_pool(players: list[dict], mp: pd.DataFrame, fetch_date: str) -> list[dict]:
    """Left-join MoneyPuck rows onto the 774 pool on nhl_player_id (name-fallback
    only where the id is blank). NEVER drops a player; no match -> onice_status
    =missing with NULL features."""
    by_id = {int(r["playerId"]): r for _, r in mp.iterrows()} if len(mp) else {}
    by_name = ({_norm_name(r["name"]): r for _, r in mp.iterrows()}
               if len(mp) else {})
    out: list[dict] = []
    for p in players:
        pid = (p.get("nhl_player_id") or "").strip()
        rec = None
        if pid.isdigit() and int(pid) in by_id:
            rec = by_id[int(pid)]
        elif not pid.isdigit():
            rec = by_name.get(_norm_name(p["full_name"]))
        if rec is None:
            out.append({
                "player_id": p["player_id"],
                "nhl_player_id": pid,
                "full_name": p["full_name"],
                "team_code": p["team_code"],
                "situation": LOCKED_SITUATION,
                "cf_pct": "", "xgf_pct": "", "ozs_pct": "",
                "mp_icetime_5v5": "", "mp_games_played_5v5": "",
                "n_team_rows": 0, "onice_status": "missing",
                "fetch_date": fetch_date,
            })
            continue
        out.append({
            "player_id": p["player_id"],
            "nhl_player_id": pid,
            "full_name": p["full_name"],
            "team_code": p["team_code"],
            "situation": LOCKED_SITUATION,
            "cf_pct": _blank(rec["cf_pct"]),
            "xgf_pct": _blank(rec["xgf_pct"]),
            "ozs_pct": _blank(rec["ozs_pct"]),
            "mp_icetime_5v5": _blank(rec["mp_icetime_5v5"]),
            "mp_games_played_5v5": _blank(rec["mp_games_played_5v5"]),
            "n_team_rows": int(rec["n_team_rows"]),
            "onice_status": rec["onice_status"],
            "fetch_date": fetch_date,
        })
    return out


def load_raw(s) -> pd.DataFrame:
    """Read the cached MoneyPuck CSV, downloading once if absent (atomic write)."""
    if not CACHE_CSV.exists():
        r = s.get(MP_URL, headers={"User-Agent": CONTACT_UA}, timeout=60)
        r.raise_for_status()
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_CSV.with_suffix(CACHE_CSV.suffix + ".tmp")
        tmp.write_bytes(r.content)
        os.replace(tmp, CACHE_CSV)
    return pd.read_csv(CACHE_CSV)


def empirical_group_report(df5v5: pd.DataFrame) -> dict[int, int]:
    """playerId -> count of 5v5 rows (spec risk #1: branch on the real file,
    do not trust one-row-per-team). >=2 => in-season trade -> aggregation."""
    sizes = df5v5.groupby(["playerId", "situation"]).size()
    out: dict[int, int] = {}
    for (pid, _sit), cnt in sizes.items():
        out[int(pid)] = out.get(int(pid), 0) + int(cnt)
    return out


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    s = session(expire_hours=24)
    raw = load_raw(s)
    # MoneyPuck `icetime` is SECONDS; the pre-registered ONICE_MIN_ICETIME_5V5
    # floor (150) is MINUTES. Convert at ingest so mp_icetime_5v5 is stored in
    # minutes and the floor compares like units. (Rate features are unaffected:
    # icetime-weighted means are scale-invariant.)
    raw["icetime"] = pd.to_numeric(raw["icetime"], errors="coerce") / 60.0
    df5v5 = filter_5v5(raw)

    report = empirical_group_report(df5v5)
    n_traded = sum(1 for n in report.values() if n >= 2)
    print(f"5v5 rows: {len(df5v5)}; unique playerIds: {len(report)}; "
          f"playerIds with >=2 5v5 rows (in-season trades): {n_traded}")

    agg = aggregate_traded(df5v5)
    floored = [apply_thin_floor(r) for r in agg.to_dict("records")]
    floored_df = pd.DataFrame(floored)

    players = load_players()
    rows = join_pool(players, floored_df, fetch_date)
    atomic_write_csv(OUT_CSV, rows, OUT_FIELDS)

    counts = {"ok": 0, "thin": 0, "missing": 0}
    for r in rows:
        counts[r["onice_status"]] = counts.get(r["onice_status"], 0) + 1
    n_agg_traded = sum(1 for r in rows if r["n_team_rows"] >= 2)
    print(f"Wrote {OUT_CSV}: {len(rows)} rows "
          f"(ok={counts['ok']}, thin={counts['thin']}, "
          f"missing={counts['missing']}; trade-aggregated={n_agg_traded})")


if __name__ == "__main__":
    main()
