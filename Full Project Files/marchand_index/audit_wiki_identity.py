"""Audit en-Wikipedia identity resolution for the locked pool (QA, not a
method change).

The A1 resolver rejects non-hockey entities but cannot reject the WRONG
hockey player with the same name (e.g. a retired NHLer holding the canonical
"<Name> (ice hockey)" slug). This audit cross-checks every resolved
`wikidata_qid` against two identity signals independent of pageviews:

  1. **P3522 (NHL.com player ID)** on the Wikidata entity vs our
     `nhl_player_id` — definitive when present.
  2. **P569 (date of birth)** on the Wikidata entity vs the NHL API landing
     `birthDate` — birth-year mismatch > 1 year flags a wrong entity.

Verdicts (strongest evidence wins):
  ok_nhl_id   P3522 present and contains our nhl_player_id
  bad_nhl_id  P3522 present and does NOT contain our id  -> WRONG ENTITY
  ok_dob      no P3522; birth years within +/-1
  bad_dob     no P3522; birth years differ > 1           -> WRONG ENTITY
  unverified  no QID, or entity has neither P3522 nor P569

Reads:  players.csv, raw/wiki_pageviews.csv
Writes: raw/wiki_identity_audit.csv (all rows) + console mismatch summary.
Network: Wikidata wbgetentities (batched 50/call) + NHL landing (cached).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (  # noqa: E402
    CONTACT_UA, RAW_DIR, atomic_write_csv, load_csv, load_players, session,
)

WD_API = "https://www.wikidata.org/w/api.php"
NHL_LANDING = "https://api-web.nhle.com/v1/player/{pid}/landing"
BATCH = 50
FIELDS = [
    "player_id", "full_name", "nhl_player_id", "wikipedia_slug_chosen",
    "wikidata_qid", "wiki_match", "wd_label", "wd_nhl_id", "wd_birth",
    "nhl_birth", "verdict",
]


def fetch_entities(sess, qids: list[str]) -> dict:
    """wbgetentities for up to BATCH qids -> entities dict."""
    r = sess.get(WD_API, params={
        "action": "wbgetentities", "ids": "|".join(qids),
        "props": "claims|labels", "languages": "en", "format": "json",
    }, headers={"User-Agent": CONTACT_UA}, timeout=30)
    r.raise_for_status()
    return r.json().get("entities", {})


def claim_values(entity: dict, prop: str) -> list:
    out = []
    for c in entity.get("claims", {}).get(prop, []):
        val = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if val is not None:
            out.append(val)
    return out


def birth_year(entity: dict) -> int | None:
    for v in claim_values(entity, "P569"):
        t = v.get("time") if isinstance(v, dict) else None
        if t and len(t) >= 5:
            try:
                return int(t[1:5])
            except ValueError:
                continue
    return None


def nhl_ids_on_entity(entity: dict) -> list[str]:
    return [str(v) for v in claim_values(entity, "P3522")]


def nhl_birth_year(sess, nhl_player_id: str) -> int | None:
    if not nhl_player_id or not nhl_player_id.strip().isdigit():
        return None
    try:
        r = sess.get(NHL_LANDING.format(pid=nhl_player_id.strip()),
                     headers={"User-Agent": CONTACT_UA}, timeout=25)
        if r.status_code != 200:
            return None
        bd = r.json().get("birthDate", "")
        return int(bd[:4]) if len(bd) >= 4 else None
    except Exception:
        return None


def verdict_for(nhl_id: str, wd_nhl_ids: list[str],
                wd_by: int | None, nhl_by: int | None) -> str:
    if wd_nhl_ids:
        hit = any(nhl_id and nhl_id.strip() and nhl_id.strip() in v
                  for v in wd_nhl_ids)
        return "ok_nhl_id" if hit else "bad_nhl_id"
    if wd_by is not None and nhl_by is not None:
        return "ok_dob" if abs(wd_by - nhl_by) <= 1 else "bad_dob"
    return "unverified"


def main() -> None:
    sess = session(expire_hours=24 * 7)
    players = {p["player_id"]: p for p in load_players()}
    wiki_rows = load_csv(RAW_DIR / "wiki_pageviews.csv")

    # Batch-fetch all distinct QIDs.
    qids = sorted({r["wikidata_qid"] for r in wiki_rows
                   if r.get("wikidata_qid", "").startswith("Q")})
    entities: dict = {}
    for i in range(0, len(qids), BATCH):
        chunk = qids[i:i + BATCH]
        entities.update(fetch_entities(sess, chunk))
        print(f"wikidata batch {i // BATCH + 1}: {len(chunk)} qids")
        time.sleep(1.0)

    out_rows = []
    mismatches = []
    for r in wiki_rows:
        p = players.get(r["player_id"], {})
        nhl_id = (p.get("nhl_player_id") or "").strip()
        qid = r.get("wikidata_qid", "")
        ent = entities.get(qid, {}) if qid.startswith("Q") else {}
        wd_nhl = nhl_ids_on_entity(ent)
        wd_by = birth_year(ent)
        label = (ent.get("labels", {}).get("en", {}) or {}).get("value", "")
        nhl_by = None
        if not wd_nhl and wd_by is not None:
            # DOB path only needed when P3522 is absent.
            nhl_by = nhl_birth_year(sess, nhl_id)
            if not getattr(sess.cache, "contains", lambda **k: False)(
                    url=NHL_LANDING.format(pid=nhl_id)):
                time.sleep(0.4)
        v = verdict_for(nhl_id, wd_nhl, wd_by, nhl_by)
        row = {
            "player_id": r["player_id"],
            "full_name": r["full_name"],
            "nhl_player_id": nhl_id,
            "wikipedia_slug_chosen": r.get("wikipedia_slug_chosen", ""),
            "wikidata_qid": qid,
            "wiki_match": r.get("wiki_match", ""),
            "wd_label": label,
            "wd_nhl_id": "|".join(wd_nhl),
            "wd_birth": wd_by if wd_by is not None else "",
            "nhl_birth": nhl_by if nhl_by is not None else "",
            "verdict": v,
        }
        out_rows.append(row)
        if v in ("bad_nhl_id", "bad_dob"):
            mismatches.append(row)

    out = RAW_DIR / "wiki_identity_audit.csv"
    atomic_write_csv(out, out_rows, FIELDS)

    counts: dict[str, int] = {}
    for r in out_rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(f"\nWrote {out} ({len(out_rows)} rows)")
    print("Verdicts:", counts)
    if mismatches:
        print("\nWRONG-ENTITY candidates (fix slug + re-fetch before compute):")
        for m in mismatches:
            print(f"  {m['full_name']:<24} qid={m['wikidata_qid']} "
                  f"label={m['wd_label']!r} wd_nhl_id={m['wd_nhl_id']} "
                  f"wd_birth={m['wd_birth']} nhl_birth={m['nhl_birth']} "
                  f"slug={m['wikipedia_slug_chosen']}")
    else:
        print("\nNo wrong-entity candidates found.")


if __name__ == "__main__":
    main()
