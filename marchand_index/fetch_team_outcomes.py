"""V3 (pre-reg A6) — team-level outcomes for the n=32 triangulation gate.

Per A6 graceful-degradation logged 2026-05-28, V3 outcome reduced to
**team Wikipedia 12-mo pageviews only** — Reddit blanket-blocks the
/about.json endpoints at $0 (403 anti-bot challenge across all UA
strategies). Subscriber column is fetched best-effort and left blank
on failure; the V3 statistic is computed off wiki_12mo alone.

Writes marchand_index/team_outcomes.csv:
  team_code, team_full_name, subreddit, subreddit_subscribers,
  wiki_article, wiki_12mo, fetch_date
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import PILOT_DIR, atomic_write_csv  # noqa: E402

import requests  # noqa: E402

UA = "marchand-index/0.1 (research; contact ana178@sfu.ca)"
SLEEP_REDDIT = 2.0          # unauthenticated Reddit
SLEEP_WIKI = 0.2            # Wikimedia is liberal

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

# Canonical Wikipedia article titles for the 32 NHL teams. Locked here
# (deterministic, no slug-resolution heuristic) — these are the unambiguous
# team articles, all confirmed by their team_franchise Wikidata entries.
TEAM_WIKI = {
    "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
    "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes",
    "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche",
    "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers",
    "FLA": "Florida Panthers", "LA": "Los Angeles Kings",
    "MIN": "Minnesota Wild", "MON": "Montreal Canadiens",
    "NAS": "Nashville Predators", "NJ": "New Jersey Devils",
    "NYI": "New York Islanders", "NYR": "New York Rangers",
    "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins", "SJ": "San Jose Sharks",
    "SEA": "Seattle Kraken", "STL": "St. Louis Blues",
    "TB": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs",
    "UTA": "Utah Hockey Club", "VAN": "Vancouver Canucks",
    "VEG": "Vegas Golden Knights", "WAS": "Washington Capitals",
    "WPG": "Winnipeg Jets",
}

OUT_FIELDS = [
    "team_code", "team_full_name", "subreddit", "subreddit_subscribers",
    "wiki_article", "wiki_12mo", "fetch_date",
]


def fetch_subreddit_subs(sub: str, session: requests.Session) -> int | None:
    """Best-effort. Reddit blocks /about.json with 403 at $0 (see A6
    graceful degradation). Single quick attempt; returns None on failure."""
    url = f"https://www.reddit.com/r/{sub}/about.json"
    try:
        r = session.get(url, headers={"User-Agent": UA}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {})
            n = data.get("subscribers")
            if isinstance(n, int) and n > 0:
                return n
    except Exception:
        pass
    return None


def fetch_team_wiki_12mo(title: str, session: requests.Session) -> int | None:
    """Wikimedia REST pageviews-per-article, daily, summed over the most recent
    365 days available (cutoff = today − 1, matching §3.1 player wiki window).
    """
    end = dt.date.today() - dt.timedelta(days=1)
    start = end - dt.timedelta(days=364)
    # Wikimedia REST API endpoint.
    encoded = title.replace(" ", "_")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia/all-access/all-agents/{encoded}/daily/"
        f"{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}"
    )
    try:
        r = session.get(url, headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200:
            return None
        items = r.json().get("items", [])
        if not items:
            return None
        total = sum(int(it.get("views", 0)) for it in items)
        return total if total > 0 else None
    except Exception:
        return None


def main() -> None:
    fetch_date = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    sess = requests.Session()
    rows: list[dict] = []
    assert set(TEAM_SUB) == set(TEAM_WIKI), "TEAM_SUB / TEAM_WIKI key mismatch"
    teams = sorted(TEAM_SUB)
    for i, tc in enumerate(teams, 1):
        sub = TEAM_SUB[tc]
        title = TEAM_WIKI[tc]
        print(f"[{i:2d}/32] {tc:3s}  r/{sub:25s}  {title}", flush=True)
        subs = fetch_subreddit_subs(sub, sess)
        time.sleep(SLEEP_REDDIT)
        wiki = fetch_team_wiki_12mo(title, sess)
        time.sleep(SLEEP_WIKI)
        rows.append({
            "team_code": tc,
            "team_full_name": title,
            "subreddit": sub,
            "subreddit_subscribers": subs if subs is not None else "",
            "wiki_article": title,
            "wiki_12mo": wiki if wiki is not None else "",
            "fetch_date": fetch_date,
        })
        ok_sub = "ok" if subs else "NULL"
        ok_w = "ok" if wiki else "NULL"
        print(f"     subs={subs}  [{ok_sub}]   wiki12mo={wiki}  [{ok_w}]")

    out = PILOT_DIR / "team_outcomes.csv"
    atomic_write_csv(out, rows, OUT_FIELDS)
    n_subs_ok = sum(1 for r in rows if r["subreddit_subscribers"] != "")
    n_wiki_ok = sum(1 for r in rows if r["wiki_12mo"] != "")
    print(f"Wrote {out}  subs_ok={n_subs_ok}/32  wiki_ok={n_wiki_ok}/32")


if __name__ == "__main__":
    main()
