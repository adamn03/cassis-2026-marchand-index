"""Build the 160-skater Tier-1 set (pre-reg pilot2 §2).

Each team's first forward line (DailyFaceoff group f1: 3 F) + first defensive
pairing (group d1: 2 D), from the line-combinations page __NEXT_DATA__ on
snapshot date D. NHL playerId is resolved against the team's NHL roster using
accent-folded name matching (the NHL search endpoint mis-ranks young/accented
names), with the search endpoint as a fallback.

Per-team fallback (pre-reg): if DF lacks a usable f1+d1 for a team, take the
top-3 F + top-2 D by 2025-26 regular-season TOI/G from the NHL public API.

team_code is kept on DailyFaceoff's scheme throughout (so it joins teams.csv);
the NHL tri-code is recorded separately as nhl_team_code.

Writes:
  pilot2/players.csv      160 rows (the locked set)
  pilot2/raw/teams.csv    32 rows (team_code, slug, city, division)
"""
from __future__ import annotations

import datetime as dt
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (BROWSER_UA, CONTACT_UA, RAW_DIR, PILOT_DIR, atomic_write_csv,  # noqa: E402
                     next_data, session)

DF = "https://www.dailyfaceoff.com/teams/{slug}/line-combinations"
NHL_API = "https://api-web.nhle.com/v1"
NHL_SEARCH = "https://search.d3.nhle.com/api/v1/search/player"
CURRENT_SEASON = "20252026"

# DailyFaceoff shortName -> NHL tri-code (only the 8 that differ are remapped).
NHL_CODE = {"LA": "LAK", "MON": "MTL", "NAS": "NSH", "NJ": "NJD",
            "SJ": "SJS", "TB": "TBL", "VEG": "VGK", "WAS": "WSH"}

# Verified nickname mismatches between DailyFaceoff and the NHL roster
# (folded DF name -> NHL playerId), applied only after roster + search miss.
MANUAL_ID = {"gabriel perreault": "8484210"}  # DF "Gabriel" = NHL "Gabe" Perreault (NYR)


def nhl_code(df_code: str) -> str:
    return NHL_CODE.get(df_code, df_code)


def fold(s: str) -> str:
    """Accent-fold, drop non-alphanumerics, lowercase, collapse spaces."""
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = "".join(c if c.isalnum() or c.isspace() else " " for c in s)
    return " ".join(s.lower().split())


def capwages_slug(name: str) -> str:
    return name.lower().replace(".", "").replace("'", "").replace(" ", "-")


def wiki_slug_guess(name: str) -> str:
    return name.strip().replace(" ", "_")


def get_team_list(s) -> list[dict]:
    r = s.get(DF.format(slug="edmonton-oilers"),
              headers={"User-Agent": BROWSER_UA}, timeout=25)
    r.raise_for_status()
    teams = next_data(r.text)["props"]["pageProps"]["sortedTeams"]
    return [{"team_code": t["shortName"], "team_slug": t["slug"],
             "city": t.get("cityName", ""), "division": t.get("division", "")}
            for t in teams]


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
    for grp in ("forwards", "defensemen", "goalies"):
        for p in data.get(grp, []):
            nm = f"{p['firstName']['default']} {p['lastName']['default']}"
            out.append({"id": str(p["id"]), "name": nm, "fold": fold(nm),
                        "pos": p.get("positionCode", ""),
                        "jersey": p.get("sweaterNumber", "")})
    return out


def df_first_unit(s, slug: str) -> list[dict] | None:
    r = s.get(DF.format(slug=slug), headers={"User-Agent": BROWSER_UA}, timeout=25)
    if r.status_code != 200:
        return None
    data = next_data(r.text)
    if not data:
        return None
    players = data["props"]["pageProps"]["combinations"]["players"]
    f1 = [p for p in players if p.get("groupIdentifier") == "f1"]
    d1 = [p for p in players if p.get("groupIdentifier") == "d1"]
    if len(f1) < 3 or len(d1) < 2:
        return None
    f1 = sorted(f1, key=lambda p: (p.get("positionRank") or 99))[:3]
    d1 = sorted(d1, key=lambda p: (p.get("positionRank") or 99))[:2]
    return [{"full_name": p["name"], "position_df": (p.get("positionIdentifier") or "").upper(),
             "group": p.get("groupIdentifier")} for p in f1 + d1]


