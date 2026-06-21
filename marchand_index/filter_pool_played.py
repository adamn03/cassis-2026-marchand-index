"""Apply the A10 pool refinement to the locked 788-skater roster snapshot.

DECISION 1 (whole-league pivot, 2026-06-17): the `/roster/{team}/current`
snapshot taken mid-June includes signed reserves / org-depth prospects who have
NEVER played an NHL regular-season game. Those rows carry no NHL production, so
they cannot be peer-matched (NaN engagement) and are pure noise. But a naive
"played >=1 GP in 2025-26" filter would wrongly drop a franchise player who
missed the whole season injured (verified: Aleksander Barkov, FLA, no 2025-26
row, eight prior 50-82 GP seasons).

RULE (Option 1 — keep career NHLers, drop never-played prospects):
  KEEP a skater iff career_nhl_gp >= 1  (ever played >=1 NHL regular-season
  game, gameTypeId==2, leagueAbbrev=="NHL"; this subsumes "played in 2025-26").
  DROP otherwise (never-played junior/AHL org depth).
On a landing fetch failure the skater is KEPT (conservative: never drop a real
roster member on a transient error) and flagged in the audit.

Reads:  pilot2/players.csv            (the 788 locked snapshot, committed @ HEAD)
Writes: pilot2/players.csv            (kept rows only, player_id re-sequenced 1..N)
        pilot2/pool_gp_audit.csv      (ALL 788 + cur_gp/career_nhl_gp/kept/reason;
                                        preserves the pre-filter snapshot for audit)

The landing calls share _common.session()'s on-disk requests-cache, so the
subsequent fetch_nhl_api.py run reads them from cache (no double network cost).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (CONTACT_UA, PILOT_DIR, atomic_write_csv,  # noqa: E402
                     load_csv, session)

NHL_API = "https://api-web.nhle.com/v1"
CUR_SEASON = "20252026"

PLAYERS_COLS = [
    "player_id", "full_name", "position", "group", "line_slot", "team_code",
    "nhl_team_code", "team_slug", "team_city", "nhl_player_id",
    "wikipedia_slug", "capwages_slug", "roster_source",
    "roster_snapshot_date", "fetch_date",
]


def landing(s, pid: str):
    try:
        r = s.get(f"{NHL_API}/player/{pid}/landing",
                  headers={"User-Agent": CONTACT_UA}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def gp_counts(land) -> tuple[int, int, bool]:
    """Return (cur_season_nhl_reg_gp, career_nhl_reg_gp, fetch_ok)."""
    if not land:
        return 0, 0, False
    cur = career = 0
    for row in (land.get("seasonTotals") or []):
        if row.get("leagueAbbrev") != "NHL" or row.get("gameTypeId") != 2:
            continue
        gp = int(row.get("gamesPlayed") or 0)
        career += gp
        if str(row.get("season")) == CUR_SEASON:
            cur += gp
    return cur, career, True


def main() -> None:
    players = load_csv(PILOT_DIR / "players.csv")
    s = session(expire_hours=24)
    n = len(players)
    print(f"loaded {n} skaters from snapshot")

    audit_rows: list[dict] = []
    kept: list[dict] = []
    dropped: list[dict] = []

    for i, p in enumerate(players, 1):
        cur, career, ok = gp_counts(landing(s, p["nhl_player_id"]))
        keep = (career >= 1) or (not ok)  # keep-on-fail is conservative
        if not ok:
            reason = "fetch_fail_kept"
        elif career >= 1:
            reason = "kept_career_nhl" if cur == 0 else "kept_played_2025_26"
        else:
            reason = "dropped_never_played_nhl"
        row = dict(p)
        row.update({"cur_gp_2025_26": cur, "career_nhl_gp": career,
                    "kept": int(keep), "drop_reason": reason})
        audit_rows.append(row)
        (kept if keep else dropped).append(p)
        time.sleep(0.12)
        if i % 100 == 0:
            print(f"  {i}/{n}", flush=True)

    # Re-sequence player_id 1..N on the kept set; preserve every other column.
    new_players: list[dict] = []
    for new_id, p in enumerate(kept, 1):
        r = {c: p.get(c, "") for c in PLAYERS_COLS}
        r["player_id"] = new_id
        new_players.append(r)

    # Audit CSV keeps the ORIGINAL 788 player_id + the decision fields.
    audit_cols = PLAYERS_COLS + ["cur_gp_2025_26", "career_nhl_gp", "kept",
                                 "drop_reason"]
    atomic_write_csv(PILOT_DIR / "pool_gp_audit.csv", audit_rows, audit_cols)
    atomic_write_csv(PILOT_DIR / "players.csv", new_players, PLAYERS_COLS)

    n_f = sum(1 for r in new_players if r["group"] == "f1")
    n_d = sum(1 for r in new_players if r["group"] == "d1")
    n_fail = sum(1 for r in audit_rows if r["drop_reason"] == "fetch_fail_kept")
    n_injured = sum(1 for r in audit_rows
                    if r["drop_reason"] == "kept_career_nhl")
    print(f"\nKEPT {len(new_players)} ({n_f} F / {n_d} D)  "
          f"DROPPED {len(dropped)}  (fetch-fail kept: {n_fail})")
    print(f"injured/absent career NHLers kept (0 GP in 2025-26): {n_injured}")
    if n_injured:
        print("  " + ", ".join(
            f"{r['full_name']}({r['team_code']})" for r in audit_rows
            if r["drop_reason"] == "kept_career_nhl"))
    print(f"\nDROPPED (never played an NHL game) — {len(dropped)}:")
    for r in dropped:
        print(f"  {r['full_name']:<26} {r['team_code']}")
    print("\nWrote players.csv (re-sequenced) + pool_gp_audit.csv (788 audit)")


if __name__ == "__main__":
    main()
