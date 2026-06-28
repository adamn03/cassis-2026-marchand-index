"""Build marchand_index/market_proxy.csv -- exogenous team market-size components.

Pre-registration sec.7 governs MarketSize_team:
  equal-weight mean of the 32-team z-scores of
    1. metro_population   (static public Census/StatCan figures)
    2. arena_attendance   (avg regular-season home attendance, latest season)
    3. team_social_followers (official team Instagram followers, instaloader)
  Graceful degradation: any component not cleanly available for ALL 32 teams
  is dropped; the surviving set is recorded per row in `components_present`.
  Metro population is the irreducible floor.

This script holds RAW component values + sources ONLY. It does NOT z-score and
does NOT compute MarketSize -- compute_oaq.py does that downstream.

$0 / local-only. metro_population + arena_attendance are static public figures
hardcoded from cited public sources (see market_proxy_sources.md). ESPN's
attendance report and the Census/StatCan tables are bot-walled or large; the
figures below were grounded against those public sources and are auditable via
the source doc. team_social_followers is a BEST-EFFORT instaloader pass that is
expected to 403 unauthenticated at $0; if it fails the column is left blank for
all teams and dropped from components_present (graceful degradation).

Run:  python fetch_market_proxy.py
Out:  market_proxy.csv  (32 rows, joins on raw/teams.csv team_code)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import atomic_write_csv  # noqa: E402

PILOT_DIR = Path(__file__).parent
TEAMS_CSV = PILOT_DIR / "raw" / "teams.csv"
OUT_CSV = PILOT_DIR / "market_proxy.csv"

FIELDNAMES = [
    "team_code",
    "team_name",
    "division",
    "metro_population",
    "arena_attendance",
    "team_ig_handle",
    "team_social_followers",
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
# COMPONENT 3: team_social_followers (BEST-EFFORT, instaloader, unauthenticated)
# Official team Instagram handles (for the audit trail + an instaloader attempt).
# --------------------------------------------------------------------------
IG_HANDLE = {
    "ANA": "anaheimducks",
    "BOS": "nhlbruins",
    "BUF": "buffalosabres",
    "CGY": "nhlflames",
    "CAR": "canes",
    "CHI": "nhlblackhawks",
    "COL": "coloradoavalanche",
    "CBJ": "bluejacketsnhl",
    "DAL": "dallasstars",
    "DET": "detroitredwings",
    "EDM": "edmontonoilers",
    "FLA": "flapanthers",
    "LA":  "lakings",
    "MIN": "minnesotawild",
    "MON": "canadiensmtl",
    "NAS": "predsnhl",
    "NJ":  "njdevils",
    "NYI": "newyorkislanders",
    "NYR": "nyrangers",
    "OTT": "senators",
    "PHI": "nhlflyers",
    "PIT": "penguins",
    "SJ":  "sanjosesharks",
    "SEA": "seattlekraken",
    "STL": "stlouisblues",
    "TB":  "tblightning",
    "TOR": "mapleleafs",
    "UTA": "utahmammoth",
    "VAN": "canucks",
    "VEG": "vegasgoldenknights",
    "WAS": "capitals",
    "WPG": "nhljets",
}


def fetch_instagram_followers(handles: dict[str, str]) -> dict[str, int]:
    """Best-effort unauthenticated instaloader pass over team IG handles.

    Expected to 403 / rate-limit at $0 with no login. Returns whatever it can;
    on any failure the team is simply absent from the result (-> blank column).
    Never raises -- this component is optional per the pre-reg.
    """
    out: dict[str, int] = {}
    try:
        import instaloader  # local import: optional dependency for this step
    except Exception as e:  # pragma: no cover
        print(f"[ig] instaloader unavailable ({e}); skipping social component.")
        return out

    try:
        L = instaloader.Instaloader(
            quiet=True,
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
        )
    except Exception as e:  # pragma: no cover
        print(f"[ig] could not init instaloader ({e}); skipping social component.")
        return out

    for code, handle in handles.items():
        try:
            prof = instaloader.Profile.from_username(L.context, handle)
            out[code] = int(prof.followers)
            print(f"[ig] {code:<3} @{handle}: {out[code]:,}")
        except Exception as e:  # 401/403/429/connection -> expected at $0
            print(f"[ig] {code:<3} @{handle}: FAILED ({type(e).__name__}); "
                  f"skipping (graceful degradation).")
            # If the very first lookup hard-blocks, bail early -- no point
            # hammering 32 handles into a 401 wall.
            if not out:
                print("[ig] first lookup blocked; abandoning social component "
                      "for all teams (expected unauthenticated at $0).")
                break
    return out


def load_team_order() -> list[dict[str, str]]:
    with TEAMS_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    teams = load_team_order()
    codes = [t["team_code"] for t in teams]

    # Integrity guards: every team must have the two floor components, and the
    # static dicts must not drift from the authoritative team list.
    missing_pop = [c for c in codes if c not in METRO_POP]
    missing_att = [c for c in codes if c not in ARENA_ATTENDANCE]
    extra_pop = [c for c in METRO_POP if c not in codes]
    if missing_pop:
        raise SystemExit(f"metro_population missing for: {missing_pop}")
    if missing_att:
        raise SystemExit(f"arena_attendance missing for: {missing_att}")
    if extra_pop:
        raise SystemExit(f"metro_population has codes not in teams.csv: {extra_pop}")
    if len(codes) != 32:
        raise SystemExit(f"expected 32 teams, teams.csv has {len(codes)}")

    # COMPONENT 3 attempt (best-effort, optional).
    ig_followers = fetch_instagram_followers(IG_HANDLE)
    social_ok = len(ig_followers) == 32  # only "present" if clean for ALL 32
    if ig_followers and not social_ok:
        print(f"[ig] only {len(ig_followers)}/32 fetched -> dropping social "
              f"component entirely (must be clean for all 32 per pre-reg).")

    rows = []
    for t in teams:
        code = t["team_code"]
        present = ["metro_population", "arena_attendance"]
        followers = ""
        if social_ok:
            followers = ig_followers[code]
            present.append("team_social_followers")

        note_bits = []
        if code in ("NYR", "NYI"):
            note_bits.append("shares New York MSA (two-team market per pre-reg)")
        if code == "NJ":
            note_bits.append("Newark is inside the New York-Newark-Jersey City "
                             "MSA; carries NY metro figure")
        if code in ("LA", "ANA"):
            note_bits.append("shares Los Angeles MSA (Anaheim in Greater LA)")
        if code == "UTA":
            note_bits.append("Utah Mammoth, relocated to Salt Lake City 2024-25")
        if code == "CAR":
            note_bits.append("plays in Raleigh, NC")
        if code == "FLA":
            note_bits.append("plays in Sunrise, FL (Miami MSA)")
        if not social_ok:
            note_bits.append("team_social_followers dropped (instaloader blocked "
                             "unauthenticated at $0)")

        rows.append({
            "team_code": code,
            "team_name": t["team_slug"].replace("-", " ").title(),
            "division": t["division"],
            "metro_population": METRO_POP[code],
            "arena_attendance": ARENA_ATTENDANCE[code],
            "team_ig_handle": IG_HANDLE[code],
            "team_social_followers": followers,
            "components_present": "|".join(present),
            "notes": "; ".join(note_bits),
        })

    atomic_write_csv(OUT_CSV, rows, FIELDNAMES)

    surviving = ["metro_population", "arena_attendance"]
    if social_ok:
        surviving.append("team_social_followers")
    print(f"\nWrote {OUT_CSV.name}: {len(rows)} rows.")
    print(f"Surviving components (clean for all 32): {'|'.join(surviving)}")
    print("metro_population: US Census 2025 MSA est. / StatCan 2021 CMA. "
          "arena_attendance: ESPN 2024-25 home avg. "
          f"team_social_followers: {'present' if social_ok else 'DROPPED (blocked)'}.")


if __name__ == "__main__":
    main()
