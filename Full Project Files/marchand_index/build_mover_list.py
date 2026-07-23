"""A38: derive in-window team-changers from NHL landing seasonTotals.

Mover set (prereg A38, mechanical):
  in-season  = consecutive distinct NHL 20252026 regular-season teams
               (gameTypeId==2, leagueAbbrev=="NHL") -- the A22 derivation;
  off-season = last 20242025 NHL team != first 20252026 NHL team
               (both season rows present).

Writes mover_dates.csv SKELETON (event_date blank, status=needs_date) for the
A38 clause-3 date research pass. `derive_moves` is pure (tested, no network).
NHL API only -- never touches wiki files. Cached session + 0.2 s politeness.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (CONTACT_UA, PILOT_DIR, atomic_write_csv,  # noqa: E402
                     load_players, session)

NHL_API = "https://api-web.nhle.com/v1"
OUT_CSV = PILOT_DIR / "mover_dates.csv"
FIELDS = ["player_id", "full_name", "nhl_player_id", "old_team", "new_team",
          "move_type", "event_date", "url_1", "url_2", "status"]


def _team(row: dict) -> str:
    """Team name from a seasonTotals row (plain-string or {'default': ...})."""
    for key in ("teamCommonName", "teamName"):
        v = row.get(key)
        if isinstance(v, dict):
            v = v.get("default")
        if v:
            return str(v)
    return ""


def _same_franchise(a: str, b: str) -> bool:
    """A22 rename rule: Utah Hockey Club / Utah Mammoth are one franchise —
    a name change between seasons is not a move (2026-07-22: the first
    skeleton emitted 19 such artifacts, excluded during date research)."""
    fa, fb = a.casefold(), b.casefold()
    utah = ("utah", "mammoth")
    return a == b or (any(k in fa for k in utah) and any(k in fb for k in utah))


def derive_moves(season_rows: list[dict]) -> list[tuple[str, str, str]]:
    """(old_team, new_team, kind) moves per A38; NHL regular-season rows only."""
    nhl = [r for r in season_rows
           if r.get("gameTypeId") == 2 and r.get("leagueAbbrev") == "NHL"]
    t2425 = [_team(r) for r in nhl if str(r.get("season")) == "20242025"]
    t2526 = [_team(r) for r in nhl if str(r.get("season")) == "20252026"]
    moves: list[tuple[str, str, str]] = []
    if t2425 and t2526 and not _same_franchise(t2425[-1], t2526[0]):
        moves.append((t2425[-1], t2526[0], "off_season"))
    for a, b in zip(t2526, t2526[1:]):
        if not _same_franchise(a, b):
            moves.append((a, b, "in_season"))
    return moves


def main() -> None:
    s = session()
    rows: list[dict] = []
    n_players = n_movers = n_fail = 0
    for p in load_players():
        n_players += 1
        pid = str(p.get("nhl_player_id", "") or "")
        if not pid.isdigit():
            continue
        try:
            r = s.get(f"{NHL_API}/player/{pid}/landing",
                      headers={"User-Agent": CONTACT_UA}, timeout=20)
            r.raise_for_status()
            totals = r.json().get("seasonTotals") or []
        except Exception as e:
            print(f"  landing {pid}: {e!r}", file=sys.stderr)
            n_fail += 1
            continue
        moves = derive_moves(totals)
        if moves:
            n_movers += 1
        for old, new, kind in moves:
            print(f"  {p['full_name']:<28} {old} -> {new} ({kind})")
            rows.append({
                "player_id": p["player_id"], "full_name": p["full_name"],
                "nhl_player_id": pid, "old_team": old, "new_team": new,
                "move_type": "", "event_date": "", "url_1": "", "url_2": "",
                "status": "needs_date",
            })
        if not getattr(r, "from_cache", False):
            time.sleep(0.2)
    atomic_write_csv(OUT_CSV, rows, FIELDS)
    print(f"players={n_players} movers={n_movers} move_rows={len(rows)} "
          f"landing_failures={n_fail}")
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
