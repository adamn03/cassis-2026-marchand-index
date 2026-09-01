"""Fetch 2025-26 cap hits for the locked player pool (players.csv) from CapWages (pre-reg §5).

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
# A51: three-season panel, matching nhl_skill.csv / nhl_onice.csv shape.
# CapWages retains full contract history, so departed players resolve for the
# seasons they actually played even though they have no 2025-26 row.
PANEL_SEASONS = ["2023-24", "2024-25", "2025-26"]
LOW, HIGH = 0.7, 20.0
MONEY = re.compile(r"[\d,]+(?:\.\d+)?")

# CapWages slugs that the deterministic candidates can't reach. Keyed by NHL
# playerId so the override is unambiguous. Two failure modes:
#
#   NICKNAME / TRANSLITERATION — CapWages slugs the name the player goes by,
#   which is not always the NHL API's legal name. It cuts both ways: our
#   "Zachary Aston-Reese" is their "zach-", our "Nick Paul" their "nicholas-",
#   our "Egor Chinakhov" their "yegor-". No rule generates these, because
#   short<->long is not a function of spelling.
#
#   SHARED NAME — the bare slug belongs to whichever player CapWages indexed
#   first; the other carries a "-1" suffix. Resolving the wrong one is worse
#   than a 404, so both members of a colliding pair are pinned by nhlId and the
#   fetcher's nhlId check backstops it.
#
# First block verified live 2026-05-27, second block 2026-08-08.
SLUG_OVERRIDE = {
    "8484210": "gabe-perreault",   # CapWages lists "Gabe", our set has "Gabriel"
    "8478427": "sebastian-aho-1",  # CAR forward; bare "sebastian-aho" = NYI dman 8480222
    # -- nickname / transliteration --
    "8479944": "zach-aston-reese",     # Zachary Aston-Reese
    "8479372": "josh-mahura",          # Joshua Mahura
    "8477384": "josh-brown",           # Joshua Brown
    "8477426": "nicholas-paul",        # Nick Paul
    "8477021": "alex-kerfoot",         # Alexander Kerfoot
    "8479423": "alexander-nylander",   # Alex Nylander
    "8474034": "pat-maroon",           # Patrick Maroon
    "8482737": "zack-bolduc",          # Zachary Bolduc
    "8481719": "maxwell-crozier",      # Max Crozier
    "8481422": "jacob-lucchini",       # Jake Lucchini
    "8485414": "benjamin-kindel",      # Ben Kindel
    "8482475": "yegor-chinakhov",      # Egor Chinakhov
    "8485702": "maxim-shabanov",       # Max Shabanov
    "8481721": "arseni-gritsyuk",      # Arseny Gritsyuk
    # -- shared name --
    "8483678": "elias-pettersson-1",   # VAN dman; bare slug = VAN forward 8480012
}

# Verified absent from CapWages entirely (not a slug problem): Dmitri Simashev
# (8483499) — 2023 1st-rounder who played in the KHL through 2024-25 and has no
# CapWages page as of 2026-08-08. Stays a genuine NULL.


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


def find_caphit(player: dict, season: str = TARGET_SEASON
                ) -> tuple[float | None, str, str]:
    """(cap_M, note, contract_type) from the contract governing `season`.

    A24: `contract_type` is the governing contract's `type` scalar (e.g.
    "Entry-Level Contract", "Standard Contract (Extension)") — the same
    contract object whose details[] row supplies capHit, so a future extension
    listed first (the Hutson case) can never mislabel the season.

    A51: the season is now a parameter. CapWages keeps a player's FULL contract
    history — a retired player's page still carries his 2023-24 and 2024-25
    rows — so the 110 players who returned "no 2025-26 detail" were not missing
    from the source at all; the parser simply only ever asked for one season.
    """
    for c in player.get("contracts", []) or []:
        for det in c.get("details", []) or []:
            if det.get("season") == season:
                ctype = str(c.get("type") or "")
                val = parse_money_to_m(det.get("capHit"))
                if val is not None:
                    return val, "", ctype
                return None, "capHit unparseable", ctype
    return None, f"no {season} detail", ""


def season_key(season: str) -> str:
    """'2023-24' -> '20232024' (the nhl_skill.csv / A22 season id)."""
    a, b = season.split("-")
    return f"{a}{int(a[:2]) * 100 + int(b)}"


def load_games_played() -> dict[tuple[str, str], float]:
    """(player_id, '2023-24') -> NHL regular-season games played that season.

    A51 BUYOUT GUARD. CapWages lists a bought-out or terminated contract's FULL
    ORIGINAL TERM, not the years it was actually honoured. Zach Parise's
    13-year Minnesota deal still shows $7,538,462 through 2024-25 even though
    he was bought out in 2021 and retired after 2023-24 — so asking for his
    2024-25 cap hit returns a real-looking $7.5M for a season he did not play.
    Gating on games played removes the whole class: a cap hit is only recorded
    for a season the player was actually in the league.
    """
    out: dict[tuple[str, str], float] = {}
    path = RAW_DIR / "nhl_skill.csv"
    if not path.exists():
        print("WARNING: nhl_skill.csv absent — buyout guard disabled",
              file=sys.stderr)
        return out
    import csv
    inv = {season_key(s): s for s in PANEL_SEASONS}
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            sea = inv.get(r.get("season", ""))
            if not sea:
                continue
            try:
                out[(r["player_id"], sea)] = float(r.get("games_played") or 0)
            except ValueError:
                out[(r["player_id"], sea)] = 0.0
    return out


def main() -> None:
    fetched_at = dt.datetime.now(dt.timezone.utc).isoformat()
    s = session(expire_hours=24)
    gp_map = load_games_played()
    rows = []
    for p in load_players():
        want_id = (p.get("nhl_player_id") or "").strip()
        cap_m, note, cw_nhlid, url, ctype = None, "", "", "", ""
        per_season: dict = {}
        from_cache = True          # only sleep for requests that hit the network
        # Try candidate slugs; accept the first whose nhlId matches (or, when we
        # have no want_id to verify against, the first with a valid 2025-26 hit).
        for slug in candidate_slugs(p["full_name"], want_id):
            url = f"https://capwages.com/players/{slug}"
            try:
                r = s.get(url, headers={"User-Agent": BROWSER_UA}, timeout=25)
                if not getattr(r, "from_cache", False):
                    from_cache = False
                if r.status_code != 200:
                    note = f"http {r.status_code}"
                    if not from_cache:
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
                    if not from_cache:
                        time.sleep(0.5)
                    continue  # wrong player (shared surname) -> try next candidate
                per_season = {sea: find_caphit(player, sea)
                              for sea in PANEL_SEASONS}
                cap_m, note, ctype = per_season[TARGET_SEASON]
                cw_nhlid = cand_id
                break
            except Exception as e:
                note = f"error {type(e).__name__}"

        id_mismatch = bool(want_id and cw_nhlid and cw_nhlid != want_id)
        got = []
        for sea in PANEL_SEASONS:
            s_cap, s_note, s_type = per_season.get(sea, (None, note, ""))
            # A51 buyout guard — see load_games_played().
            gp = gp_map.get((p["player_id"], sea))
            if gp is not None and gp <= 0 and s_cap is not None:
                s_cap, s_note, s_type = None, "did not play this season", ""
            quality = "ok"
            if s_cap is None:
                quality = "low"
            elif not (LOW <= s_cap <= HIGH):
                quality, s_note = "low", f"out of bounds {s_cap:.3f}"
            elif id_mismatch:
                quality, s_note = "low", f"nhlId mismatch cw={cw_nhlid} vs {want_id}"
            if s_cap is not None:
                got.append(sea)
            rows.append({
                "player_id": p["player_id"],
                "full_name": p["full_name"],
                "nhl_player_id": want_id,
                "capwages_nhlid": cw_nhlid,
                "cap_hit_M": "" if s_cap is None else f"{s_cap:.4f}",
                "season": sea,
                "contract_type": s_type,
                "cap_quality": quality,
                "cap_note": s_note,
                "source_url": url,
                "fetched_at": fetched_at,
            })

        print(f"{p['full_name']:<24} {TARGET_SEASON}={cap_m} "
              f"seasons_found={','.join(got) if got else 'NONE'}")
        # Politeness applies to requests we actually made. Sleeping after a
        # cache hit costs 24 min of wall clock on a full re-run and buys
        # CapWages nothing; this matches the convention already used in
        # fetch_team_outcomes.py and build_mover_list.py.
        if not from_cache:
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
