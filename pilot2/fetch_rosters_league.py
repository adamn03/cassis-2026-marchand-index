"""Build the whole-league skater pool (pilot2 'league' run, pre-reg A10).

For each of the 32 NHL teams, take EVERY rostered skater (all forwards + all
defensemen) from the NHL public roster endpoint. Goalies excluded by design.

No GP gate, no TOI selection: roster membership at the end of the 2025-26 season
IS the qualification. Players sent down to the AHL are not on the end-of-season
NHL roster, so the snapshot filters them naturally; legitimate low-GP NHLers
(e.g. a young D who missed games but is a rostered regular) are retained. A
descriptive small_sample flag (GP<20) is applied later in compute_oaq, not here.

Snapshot captured ONCE and LOCKED. Re-deriving after 2026-07-01 free agency
would overwrite /current with new rosters and corrupt the end-of-season state.

Supersedes fetch_rosters_toi.py (which picked the top-5 skaters/team by TOI/G).
The 32-team enumeration + team_code scheme come from raw/teams.csv (static), so
downstream joins are unchanged. NHL playerId comes straight from the roster
endpoint (no name-search resolution needed).

Writes:
  pilot2/players.csv   ~715 rows (the A10-locked whole-league pool)
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

# teams.csv team_code -> NHL tri-code (only the 8 that differ are remapped).
NHL_CODE = {"LA": "LAK", "MON": "MTL", "NAS": "NSH", "NJ": "NJD",
            "SJ": "SJS", "TB": "TBL", "VEG": "VGK", "WAS": "WSH"}

# NHL positionCode -> peer-split group (compute_oaq key). Goalies (G) absent by
# design: we only read the forwards + defensemen roster groups.
GROUP = {"L": "f1", "C": "f1", "R": "f1", "D": "d1"}


def nhl_code(team_code: str) -> str:
    return NHL_CODE.get(team_code, team_code)


def capwages_slug(name: str) -> str:
    return name.lower().replace(".", "").replace("'", "").replace(" ", "-")


def wiki_slug_guess(name: str) -> str:
    return name.strip().replace(" ", "_")


def nhl_roster(s, nhl_team: str) -> list[dict]:
    r = s.get(f"{NHL_API}/roster/{nhl_team}/current",
              headers={"User-Agent": CONTACT_UA}, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = []
    for grp in ("forwards", "defensemen"):  # goalies excluded by design
        for p in data.get(grp, []):
            nm = f"{p['firstName']['default']} {p['lastName']['default']}"
            out.append({"id": str(p["id"]), "name": nm,
                        "pos": p.get("positionCode", "")})
    return out


def main() -> None:
    snapshot_date = dt.date.today().isoformat()
    s = session(expire_hours=24)
    teams = load_csv(RAW_DIR / "teams.csv")
    print(f"teams: {len(teams)}  snapshot {snapshot_date}")

    rows: list[dict] = []
    pid_seq = 0
    for t in teams:
        ncode = nhl_code(t["team_code"])
        roster = nhl_roster(s, ncode)
        n_team = 0
        for p in roster:
            grp = GROUP.get(p["pos"])
            if grp is None:  # unexpected non-skater in a skater group: skip loudly
                print(f"  WARN [{t['team_code']}] {p['name']} pos={p['pos']!r} skipped")
                continue
            pid_seq += 1
            n_team += 1
            rows.append({
                "player_id": pid_seq,
                "full_name": p["name"],
                "position": p["pos"],
                "group": grp,
                "line_slot": f"{grp}:{p['pos']}",
                "team_code": t["team_code"],
                "nhl_team_code": ncode,
                "team_slug": t["team_slug"],
                "team_city": t["city"],
                "nhl_player_id": p["id"],
                "wikipedia_slug": wiki_slug_guess(p["name"]),
                "capwages_slug": capwages_slug(p["name"]),
                "roster_source": "nhl_roster_full",
                "roster_snapshot_date": snapshot_date,
                "fetch_date": snapshot_date,
            })
        print(f"  {t['team_code']:>3} -> {ncode:>3}: {n_team} skaters")
        time.sleep(0.3)

    atomic_write_csv(PILOT_DIR / "players.csv", rows, [
        "player_id", "full_name", "position", "group", "line_slot", "team_code",
        "nhl_team_code", "team_slug", "team_city", "nhl_player_id",
        "wikipedia_slug", "capwages_slug", "roster_source",
        "roster_snapshot_date", "fetch_date",
    ])
    n_f = sum(1 for r in rows if r["group"] == "f1")
    n_d = sum(1 for r in rows if r["group"] == "d1")
    print(f"\nWrote players.csv: {len(rows)} skaters ({n_f} F / {n_d} D) "
          f"across {len(teams)} teams; snapshot {snapshot_date}")


if __name__ == "__main__":
    main()
