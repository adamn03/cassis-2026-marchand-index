"""A38 + A51: derive in-window team-changers from NHL data, with dates.

Mover set. A38 derived moves from landing `seasonTotals` across ONE season
boundary (20242025 -> 20252026) and left `event_date` blank for a manual
research pass. A51 widens the window to three seasons and replaces the manual
pass for everything it can date mechanically:

  source of truth  = the per-season GAME LOG (gameTypeId 2), which lists every
                     regular-season appearance with its date and team. Reading
                     it chronologically across 20232024 / 20242025 / 20252026
                     yields the player's actual team SPELLS.
  a move           = two consecutive spells with different franchises.
  in_season        = the two spells sit inside one season. The move is then
                     BRACKETED to [last game with old team, first game with
                     new team] — usually a handful of days.
  off_season       = the spells straddle a season boundary. The bracket is
                     months wide and the transaction date is NOT derivable
                     from appearances; such rows keep status=needs_date unless
                     a researched date already exists.

Why game logs rather than seasonTotals for dating: seasonTotals gives the set
of teams but no dates at all, so A38 had to send every row to manual research.
Game logs are the same NHL source, already free, and pin in-season moves to a
few days without a human in the loop.

MERGE DISCIPLINE. The existing mover_dates.csv holds 192 hand-researched rows
with source URLs. Those are NOT regenerated: a derived move that matches an
existing (player, old_team, new_team) row inherits that row's event_date,
urls and status verbatim. Manual research is only ever added to, never
overwritten.

Writes mover_dates.csv. `derive_moves` and `spells_to_moves` are pure (tested,
no network). NHL API only. Cached session + politeness sleep.
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (CONTACT_UA, PILOT_DIR, WINDOW_END_DATE,  # noqa: E402
                     WINDOW_SEASONS, WINDOW_START_DATE, atomic_write_csv,
                     load_players, session)

NHL_API = "https://api-web.nhle.com/v1"
OUT_CSV = PILOT_DIR / "mover_dates.csv"
FIELDS = ["player_id", "full_name", "nhl_player_id", "old_team", "new_team",
          "move_type", "event_date", "date_lower", "date_upper", "bracket_days",
          "season", "url_1", "url_2", "status"]

SEASONS = sorted(WINDOW_SEASONS)          # 20232024, 20242025, 20252026

# A51: one franchise, three identities inside the window. A name change is not
# a move. (A38 covered only the Utah pair; the window now also spans Arizona.)
FRANCHISE_ALIASES = {
    "ARI": "UTA", "UTA": "UTA", "UTAH": "UTA",
}


def canon_team(abbrev: str) -> str:
    """Franchise key for a game-log teamAbbrev."""
    a = (abbrev or "").upper()
    return FRANCHISE_ALIASES.get(a, a)


def spells_from_log(entries: list[dict]) -> list[tuple[str, str, str]]:
    """Chronological (franchise, first_date, last_date) spells from game-log
    rows. Input may be in any order; it is sorted by gameDate here."""
    rows = sorted((e for e in entries if e.get("gameDate")),
                  key=lambda e: e["gameDate"])
    spells: list[list[str]] = []
    for e in rows:
        t = canon_team(e.get("teamAbbrev", ""))
        if not t:
            continue
        if spells and spells[-1][0] == t:
            spells[-1][2] = e["gameDate"]           # extend current spell
        else:
            spells.append([t, e["gameDate"], e["gameDate"]])
    return [(a, b, c) for a, b, c in spells]


def spells_to_moves(spells: list[tuple[str, str, str]],
                    season_of: dict[str, str]) -> list[dict]:
    """Consecutive distinct franchises -> bracketed move records."""
    out = []
    for (t0, _f0, l0), (t1, f1, _l1) in zip(spells, spells[1:]):
        if t0 == t1:
            continue
        d0 = dt.date.fromisoformat(l0)
        d1 = dt.date.fromisoformat(f1)
        same_season = season_of.get(l0) == season_of.get(f1)
        out.append({
            "old_team": t0, "new_team": t1,
            "date_lower": l0, "date_upper": f1,
            "bracket_days": (d1 - d0).days,
            "move_type": "in_season" if same_season else "off_season",
            "season": season_of.get(f1, ""),
        })
    return out


def load_existing() -> dict[tuple[str, str, str], dict]:
    """(nhl_player_id, old, new) -> existing researched row, if any."""
    if not OUT_CSV.exists():
        return {}
    out = {}
    with OUT_CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = (str(r.get("nhl_player_id", "")),
                   canon_team_name(r.get("old_team", "")),
                   canon_team_name(r.get("new_team", "")))
            out[key] = r
    return out


# The pre-A51 file stored franchise NICKNAMES ("Stars", "Ducks"); the game log
# gives abbreviations. Map nicknames onto abbreviations so researched rows can
# still be matched to derived ones.
NICK_TO_ABBREV = {
    "ducks": "ANA", "bruins": "BOS", "sabres": "BUF", "flames": "CGY",
    "hurricanes": "CAR", "blackhawks": "CHI", "avalanche": "COL",
    "blue jackets": "CBJ", "stars": "DAL", "red wings": "DET",
    "oilers": "EDM", "panthers": "FLA", "kings": "LAK", "wild": "MIN",
    "canadiens": "MTL", "predators": "NSH", "devils": "NJD",
    "islanders": "NYI", "rangers": "NYR", "senators": "OTT", "flyers": "PHI",
    "penguins": "PIT", "sharks": "SJS", "kraken": "SEA", "blues": "STL",
    "lightning": "TBL", "maple leafs": "TOR", "canucks": "VAN",
    "golden knights": "VGK", "capitals": "WSH", "jets": "WPG",
    "coyotes": "UTA", "utah hockey club": "UTA", "mammoth": "UTA",
}


def canon_team_name(v: str) -> str:
    """Nickname or abbreviation -> canonical franchise abbreviation."""
    s = (v or "").strip()
    if not s:
        return ""
    low = s.casefold()
    if low in NICK_TO_ABBREV:
        return NICK_TO_ABBREV[low]
    return canon_team(s)


def main() -> None:
    s = session()
    existing = load_existing()
    print(f"existing researched rows: {len(existing)}")

    rows: list[dict] = []
    n_players = n_movers = n_fail = 0
    kept_research = 0

    for p in load_players():
        n_players += 1
        pid = str(p.get("nhl_player_id", "") or "")
        if not pid.isdigit():
            continue

        entries: list[dict] = []
        season_of: dict[str, str] = {}
        failed = False
        for sea in SEASONS:
            try:
                r = s.get(f"{NHL_API}/player/{pid}/game-log/{sea}/2",
                          headers={"User-Agent": CONTACT_UA}, timeout=25)
                if r.status_code != 200:
                    continue
                log = r.json().get("gameLog") or []
                for e in log:
                    if e.get("gameDate"):
                        season_of[e["gameDate"]] = sea
                entries.extend(log)
                if not getattr(r, "from_cache", False):
                    time.sleep(0.25)
            except Exception as e:
                print(f"  game-log {pid} {sea}: {e!r}", file=sys.stderr)
                failed = True
        if failed and not entries:
            n_fail += 1
            continue

        spells = spells_from_log(entries)
        moves = spells_to_moves(spells, season_of)
        # Keep only moves whose bracket touches the attention window.
        moves = [m for m in moves
                 if dt.date.fromisoformat(m["date_upper"]) >= WINDOW_START_DATE
                 and dt.date.fromisoformat(m["date_lower"]) <= WINDOW_END_DATE]
        if moves:
            n_movers += 1

        for m in moves:
            key = (pid, m["old_team"], m["new_team"])
            prior = existing.get(key)
            if prior and (prior.get("event_date") or "").strip():
                event_date = prior["event_date"]
                status = prior.get("status", "dated")
                u1, u2 = prior.get("url_1", ""), prior.get("url_2", "")
                kept_research += 1
            elif m["move_type"] == "in_season":
                # Bracketed to a few days: take the midpoint of the bracket.
                d0 = dt.date.fromisoformat(m["date_lower"])
                d1 = dt.date.fromisoformat(m["date_upper"])
                event_date = (d0 + (d1 - d0) / 2).isoformat()
                status = "dated_gamelog_bracket"
                u1 = u2 = ""
            else:
                event_date = ""
                status = "needs_date"
                u1 = u2 = ""
            rows.append({
                "player_id": p["player_id"], "full_name": p["full_name"],
                "nhl_player_id": pid,
                "old_team": m["old_team"], "new_team": m["new_team"],
                "move_type": m["move_type"], "event_date": event_date,
                "date_lower": m["date_lower"], "date_upper": m["date_upper"],
                "bracket_days": m["bracket_days"], "season": m["season"],
                "url_1": u1, "url_2": u2, "status": status,
            })

        if n_players % 100 == 0:
            print(f"  [{n_players}] moves so far: {len(rows)}", flush=True)

    rows.sort(key=lambda r: (r["date_lower"], r["full_name"]))
    atomic_write_csv(OUT_CSV, rows, FIELDS)

    import collections
    by_status = collections.Counter(r["status"] for r in rows)
    by_type = collections.Counter(r["move_type"] for r in rows)
    tight = sum(1 for r in rows
                if r["status"] == "dated_gamelog_bracket"
                and int(r["bracket_days"]) <= 7)
    print(f"\nplayers={n_players} movers={n_movers} move_rows={len(rows)} "
          f"gamelog_failures={n_fail}")
    print(f"  by type:   {dict(by_type)}")
    print(f"  by status: {dict(by_status)}")
    print(f"  researched dates preserved: {kept_research}")
    print(f"  in-season moves bracketed to <=7 days: {tight}")
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
