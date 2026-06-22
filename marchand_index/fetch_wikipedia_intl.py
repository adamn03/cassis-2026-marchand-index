"""Fetch multi-language Wikipedia pageviews for the 774-skater pool (A12).

Adds a SEPARATE flow component `wiki_intl_12mo` = sum of per-article pageviews
over the locked non-English hockey-market editions {sv,fi,cs,ru,de,sk,fr},
over the FIXED A11 window [2025-04-18, 2026-04-17] (hardcoded — diverges from
the en fetcher's run-time window). Each player's wikidata_qid is REUSED from
raw/wiki_pageviews.csv (A1 occupation-checked resolver); no re-resolution.

Writes:
  marchand_index/raw/wiki_intl_pageviews.csv
    player_id, full_name, wikidata_qid, editions_available, editions_fetched,
    wiki_intl_12mo, per_edition_json, window_start, window_end, fetch_date,
    intl_match
  marchand_index/raw/wiki_intl_daily.csv
    player_id, edition, n_days, daily_views
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONTACT_UA, RAW_DIR, atomic_write_csv, load_csv, session  # noqa: E402

PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
WD = "https://www.wikidata.org/w/api.php"

# A11 FIXED window, hardcoded (NOT run-time). [2025-04-18 00:00 UTC, 2026-04-18).
WINDOW_START = "20250418"
WINDOW_END = "20260417"

# Locked hockey-market edition whitelist (A12; locked before fetch).
WHITELIST = ("sv", "fi", "cs", "ru", "de", "sk", "fr")


def window_strings() -> tuple[str, str, str]:
    """Return (fixed_start, fixed_end, today_iso). Only fetch_date is dynamic."""
    return WINDOW_START, WINDOW_END, dt.date.today().isoformat()


def parse_sitelinks(entity_json: dict, qid: str) -> dict[str, str]:
    """Map whitelisted edition code -> verbatim article title for one QID.

    entity_json is a wbgetentities response. Returns {} if the QID is absent
    or has no whitelisted sitelink. Sitelink keys look like 'svwiki'; we strip
    the 'wiki' suffix to the bare code and keep only WHITELIST codes.
    """
    ent = entity_json.get("entities", {}).get(qid, {})
    sitelinks = ent.get("sitelinks", {})
    out: dict[str, str] = {}
    for site, info in sitelinks.items():
        if not site.endswith("wiki"):
            continue
        code = site[:-len("wiki")]
        if code in WHITELIST:
            out[code] = info.get("title", "")
    return {k: v for k, v in out.items() if v}


def edition_pv_url(edition: str, title: str, start: str, end: str) -> str:
    """Wikimedia REST per-article URL for a given language edition + window."""
    slug = quote(title.replace(" ", "_"), safe="")
    return f"{PV}/{edition}.wikipedia/all-access/all-agents/{slug}/daily/{start}/{end}"


def fetch_edition_views(s, edition: str, title: str, start: str,
                        end: str) -> tuple[int, list[int]] | None:
    """Return (12-mo total, daily vector) for one edition; None on 404 (skip).

    The daily vector is kept so the §10 bootstrap can resample intl signal.
    """
    url = edition_pv_url(edition, title, start, end)
    r = s.get(url, headers={"User-Agent": CONTACT_UA}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    daily = [int(it["views"]) for it in r.json().get("items", [])]
    return sum(daily), daily


def aggregate_player(sitelinks: dict[str, str], fetch_fn) -> dict:
    """Sum pageviews over whitelisted editions for one player.

    fetch_fn(edition, title) -> (total, daily) | None (None = edition skipped).
    wiki_intl_12mo is NULL (None) when no edition was successfully fetched, so
    the §4/§5 sentinel renorm drops the component for that player.
    """
    available = sorted(sitelinks.keys())
    fetched: list[str] = []
    per_edition: dict[str, int] = {}
    daily_by_edition: dict[str, list[int]] = {}
    total = 0
    for ed in available:
        res = fetch_fn(ed, sitelinks[ed])
        if res is None:
            continue
        ed_total, daily = res
        fetched.append(ed)
        per_edition[ed] = ed_total
        daily_by_edition[ed] = daily
        total += ed_total
    has = len(fetched) > 0
    return {
        "editions_available": "|".join(available),
        "editions_fetched": "|".join(fetched),
        "wiki_intl_12mo": total if has else None,
        "per_edition": per_edition,
        "daily_by_edition": daily_by_edition,
        "intl_match": "ok" if has else "none",
    }


PAGEVIEWS_FIELDS = [
    "player_id", "full_name", "wikidata_qid", "editions_available",
    "editions_fetched", "wiki_intl_12mo", "per_edition_json",
    "window_start", "window_end", "fetch_date", "intl_match",
]
DAILY_FIELDS = ["player_id", "edition", "n_days", "daily_views"]


def build_summary_row(player: dict, qid: str, agg: dict, start: str, end: str,
                      fetch_date: str) -> dict:
    val = agg["wiki_intl_12mo"]
    return {
        "player_id": player["player_id"],
        "full_name": player["full_name"],
        "wikidata_qid": qid,
        "editions_available": agg["editions_available"],
        "editions_fetched": agg["editions_fetched"],
        "wiki_intl_12mo": "" if val is None else val,
        "per_edition_json": json.dumps(agg["per_edition"], ensure_ascii=True),
        "window_start": start,
        "window_end": end,
        "fetch_date": fetch_date,
        "intl_match": agg["intl_match"],
    }


def build_daily_rows(player: dict, agg: dict) -> list[dict]:
    rows = []
    for ed, daily in agg["daily_by_edition"].items():
        rows.append({
            "player_id": player["player_id"],
            "edition": ed,
            "n_days": len(daily),
            "daily_views": "|".join(str(v) for v in daily),
        })
    return rows


def load_qids() -> list[dict]:
    """Reuse the A1-resolved wikidata_qid per player from wiki_pageviews.csv."""
    rows = load_csv(RAW_DIR / "wiki_pageviews.csv")
    out = []
    for r in rows:
        qid = (r.get("wikidata_qid") or "").strip()
        if not qid:
            continue
        out.append({"player_id": r["player_id"], "full_name": r["full_name"],
                    "wikidata_qid": qid})
    return out


def fetch_sitelinks(s, qid: str) -> dict:
    """One wbgetentities sitelinks call; returns the parsed JSON dict."""
    r = s.get(WD, params={"action": "wbgetentities", "ids": qid,
                          "props": "sitelinks", "format": "json"},
              headers={"User-Agent": CONTACT_UA}, timeout=20)
    r.raise_for_status()
    return r.json()


def main() -> None:
    start, end, fetch_date = window_strings()
    s = session(expire_hours=24)
    summary_rows = []
    daily_rows = []
    for p in load_qids():
        qid = p["wikidata_qid"]
        try:
            entity = fetch_sitelinks(s, qid)
        except Exception as e:
            print(f"  sitelinks {qid}: {e!r}", file=sys.stderr)
            entity = {"entities": {}}
        time.sleep(0.15)
        sitelinks = parse_sitelinks(entity, qid)

        def fetch_fn(edition, title):
            try:
                res = fetch_edition_views(s, edition, title, start, end)
            except Exception as e:
                print(f"  views {edition}:{title!r}: {e!r}", file=sys.stderr)
                res = None
            time.sleep(0.2)
            return res

        agg = aggregate_player(sitelinks, fetch_fn)
        print(f"{p['full_name']:<28} {agg['editions_fetched']:<20} "
              f"{agg['wiki_intl_12mo']} ({agg['intl_match']})")
        summary_rows.append(
            build_summary_row(p, qid, agg, start, end, fetch_date))
        daily_rows.extend(build_daily_rows(p, agg))

    out = RAW_DIR / "wiki_intl_pageviews.csv"
    atomic_write_csv(out, summary_rows, PAGEVIEWS_FIELDS)
    atomic_write_csv(RAW_DIR / "wiki_intl_daily.csv", daily_rows, DAILY_FIELDS)
    n_ok = sum(1 for r in summary_rows if r["intl_match"] == "ok")
    print(f"\nWrote {out} ({len(summary_rows)} rows, {n_ok} intl_match=ok)")
    print(f"Wrote {RAW_DIR / 'wiki_intl_daily.csv'} (daily vectors for bootstrap)")


if __name__ == "__main__":
    main()
