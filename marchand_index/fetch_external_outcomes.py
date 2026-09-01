"""Map TWO independent published fan-attention outcomes onto the locked
774-player pool (pre-reg §9 external validation).

V1 (primary): most-recent published NHL/NHLPA top-selling player-jersey list.
V2 (secondary): 2024 NHL All-Star Game (Toronto, Feb 2024) fan-vote selections.

Both outcomes must be REAL published data, independent of the model inputs
(Wikipedia pageviews, Reddit, Google Trends, Instagram). No rank or vote total is
invented. Source URLs, raw lists, and overlap counts are recorded in
external_outcomes_sources.md, and any component without verifiable published data
is reported as missing / underpowered rather than fabricated.

V1 status (pre-reg §14 A3, updated A20): the NHLPA/NHL "most popular jerseys"
pages are client-rendered SPAs (the --discover probes document this). The three
official best-seller lists used here were retrieved via web search and are
hard-coded with their source URLs below: the 2025-26 NHL-PR top-10 (published
2026-04-17/18, covering exactly the A11/A14 attention window), the 2024-25
NHL-PR top-5, and the NHL.com 2023-10-10 top-10. V1a (Spearman) uses the
2025-26 ranks (A3's most-recent rule); V1b (AUC) uses union membership across
all three lists. Overlap n is reported; <10 -> underpowered.

V2 status (A33): membership = the UNION of official fan-vote selections
across 2022 (4 captains + 4 "Last Men In" winners), 2023 (final-12 fan
ballot) and 2024 (12 fan-vote adds). Winners only; roster replacements are
league-named and excluded. No season ever published per-player vote totals,
so V2 stays membership-based (asg2024_votes blank; the `asg2024_member`
column name is retained for schema stability and now carries the union —
per-season membership is in `asg_fanvote_seasons`). Only skaters can fall
in-sample; overlap >= 10 -> powered under the unchanged §9 floor.

Writes:
  marchand_index/external_outcomes.csv          774 rows

Run modes:
  python fetch_external_outcomes.py             build the CSV
  python fetch_external_outcomes.py --discover  re-run the jersey-source probes
  python fetch_external_outcomes.py --verify-asg verify the 12 ASG ids vs NHL API
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from _common import atomic_write_csv, load_players  # noqa: E402

PILOT_DIR = Path(__file__).parent
OUT_CSV = PILOT_DIR / "external_outcomes.csv"

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CONTACT_UA = "marchand-index/0.1 (research; ana178@sfu.ca)"

FIELDNAMES = ["player_id", "full_name", "nhl_player_id", "jersey_list_member",
              "jersey_rank", "asg2024_member", "asg2024_votes",
              "asg_fanvote_seasons", "match_note"]


def fold(s: str) -> str:
    """Accent-fold, drop non-alphanumerics, lowercase, collapse spaces."""
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = "".join(c if c.isalnum() or c.isspace() else " " for c in s)
    return " ".join(s.lower().split())


# ---------------------------------------------------------------------------
# V2 -- 2024 NHL All-Star Game fan vote (Toronto, Feb 3 2024).
# Source: NHL.com, "Nylander, Marner, Rielly of Maple Leafs, 4 Canucks added to
#   All-Star roster", published Jan 13 2024 (live URL verified 2026-05-27):
#   https://www.nhl.com/news/final-seven-players-added-to-2024-nhl-all-star-weekend-via-fan-vote
# Cross-checked vs. en.wikipedia.org/wiki/2024_National_Hockey_League_All-Star_Game
#   ("Fan vote" table). These 12 players (8 skaters + 4 goalies) were the ONLY
#   ones chosen by fans; the other 32 were NHL Hockey-Ops selections (NOT fan
#   vote) and are therefore NOT asg2024 members. No per-player vote totals were
#   ever published, so asg2024_votes is blank for everyone (membership-only).
# nhl_player_id verified against api-web.nhle.com (--verify-asg): all 12 match.
ASG2024_FAN_VOTE = [
    # (name, nhl_player_id, team_at_selection)
    ("Jeremy Swayman", "8480280", "BOS"),
    ("Alexandar Georgiev", "8480382", "COL"),
    ("Cale Makar", "8480069", "COL"),
    ("Leon Draisaitl", "8477934", "EDM"),
    ("Sergei Bobrovsky", "8475683", "FLA"),
    ("Mitch Marner", "8478483", "TOR"),
    ("William Nylander", "8477939", "TOR"),
    ("Morgan Rielly", "8476853", "TOR"),
    ("Brock Boeser", "8478444", "VAN"),
    ("Thatcher Demko", "8477967", "VAN"),
    ("J.T. Miller", "8476468", "VAN"),
    ("Elias Pettersson", "8480012", "VAN"),
]
ASG2024_IDS = {pid for _, pid, _ in ASG2024_FAN_VOTE}
ASG2024_FOLD = {fold(nm) for nm, _, _ in ASG2024_FAN_VOTE}

# ---------------------------------------------------------------------------
# A33: V2 membership = union of the OFFICIAL FAN-VOTE components of the
# 2022, 2023 and 2024 All-Star selections. WINNERS only — roster
# replacements (Guentzel for Zibanejad; Pavelski/Josi for MacKinnon;
# Giroux for Ovechkin) were league-named, never fan-voted, and are
# excluded. Mechanisms + >=2 independent URLs per season documented in
# external_outcomes_sources.md. Ids verified vs api-web.nhle.com
# (--verify-asg, 2026-07-18).
#
# 2022 (Vegas, Feb 5 2022): fan vote named the 4 division captains
# (Dec 11 2021 - Jan 8 2022 ballot) and the 4 "Last Men In" (Jan 14-17
# 2022 ballot, winners announced Jan 18-19 2022).
ASG2022_FAN_VOTE = [
    # (name, nhl_player_id, team_at_selection, component)
    ("Alex Ovechkin", "8471214", "WSH", "captain"),
    ("Auston Matthews", "8479318", "TOR", "captain"),
    ("Nathan MacKinnon", "8477492", "COL", "captain"),
    ("Connor McDavid", "8478402", "EDM", "captain"),
    ("Steven Stamkos", "8474564", "TBL", "last_men_in"),
    ("Nazem Kadri", "8475172", "COL", "last_men_in"),
    ("Mika Zibanejad", "8476459", "NYR", "last_men_in"),
    ("Troy Terry", "8478873", "ANA", "last_men_in"),
]
# 2023 (Sunrise, Feb 4 2023): fan ballot (Twitter/NHL.com, Jan 12-24 2023)
# named the final 3 per division (2 skaters + 1 goalie), 12 total,
# winners announced Jan 26 2023.
ASG2023_FAN_VOTE = [
    # (name, nhl_player_id, team_at_selection, division)
    ("David Pastrnak", "8477956", "BOS", "ATL"),
    ("Auston Matthews", "8479318", "TOR", "ATL"),
    ("Andrei Vasilevskiy", "8476883", "TBL", "ATL"),
    ("Artemi Panarin", "8478550", "NYR", "MET"),
    ("Adam Fox", "8479323", "NYR", "MET"),
    ("Ilya Sorokin", "8478009", "NYI", "MET"),
    ("Mikko Rantanen", "8478420", "COL", "CEN"),
    ("Nathan MacKinnon", "8477492", "COL", "CEN"),
    ("Connor Hellebuyck", "8476945", "WPG", "CEN"),
    ("Leon Draisaitl", "8477934", "EDM", "PAC"),
    ("Stuart Skinner", "8479973", "EDM", "PAC"),
    ("Bo Horvat", "8477500", "VAN", "PAC"),
]

SEASON_FAN_VOTE_IDS = {
    "2022": {pid for _, pid, _, _ in ASG2022_FAN_VOTE},
    "2023": {pid for _, pid, _, _ in ASG2023_FAN_VOTE},
    "2024": ASG2024_IDS,
}
SEASON_FAN_VOTE_FOLD = {
    "2022": {fold(nm) for nm, _, _, _ in ASG2022_FAN_VOTE},
    "2023": {fold(nm) for nm, _, _, _ in ASG2023_FAN_VOTE},
    "2024": ASG2024_FOLD,
}
ASG_FANVOTE_IDS = set().union(*SEASON_FAN_VOTE_IDS.values())
ASG_FANVOTE_FOLD = set().union(*SEASON_FAN_VOTE_FOLD.values())


# ---------------------------------------------------------------------------
# V1 -- official NHL/Fanatics top-selling player-jersey lists (pre-reg §14
# A3, updated A20). Retrieved via web search (the NHLPA/NHL pages are
# client-rendered SPAs). Three strongly-sourced official lists:
#
#  (a) 2025-26 SEASON, most recent, NHL Public Relations, released
#      2026-04-17/18 (ranking only; the NHL publishes no unit figures).
#      Identical top-10 re-reported by three independent outlets:
#      https://www.hockeyfeed.com/nhl-news/nhl-reveals-the-top-10-selling-jerseys-of-2025-26-season (2026-04-18)
#      https://thehockeynews.com/nhl/chicago-blackhawks/community/connor-bedard-has-the-nhls-highest-selling-jersey-for-2025-26 (2026-04-18)
#      https://www.nhltraderumor.com/top-selling-nhl-jersey-connor-bedard-2026/ (2026-04-19, cites NHL PR)
#  (b) 2024-25 SEASON, NHL League PR -- via Russian Machine Never
#      Breaks, 2025-10-13: https://russianmachineneverbreaks.com/2025/10/13/
#      alex-ovechkin-best-selling-jersey-nhl-shop-fanatics-2024-25-season/
#  (c) NHL.com, 2023-10-10 ("...top-selling-nhl-jerseys-since-june"):
#      https://www.nhl.com/news/bedard-hughes-marchand-top-selling-nhl-jerseys-since-june
#
# V1a (secondary, rank): Spearman uses the most-recent (2025-26) ranks below
# (A3's most-recent rule; A20 logged before the final V1 computation). This
# list covers exactly the A11/A14 attention window [2025-04-18, 2026-04-17].
# V1b (primary, membership/AUC): "appeared on an official best-selling list in
# 2023-24, 2024-25 or 2025-26" = the UNION of (a)+(b)+(c). No soft names added.

# (rank, display_name) -- most recent (2025-26); drives jersey_rank + V1a.
JERSEY_2025_26 = [
    (1, "Connor Bedard"), (2, "Alex Ovechkin"), (3, "Sidney Crosby"),
    (4, "Jack Hughes"), (5, "Connor McDavid"), (6, "Nathan MacKinnon"),
    (7, "Cale Makar"), (8, "David Pastrnak"), (9, "Auston Matthews"),
    (10, "Macklin Celebrini"),
]
# 2024-25 NHL League PR top-5 (previous most-recent; stays in the V1b union).
JERSEY_2024_25 = [
    (1, "Alex Ovechkin"), (2, "Connor Bedard"), (3, "Auston Matthews"),
    (4, "Connor McDavid"), (5, "Sidney Crosby"),
]
# NHL.com 2023-10-10 top-10 (the third verified official list).
JERSEY_2023 = [
    "Connor Bedard", "Jack Hughes", "Brad Marchand", "Sidney Crosby",
    "David Pastrnak", "Patrice Bergeron", "Alex Ovechkin", "Kirill Kaprizov",
    "Nathan MacKinnon", "Cale Makar",
]
# A37 sweep adoption (2026-07-18): 2023-24 season-through-February Fanatics
# top-5 (league-wide, Fanatics-attributed, ranked, in-season — all 5 clauses;
# ESPN 2024-03-01 + Yardbarker + HockeyFeed corroboration, see sources doc).
# Members only — jersey_rank stays 2025-26 per the A3 most-recent rule.
JERSEY_2023_24_FANATICS = [
    (1, "Connor Bedard"), (2, "Jack Hughes"), (3, "Artemi Panarin"),
    (4, "Auston Matthews"), (5, "Mika Zibanejad"),
]
# Union membership set (folded names) -> jersey_list_member + V1b AUC.
JERSEY_UNION_FOLD = ({fold(nm) for _, nm in JERSEY_2025_26}
                     | {fold(nm) for _, nm in JERSEY_2024_25}
                     | {fold(nm) for nm in JERSEY_2023}
                     | {fold(nm) for _, nm in JERSEY_2023_24_FANATICS})
JERSEY_RANK_FOLD = {fold(nm): rank for rank, nm in JERSEY_2025_26}


# ---------------------------------------------------------------------------
def discover_jersey_sources() -> None:
    """Re-run the channels probed for a published ranked jersey list and report
    each one's outcome. Establishes (reproducibly) why JERSEY_LIST is empty: no
    reachable source yields verifiable ranked names in this environment."""
    s = requests.Session()
    s.headers.update({"User-Agent": BROWSER_UA})

    def soft404(text: str) -> bool:
        low = text.lower()
        return ("page not found" in low) or low.count("404") > 3

    print("[1] Wikipedia article search for an NHL jersey-sales list")
    try:
        r = s.get("https://en.wikipedia.org/w/api.php", timeout=30, params={
            "action": "query", "list": "search", "srlimit": 8, "format": "json",
            "srsearch": "NHL best selling jerseys most popular players list season"})
        titles = [h["title"] for h in r.json()["query"]["search"]]
        print("    top hits:", titles)
        print("    -> none is a jersey-sales list (teams/franchise pages only).")
    except Exception as e:
        print("    error:", repr(e)[:160])

    print("[2] NHLPA article URLs (the league's canonical 'most popular jerseys')")
    for u in (
        "https://www.nhlpa.com/news/1-21127/the-most-popular-player-jerseys-and-products-of-the-2023-24-nhl-season",
        "https://www.nhlpa.com/news/the-most-popular-player-jerseys-and-products-of-the-2024-25-nhl-season",
    ):
        try:
            r = s.get(u, timeout=30)
            has_names = any(k in r.text for k in ("McDavid", "Ovechkin", "Crosby"))
            print(f"    {r.status_code} names_in_static_html={has_names} len={len(r.text)}")
            print(f"      {u}")
        except Exception as e:
            print("    error:", repr(e)[:120], u)
    print("    -> page is a client-rendered Sanity-CMS SPA; the ranked list is")
    print("       NOT in the static HTML and no public Sanity API was found.")

    print("[3] NHL.com guessed article slugs")
    for u in (
        "https://www.nhl.com/news/nhl-best-selling-jerseys-2024-25-season",
        "https://www.nhl.com/news/nhl-fanatics-best-selling-jerseys-2024-25-season",
    ):
        try:
            r = s.get(u, timeout=30)
            print(f"    {r.status_code} soft404={soft404(r.text)}  {u}")
        except Exception as e:
            print("    error:", repr(e)[:120], u)
    print("    -> all soft-404 shells (no real article at the guessed slugs).")

    print("[4] NHL.com forge content API (stories) -- search/tag filters")
    try:
        base = "https://forge-dapi.d3.nhle.com/v2/content/en-us/stories"
        a = s.get(base, timeout=30, params={"$searchString": "best selling jerseys", "$limit": 5})
        b = s.get(base, timeout=30, params={"$limit": 5})
        same = [i.get("slug") for i in a.json().get("items", [])][:3] == \
               [i.get("slug") for i in b.json().get("items", [])][:3]
        print(f"    search vs unfiltered return identical items: {same}")
        print("    -> the public forge API ignores search/tag filters; cannot")
        print("       locate the jersey story this way.")
    except Exception as e:
        print("    error:", repr(e)[:160])

    print("\nCONCLUSION: ranked jersey list NOT retrievable here. JERSEY_LIST left")
    print("empty; ranks were not fabricated. V1 -> DATA-NOT-RETRIEVED (see sources).")


def verify_asg_ids() -> None:
    """Verify every fan-vote player id (2022+2023+2024) vs the live NHL API."""
    s = requests.Session()
    s.headers.update({"User-Agent": CONTACT_UA})
    seen: set[str] = set()
    entries = ([(nm, pid) for nm, pid, _, _ in ASG2022_FAN_VOTE]
               + [(nm, pid) for nm, pid, _, _ in ASG2023_FAN_VOTE]
               + [(nm, pid) for nm, pid, _ in ASG2024_FAN_VOTE])
    for nm, pid in entries:
        if pid in seen:
            continue
        seen.add(pid)
        try:
            j = s.get(f"https://api-web.nhle.com/v1/player/{pid}/landing", timeout=20).json()
            api_nm = f"{j['firstName']['default']} {j['lastName']['default']}"
            ok = fold(api_nm) == fold(nm)
            print(f"  {pid} expect={nm!r:22} api={api_nm!r:22} {'OK' if ok else 'MISMATCH'}")
        except Exception as e:
            print(f"  {pid} {nm}: ERR {repr(e)[:90]}")


def build_rows() -> list[dict]:
    players = load_players()
    # A51: the pool is no longer a fixed 774 — it tracks players.csv (973 as of
    # the three-season expansion). The check now only guards against reading an
    # empty or obviously truncated pool file.
    if len(players) < 700:
        print(f"WARNING: pool looks truncated — got {len(players)} players",
              file=sys.stderr)

    rows = []
    for p in players:
        pid = p["player_id"]
        name = p["full_name"]
        nhl_id = (p.get("nhl_player_id") or "").strip()
        fn = fold(name)
        notes: list[str] = []

        # ---- V1 jersey list (pre-reg §14 A3, updated A20) ----
        # member (V1b) = appeared on an official 2023-24, 2024-25 or 2025-26
        # best-seller list; rank (V1a) = most-recent (2025-26) rank if present.
        jersey_member = 1 if fn in JERSEY_UNION_FOLD else 0
        jersey_rank: object = JERSEY_RANK_FOLD.get(fn, "")

        # ---- V2 fan-vote union 2022+2023+2024 (A33; membership only) ----
        # Column keeps its historical name `asg2024_member` for schema
        # stability downstream; since A33 it carries the three-season union.
        # NHL id decides whenever present (the pool contains namesakes, e.g.
        # two Elias Petterssons); folded name is a backup for blank-id rows only.
        if nhl_id:
            asg_member = 1 if nhl_id in ASG_FANVOTE_IDS else 0
            seasons = sorted(s for s, ids in SEASON_FAN_VOTE_IDS.items()
                             if nhl_id in ids)
        else:
            asg_member = 1 if fn in ASG_FANVOTE_FOLD else 0
            seasons = sorted(s for s, folds in SEASON_FAN_VOTE_FOLD.items()
                             if fn in folds)

        # ---- ambiguous-name note: Sebastian Aho ----
        if fn == "sebastian aho":
            notes.append(
                "Sebastian Aho disambiguation: nhl_player_id 8478427 = Carolina "
                "forward, NOT the NYI defenseman (8480222). He was a league "
                "*selection* in ASG years, never a fan-vote pick in "
                "2022/2023/2024 -> asg2024_member=0.")
            if asg_member:
                notes.append("WARN: name-matched ASG fan vote -- id check failed.")

        rows.append({
            "player_id": pid,
            "full_name": name,
            "nhl_player_id": nhl_id,
            "jersey_list_member": jersey_member,
            "jersey_rank": jersey_rank,
            "asg2024_member": asg_member,
            "asg2024_votes": "",  # no per-player totals published any year
            "asg_fanvote_seasons": ",".join(seasons),
            "match_note": " | ".join(notes),
        })
    return rows


def main() -> None:
    if "--discover" in sys.argv:
        discover_jersey_sources()
        return
    if "--verify-asg" in sys.argv:
        verify_asg_ids()
        return

    rows = build_rows()
    atomic_write_csv(OUT_CSV, rows, FIELDNAMES)
    nj = sum(r["jersey_list_member"] for r in rows)
    na = sum(r["asg2024_member"] for r in rows)
    print(f"Wrote {OUT_CSV.name}: {len(rows)} rows")
    print(f"  V1 jersey-list members in pool (union 2023-24 + 2024-25 + 2025-26): {nj}")
    print(f"  V2 fan-vote union members in pool (A33, 2022+2023+2024): {na}")
    for season in ("2022", "2023", "2024"):
        ns = sum(1 for r in rows
                 if season in r["asg_fanvote_seasons"].split(","))
        print(f"    {season}: {ns} in pool")
    if nj < 10:
        print(f"  NOTE: V1 overlap {nj} < 10 -> inconclusive/underpowered (pre-reg §9)")
    if na < 10:
        print(f"  NOTE: V2 overlap {na} < 10 -> underpowered (pre-reg §9)")
    else:
        print(f"  V2 overlap {na} >= 10 -> POWERED under the existing §9 floor (A33 rule 4)")


if __name__ == "__main__":
    main()
