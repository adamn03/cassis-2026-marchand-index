"""Per-game arena attendance for every game in the A51 three-season window.

The NHL public API does NOT expose attendance: neither api-web gamecenter
(landing / boxscore / right-rail) nor the stats REST `game` endpoint carries an
attendance field, and the legacy statsapi.web.nhl.com host no longer resolves
(all three verified live 2026-08-08). Hockey-Reference publishes it in the
season games table, one page per season, which is also far politer than ~3,900
per-game requests.

Source: https://www.hockey-reference.com/leagues/NHL_<end_year>_games.html
  table#games            regular season
  table#games_playoffs   playoffs
Three requests total, spaced by SLEEP; Sports-Reference asks for <= 20 req/min.

Franchise identity follows the A51 rule used everywhere else in this codebase:
Arizona Coyotes / Utah Hockey Club / Utah Mammoth are ONE franchise and all map
to UTA, so the panel is continuous across both relocations.

Attendance semantics: Hockey-Reference reports tickets DISTRIBUTED for the home
venue, not turnstile count. Neutral-site games (e.g. the 2024-25 openers in
Prague) are kept and flagged `neutral_site` because the home team's own market
did not supply the crowd.

Writes:
  marchand_index/raw/game_attendance.csv
    game_date, season, game_type, visitor_team, visitor_code, visitor_goals,
    home_team, home_code, home_goals, overtime, attendance, game_length,
    neutral_site, in_window, fetch_date
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from _common import (BROWSER_UA, RAW_DIR, WINDOW_END_DATE,  # noqa: E402
                     WINDOW_START_DATE, atomic_write_csv, load_csv, session)

# Hockey-Reference labels a season by its END year: 2023-24 -> NHL_2024.
SEASON_PAGES = {"20232024": 2024, "20242025": 2025, "20252026": 2026}
BASE = "https://www.hockey-reference.com/leagues/NHL_{year}_games.html"
SLEEP = 6.0          # <= 20 req/min per Sports-Reference guidance

OUT_CSV = RAW_DIR / "game_attendance.csv"
OUT_FIELDS = [
    "game_date", "season", "game_type", "visitor_team", "visitor_code",
    "visitor_goals", "home_team", "home_code", "home_goals", "overtime",
    "attendance", "game_length", "neutral_site", "venue_note", "in_window",
    "fetch_date",
]

# A51 franchise continuity: all three identities are the same club.
NAME_ALIASES = {
    "Arizona Coyotes": "UTA",
    "Utah Hockey Club": "UTA",
    "Utah Mammoth": "UTA",
}

# Hockey-Reference fills `game_remarks` ONLY when a game is played somewhere
# other than the home club's building, and the value names the venue, e.g.
# "at Ohio Stadium (Columbus, OH)" for the 2025 Stadium Series. Presence of the
# remark is therefore the flag itself — do not pattern-match event names
# ("Winter Classic", "Global Series", ...), which do NOT appear in this field.
#
# This matters: the 94,751 crowd at Ohio Stadium is credited to Columbus, and
# leaving it in inflates CBJ's home average by ~8% against ESPN's figure.


def build_name_map() -> dict[str, str]:
    """Full team name -> project team_code, from teams.csv plus A51 aliases."""
    out: dict[str, str] = {}
    for t in load_csv(RAW_DIR / "teams.csv"):
        # "anaheim-ducks" -> "Anaheim Ducks"
        name = " ".join(w.capitalize() for w in t["team_slug"].split("-"))
        out[name] = t["team_code"]
    # capitalize() mangles these; pin them explicitly.
    out["St. Louis Blues"] = "STL"
    out["St Louis Blues"] = "STL"
    out.update(NAME_ALIASES)
    return out


def cell(row, stat: str) -> str:
    """Text of the <td|th data-stat=...> cell, '' when absent."""
    el = row.find(attrs={"data-stat": stat})
    return el.get_text(strip=True) if el else ""


def parse_table(soup: BeautifulSoup, table_id: str, season: str,
                game_type: str, name_map: dict[str, str],
                fetch_date: str) -> tuple[list[dict], list[str]]:
    """Rows for one table; also returns team names that failed to map."""
    table = soup.find("table", id=table_id)
    rows: list[dict] = []
    unmapped: list[str] = []
    if table is None:
        return rows, unmapped
    body = table.find("tbody")
    for tr in (body.find_all("tr") if body else []):
        if tr.get("class") and "thead" in tr.get("class"):
            continue
        date = cell(tr, "date_game")
        if not date:
            continue
        vt, ht = cell(tr, "visitor_team_name"), cell(tr, "home_team_name")
        vc, hc = name_map.get(vt, ""), name_map.get(ht, "")
        for nm, code in ((vt, vc), (ht, hc)):
            if nm and not code:
                unmapped.append(nm)
        att = cell(tr, "attendance").replace(",", "")
        notes = cell(tr, "game_remarks") or ""
        d = dt.date.fromisoformat(date)
        rows.append({
            "game_date": date,
            "season": season,
            "game_type": game_type,
            "visitor_team": vt,
            "visitor_code": vc,
            "visitor_goals": cell(tr, "visitor_goals"),
            "home_team": ht,
            "home_code": hc,
            "home_goals": cell(tr, "home_goals"),
            "overtime": cell(tr, "overtimes"),
            "attendance": att,
            "game_length": cell(tr, "game_duration"),
            # `game_remarks` is ALSO used for scoring notes (e.g. "No point for
            # regulation tie for Minnesota"), so presence alone over-flags.
            # Venue remarks are exactly those of the form "at <venue> (<city>)".
            "neutral_site": int(notes.strip().startswith("at ")),
            "venue_note": notes,
            "in_window": int(WINDOW_START_DATE <= d <= WINDOW_END_DATE),
            "fetch_date": fetch_date,
        })
    return rows, unmapped


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    name_map = build_name_map()
    s = session(expire_hours=24 * 7)     # season pages are static once played
    all_rows: list[dict] = []
    all_unmapped: set[str] = set()

    for season, year in SEASON_PAGES.items():
        url = BASE.format(year=year)
        r = s.get(url, headers={"User-Agent": BROWSER_UA}, timeout=60)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        reg, u1 = parse_table(soup, "games", season, "regular",
                              name_map, fetch_date)
        po, u2 = parse_table(soup, "games_playoffs", season, "playoff",
                             name_map, fetch_date)
        all_unmapped |= set(u1) | set(u2)
        n_att = sum(1 for x in reg + po if x["attendance"])
        print(f"[{season}] regular={len(reg)} playoff={len(po)} "
              f"with-attendance={n_att}")
        all_rows.extend(reg + po)
        if not getattr(r, "from_cache", False):
            time.sleep(SLEEP)

    if all_unmapped:
        print(f"WARNING: unmapped team names {sorted(all_unmapped)}",
              file=sys.stderr)

    all_rows.sort(key=lambda x: (x["game_date"], x["home_team"]))
    atomic_write_csv(OUT_CSV, all_rows, OUT_FIELDS)

    n_att = sum(1 for x in all_rows if x["attendance"])
    n_win = sum(1 for x in all_rows if x["in_window"])
    print(f"\nWrote {OUT_CSV}: {len(all_rows)} games "
          f"({n_att} with attendance, {n_win} inside the A51 window)")


if __name__ == "__main__":
    main()
