"""A19 en-Wikipedia identity repair via NHL-ID reverse lookup (P3522).

Scope (fixed by the 2026-07-03 audit, see preregistration.md A19): every row
in raw/wiki_identity_audit.csv whose verdict is bad_* OR whose wiki_match is
"none" is re-resolved by Wikidata fulltext search
`haswbstatement:"P3522=<nhl_player_id>"`; an entity is accepted only if its
P3522 claim values contain the id exactly; the slug is its enwiki sitelink.
Pageviews + the §10 daily vector are re-fetched for repaired rows only, on the
unchanged A14 fixed window. Rows verified ok_nhl_id / ok_dob are not touched.

Reads:  raw/wiki_identity_audit.csv, raw/wiki_pageviews.csv, raw/wiki_daily.csv
Writes: raw/wiki_pageviews.csv, raw/wiki_daily.csv (atomic, repaired rows only)
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (  # noqa: E402
    CONTACT_UA, RAW_DIR, atomic_write_csv, load_csv, session,
)
from fetch_wikipedia import WINDOW_END, WINDOW_START, fetch_views  # noqa: E402

WD_API = "https://www.wikidata.org/w/api.php"

PV_FIELDS = [
    "player_id", "full_name", "wikipedia_slug_tried", "wikipedia_slug_chosen",
    "wikidata_qid", "wiki_match", "wiki_12mo", "fetch_date", "window_start",
    "window_end",
]
DAILY_FIELDS = ["player_id", "full_name", "n_days", "daily_views"]


def needs_repair(audit_row: dict) -> bool:
    return (audit_row.get("verdict", "").startswith("bad_")
            or audit_row.get("wiki_match", "") == "none")


def entity_matches_nhl_id(entity: dict, nhl_id: str) -> bool:
    """Exact P3522 equality — substring/prefix hits do not count."""
    for c in entity.get("claims", {}).get("P3522", []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if v is not None and str(v) == nhl_id:
            return True
    return False


def entity_enwiki_title(entity: dict) -> str:
    return (entity.get("sitelinks", {}).get("enwiki", {}) or {}).get("title", "")


def apply_repair(pv_row: dict, qid: str, title: str, total,
                 fetch_date: str) -> dict:
    out = dict(pv_row)
    out["wikipedia_slug_chosen"] = title.replace(" ", "_")
    out["wikidata_qid"] = qid
    out["wiki_match"] = "nhl_id"
    out["wiki_12mo"] = "" if total is None else total
    out["fetch_date"] = fetch_date
    return out


def search_entities_by_nhl_id(sess, nhl_id: str) -> list[str]:
    """QIDs of Wikidata entities carrying P3522 = nhl_id (fulltext search)."""
    r = sess.get(WD_API, params={
        "action": "query", "list": "search",
        "srsearch": f'haswbstatement:"P3522={nhl_id}"',
        "srnamespace": 0, "format": "json",
    }, headers={"User-Agent": CONTACT_UA}, timeout=30)
    r.raise_for_status()
    hits = r.json().get("query", {}).get("search", [])
    return [h["title"] for h in hits if h.get("title", "").startswith("Q")]


def get_entity(sess, qid: str) -> dict:
    r = sess.get(WD_API, params={
        "action": "wbgetentities", "ids": qid,
        "props": "claims|sitelinks", "format": "json",
    }, headers={"User-Agent": CONTACT_UA}, timeout=30)
    r.raise_for_status()
    return r.json().get("entities", {}).get(qid, {})


def resolve_by_nhl_id(sess, nhl_id: str) -> tuple[str, str]:
    """Return (qid, enwiki_title). Empty strings when unresolvable."""
    if not nhl_id or not nhl_id.strip().isdigit():
        return "", ""
    for qid in search_entities_by_nhl_id(sess, nhl_id.strip())[:5]:
        time.sleep(0.3)
        ent = get_entity(sess, qid)
        if entity_matches_nhl_id(ent, nhl_id.strip()):
            return qid, entity_enwiki_title(ent)
    return "", ""


def main() -> None:
    sess = session(expire_hours=24)
    today = dt.date.today().isoformat()
    audit = load_csv(RAW_DIR / "wiki_identity_audit.csv")
    pv_rows = load_csv(RAW_DIR / "wiki_pageviews.csv")
    daily_rows = load_csv(RAW_DIR / "wiki_daily.csv")
    pv_by_id = {r["player_id"]: r for r in pv_rows}
    daily_by_id = {r["player_id"]: r for r in daily_rows}

    targets = [a for a in audit if needs_repair(a)]
    print(f"A19 repair targets: {len(targets)}")
    repaired, unresolvable = 0, 0
    for a in targets:
        pid, name, nhl_id = a["player_id"], a["full_name"], a["nhl_player_id"]
        qid, title = resolve_by_nhl_id(sess, nhl_id)
        time.sleep(0.3)
        if not qid or not title:
            why = "no entity with P3522" if not qid else f"{qid} has no enwiki sitelink"
            print(f"  {name:<24} UNRESOLVABLE ({why}) — stays wiki_match=none")
            unresolvable += 1
            continue
        total, daily = None, []
        res = fetch_views(sess, title, WINDOW_START, WINDOW_END)
        if res is not None:
            total, daily = res
        pv_by_id[pid] = apply_repair(pv_by_id[pid], qid, title, total, today)
        d = dict(daily_by_id[pid])
        d["n_days"] = len(daily)
        d["daily_views"] = "|".join(str(v) for v in daily)
        daily_by_id[pid] = d
        repaired += 1
        print(f"  {name:<24} -> {title!r} qid={qid} views={total}")
        time.sleep(0.3)

    out_pv = [pv_by_id[r["player_id"]] for r in pv_rows]
    out_daily = [daily_by_id[r["player_id"]] for r in daily_rows]
    atomic_write_csv(RAW_DIR / "wiki_pageviews.csv", out_pv, PV_FIELDS)
    atomic_write_csv(RAW_DIR / "wiki_daily.csv", out_daily, DAILY_FIELDS)
    print(f"\nRepaired {repaired}, unresolvable {unresolvable} "
          f"(of {len(targets)} targets). Re-run audit_wiki_identity.py to verify.")


if __name__ == "__main__":
    main()
