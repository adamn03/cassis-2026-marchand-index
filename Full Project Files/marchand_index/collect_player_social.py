"""Build a descriptive player-social snapshot from public-facing profile data.

Instagram identities are accepted only when Wikidata explicitly links the player's
canonical QID to an Instagram username (P2003).  This deliberately leaves a null
instead of guessing from a name search.  Instagram follower counts are then read
from the public web-profile response.  X fields are reserved for a future
equivalently verified collection pass and are never used by OAQ_portable.

Output: raw/player_social.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
ATTENTION = ROOT / "attention_affiliation.csv"
WIKI = RAW / "wiki_pageviews.csv"
OUT = RAW / "player_social.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MarchandIndex/1.0; public descriptive research)",
    "X-IG-App-ID": "936619743392459",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_json(url: str, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def wikidata_instagram_handles(qids: list[str]) -> dict[str, str]:
    """Return only P2003 values explicitly associated with supplied QIDs."""
    found: dict[str, str] = {}
    for start in range(0, len(qids), 80):
        values = " ".join(f"wd:{qid}" for qid in qids[start : start + 80])
        query = f"SELECT ?item ?handle WHERE {{ VALUES ?item {{ {values} }} ?item wdt:P2003 ?handle }}"
        url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query)
        try:
            payload = get_json(url, {"User-Agent": HEADERS["User-Agent"]})
        except Exception as exc:  # availability is recorded per player below
            print(f"Wikidata batch {start // 80 + 1} unavailable: {type(exc).__name__}")
            continue
        for row in payload.get("results", {}).get("bindings", []):
            qid = row["item"]["value"].rsplit("/", 1)[-1]
            found[qid] = row["handle"]["value"]
        time.sleep(0.25)
    return found


def instagram_profile(handle: str) -> tuple[int | None, str, str]:
    """Return (followers, displayed_count, status) from Instagram's public profile response."""
    url = "https://www.instagram.com/api/v1/users/web_profile_info/?username=" + urllib.parse.quote(handle)
    try:
        user = get_json(url, HEADERS).get("data", {}).get("user")
    except Exception as exc:
        return None, "", f"profile_unavailable:{type(exc).__name__}"
    if not user:
        return None, "", "profile_unavailable:empty_response"
    count = user.get("edge_followed_by", {}).get("count")
    if not isinstance(count, int):
        return None, "", "profile_unavailable:no_count"
    return count, str(count), "ok"


def main() -> None:
    attention = read_rows(ATTENTION)
    qid_by_id = {row["player_id"]: row.get("wikidata_qid", "") for row in read_rows(WIKI)}
    qids = sorted({qid_by_id.get(row["player_id"], "") for row in attention if qid_by_id.get(row["player_id"], "")})
    handles = wikidata_instagram_handles(qids)
    today = dt.date.today().isoformat()
    rows: list[dict[str, str | int]] = []

    for n, player in enumerate(attention, start=1):
        qid = qid_by_id.get(player["player_id"], "")
        handle = handles.get(qid, "")
        followers: int | None = None
        verbatim = ""
        status = "null_unverified_handle"
        source = ""
        if handle:
            followers, verbatim, status = instagram_profile(handle)
            source = "wikidata:P2003+instagram_public_profile"
            time.sleep(0.6)
        rows.append({
            "player_id": player["player_id"],
            "full_name": player["full_name"],
            "team_code": player["team_code"],
            "ig_handle": handle or "null",
            "ig_followers": followers if followers is not None else "null",
            "ig_followers_verbatim": verbatim or "null",
            "ig_precision": "exact_public_response" if followers is not None else "null",
            "ig_status": status,
            "ig_source": source or "null",
            "ig_retrieved_on": today if handle else "null",
            "x_handle": "null",
            "x_followers": "null",
            "x_followers_verbatim": "null",
            "x_precision": "null",
            "x_status": "null_uncollected",
            "x_source": "null",
            "x_retrieved_on": "null",
        })
        if n % 25 == 0:
            print(f"processed {n}/{len(attention)}")

    fields = list(rows[0])
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    n_ok = sum(row["ig_followers"] != "null" for row in rows)
    n_handles = sum(row["ig_handle"] != "null" for row in rows)
    print(f"Wrote {OUT} ({len(rows)} players; {n_handles} verified handles; {n_ok} IG counts)")


if __name__ == "__main__":
    main()
