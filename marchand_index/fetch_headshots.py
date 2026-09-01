"""Fetch and inline player headshots for the dashboard tables.

WHY INLINE. The published dashboard runs under a strict content-security policy
that blocks every external host except the font CDN, so a remote
`assets.nhle.com` image URL renders as a broken box. The images therefore have
to travel inside the page. NHL's source mugs are ~165 KB each, which is far too
heavy to embed a hundred of, so each one is downscaled to a thumbnail and
re-encoded as WebP before being base64'd -- roughly a 50x reduction, and still
sharper than the 36 px it is displayed at.

WHICH PLAYERS. All of them. The page's search reaches every player in the pool,
so any of them can end up on screen; fetching only the tier examples left search
results falling back to monograms. At ~1.2 KB per thumbnail the whole pool costs
about 900 KB inlined, which is affordable. The monogram fallback is retained for
the handful with no NHL headshot on file.

Headshot URLs come from the same `player/{id}/landing` response the rest of the
pipeline already calls, so this adds no new source and reuses the on-disk HTTP
cache. The URL NHL returns is the player's CURRENT mug, which can be a later
season's photo than the analysis window -- a portrait, not a measurement.

Reads:  marchand_index/dashboard/data.json   (the pooled players)
Writes: marchand_index/dashboard/headshots.json   {player_id: "data:image/webp;base64,..."}
"""
from __future__ import annotations

import base64
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONTACT_UA, session  # noqa: E402

API = "https://api-web.nhle.com/v1"
HERE = Path(__file__).resolve().parent
DASH = HERE / "dashboard"

PX = 72             # stored size; displayed at 36 for a 2x screen
QUALITY = 80


def wanted(data: dict) -> list[dict]:
    """Every player in the pool -- search can surface any of them."""
    return list(data["players"])


def thumb(raw: bytes) -> str | None:
    """Downscale to a square WebP thumbnail and return a data URI."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:
        return None
    im.thumbnail((PX, PX), Image.LANCZOS)
    # Flatten onto the page's own surface colour: the mugs carry transparency,
    # and a white matte would ring every face on an obsidian ground.
    bg = Image.new("RGBA", im.size, (30, 30, 37, 255))
    bg.alpha_composite(im)
    buf = io.BytesIO()
    bg.convert("RGB").save(buf, "WEBP", quality=QUALITY, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    data = json.loads((DASH / "data.json").read_text(encoding="utf-8"))
    targets = wanted(data)
    print(f"{len(targets)} players in the pool")

    pl = {}
    import csv
    with (HERE / "players.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pl[int(row["player_id"])] = (row.get("nhl_player_id") or "").strip()

    s = session(expire_hours=24 * 30)   # mugs are static; cache hard
    out: dict[str, str] = {}
    n_fail = 0
    for i, p in enumerate(targets, 1):
        nid = pl.get(p["id"], "")
        if not nid.isdigit():
            n_fail += 1
            continue
        try:
            land = s.get(f"{API}/player/{nid}/landing",
                         headers={"User-Agent": CONTACT_UA}, timeout=20)
            land.raise_for_status()
            url = land.json().get("headshot")
            if not url:
                n_fail += 1
                continue
            img = s.get(url, headers={"User-Agent": CONTACT_UA}, timeout=25)
            img.raise_for_status()
            uri = thumb(img.content)
            if uri:
                out[str(p["id"])] = uri
            else:
                n_fail += 1
            if not getattr(img, "from_cache", False):
                time.sleep(0.25)
        except Exception as e:
            n_fail += 1
            print(f"  {p['name']}: {e!r}", file=sys.stderr)
        if i % 25 == 0:
            print(f"  [{i}/{len(targets)}] ok={len(out)} fail={n_fail}",
                  flush=True)

    dest = DASH / "headshots.json"
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    tmp.replace(dest)
    kb = dest.stat().st_size / 1024
    print(f"\nwrote {dest}  images={len(out)}  failed={n_fail}  {kb:.0f} KB"
          f"  ({kb / max(len(out), 1):.1f} KB each)")


if __name__ == "__main__":
    main()
