"""Build the 160-skater Tier-1 set (pre-reg pilot2 §2 as amended by A7).

For each of the 32 NHL teams, take the most-deployed skater at each position
by 2025-26 regular-season TOI/G from the NHL public API:
  - the LEFT WING (L), CENTER (C), and RIGHT WING (R) with the highest TOI/G;
  - the two DEFENSEMEN (D) with the highest TOI/G.
Eligibility floor: >= 41 GP (half the 82-game season) so a short high-minute
call-up cannot win a slot on a small sample. TOI/G and GP are aggregated across
all current-season NHL reg-season seasonTotals rows (GP-weighted TOI/G; summed
GP), so a mid-season trade is handled correctly.

5 skaters/team x 32 = 160 (96 F / 64 D). Goalies excluded.

A7 supersedes fetch_rosters_dailyfaceoff.py: selection is now an objective,
reproducible NHL quantity (deployment) with no DailyFaceoff dependency. The
32-team enumeration + team_code scheme come from raw/teams.csv (static), so
downstream joins are unchanged. NHL playerId comes straight from the roster
endpoint (no name-search resolution needed).

Per-slot relaxation (pre-reg A7): if a position has NO skater clearing the 41-GP
floor for a team, the floor is relaxed for that one slot to the highest-TOI/G
rostered skater at that position; recorded as roster_source = nhl_toi_relaxed.

Writes:
  pilot2/players.csv   160 rows (the A7-locked set)
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (CONTACT_UA, RAW_DIR, PILOT_DIR, atomic_write_csv,  # noqa: E402
                     load_csv, session)

NHL_API = "https://api-web.nhle.com/v1"
CURRENT_SEASON = "20252026"
GP_FLOOR = 41  # half of the 82-game regular season (pre-reg A7)

# teams.csv shortName -> NHL tri-code (only the 8 that differ are remapped).
NHL_CODE = {"LA": "LAK", "MON": "MTL", "NAS": "NSH", "NJ": "NJD",
            "SJ": "SJS", "TB": "TBL", "VEG": "VGK", "WAS": "WSH"}


def nhl_code(team_code: str) -> str:
    return NHL_CODE.get(team_code, team_code)


def capwages_slug(name: str) -> str:
    return name.lower().replace(".", "").replace("'", "").replace(" ", "-")


def wiki_slug_guess(name: str) -> str:
    return name.strip().replace(" ", "_")


def nhl_roster(s, nhl_team: str) -> list[dict]:
    try:
        r = s.get(f"{NHL_API}/roster/{nhl_team}/current",
                  headers={"User-Agent": CONTACT_UA}, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  roster {nhl_team}: {e!r}", file=sys.stderr)
        return []
    out = []
    for grp in ("forwards", "defensemen"):  # goalies excluded by design
        for p in data.get(grp, []):
            nm = f"{p['firstName']['default']} {p['lastName']['default']}"
            out.append({"id": str(p["id"]), "name": nm,
                        "pos": p.get("positionCode", "")})
    return out


def landing(s, pid: str) -> dict | None:
    try:
        r = s.get(f"{NHL_API}/player/{pid}/landing",
                  headers={"User-Agent": CONTACT_UA}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _toi_seconds(avg_toi: str) -> int | None:
    if ":" not in str(avg_toi):
        return None
    m, ss = str(avg_toi).split(":")[:2]
    return int(m) * 60 + int(ss)


def reg_toi_gp(land: dict | None) -> tuple[float, int]:
    """GP-weighted TOI/G (minutes) + total GP across all current-season NHL
    reg-season seasonTotals rows. Handles mid-season trades (multiple rows)."""
    if not land:
        return -1.0, 0
    tot_gp, tot_sec = 0, 0
    for row in (land.get("seasonTotals") or []):
        if (str(row.get("season")) == CURRENT_SEASON
                and row.get("gameTypeId") == 2
                and row.get("leagueAbbrev") == "NHL"):
            gp = row.get("gamesPlayed") or 0
            sec = _toi_seconds(row.get("avgToi") or "")
            if gp and sec is not None:
                tot_gp += int(gp)
                tot_sec += sec * int(gp)
    if tot_gp == 0:
        return -1.0, 0
    return (tot_sec / tot_gp) / 60, tot_gp


def select_unit(skaters: list[dict]) -> list[dict]:
    """skaters: dicts with id, name, pos (L/C/R/D), toi, gp.
    Returns 5: highest-TOI L, C, R + top-2 D, with the >=41 GP floor and
    per-slot relaxation. Each row tagged group/position/source."""
    unit: list[dict] = []
    chosen: set[str] = set()

    def pick(cands: list[dict]) -> dict | None:
        elig = [c for c in cands if c["gp"] >= GP_FLOOR and c["id"] not in chosen]
        pool, relaxed = (elig, False) if elig else (
            [c for c in cands if c["id"] not in chosen], True)
        if not pool:
            return None
        best = max(pool, key=lambda c: c["toi"])
        best = {**best, "_relaxed": relaxed}
        chosen.add(best["id"])
        return best

    # Forwards: one per position by NHL roster code.
    fwds = [c for c in skaters if c["pos"] in ("L", "C", "R")]
    for pos in ("L", "C", "R"):
        cands = [c for c in fwds if c["pos"] == pos]
        sel = pick(cands)
        if sel is None:  # team has no rostered skater at this position: spill over
            sel = pick(fwds)
            if sel:
                sel["_relaxed"] = True
        if sel:
            sel.update(group="f1", slot_pos=pos)
            unit.append(sel)

    # Defense: top-2 by TOI/G (floor, then relax to fill 2).
    dmen = [c for c in skaters if c["pos"] == "D"]
    for _ in range(2):
        sel = pick(dmen)
        if sel:
            sel.update(group="d1", slot_pos="D")
            unit.append(sel)
    return unit


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    s = session(expire_hours=24)
    teams = load_csv(RAW_DIR / "teams.csv")
    print(f"teams: {len(teams)}")

    rows = []
    pid_seq = 0
    for t in teams:
        ncode = nhl_code(t["team_code"])
        roster = nhl_roster(s, ncode)
        skaters = []
        for p in roster:
            toi, gp = reg_toi_gp(landing(s, p["id"]))
            time.sleep(0.25)
            skaters.append({"id": p["id"], "name": p["name"],
                            "pos": p["pos"], "toi": toi, "gp": gp})

        unit = select_unit(skaters)
        if len(unit) != 5:
            print(f"  WARNING [{t['team_code']}] got {len(unit)} skaters (expected 5)")

        for u in unit:
            pid_seq += 1
            source = "nhl_toi_relaxed" if u.get("_relaxed") else "nhl_toi_position"
            rows.append({
                "player_id": pid_seq,
                "full_name": u["name"],
                "position": u["slot_pos"],
                "group": u["group"],
                "line_slot": f"{u['group']}:{u['slot_pos']}",
                "team_code": t["team_code"],
                "nhl_team_code": ncode,
                "team_slug": t["team_slug"],
                "team_city": t["city"],
                "nhl_player_id": u["id"],
                "wikipedia_slug": wiki_slug_guess(u["name"]),
                "capwages_slug": capwages_slug(u["name"]),
                "roster_source": source,
                "fetch_date": fetch_date,
            })
            flag = "  <-- GP-relaxed" if u.get("_relaxed") else ""
            print(f"  {t['team_code']:>3} {u['slot_pos']:>2} "
                  f"{u['name']:<24} toi={u['toi']:5.2f} gp={u['gp']:>2} "
                  f"nhl={u['id']}{flag}")
        time.sleep(0.3)

    atomic_write_csv(PILOT_DIR / "players.csv", rows, [
        "player_id", "full_name", "position", "group", "line_slot", "team_code",
        "nhl_team_code", "team_slug", "team_city", "nhl_player_id",
        "wikipedia_slug", "capwages_slug", "roster_source", "fetch_date",
    ])
    n_relax = sum(1 for r in rows if r["roster_source"] == "nhl_toi_relaxed")
    n_f = sum(1 for r in rows if r["group"] == "f1")
    n_d = sum(1 for r in rows if r["group"] == "d1")
    print(f"\nWrote players.csv: {len(rows)} skaters "
          f"({n_f} F / {n_d} D; {n_relax} GP-relaxed slots)")


if __name__ == "__main__":
    main()
