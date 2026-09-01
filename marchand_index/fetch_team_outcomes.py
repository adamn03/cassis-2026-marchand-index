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
from _common import PILOT_DIR, atomic_write_csv, load_csv  # noqa: E402

import requests  # noqa: E402

UA = "marchand-index/0.2 (research; contact ana178@sfu.ca)"
SLEEP_REDDIT = 2.0          # unauthenticated Reddit
SLEEP_WIKI = 0.2            # Wikimedia is liberal

# Fixed attention window (pre-reg A11/A29) — identical to fetch_wikipedia.py.
# A51: sourced from _common. This file was MISSED in the first A51 pass and
# still held the 365-day window while every player file had moved to 921 days,
# so the A29 aggregation check would have compared 921-day player sums against
# 365-day team totals.
from _common import WINDOW_END, WINDOW_START  # noqa: E402,F401

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"

# A51: former franchise identities that live at their OWN article rather than
# as a redirect to the current one. Only needed where a rename/relocation falls
# inside the window. See fetch_one_team for the verification note.
PREDECESSOR_ARTICLES = {"UTA": ["Arizona Coyotes", "Utah Hockey Club"]}

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
    redirects, so redirect titles carry their own legitimate series).

    Retries on 429/5xx with backoff — a silently dropped canonical series
    corrupts the redirect sum (the NYR/SEA/SJ failure mode on first run)."""
    encoded = title.replace(" ", "_")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia/all-access/all-agents/{encoded}/daily/"
        f"{WINDOW_START}/{WINDOW_END}"
    )
    # 404 is retried too: the pageviews edge intermittently 404s titles that
    # have full series (observed live 2026-07-15 — Seattle Kraken 404 then
    # 200/365-items seconds later). A title that 404s the whole ladder is
    # treated as a real null.
    for backoff in (0.0, 2.0, 5.0, 15.0):
        if backoff:
            time.sleep(backoff)
        try:
            r = session.get(url, headers={"User-Agent": UA}, timeout=30)
            if r.status_code != 200:
                continue             # 404/429/5xx — retry
            items = r.json().get("items", [])
            if not items:
                return None
            total = sum(int(it.get("views", 0)) for it in items)
            return total if total > 0 else None
        except Exception:
            continue

    # A51 multi-route reconstruction — see `robust_title_views` below.
    start = dt.datetime.strptime(WINDOW_START, "%Y%m%d").date()
    end = dt.datetime.strptime(WINDOW_END, "%Y%m%d").date()
    total, missing_days = robust_title_views(encoded, start, end, session)
    if missing_days:
        print(f"     {title}: {missing_days} day(s) unrecoverable on every "
              f"route — reporting NULL rather than a partial total",
              file=sys.stderr)
        return None
    return total or None


PV_BASE = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           "en.wikipedia/")
ACCESS_TYPES = ("desktop", "mobile-web", "mobile-app")
AGENT_TYPES = ("user", "spider", "automated")


def _pv(session, access: str, agent: str, title: str, a: dt.date, b: dt.date,
        gran: str = "daily") -> int | None:
    """One pageviews call; None on any non-200."""
    url = f"{PV_BASE}{access}/{agent}/{title}/{gran}/{a:%Y%m%d}/{b:%Y%m%d}"
    try:
        r = session.get(url, headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200:
            return None
        return sum(int(it.get("views", 0)) for it in r.json().get("items", []))
    except Exception:
        return None


def robust_title_views(title: str, start: dt.date, end: dt.date,
                       session) -> tuple[int, int]:
    """In-window total for one title, reconstructed across every available
    route. Returns (total, n_days_unrecoverable).

    WHY THIS EXISTS (A51). The Wikimedia pageviews API serves PRE-AGGREGATED
    keys, and individual keys are intermittently missing — the endpoint 404s
    even though the underlying data exists. Verified live 2026-08-08 on
    `Buffalo Sabres`: `all-access/all-agents` 404s for 2023-11 while
    `desktop/all-agents` and `mobile-web/all-agents` both return 200 for the
    identical range. Lengthening the window to 921 days made this common
    enough to wipe out four teams (BUF/WPG/WAS/CHI), each of which silently
    reported ~2% of its true total with redirect_share=1.0000.

    Routes, in order of preference — the first that yields a COMPLETE answer
    wins. None of them is an estimate; each is an exact identity over a
    different slicing of the same counter:
      1. all-access/all-agents            (the normal path)
      2. monthly granularity              (a different pre-aggregate key)
      3. agent grid: sum over the three agent classes, taking each class from
         its all-access margin, or from the sum of its three access cells
      4. recursive halving, then per-day, retrying 1-3 on each piece

    A day that fails every route is COUNTED, never guessed. The caller turns
    any non-zero count into a NULL row, because a plausible-looking partial is
    far more dangerous than a loud gap.
    """
    def agent_class_total(ag: str, a: dt.date, b: dt.date) -> int | None:
        v = _pv(session, "all-access", ag, title, a, b)
        if v is not None:
            return v
        cells = [_pv(session, acc, ag, title, a, b) for acc in ACCESS_TYPES]
        return sum(cells) if all(c is not None for c in cells) else None

    def period(a: dt.date, b: dt.date) -> tuple[int, int]:
        v = _pv(session, "all-access", "all-agents", title, a, b)
        if v is not None:
            return v, 0
        v = _pv(session, "all-access", "all-agents", title, a, b, "monthly")
        if v is not None:
            return v, 0
        parts = [agent_class_total(ag, a, b) for ag in AGENT_TYPES]
        if all(p is not None for p in parts):
            return sum(parts), 0
        if a == b:
            return 0, 1                      # single day, every route failed
        mid = a + (b - a) // 2
        t1, m1 = period(a, mid)
        t2, m2 = period(mid + dt.timedelta(days=1), b)
        return t1 + t2, m1 + m2

    return period(start, end)
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


def fetch_one_team(tc: str, sess: requests.Session, fetch_date: str,
                   with_subs: bool = True) -> dict:
    sub = TEAM_SUB[tc]
    canonical = resolve_canonical(TEAM_WIKI[tc], sess)
    time.sleep(SLEEP_WIKI)
    redirects = enumerate_redirects(canonical, sess)
    time.sleep(SLEEP_WIKI)

    # A51: a franchise that relocated inside the window may keep its former
    # identity as a SEPARATE standalone article rather than a redirect, which
    # the mechanical enumeration above cannot reach. Verified live 2026-08-08:
    # "Arizona Coyotes" does NOT redirect to "Utah Mammoth", so without this
    # the team's entire 2023-24 attention is silently dropped.
    # Titles are merged into the same dict as redirects, so any predecessor
    # that IS already a redirect cannot be double-counted.
    for extra in PREDECESSOR_ARTICLES.get(tc, []):
        if extra not in redirects and extra != canonical:
            redirects.append(extra)
            for rt in enumerate_redirects(extra, sess):
                if rt not in redirects and rt != canonical:
                    redirects.append(rt)
            time.sleep(SLEEP_WIKI)

    subs = fetch_subreddit_subs(sub, sess) if with_subs else None
    if with_subs:
        time.sleep(SLEEP_REDDIT)

    canon_views = fetch_title_views(canonical, sess)
    time.sleep(SLEEP_WIKI)
    rd_views: dict[str, int | None] = {}
    for rt in redirects:
        rd_views[rt] = fetch_title_views(rt, sess)
        time.sleep(SLEEP_WIKI)
    wiki, canon_total, share, contributing = combine_view_totals(
        canon_views, rd_views)
    return {
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
    }


def main() -> None:
    fetch_date = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sess = requests.Session()
    rows: list[dict] = []
    assert set(TEAM_SUB) == set(TEAM_WIKI), "TEAM_SUB / TEAM_WIKI key mismatch"
    # `--teams CHI,WPG` repairs specific rows in place (see merge below).
    only = [t for t in " ".join(sys.argv[1:]).replace(",", " ").split()
            if t in TEAM_SUB]
    teams = only or sorted(TEAM_SUB)
    for i, tc in enumerate(teams, 1):
        row = fetch_one_team(tc, sess, fetch_date, with_subs=not only)
        rows.append(row)
        print(f"[{i:2d}/{len(teams)}] {tc:3s}  r/{row['subreddit']:25s}  "
              f"{row['wiki_article']}  wiki12mo={row['wiki_12mo']}  "
              f"redirect_share={row['redirect_share']}", flush=True)

    # Second pass: a series that 404-flaked through the whole ladder usually
    # heals within minutes — refetch those teams once (subscriber value kept
    # from the first pass).
    #
    # A51: the trigger also covers an EMPTY redirect set. Every one of the 32
    # articles has at least 7 live redirects (min observed: NSH at 7), so
    # `redirect_titles == ""` is a failure signature, never a legitimate state.
    # Without this the first A51 run left CHI/NAS/NJ/NYI/WAS/WPG at
    # redirect_share=0.0000 — a good canonical total with every redirect series
    # silently dropped, understating CHI by ~80k views (5.3%). Cause was
    # network contention from three concurrent scrapers, not a bad title: the
    # identical call succeeded on a quiet link minutes later.
    for i, row in enumerate(rows):
        if row["wiki_12mo_canonical"] == "" or row["redirect_titles"] == "":
            tc = row["team_code"]
            why = ("canonical series missing" if row["wiki_12mo_canonical"] == ""
                   else "zero redirect series recovered")
            print(f"RETRY {tc}: {why} — second pass")
            time.sleep(20)
            redo = fetch_one_team(tc, sess, fetch_date, with_subs=False)
            redo["subreddit_subscribers"] = row["subreddit_subscribers"]
            rows[i] = redo
            if redo["wiki_12mo_canonical"] == "" or redo["redirect_titles"] == "":
                print(f"     WARN {tc}: STILL incomplete after retry — row is "
                      f"suspect, do not commit without investigating")

    out = PILOT_DIR / "team_outcomes.csv"
    if only:
        # Targeted repair: merge the refetched teams into the existing file
        # rather than rewriting 32 rows from a 6-team run.
        prior = {r["team_code"]: r for r in load_csv(out)} if out.exists() else {}
        prior.update({r["team_code"]: r for r in rows})
        rows = [prior[tc] for tc in sorted(prior)]
    atomic_write_csv(out, rows, OUT_FIELDS)
    n_subs_ok = sum(1 for r in rows if r["subreddit_subscribers"] != "")
    n_wiki_ok = sum(1 for r in rows if r["wiki_12mo"] != "")
    n_rd_ok = sum(1 for r in rows if r["redirect_titles"] != "")
    print(f"Wrote {out}  subs_ok={n_subs_ok}/{len(rows)}  "
          f"wiki_ok={n_wiki_ok}/{len(rows)}  redirects_ok={n_rd_ok}/{len(rows)}")
    print("Per-team redirect share (A29 audit):")
    for r in rows:
        if float(r["redirect_share"]) > 0:
            print(f"  {r['team_code']}: {r['redirect_share']} "
                  f"({r['redirect_titles'] or '-'})")


if __name__ == "__main__":
    main()
