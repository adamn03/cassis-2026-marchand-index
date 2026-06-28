"""Fetch public Instagram follower counts for each pilot player.

Per pre-registration section 3.5 (composite weight 0.139). Uses instaloader
in unauthenticated mode against verified public profiles.

When `instagram_handle` in players.csv is "TBD", this script attempts to
auto-resolve it by parsing the player's Wikipedia page external-links
section. If still unresolved, the field stays NULL and the player's
composite renormalizes per sentinel handling (pre-reg section 4).

Writes: pilot/raw/instagram_followers.csv with columns
  player_id, full_name, instagram_handle, instagram_followers, resolved_from, fetch_date
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_players, session  # noqa: E402

import instaloader  # noqa: E402

USER_AGENT = "marchand-index-pilot/0.1 (https://github.com/adamn03; ana178@sfu.ca)"
WIKI_HTML = "https://en.wikipedia.org/wiki/{slug}"
IG_HANDLE_PATTERN = re.compile(r"instagram\.com/([A-Za-z0-9._]+)", re.IGNORECASE)


def resolve_handle_from_wikipedia(s, slug: str) -> str | None:
    """Look for an instagram.com/<handle> link on the player's Wikipedia page."""
    url = WIKI_HTML.format(slug=slug)
    try:
        r = s.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        r.raise_for_status()
        # Find ALL hits; pick the first that isn't obviously a generic share link.
        for handle in IG_HANDLE_PATTERN.findall(r.text):
            if handle.lower() not in {"sharer", "share", "explore", "p"}:
                return handle.strip("/")
    except Exception as e:
        print(f"  wiki-resolve {slug}: {e!r}", file=sys.stderr)
    return None


def get_follower_count(L: "instaloader.Instaloader", handle: str) -> int | None:
    try:
        profile = instaloader.Profile.from_username(L.context, handle)
        return int(profile.followers)
    except Exception as e:
        print(f"  ig profile {handle}: {e!r}", file=sys.stderr)
        return None


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    s = session(expire_hours=24)
    L = instaloader.Instaloader(quiet=True, download_pictures=False,
                                download_videos=False, download_video_thumbnails=False,
                                download_geotags=False, download_comments=False,
                                save_metadata=False)
    rows = []
    players = load_players()
    for p in players:
        handle = (p["instagram_handle"] or "").strip()
        resolved_from = ""
        if handle in ("", "TBD"):
            resolved = resolve_handle_from_wikipedia(s, p["wikipedia_slug"])
            if resolved:
                handle = resolved
                resolved_from = "wikipedia"
            else:
                handle = ""

        followers = get_follower_count(L, handle) if handle else None
        print(f"{p['full_name']:<22} ig=@{handle!s:<22} followers={followers}")

        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "instagram_handle": handle,
            "instagram_followers": "" if followers is None else followers,
            "resolved_from": resolved_from,
            "fetch_date": fetch_date,
        })
        time.sleep(2.0)  # polite pacing

    out = RAW_DIR / "instagram_followers.csv"
    atomic_write_csv(out, rows, [
        "player_id", "full_name", "instagram_handle",
        "instagram_followers", "resolved_from", "fetch_date",
    ])
    print(f"\nWrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
