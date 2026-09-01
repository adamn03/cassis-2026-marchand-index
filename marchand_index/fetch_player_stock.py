"""Fetch career-stock features for the locked pool (pre-reg A53, Lens B).

A53's Lens B tests the objection that the OAQ residual is accumulated fame
rather than a current-season attention surplus: every §6/A13 peer feature is a
single-season FLOW, while attention is a STOCK. The four features below are
career quantities that let the peer match control for that stock.

No new source. These come from the SAME `api-web.nhle.com/v1/player/{id}/landing`
response `fetch_nhl_api.py` already consumes -- `careerTotals.regularSeason`,
`draftDetails`, and the `seasonTotals` array -- so this adds one pass over the
pool and nothing else.

Transforms are locked in A53 and applied downstream, not here: this file stores
the RAW quantities so the log1p / sentinel rules stay auditable and reversible.
`draft_overall` is blank for an undrafted player; A53 fixes the substitution at
225 (one past the last pick of a seven-round, 32-team draft) in the consumer.

Writes:
  marchand_index/raw/player_stock.csv   one row per pooled player
    player_id, full_name, nhl_player_id, career_gp, career_points,
    career_goals, nhl_seasons, draft_year, draft_round, draft_overall,
    is_undrafted, stock_status, fetch_date
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (CONTACT_UA, RAW_DIR,  # noqa: E402
                     atomic_write_csv, load_players, session)

API = "https://api-web.nhle.com/v1"

FIELDS = ["player_id", "full_name", "nhl_player_id", "career_gp",
          "career_points", "career_goals", "nhl_seasons", "draft_year",
          "draft_round", "draft_overall", "is_undrafted", "stock_status",
          "fetch_date"]


def landing(s, pid: str) -> tuple[dict | None, bool]:
    """Return (payload, served_from_cache). The cache flag lets the caller skip
    the politeness sleep on a cache hit -- a re-run over an already-fetched
    pool costs no requests, so it should not cost the wall-clock either."""
    try:
        r = s.get(f"{API}/player/{pid}/landing",
                  headers={"User-Agent": CONTACT_UA}, timeout=20)
        r.raise_for_status()
        return r.json(), bool(getattr(r, "from_cache", False))
    except Exception as e:
        print(f"  landing {pid}: {e!r}", file=sys.stderr)
        return None, False


def extract_stock(land: dict | None) -> dict:
    """Career totals, NHL tenure, and draft slot from one landing response.

    `nhl_seasons` counts DISTINCT seasons, not rows: a player traded mid-season
    has one `seasonTotals` row per team, and counting rows would inflate tenure
    for exactly the well-travelled players Lens B is meant to control.
    """
    out = {k: "" for k in ("career_gp", "career_points", "career_goals",
                           "nhl_seasons", "draft_year", "draft_round",
                           "draft_overall")}
    out["is_undrafted"] = ""
    out["stock_status"] = "missing"
    if not land:
        return out

    ct = (land.get("careerTotals") or {}).get("regularSeason") or {}
    if ct:
        out["career_gp"] = ct.get("gamesPlayed", "")
        out["career_points"] = ct.get("points", "")
        out["career_goals"] = ct.get("goals", "")

    seasons = {
        str(r.get("season"))
        for r in (land.get("seasonTotals") or [])
        if r.get("leagueAbbrev") == "NHL" and r.get("gameTypeId") == 2
    }
    out["nhl_seasons"] = len(seasons)

    dd = land.get("draftDetails")
    if dd and dd.get("overallPick"):
        out["draft_year"] = dd.get("year", "")
        out["draft_round"] = dd.get("round", "")
        out["draft_overall"] = dd.get("overallPick", "")
        out["is_undrafted"] = 0
    else:
        # Genuinely undrafted, or a rookie whose draft record is absent.
        # A53 substitutes 225 downstream; the flag keeps the two cases
        # countable so the substitution's footprint is reportable.
        out["is_undrafted"] = 1

    out["stock_status"] = "ok" if ct else "thin"
    return out


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    s = session(expire_hours=12)
    players = load_players()

    rows = []
    n_missing_id = 0
    n_undrafted = 0
    n_thin = 0
    n_cached = 0
    for i, p in enumerate(players, 1):
        pid = (p.get("nhl_player_id") or "").strip()
        land, cached = landing(s, pid) if pid.isdigit() else (None, False)
        n_cached += 1 if cached else 0
        if not pid.isdigit():
            n_missing_id += 1
        info = extract_stock(land)
        n_undrafted += 1 if info["is_undrafted"] == 1 else 0
        n_thin += 1 if info["stock_status"] != "ok" else 0
        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "nhl_player_id": pid,
            "fetch_date": fetch_date,
            **info,
        })
        if i % 50 == 0 or i == len(players):
            print(f"[{i}/{len(players)}] {p['full_name']:<24} "
                  f"gp={info['career_gp']} pts={info['career_points']} "
                  f"seasons={info['nhl_seasons']} pick={info['draft_overall']}")
        if pid.isdigit() and not cached:
            time.sleep(0.4)

    out = RAW_DIR / "player_stock.csv"
    atomic_write_csv(out, rows, FIELDS)
    print(f"\nwrote {out} rows={len(rows)}")
    print(f"  no nhl_player_id : {n_missing_id}")
    print(f"  undrafted/no rec : {n_undrafted}")
    print(f"  stock not ok     : {n_thin}")
    print(f"  served from cache: {n_cached}")


if __name__ == "__main__":
    main()
