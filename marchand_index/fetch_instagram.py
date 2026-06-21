"""Fetch public Instagram follower counts for the 160-skater set (pre-reg §3.5).

Composite weight 0.139. players.csv carries no handle column, so the handle is
auto-resolved from the player's *canonical* Wikipedia article (the slug chosen
by the §14-A1 resolver, read from raw/wiki_pageviews.csv) by scraping
instagram.com/<handle> external links. instaloader then reads the follower
count unauthenticated.

Pre-declared expectation (§3.5): Meta's anonymous block (the v1 403) will likely
recur, leaving Instagram NULL across the set; sentinel renorm (§4) then applies.
We still attempt it so the failure is recorded, not assumed.

Writes: pilot2/raw/instagram_followers.csv
  player_id, full_name, instagram_handle, instagram_followers, resolved_from,
  ig_status, fetch_date
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (CONTACT_UA, RAW_DIR, atomic_write_csv, load_csv,  # noqa: E402
                     load_players, session)

import instaloader  # noqa: E402

WIKI_HTML = "https://en.wikipedia.org/wiki/{slug}"
IG_PATTERN = re.compile(r"instagram\.com/([A-Za-z0-9._]+)", re.IGNORECASE)
NON_HANDLE = {"sharer", "share", "explore", "p", "reel", "reels", "accounts", "tv"}


def chosen_slugs() -> dict[str, str]:
    path = RAW_DIR / "wiki_pageviews.csv"
    if not path.exists():
        return {}
    return {r["player_id"]: (r.get("wikipedia_slug_chosen") or "")
            for r in load_csv(path)}


def resolve_handle(s, slug: str) -> str | None:
    if not slug:
        return None
    try:
        r = s.get(WIKI_HTML.format(slug=slug), headers={"User-Agent": CONTACT_UA}, timeout=30)
        r.raise_for_status()
        for handle in IG_PATTERN.findall(r.text):
            h = handle.strip("/").lower()
            if h not in NON_HANDLE and len(h) > 1:
                return handle.strip("/")
    except Exception as e:
        print(f"  wiki-resolve {slug}: {e!r}", file=sys.stderr)
    return None


def follower_count(L, handle: str):
    """Returns (count|None, status)."""
    try:
        prof = instaloader.Profile.from_username(L.context, handle)
        return int(prof.followers), "ok"
    except Exception as e:
        msg = type(e).__name__
        return None, f"blocked:{msg}"


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    s = session(expire_hours=24)
    slugs = chosen_slugs()
    L = instaloader.Instaloader(quiet=True, download_pictures=False,
                                download_videos=False, download_video_thumbnails=False,
                                download_geotags=False, download_comments=False,
                                save_metadata=False)
    rows = []
    for p in load_players():
        slug = slugs.get(p["player_id"]) or p["wikipedia_slug"]
        handle = resolve_handle(s, slug) or ""
        resolved_from = "wikipedia" if handle else ""
        followers, status = (None, "no_handle")
        if handle:
            followers, status = follower_count(L, handle)
            time.sleep(2.0)
        print(f"{p['full_name']:<24} ig=@{handle:<22} followers={followers} {status}")
        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "instagram_handle": handle,
            "instagram_followers": "" if followers is None else followers,
            "resolved_from": resolved_from,
            "ig_status": status,
            "fetch_date": fetch_date,
        })

    out = RAW_DIR / "instagram_followers.csv"
    atomic_write_csv(out, rows, [
        "player_id", "full_name", "instagram_handle", "instagram_followers",
        "resolved_from", "ig_status", "fetch_date",
    ])
    n_ok = sum(1 for r in rows if r["instagram_followers"] != "")
    print(f"\nWrote {out} ({len(rows)} rows, {n_ok} with follower counts)")


if __name__ == "__main__":
    main()
