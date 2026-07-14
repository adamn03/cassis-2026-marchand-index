"""Fetch 2025-26 cap hits for the 160-skater set from CapWages (pre-reg §5).

cap_hit_M = the 2025-26-season cap hit in $M, read from CapWages structured
page data. CapWages embeds it in __NEXT_DATA__ at
  props.pageProps.player.contracts[i].details[j]
where details[j].season == "2025-26"; we read that row's `capHit` (NOT the
headline `aav`, which differs for front-loaded / bonus deals; NOT a future
season). A player's contracts list can hold a future deal first (e.g. McDavid's
2026-27 extension), so we scan every contract's details for the 2025-26 row.

Validation (§5): the player's CapWages `nhlId` must equal players.csv
nhl_player_id (guards against a slug resolving to the wrong player); the value
must fall in [$0.7M league-min, $20M]. Any failure -> cap_quality=low with a
note, kept in the CSV but excluded from the Marchand Index leaderboard
downstream. A 10-player random sample is hand-verified before compute.

A24: the governing contract's `type` field (the contract whose details[] holds
the 2025-26 row) is extracted as `contract_type` — the mechanical rookie-flag
key ("entry-level" substring, case-folded) that replaces the price+age proxy.

Writes: marchand_index/raw/cap_hits.csv
  player_id, full_name, nhl_player_id, capwages_nhlid, cap_hit_M, season,
  contract_type, cap_quality, cap_note, source_url, fetched_at
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import BROWSER_UA, RAW_DIR, atomic_write_csv, load_players, next_data, session  # noqa: E402

TARGET_SEASON = "2025-26"
LOW, HIGH = 0.7, 20.0
MONEY = re.compile(r"[\d,]+(?:\.\d+)?")

# CapWages slugs that the deterministic candidates can't reach (verified by
# probing the live pages 2026-05-27): a nickname and a shared-surname index.
# Keyed by NHL playerId so the override is unambiguous.
SLUG_OVERRIDE = {
    "8484210": "gabe-perreault",   # CapWages lists "Gabe", our set has "Gabriel"
    "8478427": "sebastian-aho-1",  # CAR forward; bare "sebastian-aho" = NYI dman 8480222
}


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def candidate_slugs(full_name: str, nhl_id: str) -> list[str]:
    """Ordered CapWages slug candidates: override, then accent-folded forms with
    apostrophes/periods stripped (oreilly) and turned into hyphens (o-reilly)."""
    if nhl_id in SLUG_OVERRIDE:
        return [SLUG_OVERRIDE[nhl_id]]
    base = fold(full_name).lower()
    stripped = base.replace(".", "").replace("'", "").replace("’", "")
    a = "-".join(stripped.split())
    b = "-".join(re.sub(r"[.'’]", " ", base).split())
    out = [a]
    if b != a:
        out.append(b)
    return out


def parse_money_to_m(raw) -> float | None:
    if raw is None:
        return None
    m = MONEY.search(str(raw))
    if not m:
        return None
    val = float(m.group(0).replace(",", ""))
    return val / 1_000_000 if val > 1000 else val  # "$12,500,000" -> 12.5; "12.5" -> 12.5


def find_2025_26_caphit(player: dict) -> tuple[float | None, str, str]:
    """(cap_M, note, contract_type) from the contract governing 2025-26.

    A24: `contract_type` is the governing contract's `type` scalar (e.g.
    "Entry-Level Contract", "Standard Contract (Extension)") — the same
    contract object whose details[] row supplies capHit, so a future extension
    listed first (the Hutson case) can never mislabel the season.
    """
    for c in player.get("contracts", []) or []:
        for det in c.get("details", []) or []:
            if det.get("season") == TARGET_SEASON:
                ctype = str(c.get("type") or "")
                val = parse_money_to_m(det.get("capHit"))
                if val is not None:
                    return val, "", ctype
                return None, "capHit unparseable", ctype
    return None, f"no {TARGET_SEASON} detail", ""


def main() -> None:
    fetched_at = dt.datetime.now(dt.timezone.utc).isoformat()
    s = session(expire_hours=24)
    rows = []
    for p in load_players():
        want_id = (p.get("nhl_player_id") or "").strip()
        cap_m, note, cw_nhlid, url, ctype = None, "", "", "", ""
        # Try candidate slugs; accept the first whose nhlId matches (or, when we
        # have no want_id to verify against, the first with a valid 2025-26 hit).
        for slug in candidate_slugs(p["full_name"], want_id):
            url = f"https://capwages.com/players/{slug}"
            try:
                r = s.get(url, headers={"User-Agent": BROWSER_UA}, timeout=25)
                if r.status_code != 200:
                    note = f"http {r.status_code}"
                    time.sleep(0.5)
                    continue
                data = next_data(r.text)
                player = (data or {}).get("props", {}).get("pageProps", {}).get("player", {})
                if not player:
                    note = "no player object"
                    continue
                cand_id = str(player.get("nhlId") or "")
                if want_id and cand_id and cand_id != want_id:
                    note = f"nhlId mismatch cw={cand_id} vs {want_id}"
                    time.sleep(0.5)
                    continue  # wrong player (shared surname) -> try next candidate
                cap_m, note, ctype = find_2025_26_caphit(player)
                cw_nhlid = cand_id
                break
            except Exception as e:
                note = f"error {type(e).__name__}"

        quality = "ok"
        if cap_m is None:
            quality = "low"
        elif not (LOW <= cap_m <= HIGH):
            quality, note = "low", f"out of bounds {cap_m:.3f}"
        elif want_id and cw_nhlid and cw_nhlid != want_id:
            quality, note = "low", f"nhlId mismatch cw={cw_nhlid} vs {want_id}"

        print(f"{p['full_name']:<24} cap_M={cap_m} q={quality} {note}")
        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "nhl_player_id": want_id,
            "capwages_nhlid": cw_nhlid,
            "cap_hit_M": "" if cap_m is None else f"{cap_m:.4f}",
            "season": TARGET_SEASON,
            "contract_type": ctype,
            "cap_quality": quality,
            "cap_note": note,
            "source_url": url,
            "fetched_at": fetched_at,
        })
        time.sleep(1.5)

    out = RAW_DIR / "cap_hits.csv"
    atomic_write_csv(out, rows, [
        "player_id", "full_name", "nhl_player_id", "capwages_nhlid", "cap_hit_M",
        "season", "contract_type", "cap_quality", "cap_note", "source_url",
        "fetched_at",
    ])
    n_ok = sum(1 for r in rows if r["cap_quality"] == "ok")
    n_low = sum(1 for r in rows if r["cap_quality"] == "low")
    print(f"\nWrote {out} ({len(rows)} rows; {n_ok} ok, {n_low} low)")
    if n_low:
        print("LOW rows (hand-verify / slug-fix candidates):")
        for r in rows:
            if r["cap_quality"] == "low":
                print(f"  {r['full_name']:<24} {r['cap_note']}  ({r['source_url']})")


if __name__ == "__main__":
    main()
