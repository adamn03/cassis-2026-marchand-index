"""Fetch 12-month Wikipedia pageview totals for the 774-skater pool (pre-reg §3.1).

Largest engagement component (A12 composite weight 0.29 = wiki_en). Source:
Wikimedia REST API, no auth. Window = the FIXED A11/A14 interval
[2025-04-18, 2026-04-17] (regular-season-end boundary, identical for all 774),
NOT a run-time trailing window — see preregistration.md A14.

Slug resolution (pre-reg §2 as amended by §14 A1, 2026-05-27): the Wikimedia
pageviews API does NOT follow redirects and counts views to the exact title
requested, so a nickname/un-accented slug that redirects to the canonical
article (Alex_Ovechkin -> Alexander Ovechkin) badly undercounts, and a bare
ambiguous name can match the wrong entity (Marco_Rossi = a football manager).

Resolver: for each candidate title in order [stored "First_Last",
"First Last (ice hockey)"], resolve via the MediaWiki API (redirects=1) to its
canonical title and accept it only if its Wikidata entity has occupation
(P106) = ice-hockey player (Q11774891). Pageviews are summed for the accepted
canonical title. Falls back to the first non-disambiguation real title
(wiki_match=weak) or NULL (wiki_match=none).

Writes: marchand_index/raw/wiki_pageviews.csv
  player_id, full_name, wikipedia_slug_tried, wikipedia_slug_chosen,
  wikidata_qid, wiki_match, wiki_12mo, fetch_date, window_start, window_end
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONTACT_UA, RAW_DIR, atomic_write_csv, load_players, session  # noqa: E402

PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
MW = "https://en.wikipedia.org/w/api.php"
WD = "https://www.wikidata.org/w/api.php"
ICE_HOCKEY_PLAYER = "Q11774891"


# A14 FIXED window, now sourced from _common (A51). Still fixed, NOT run-time:
# the start moved back to the 2023-24 opener (2023-10-10) and the inclusive end
# day 2026-04-17 (NHL 2025-26 regular-season end) is UNCHANGED, so the A14
# regular-season-end boundary that removes the playoff-selection confound still
# holds. See preregistration.md A14 and amendment A51.
from _common import WINDOW_END, WINDOW_START  # noqa: E402,F401


def window_strings() -> tuple[str, str, str]:
    """Return (fixed_start, fixed_end, today_iso). Only fetch_date is dynamic
    (A14 — was a run-time trailing-365-day window; now the fixed A11 window)."""
    return WINDOW_START, WINDOW_END, dt.date.today().isoformat()


def resolve_page(s, title: str) -> dict:
    """Redirect-resolve a title; return canonical title, qid, disambig, missing."""
    try:
        r = s.get(MW, params={"action": "query", "titles": title, "redirects": 1,
                              "prop": "pageprops", "format": "json"},
                  headers={"User-Agent": CONTACT_UA}, timeout=20)
        r.raise_for_status()
        pg = list(r.json()["query"]["pages"].values())[0]
        pp = pg.get("pageprops", {})
        return {"final": pg.get("title", ""), "missing": "missing" in pg,
                "disambig": "disambiguation" in pp, "qid": pp.get("wikibase_item", "")}
    except Exception as e:
        print(f"  resolve {title!r}: {e!r}", file=sys.stderr)
        return {"final": "", "missing": True, "disambig": False, "qid": ""}


def is_hockey_player(s, qid: str) -> bool:
    if not qid:
        return False
    try:
        r = s.get(WD, params={"action": "wbgetentities", "ids": qid,
                              "props": "claims", "format": "json"},
                  headers={"User-Agent": CONTACT_UA}, timeout=20)
        r.raise_for_status()
        claims = r.json()["entities"][qid].get("claims", {})
        for c in claims.get("P106", []):
            if c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") == ICE_HOCKEY_PLAYER:
                return True
    except Exception as e:
        print(f"  wikidata {qid}: {e!r}", file=sys.stderr)
    return False


def choose_slug(s, full_name: str, stored: str) -> tuple[str, str, str]:
    """Return (canonical_title_or_'', wikidata_qid, match) where match in
    {'occupation','weak','none'}."""
    candidates = [stored.replace("_", " "), f"{full_name} (ice hockey)"]
    weak = None
    for cand in candidates:
        info = resolve_page(s, cand)
        time.sleep(0.15)
        if info["missing"] or info["disambig"] or not info["final"]:
            continue
        if is_hockey_player(s, info["qid"]):
            return info["final"], info["qid"], "occupation"
        time.sleep(0.15)
        if weak is None:
            weak = (info["final"], info["qid"])
    if weak:
        return weak[0], weak[1], "weak"
    return "", "", "none"


def fetch_views(s, title: str, start: str, end: str) -> tuple[int, list[int]] | None:
    """Return (12-mo total, daily-views vector). The daily vector is kept so the
    §10 bootstrap can resample it with replacement."""
    slug = quote(title.replace(" ", "_"), safe="")
    url = f"{PV}/en.wikipedia/all-access/all-agents/{slug}/daily/{start}/{end}"
    r = s.get(url, headers={"User-Agent": CONTACT_UA}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    daily = [int(it["views"]) for it in r.json().get("items", [])]
    return sum(daily), daily


def main() -> None:
    start, end, fetch_date = window_strings()
    s = session(expire_hours=24)
    rows = []
    daily_rows = []
    for p in load_players():
        stored = p["wikipedia_slug"]
        chosen, qid, match = choose_slug(s, p["full_name"], stored)
        total, daily = None, []
        if chosen:
            try:
                res = fetch_views(s, chosen, start, end)
                if res is not None:
                    total, daily = res
            except Exception as e:
                print(f"  views {chosen!r}: {e!r}", file=sys.stderr)
        flag = "" if match == "occupation" else f"  <-- {match}"
        print(f"{p['full_name']:<24} {chosen:<34} {match:<10} {total}{flag}")
        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "wikipedia_slug_tried": stored,
            "wikipedia_slug_chosen": chosen.replace(" ", "_"),
            "wikidata_qid": qid,
            "wiki_match": match,
            "wiki_12mo": "" if total is None else total,
            "fetch_date": fetch_date,
            "window_start": start,
            "window_end": end,
        })
        daily_rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "n_days": len(daily),
            "daily_views": "|".join(str(v) for v in daily),
        })
        time.sleep(0.2)

    out = RAW_DIR / "wiki_pageviews.csv"
    atomic_write_csv(out, rows, [
        "player_id", "full_name", "wikipedia_slug_tried", "wikipedia_slug_chosen",
        "wikidata_qid", "wiki_match", "wiki_12mo", "fetch_date", "window_start", "window_end",
    ])
    # Daily vectors for the §10 bootstrap (resampled with replacement per draw).
    atomic_write_csv(RAW_DIR / "wiki_daily.csv", daily_rows,
                     ["player_id", "full_name", "n_days", "daily_views"])
    n_ok = sum(1 for r in rows if r["wiki_12mo"] != "")
    n_weak = sum(1 for r in rows if r["wiki_match"] == "weak")
    n_none = sum(1 for r in rows if r["wiki_match"] == "none")
    print(f"\nWrote {out} ({len(rows)} rows, {n_ok} with pageviews, "
          f"{n_weak} weak-match, {n_none} unresolved)")
    print(f"Wrote {RAW_DIR/'wiki_daily.csv'} (daily vectors for bootstrap)")


if __name__ == "__main__":
    main()
