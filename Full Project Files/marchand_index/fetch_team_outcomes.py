"""V3 (pre-reg A6, repaired by A29) — team-level outcomes for the n=32
aggregation-consistency check (A29 relabel: shared-method with the wiki_en
composite component, NOT counted toward the >=3-independent-pathways claim).

A29 repairs applied here:
1. FIXED WINDOW — pageviews summed over [2025-04-18, 2026-04-17] using the
   same WINDOW_START/WINDOW_END constants as the player wiki fetchers
   (the old code used a run-anchored trailing 365 days — J1-N7).
2. REDIRECT SUM — the pageviews API does not follow redirects (the A1
   lesson). For each team the canonical title is resolved (follows any
   rename), every redirect title is enumerated via MediaWiki
   `prop=redirects`, and all non-zero in-window series are summed. Utah is
   the known in-window rename: "Utah Hockey Club" -> "Utah Mammoth"; both
   titles contribute. Per-team `redirect_share` makes any surprise rename
   visible.

Subscriber column remains best-effort/blank (Reddit 403 at $0 — A6 graceful
degradation; the A30 transport probe will revisit).

Writes marchand_index/team_outcomes.csv:
  team_code, team_full_name, subreddit, subreddit_subscribers,
  wiki_article, redirect_titles, wiki_12mo, wiki_12mo_canonical,
  redirect_share, window_start, window_end, fetch_date
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import PILOT_DIR, atomic_write_csv  # noqa: E402

import requests  # noqa: E402

UA = "marchand-index/0.2 (research; contact ana178@sfu.ca)"
SLEEP_REDDIT = 2.0          # unauthenticated Reddit
SLEEP_WIKI = 0.2            # Wikimedia is liberal

# Fixed attention window (pre-reg A11/A29) — identical to fetch_wikipedia.py.
WINDOW_START = "20250418"
WINDOW_END = "20260417"

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"

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

# Seed Wikipedia article titles for the 32 NHL teams. Each is resolved to
# its CURRENT canonical title at fetch time (A29: follows renames — Utah's
# seed intentionally stays the pre-rename title to exercise the resolver).
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
    "wiki_article", "redirect_titles", "wiki_12mo", "wiki_12mo_canonical",
    "redirect_share", "window_start", "window_end", "fetch_date",
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


def resolve_canonical(title: str, session: requests.Session) -> str:
    """Follow any redirect to the CURRENT canonical article title (A29:
    a seed title that was renamed mid-window resolves to the new name)."""
    params = {"action": "query", "titles": title, "redirects": 1,
              "format": "json", "formatversion": 2}
    try:
        r = session.get(MEDIAWIKI_API, params=params,
                        headers={"User-Agent": UA}, timeout=30)
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", [])
            if pages and pages[0].get("title"):
                return pages[0]["title"]
    except Exception:
        pass
    return title


def enumerate_redirects(canonical: str, session: requests.Session) -> list[str]:
    """All redirect titles pointing at the canonical article (mechanical,
    identity-keyed — A29 rule 2). Paginates rdcontinue."""
    titles: list[str] = []
    params = {"action": "query", "titles": canonical, "prop": "redirects",
              "rdlimit": "max", "format": "json", "formatversion": 2}
    while True:
        try:
            r = session.get(MEDIAWIKI_API, params=params,
                            headers={"User-Agent": UA}, timeout=30)
            if r.status_code != 200:
                break
            data = r.json()
            pages = data.get("query", {}).get("pages", [])
            if pages:
                titles.extend(rd["title"] for rd in pages[0].get("redirects", []))
            cont = data.get("continue")
            if not cont:
                break
            params.update(cont)
        except Exception:
            break
    return titles


def fetch_title_views(title: str, session: requests.Session) -> int | None:
    """In-window pageview total for ONE exact title (API does not follow
    redirects, so redirect titles carry their own legitimate series)."""
    encoded = title.replace(" ", "_")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia/all-access/all-agents/{encoded}/daily/"
        f"{WINDOW_START}/{WINDOW_END}"
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


def combine_view_totals(canonical_total: int | None,
                        redirect_totals: dict[str, int | None]):
    """(wiki_12mo summed, canonical_total, redirect_share, contributing titles).

    Sums the canonical series plus every NON-ZERO redirect series (A29 rule 2).
    redirect_share = redirect views / total (0.0 when total is 0/None)."""
    canon = canonical_total or 0
    contributing = {t: v for t, v in redirect_totals.items() if v}
    redirect_sum = sum(contributing.values())
    total = canon + redirect_sum
    share = (redirect_sum / total) if total > 0 else 0.0
    return (total if total > 0 else None), canonical_total, share, sorted(contributing)


def main() -> None:
    fetch_date = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sess = requests.Session()
    rows: list[dict] = []
    assert set(TEAM_SUB) == set(TEAM_WIKI), "TEAM_SUB / TEAM_WIKI key mismatch"
    teams = sorted(TEAM_SUB)
    for i, tc in enumerate(teams, 1):
        sub = TEAM_SUB[tc]
        seed_title = TEAM_WIKI[tc]
        canonical = resolve_canonical(seed_title, sess)
        time.sleep(SLEEP_WIKI)
        redirects = enumerate_redirects(canonical, sess)
        time.sleep(SLEEP_WIKI)
        print(f"[{i:2d}/32] {tc:3s}  r/{sub:25s}  {canonical} "
              f"({len(redirects)} redirects)", flush=True)

        subs = fetch_subreddit_subs(sub, sess)
        time.sleep(SLEEP_REDDIT)

        canon_views = fetch_title_views(canonical, sess)
        time.sleep(SLEEP_WIKI)
        rd_views: dict[str, int | None] = {}
        for rt in redirects:
            rd_views[rt] = fetch_title_views(rt, sess)
            time.sleep(SLEEP_WIKI)
        wiki, canon_total, share, contributing = combine_view_totals(
            canon_views, rd_views)

        rows.append({
            "team_code": tc,
            "team_full_name": canonical,
            "subreddit": sub,
            "subreddit_subscribers": subs if subs is not None else "",
            "wiki_article": canonical,
            "redirect_titles": "|".join(contributing),
            "wiki_12mo": wiki if wiki is not None else "",
            "wiki_12mo_canonical": canon_total if canon_total is not None else "",
            "redirect_share": f"{share:.4f}",
            "window_start": WINDOW_START,
            "window_end": WINDOW_END,
            "fetch_date": fetch_date,
        })
        ok_sub = "ok" if subs else "NULL"
        ok_w = "ok" if wiki else "NULL"
        print(f"     subs={subs} [{ok_sub}]  wiki12mo={wiki} [{ok_w}]  "
              f"redirect_share={share:.3f}")

    out = PILOT_DIR / "team_outcomes.csv"
    atomic_write_csv(out, rows, OUT_FIELDS)
    n_subs_ok = sum(1 for r in rows if r["subreddit_subscribers"] != "")
    n_wiki_ok = sum(1 for r in rows if r["wiki_12mo"] != "")
    print(f"Wrote {out}  subs_ok={n_subs_ok}/32  wiki_ok={n_wiki_ok}/32")
    print("Per-team redirect share (A29 audit):")
    for r in rows:
        if float(r["redirect_share"]) > 0:
            print(f"  {r['team_code']}: {r['redirect_share']} "
                  f"({r['redirect_titles'] or '-'})")


if __name__ == "__main__":
    main()