def search_fallback(s, name: str) -> str:
    """Last-resort NHL id via the search endpoint, accent-folded exact match."""
    try:
        r = s.get(NHL_SEARCH, params={"culture": "en-us", "limit": 8, "q": name},
                  headers={"User-Agent": CONTACT_UA}, timeout=20)
        r.raise_for_status()
        for h in r.json():
            if fold(h.get("name", "")) == fold(name) and h.get("active"):
                return str(h["playerId"])
    except Exception as e:
        print(f"  search {name}: {e!r}", file=sys.stderr)
    return ""


def reg_toi_per_game(land: dict) -> float:
    if not land:
        return -1.0
    for row in (land.get("seasonTotals") or []):
        if str(row.get("season")) == CURRENT_SEASON and row.get("gameTypeId") == 2:
            toi = row.get("avgToi") or ""
            if ":" in str(toi):
                m, ss = str(toi).split(":")[:2]
                return int(m) + int(ss) / 60
    return -1.0


def landing(s, pid: str) -> dict | None:
    try:
        r = s.get(f"{NHL_API}/player/{pid}/landing",
                  headers={"User-Agent": CONTACT_UA}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def nhl_fallback_unit(s, roster: list[dict]) -> list[dict]:
    """Top-3 F + top-2 D by 2025-26 reg-season TOI/G from the NHL roster."""
    fwd, dmen = [], []
    for p in roster:
        if p["pos"] == "G":
            continue
        toi = reg_toi_per_game(landing(s, p["id"]))
        time.sleep(0.3)
        rec = {"full_name": p["name"], "position_df": p["pos"],
               "group": "nhl_fallback", "_id": p["id"], "_toi": toi}
        (dmen if p["pos"] == "D" else fwd).append(rec)
    fwd.sort(key=lambda x: x["_toi"], reverse=True)
    dmen.sort(key=lambda x: x["_toi"], reverse=True)
    unit = fwd[:3] + dmen[:2]
    for u in unit:
        u.pop("_toi", None)
    return unit


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    s = session(expire_hours=24)
    teams = get_team_list(s)
    print(f"teams: {len(teams)}")
    atomic_write_csv(RAW_DIR / "teams.csv", teams,
                     ["team_code", "team_slug", "city", "division"])

    rows = []
    pid_seq = 0
    for t in teams:
        ncode = nhl_code(t["team_code"])
        roster = nhl_roster(s, ncode)
        by_fold = {p["fold"]: p["id"] for p in roster}

        unit = df_first_unit(s, t["team_slug"])
        source = "dailyfaceoff_f1d1"
        if unit is None:
            print(f"  [{t['team_code']}] DF incomplete -> NHL TOI fallback")
            unit = nhl_fallback_unit(s, roster)
            source = "nhl_toi_fallback"
        if len(unit) != 5:
            print(f"  WARNING [{t['team_code']}] got {len(unit)} skaters (expected 5)")

        for u in unit:
            pid_seq += 1
            nhl_id = u.pop("_id", "") or by_fold.get(fold(u["full_name"]), "")
            if not nhl_id:
                nhl_id = search_fallback(s, u["full_name"])
                time.sleep(0.2)
            if not nhl_id:
                nhl_id = MANUAL_ID.get(fold(u["full_name"]), "")
            rows.append({
                "player_id": pid_seq,
                "full_name": u["full_name"],
                "position": u["position_df"],
                "group": u["group"],
                "line_slot": u["group"] + ":" + u["position_df"],
                "team_code": t["team_code"],
                "nhl_team_code": ncode,
                "team_slug": t["team_slug"],
                "team_city": t["city"],
                "nhl_player_id": nhl_id,
                "wikipedia_slug": wiki_slug_guess(u["full_name"]),
                "capwages_slug": capwages_slug(u["full_name"]),
                "roster_source": source,
                "fetch_date": fetch_date,
            })
            flag = "" if nhl_id else "  <-- NO NHL ID"
            print(f"  {t['team_code']:>3} {u['group']:>3} {u['position_df']:>2} "
                  f"{u['full_name']:<24} nhl={nhl_id}{flag}")
        time.sleep(0.3)

    atomic_write_csv(PILOT_DIR / "players.csv", rows, [
        "player_id", "full_name", "position", "group", "line_slot", "team_code",
        "nhl_team_code", "team_slug", "team_city", "nhl_player_id",
        "wikipedia_slug", "capwages_slug", "roster_source", "fetch_date",
    ])
    n_fb = sum(1 for r in rows if r["roster_source"] == "nhl_toi_fallback")
    n_noid = sum(1 for r in rows if not r["nhl_player_id"])
    print(f"\nWrote players.csv: {len(rows)} skaters "
          f"({n_fb} from NHL fallback, {n_noid} missing NHL id)")


if __name__ == "__main__":
    main()
