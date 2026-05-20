"""Fetch 2025-26 cap hits for the 14 pilot players.

Per pre-registration section 5, cap_hit_M is fetched programmatically. We
try two routes:
  1. PuckPedia per-player page (preferred — most stable HTML structure)
  2. CapWages per-player page (fallback)

This script is unauthenticated; the pages we hit are public. We record the
source URL alongside each value so reviewers can audit.

Writes: pilot/raw/cap_hits.csv with columns
  player_id, full_name, cap_hit_M, season, source_url, fetched_at
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_players, session  # noqa: E402

from bs4 import BeautifulSoup  # noqa: E402

USER_AGENT = "marchand-index-pilot/0.1 (https://github.com/adamn03; ana178@sfu.ca)"

CAP_PATTERN = re.compile(r"\$?([\d,]+(?:\.\d+)?)\s*(?:M|million|/season|/year|cap hit)",
                         re.IGNORECASE)
DOLLAR_PATTERN = re.compile(r"\$([\d,]{2,})(?!\d)")


def slugify_puckpedia(name: str) -> str:
    return name.lower().replace(".", "").replace("'", "").replace(" ", "-")


def parse_first_dollar_amount(text: str) -> float | None:
    """Try to extract a cap-hit-style dollar value from page text."""
    # Prefer explicitly-labeled "$X.XXX,XXX" near the words "cap hit" or "AAV".
    near = re.search(r"(?:cap hit|AAV|aav|cap_hit)[^$]{0,60}\$([\d,]+(?:\.\d+)?)",
                     text, re.IGNORECASE)
    if near:
        val = float(near.group(1).replace(",", ""))
        return val / 1_000_000 if val > 100_000 else val
    # Otherwise the largest dollar amount on the page is usually the cap hit.
    candidates = []
    for m in DOLLAR_PATTERN.finditer(text):
        try:
            v = float(m.group(1).replace(",", ""))
            candidates.append(v)
        except ValueError:
            continue
    if not candidates:
        return None
    big = max(candidates)
    return big / 1_000_000 if big > 100_000 else big


def fetch_puckpedia(s, name: str) -> tuple[float | None, str]:
    slug = slugify_puckpedia(name)
    url = f"https://puckpedia.com/player/{slug}"
    try:
        r = s.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        if r.status_code != 200:
            return None, url
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.get_text(" ", strip=True)
        val = parse_first_dollar_amount(text)
        return val, url
    except Exception as e:
        print(f"  puckpedia {name}: {e!r}", file=sys.stderr)
        return None, url


def fetch_capwages(s, name: str) -> tuple[float | None, str]:
    slug = name.lower().replace(".", "").replace("'", "").replace(" ", "-")
    url = f"https://capwages.com/players/{slug}"
    try:
        r = s.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        if r.status_code != 200:
            return None, url
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.get_text(" ", strip=True)
        val = parse_first_dollar_amount(text)
        return val, url
    except Exception as e:
        print(f"  capwages {name}: {e!r}", file=sys.stderr)
        return None, url


def main() -> None:
    fetched_at = dt.datetime.utcnow().isoformat() + "Z"
    s = session(expire_hours=24)
    rows = []
    players = load_players()
    for p in players:
        cap, url = fetch_puckpedia(s, p["full_name"])
        if cap is None:
            cap, url = fetch_capwages(s, p["full_name"])
        print(f"{p['full_name']:<22} cap_M={cap}  src={url}")
        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "cap_hit_M": "" if cap is None else f"{cap:.4f}",
            "season": "2025-26",
            "source_url": url,
            "fetched_at": fetched_at,
        })
        time.sleep(2.0)  # polite

    out = RAW_DIR / "cap_hits.csv"
    atomic_write_csv(out, rows, [
        "player_id", "full_name", "cap_hit_M", "season", "source_url", "fetched_at",
    ])
    print(f"\nWrote {out} ({len(rows)} rows)")
    print("Manual review note: cap_hit_M values should be in $M (e.g. 9.5 for $9.5M/yr). "
          "Sanity check a couple of well-known values (e.g. McDavid 12.5M) before trusting "
          "the parsed numbers downstream.")


if __name__ == "__main__":
    main()
