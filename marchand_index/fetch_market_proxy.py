"""Build marchand_index/market_proxy.csv -- exogenous team market-size components.

A30 (owner decision D-2) governs MarketSize_team:
  equal-weight mean of the 32-team z-scores of
    1. metro_population         (static public Census/StatCan figures)
    2. team_sub_subscribers     (team-subreddit subscriber count, Arctic Shift
                                 archive snapshot; the hockey-market intensity
                                 metro pop cannot see — J2-F1. UTA = SUM over
                                 the A22 sub set {UtahHockey, utahmammoth})
    3. attendance_pct_capacity  (announced avg home attendance / arena seating
                                 capacity — raw attendance measures arena size
                                 at sellout, J2-F8)
  The displaced §7-original pair (metro + raw attendance) stays in this CSV so
  compute_oaq.py can build the `market_z_lockedv1` audit lens; metro-only is
  the E9 sensitivity. Graceful degradation unchanged: a component not cleanly
  available for ALL 32 teams is dropped (recorded in `components_present`);
  metro population is the irreducible floor.

This script holds RAW component values + sources ONLY. It does NOT z-score and
does NOT compute MarketSize -- compute_oaq.py does that downstream.

$0 / local-only. metro_population, arena_attendance, and arena_capacity are
static public figures hardcoded from cited public sources (see
market_proxy_sources.md). team_sub_subscribers is fetched live from the Arctic
Shift subreddits endpoint (per-record `retrieved_on` snapshot vintage kept in
`sub_retrieved_on` — A30 disclosure).

Run:  python fetch_market_proxy.py
Out:  market_proxy.csv  (32 rows, joins on raw/teams.csv team_code)
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import atomic_write_csv  # noqa: E402

import requests  # noqa: E402

PILOT_DIR = Path(__file__).parent
TEAMS_CSV = PILOT_DIR / "raw" / "teams.csv"
OUT_CSV = PILOT_DIR / "market_proxy.csv"

UA = "marchand-index/0.3 (research; contact ana178@sfu.ca)"
ARCTIC_SUBS_API = "https://arctic-shift.photon-reddit.com/api/subreddits/search"
SLEEP_ARCTIC = 1.0

FIELDNAMES = [
    "team_code",
    "team_name",
    "division",
    "metro_population",
    "arena_attendance",
    "arena_capacity",
    "attendance_pct_capacity",
    "team_sub",
    "team_sub_subscribers",
    "sub_retrieved_on",
    "components_present",
    "notes",
]

# --------------------------------------------------------------------------
# COMPONENT 1: metro_population
# US teams  -> US Census Bureau MSA population estimate, July 1, 2025 (Vintage
#              2025), via en.wikipedia.org/wiki/List_of_metropolitan_statistical_areas
# CA teams  -> Statistics Canada 2021 Census, Census Metropolitan Area (CMA)
#              population, via en.wikipedia.org/wiki/List_of_census_metropolitan_
#              areas_and_agglomerations_in_Canada
# Shared markets (pre-reg sec.7): NYR + NYI share the New York metro figure;
#              LA + ANA share the Los Angeles metro figure. The New Jersey Devils
#              play in Newark, which the Census places INSIDE the
#              New York-Newark-Jersey City MSA, so NJ carries the same NY MSA
#              figure (its true home metropolitan area per the spec definition
#              "population of the team's home metropolitan area"). Documented in
#              notes + market_proxy_sources.md.
# Vintage note: US figures are 2025 estimates; CA figures are 2021 census (the
#              latest official StatCan CMA enumeration). Cross-border vintage
#              differs but each is the canonical official figure for its country;
#              downstream z-scoring is rank-relative within the 32-team set.
# --------------------------------------------------------------------------
NY_MSA = 20_112_448   # New York-Newark-Jersey City, NY-NJ MSA (2025 est.)
LA_MSA = 12_844_441   # Los Angeles-Long Beach-Anaheim, CA MSA (2025 est.)

METRO_POP = {
    "ANA": LA_MSA,        # Anaheim is in Greater LA -> shares LA MSA
    "BOS": 5_034_221,     # Boston-Cambridge-Newton, MA-NH MSA
    "BUF": 1_155_653,     # Buffalo-Cheektowaga, NY MSA
    "CGY": 1_481_806,     # Calgary CMA (2021 census)
    "CAR": 1_595_720,     # Raleigh-Cary, NC MSA (Carolina Hurricanes play in Raleigh)
    "CHI": 9_434_123,     # Chicago-Naperville-Elgin, IL-IN MSA
    "COL": 3_092_037,     # Denver-Aurora-Centennial, CO MSA
    "CBJ": 2_242_028,     # Columbus, OH MSA
    "DAL": 8_477_157,     # Dallas-Fort Worth-Arlington, TX MSA
    "DET": 4_390_913,     # Detroit-Warren-Dearborn, MI MSA
    "EDM": 1_418_118,     # Edmonton CMA (2021 census)
    "FLA": 6_391_072,     # Miami-Fort Lauderdale-West Palm Beach, FL MSA (Panthers play in Sunrise, in this MSA)
    "LA":  LA_MSA,        # Los Angeles-Long Beach-Anaheim, CA MSA
    "MIN": 3_790_295,     # Minneapolis-St. Paul-Bloomington, MN-WI MSA
    "MON": 4_291_732,     # Montreal CMA (2021 census)
    "NAS": 2_197_416,     # Nashville-Davidson-Murfreesboro-Franklin, TN MSA
    "NJ":  NY_MSA,        # Newark is inside New York-Newark-Jersey City MSA
    "NYI": NY_MSA,        # shares New York MSA
    "NYR": NY_MSA,        # shares New York MSA
    "OTT": 1_488_307,     # Ottawa-Gatineau CMA (2021 census)
    "PHI": 6_329_118,     # Philadelphia-Camden-Wilmington, PA-NJ-DE-MD MSA
    "PIT": 2_421_992,     # Pittsburgh, PA MSA
    "SJ":  1_984_473,     # San Jose-Sunnyvale-Santa Clara, CA MSA
    "SEA": 4_161_883,     # Seattle-Tacoma-Bellevue, WA MSA
    "STL": 2_814_421,     # St. Louis, MO-IL MSA
    "TB":  3_418_895,     # Tampa-St. Petersburg-Clearwater, FL MSA
    "TOR": 6_202_225,     # Toronto CMA (2021 census)
    "UTA": 1_308_377,     # Salt Lake City-Murray, UT MSA (Utah Mammoth, relocated 2024)
    "VAN": 2_642_825,     # Vancouver CMA (2021 census)
    "VEG": 2_407_226,     # Las Vegas-Henderson-North Las Vegas, NV MSA
    "WAS": 6_465_724,     # Washington-Arlington-Alexandria, DC-VA-MD-WV MSA
    "WPG": 834_678,       # Winnipeg CMA (2021 census)
}

# --------------------------------------------------------------------------
# COMPONENT 2: arena_attendance
# Average regular-season HOME attendance, 2024-25 season (most recent completed).
# Source: ESPN NHL Attendance Report, year/2025
#   https://www.espn.com/nhl/attendance/_/year/2025  ("HOME AVG" column).
# Figures are season home per-game averages. See market_proxy_sources.md.
# --------------------------------------------------------------------------
ARENA_ATTENDANCE = {
    "ANA": 16_046,
    "BOS": 17_850,
    "BUF": 16_127,
    "CGY": 18_249,
    "CAR": 18_700,
    "CHI": 19_277,
    "COL": 18_133,
    "CBJ": 17_531,
    "DAL": 18_148,
    "DET": 18_843,
    "EDM": 18_347,
    "FLA": 19_417,
    "LA":  18_204,
    "MIN": 18_790,
    "MON": 21_105,
    "NAS": 17_345,
    "NJ":  16_514,
    "NYI": 17_255,
    "NYR": 18_006,
    "OTT": 18_309,
    "PHI": 18_589,
    "PIT": 17_452,
    "SJ":  14_472,
    "SEA": 17_151,
    "STL": 18_096,
    "TB":  19_092,
    "TOR": 18_572,
    "UTA": 16_044,
    "VAN": 18_834,
    "VEG": 17_973,
    "WAS": 18_573,
    "WPG": 14_775,
}

# --------------------------------------------------------------------------
# COMPONENT 3 input: arena_capacity (hockey configuration)
# Source: en.wikipedia.org/wiki/List_of_National_Hockey_League_arenas
# (retrieved 2026-07-15; see market_proxy_sources.md).
# attendance_pct_capacity = ARENA_ATTENDANCE / ARENA_CAPACITY (A30 rule 1c).
# --------------------------------------------------------------------------
ARENA_CAPACITY = {
    "ANA": 17_174,   # Honda Center
    "BOS": 17_565,   # TD Garden
    "BUF": 19_070,   # KeyBank Center
    "CGY": 19_289,   # Scotiabank Saddledome
    "CAR": 18_547,   # Lenovo Center
    "CHI": 19_717,   # United Center
    "COL": 17_809,   # Ball Arena
    "CBJ": 18_144,   # Nationwide Arena
    "DAL": 18_532,   # American Airlines Center
    "DET": 19_515,   # Little Caesars Arena
    "EDM": 18_347,   # Rogers Place
    "FLA": 19_250,   # Amerant Bank Arena
    "LA":  18_230,   # Crypto.com Arena
    "MIN": 17_954,   # Grand Casino Arena
    "MON": 20_962,   # Bell Centre
    "NAS": 17_159,   # Bridgestone Arena
    "NJ":  16_514,   # Prudential Center
    "NYI": 17_255,   # UBS Arena
    "NYR": 18_006,   # Madison Square Garden
    "OTT": 19_347,   # Canadian Tire Centre
    "PHI": 19_538,   # Xfinity Mobile Arena
    "PIT": 18_387,   # PPG Paints Arena
    "SJ":  17_435,   # SAP Center
    "SEA": 17_151,   # Climate Pledge Arena
    "STL": 18_096,   # Enterprise Center
    "TB":  19_092,   # Benchmark International Arena
    "TOR": 18_800,   # Scotiabank Arena
    "UTA": 16_020,   # Delta Center (hockey configuration)
    "VAN": 18_910,   # Rogers Arena
    "VEG": 17_367,   # T-Mobile Arena
    "WAS": 18_573,   # Capital One Arena
    "WPG": 15_321,   # Canada Life Centre
}

# --------------------------------------------------------------------------
# COMPONENT 2: team_sub_subscribers (Arctic Shift archive snapshot — A30 1b)
# Sub map identical to fetch_reddit.TEAM_SUB. UTA additionally sums the
# pre-rename A22 sub (r/UtahHockey) — one fanbase split by the rename.
# --------------------------------------------------------------------------
TEAM_SUB = {
    "ANA": "anaheimducks", "BOS": "BostonBruins", "BUF": "sabres",
    "CGY": "CalgaryFlames", "CAR": "canes", "CHI": "hawks",
    "COL": "ColoradoAvalanche", "CBJ": "BlueJackets", "DAL": "DallasStars",
    "DET": "DetroitRedWings", "EDM": "EdmontonOilers", "FLA": "FloridaPanthers",
    "LA": "losangeleskings", "MIN": "wildhockey", "MON": "Habs",
    "NAS": "Predators", "NJ": "devils", "NYI": "NewYorkIslanders",
    "NYR": "rangers", "OTT": "OttawaSenators", "PHI": "Flyers",
    "PIT": "penguins", "SJ": "SanJoseSharks", "SEA": "SeattleKraken",
    "STL": "stlouisblues", "TB": "TampaBayLightning", "TOR": "leafs",
    "UTA": "utahmammoth", "VAN": "canucks", "VEG": "goldenknights",
    "WAS": "caps", "WPG": "winnipegjets",
}
UTA_EXTRA_SUBS = ["UtahHockey"]   # A22 rename rule — summed into UTA


def fetch_sub_record(sub: str, session: requests.Session):
    """(subscribers, retrieved_on ISO date) from Arctic Shift, exact-name match.
    Returns (None, None) on any failure."""
    for backoff in (0.0, 2.0, 5.0, 15.0):
        if backoff:
            time.sleep(backoff)
        try:
            r = session.get(ARCTIC_SUBS_API, params={"subreddit": sub},
                            headers={"User-Agent": UA}, timeout=30)
            if r.status_code != 200:
                continue
            payload = r.json().get("data") or []
            if isinstance(payload, dict):
                payload = [payload]
            for d in payload:
                if d.get("display_name", "").lower() == sub.lower():
                    n = d.get("subscribers")
                    ro = d.get("retrieved_on")
                    when = (dt.datetime.fromtimestamp(
                        ro, dt.timezone.utc).date().isoformat() if ro else "")
                    return (int(n) if isinstance(n, int) and n >= 0 else None,
                            when)
            return (None, None)   # 200 but no exact match — real miss
        except Exception:
            continue
    return (None, None)


def fetch_team_sub_subscribers(codes: list[str]):
    """{team_code: (subscribers_summed, 'date[|date]')} — A30 rule 1b."""
    sess = requests.Session()
    out: dict[str, tuple[int | None, str]] = {}
    for code in codes:
        subs_list = [TEAM_SUB[code]] + (UTA_EXTRA_SUBS if code == "UTA" else [])
        total, dates, ok = 0, [], True
        for s in subs_list:
            n, when = fetch_sub_record(s, sess)
            time.sleep(SLEEP_ARCTIC)
            if n is None:
                ok = False
                break
            total += n
            dates.append(when or "?")
        out[code] = (total if ok else None, "|".join(dates))
        print(f"[subs] {code:<3} {'+'.join(subs_list):35s} "
              f"= {out[code][0]} (retrieved {out[code][1]})")
    return out


def load_team_order() -> list[dict[str, str]]:
    with TEAMS_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    teams = load_team_order()
    codes = [t["team_code"] for t in teams]

    # Integrity guards: every team must have the static components, and the
    # static dicts must not drift from the authoritative team list.
    for name, d in (("metro_population", METRO_POP),
                    ("arena_attendance", ARENA_ATTENDANCE),
                    ("arena_capacity", ARENA_CAPACITY),
                    ("team_sub", TEAM_SUB)):
        missing = [c for c in codes if c not in d]
        extra = [c for c in d if c not in codes]
        if missing:
            raise SystemExit(f"{name} missing for: {missing}")
        if extra:
            raise SystemExit(f"{name} has codes not in teams.csv: {extra}")
    if len(codes) != 32:
        raise SystemExit(f"expected 32 teams, teams.csv has {len(codes)}")

    # COMPONENT 2: Arctic Shift subscriber snapshots (A30 rule 1b).
    sub_counts = fetch_team_sub_subscribers(codes)
    subs_ok = all(sub_counts[c][0] is not None for c in codes)
    if not subs_ok:
        bad = [c for c in codes if sub_counts[c][0] is None]
        print(f"[subs] MISSING for {bad} -> component dropped for ALL 32 "
              f"(graceful degradation; metro floor stands)")

    rows = []
    for t in teams:
        code = t["team_code"]
        att_pct = ARENA_ATTENDANCE[code] / ARENA_CAPACITY[code]
        present = ["metro_population", "attendance_pct_capacity"]
        subs_val, subs_when = sub_counts[code]
        if subs_ok:
            present.insert(1, "team_sub_subscribers")

        note_bits = []
        if code in ("NYR", "NYI"):
            note_bits.append("shares New York MSA (two-team market per pre-reg)")
        if code == "NJ":
            note_bits.append("Newark is inside the New York-Newark-Jersey City "
                             "MSA; carries NY metro figure")
        if code in ("LA", "ANA"):
            note_bits.append("shares Los Angeles MSA (Anaheim in Greater LA)")
        if code == "UTA":
            note_bits.append("Utah Mammoth, relocated to Salt Lake City "
                             "2024-25; subscribers = utahmammoth + UtahHockey "
                             "(A22 rename rule); relocation novelty disclosed")
        if code == "CAR":
            note_bits.append("plays in Raleigh, NC")
        if code == "FLA":
            note_bits.append("plays in Sunrise, FL (Miami MSA)")

        rows.append({
            "team_code": code,
            "team_name": t["team_slug"].replace("-", " ").title(),
            "division": t["division"],
            "metro_population": METRO_POP[code],
            "arena_attendance": ARENA_ATTENDANCE[code],
            "arena_capacity": ARENA_CAPACITY[code],
            "attendance_pct_capacity": f"{att_pct:.4f}",
            "team_sub": TEAM_SUB[code],
            "team_sub_subscribers": subs_val if subs_val is not None else "",
            "sub_retrieved_on": subs_when,
            "components_present": "|".join(present),
            "notes": "; ".join(note_bits),
        })

    atomic_write_csv(OUT_CSV, rows, FIELDNAMES)

    print(f"\nWrote {OUT_CSV.name}: {len(rows)} rows.")
    print("A30 primary components: metro_population"
          + ("|team_sub_subscribers" if subs_ok else " (subs DROPPED)")
          + "|attendance_pct_capacity")

    # A30 acceptance: proxy correlation matrix (Spearman) — expect the
    # metro / sub-subscribers divergence for the Canadian teams.
    try:
        import pandas as pd
        mp = pd.DataFrame(rows)
        cols = ["metro_population", "arena_attendance",
                "attendance_pct_capacity", "team_sub_subscribers"]
        num = mp[cols].apply(pd.to_numeric, errors="coerce")
        print("\nSpearman correlation matrix (A30 acceptance):")
        print(num.corr(method="spearman").round(3).to_string())
        can = ["CGY", "EDM", "MON", "OTT", "TOR", "VAN", "WPG"]
        sub_can = mp[mp["team_code"].isin(can)]
        print("\nCanadian teams (metro vs sub-subscribers):")
        print(sub_can[["team_code", "metro_population",
                       "team_sub_subscribers"]].to_string(index=False))
    except Exception as e:
        print(f"(correlation matrix skipped: {e})")


if __name__ == "__main__":
    main()
