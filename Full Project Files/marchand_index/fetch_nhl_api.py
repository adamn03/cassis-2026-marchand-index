"""Fetch on-ice skill features for the locked player pool (players.csv; pre-reg §6).

Skill vector for peer matching = (age, PPG, TOI/G), pulled from the NHL public
landing endpoint for the 2025-26 regular season (gameTypeId 2). The
nhl_player_id is already resolved in players.csv (fetch_rosters step), so we
use it directly and never hit the unreliable search endpoint here.

Unlike v1, pilot2 needs NO team_rosters export: the market baseline is an
exogenous proxy (§7), not a roster-mean, so per-team rosters are not fetched.

A skater with a missing nhl_player_id (pre-declared: Michael Benning, a
DailyFaceoff top-pair anomaly absent from FLA's NHL roster) gets NULL skill
fields and is flagged match_quality=low downstream — kept, not dropped.

Writes:
  marchand_index/raw/nhl_skill.csv   one row per pooled player
    player_id, full_name, nhl_player_id, team_code, position, age, ppg,
    toi_per_game, games_played, fetch_date
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONTACT_UA, RAW_DIR, atomic_write_csv, load_players, session  # noqa: E402

API = "https://api-web.nhle.com/v1"
CURRENT_SEASON = "20252026"  # pre-reg locks the 2025-26 season


def landing(s, pid: str) -> dict | None:
    try:
        r = s.get(f"{API}/player/{pid}/landing",
                  headers={"User-Agent": CONTACT_UA}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  landing {pid}: {e!r}", file=sys.stderr)
        return None


def extract_skill(land: dict | None) -> dict:
    """Age, position, and current-season regular-season PPG + TOI/G."""
    out = {"position": "", "age": "", "ppg": "", "toi_per_game": "", "games_played": ""}
    if not land:
        return out
    out["position"] = land.get("position", "")
    bd = land.get("birthDate")
    if bd:
        try:
            born = dt.date.fromisoformat(bd)
            today = dt.date.today()
            out["age"] = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except Exception:
            pass
    # A player's current-season regular-season line can span MULTIPLE
    # seasonTotals rows (one per team after a mid-season trade, or split
    # stints). Sum them for the true season total; a single-row player is
    # unaffected (sum of one == that row). leagueAbbrev must be NHL so AHL
    # conditioning rows with the same gameTypeId are never folded in. TOI is
    # games-weighted across the rows that report it.
    gp_sum = 0
    pts_sum = 0
    toi_num = 0.0
    toi_den = 0
    found = False
    for row in (land.get("seasonTotals") or []):
        if (str(row.get("season")) == CURRENT_SEASON
                and row.get("gameTypeId") == 2
                and row.get("leagueAbbrev") == "NHL"):
            found = True
            gp = row.get("gamesPlayed") or 0
            gp_sum += gp
            pts_sum += row.get("points") or 0
            toi = row.get("avgToi") or ""
            if ":" in str(toi) and gp:
                m, ss = str(toi).split(":")[:2]
                toi_num += (int(m) + int(ss) / 60) * gp
                toi_den += gp
    if found:
        out["games_played"] = gp_sum
        if gp_sum:
            out["ppg"] = round(pts_sum / gp_sum, 4)
        if toi_den:
            out["toi_per_game"] = round(toi_num / toi_den, 3)
    return out


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    s = session(expire_hours=12)
    players = load_players()

    rows = []
    n_missing = 0
    for p in players:
        pid = (p.get("nhl_player_id") or "").strip()
        info = extract_skill(landing(s, pid)) if pid.isdigit() else extract_skill(None)
        if not pid.isdigit():
            n_missing += 1
        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "nhl_player_id": pid,
            "team_code": p["team_code"],
            "position": info["position"] or p["position"],
            "age": info["age"],
            "ppg": info["ppg"],
            "toi_per_game": info["toi_per_game"],
            "games_played": info["games_played"],
            "fetch_date": fetch_date,
        })
        flag = "" if pid.isdigit() else "  <-- NO NHL ID (NULL skill)"
        print(f"{p['full_name']:<24} pid={pid:<9} pos={info['position'] or p['position']:<2} "
              f"age={info['age']} ppg={info['ppg']} toi={info['toi_per_game']} "
              f"gp={info['games_played']}{flag}")
        if pid.isdigit():
            time.sleep(0.4)

    atomic_write_csv(RAW_DIR / "nhl_skill.csv", rows, [
        "player_id", "full_name", "nhl_player_id", "team_code", "position",
        "age", "ppg", "toi_per_game", "games_played", "fetch_date",
    ])
    n_ppg = sum(1 for r in rows if r["ppg"] != "")
    print(f"\nWrote nhl_skill.csv: {len(rows)} rows "
          f"({n_ppg} with PPG, {n_missing} missing NHL id)")


if __name__ == "__main__":
    main()
