"""Fetch on-ice skill features + active rosters from the NHL public API.

Per pre-registration section 6, skill features for peer matching are
PPG, TOI/G, age, position (position is a hard filter).
Per section 7, team active rosters are needed to compute the team market
baseline = mean Wikipedia 12-mo pageviews across the team's roster.

This script writes two outputs:
  pilot/raw/nhl_skill.csv          14 rows, one per pilot player
  pilot/raw/team_rosters.csv       N rows per team, all rostered players

For Reaves (whose team is flagged VERIFY), we look up the current team by
searching the league-wide player-stats roster, and update pilot/players.csv
ONLY for that row, with a logged note. (This is the one allowed in-place
edit per pre-reg section 14 amendment policy because the player's identity
is locked but team is a queryable property; the team assignment is not
pre-registered material.)
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_players, session  # noqa: E402

USER_AGENT = "marchand-index-pilot/0.1 (https://github.com/adamn03; ana178@sfu.ca)"
API = "https://api-web.nhle.com/v1"
SEARCH = "https://search.d3.nhle.com/api/v1/search/player"
CURRENT_SEASON = "20252026"  # 2025-26 NHL season; pre-reg locks cap year 2025-26


def find_player_id(s, full_name: str) -> int | None:
    """Search the NHL player-search endpoint by full name."""
    try:
        r = s.get(SEARCH, params={"culture": "en-us", "limit": 5, "q": full_name},
                  headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        hits = r.json()
        # Prefer an active player whose full name matches exactly.
        for h in hits:
            name = f"{h.get('firstName','')} {h.get('lastName','')}".strip()
            if name.lower() == full_name.lower() and h.get("active"):
                return int(h["playerId"])
        # Fallback: first hit.
        if hits:
            return int(hits[0]["playerId"])
    except Exception as e:
        print(f"  search {full_name}: {e!r}", file=sys.stderr)
    return None


def player_landing(s, pid: int) -> dict | None:
    try:
        r = s.get(f"{API}/player/{pid}/landing", headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  landing {pid}: {e!r}", file=sys.stderr)
        return None


def team_roster(s, team_code: str) -> list[dict]:
    try:
        r = s.get(f"{API}/roster/{team_code}/current",
                  headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        data = r.json()
        rows = []
        for group_key in ("forwards", "defensemen", "goalies"):
            for p in data.get(group_key, []):
                rows.append({
                    "team_code": team_code,
                    "player_id_nhl": p["id"],
                    "first_name": p.get("firstName", {}).get("default", ""),
                    "last_name": p.get("lastName", {}).get("default", ""),
                    "position": p.get("positionCode", ""),
                    "group": group_key,
                })
        return rows
    except Exception as e:
        print(f"  roster {team_code}: {e!r}", file=sys.stderr)
        return []


def extract_skill(landing: dict) -> dict:
    """Pull PPG, TOI/G, age, position from the season totals (regular season, current season)."""
    out = {"ppg": "", "toi_per_game": "", "age": "", "position": "", "team_code": ""}
    if not landing:
        return out
    out["position"] = landing.get("position", "")
    bd = landing.get("birthDate")
    if bd:
        try:
            born = dt.date.fromisoformat(bd)
            today = dt.date.today()
            out["age"] = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except Exception:
            pass
    out["team_code"] = landing.get("currentTeamAbbrev", "") or ""

    # Find the row for current season regular-season totals.
    season_totals = (landing.get("seasonTotals") or [])
    cur = None
    for row in season_totals:
        if str(row.get("season")) == CURRENT_SEASON and row.get("gameTypeId") == 2:
            cur = row
            break
    if cur:
        gp = cur.get("gamesPlayed") or 0
        if gp:
            points = cur.get("points") or 0
            out["ppg"] = round(points / gp, 4)
        # NHL API exposes timeOnIce as M:SS string in some season-total payloads
        toi_str = cur.get("avgToi") or cur.get("timeOnIcePerGame") or ""
        if toi_str and ":" in str(toi_str):
            m, ss = str(toi_str).split(":")[:2]
            out["toi_per_game"] = round(int(m) + int(ss) / 60, 3)
    return out


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    s = session(expire_hours=12)
    players = load_players()

    skill_rows = []
    seen_teams: set[str] = set()
    for p in players:
        # Prefer the pre-populated nhl_player_id (amendment A2) over the
        # search endpoint, which mis-ranks for common names.
        pid_field = (p.get("nhl_player_id") or "").strip()
        if pid_field.isdigit():
            pid = int(pid_field)
        else:
            pid = find_player_id(s, p["full_name"])
        landing = player_landing(s, pid) if pid else None
        info = extract_skill(landing)
        # If players.csv had team_code=VERIFY (Reaves), trust the API value.
        team_from_api = info["team_code"]
        team_code = p["team_code"] if p["team_code"] != "VERIFY" else team_from_api
        if p["team_code"] == "VERIFY":
            print(f"  resolved {p['full_name']} team via NHL API -> {team_from_api}")
        seen_teams.add(team_code)
        skill_rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "nhl_player_id": pid or "",
            "team_code": team_code,
            "position": info["position"] or p["position"],
            "age": info["age"],
            "ppg": info["ppg"],
            "toi_per_game": info["toi_per_game"],
            "fetch_date": fetch_date,
        })
        print(f"{p['full_name']:<22} pid={pid} team={team_code} pos={info['position']} "
              f"age={info['age']} ppg={info['ppg']} toi={info['toi_per_game']}")
        time.sleep(0.5)

    atomic_write_csv(RAW_DIR / "nhl_skill.csv", skill_rows, [
        "player_id", "full_name", "nhl_player_id", "team_code", "position",
        "age", "ppg", "toi_per_game", "fetch_date",
    ])

    # Pull rosters for every team appearing in skill_rows (needed for market baseline).
    roster_rows = []
    for code in sorted(t for t in seen_teams if t):
        rows = team_roster(s, code)
        roster_rows.extend(rows)
        print(f"  roster {code}: {len(rows)} players")
        time.sleep(0.5)
    atomic_write_csv(RAW_DIR / "team_rosters.csv", roster_rows, [
        "team_code", "player_id_nhl", "first_name", "last_name", "position", "group",
    ])

    print(f"\nWrote {RAW_DIR/'nhl_skill.csv'} ({len(skill_rows)} rows)")
    print(f"Wrote {RAW_DIR/'team_rosters.csv'} ({len(roster_rows)} rows)")


if __name__ == "__main__":
    main()
