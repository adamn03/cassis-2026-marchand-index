"""Stage-0 feasibility probe: is player-level commercial intent estimable on Google Trends?

The question behind it: attention is only "useable" if it converts into costly action.
Search volume for `"<player> jersey"` is purchase INTENT — free, no ToS risk, no
marketplace approval, and (unlike card listings) not confounded by print run.

The reason this is a probe and not a build: Google Trends quantizes to integers on a
0-100 relative scale, so low-volume terms return all zeros. The production run already
zero-quantizes **78 of 973 players on their plain name** (A35). `"<player> jersey"` is a
strict subset of that volume, so the floor should bite much harder. If it bites below the
top tier, the whole-pool-reach attack that killed Jersey Index applies here too and the
idea dies for 20 minutes of fetching instead of three hours.

Measures BOTH candidate signals on the same sample, in one pass:

  A. direct   -- payload [COMMERCIAL_ANCHOR, "<player> jersey"], mean of the weekly
                 series. NOTE the anchor is NOT the A16 entity anchor used by
                 `fetch_trends.py`. Measured 2026-08-27: "Connor McDavid jersey" scores
                 mean 25.6 (110/132 non-zero weeks) against other jersey queries but
                 mean 0.015 (2/132) against the Brad Marchand ENTITY -- 1700x apart. An
                 entity aggregates every search about a player, so scaling a long-tail
                 string against one quantizes it to zero by construction. The anchor here
                 is a fixed commercial query on the same order of magnitude as the
                 targets.
  B. related  -- `related_queries` on the player's OWN resolved entity MID, scanned for
                 commercial terms. Ordinal, not continuous, but returns a ranked list
                 even for mid-volume entities, so it may survive where A does not.
                 pytrends' related_queries has historically broken against Google API
                 changes; a None return is reported as UNAVAILABLE, not as a zero.

Sampling: stratified by `wiki_12mo` decile, `--per-decile` players each, restricted to
rows where `trends.csv` already resolved a topic MID and returned a non-null ratio, so
every probed player has a working name-level baseline to compare against. Seeded.

NOT pre-registered, NOT a validation pathway -- a go/no-go on data availability only.

Usage:
    python diagnostics/trends_commercial_intent_probe.py
    python diagnostics/trends_commercial_intent_probe.py --per-decile 2 --seed 7

Writes diagnostics/trends_commercial_intent_probe.csv and prints the verdict.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/

from _common import RAW_DIR, atomic_write_csv, load_csv  # noqa: E402
from fetch_trends import SLEEP, TIMEFRAME, TrendReq  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / "trends_commercial_intent_probe.csv"

# Terms that mark a query as commercial intent rather than curiosity.
COMMERCIAL_TERMS = ("jersey", "card", "cards", "shirt", "signed", "autograph",
                    "rookie card", "merch", "hoodie", "buy", "for sale")

SUFFIX = "jersey"
# Fixed commercial-scale anchor. Non-zero in 132/132 weeks, mean 6.8 / max 15 against
# "hockey jersey" -- stable and never itself quantized away, unlike a player entity.
COMMERCIAL_ANCHOR = "nhl jersey"

FIELDS = [
    "player_id", "full_name", "wiki_decile", "wiki_12mo", "trends_12mo_name",
    "query_mid", "direct_query", "direct_mean", "direct_nonzero_weeks",
    "direct_n_weeks", "direct_status", "related_status", "related_commercial_hits",
]


def sample_players(per_decile: int, seed: int) -> list[dict]:
    """Stratify by wiki_12mo decile; keep only players with a working Trends baseline."""
    wiki = {r["player_id"]: r for r in load_csv(RAW_DIR / "wiki_pageviews.csv")}
    trends = {r["player_id"]: r for r in load_csv(RAW_DIR / "trends.csv")}

    pool = []
    for pid, w in wiki.items():
        t = trends.get(pid)
        if not t or t.get("trends_method") != "topic":
            continue
        if not t.get("trends_12mo", "").strip() or not t.get("query_mid", "").strip():
            continue
        try:
            views = int(float(w.get("wiki_12mo") or 0))
        except ValueError:
            continue
        if views <= 0:
            continue
        pool.append({
            "player_id": pid,
            "full_name": w["full_name"],
            "wiki_12mo": views,
            "trends_12mo_name": t["trends_12mo"],
            "query_mid": t["query_mid"],
        })

    pool.sort(key=lambda r: r["wiki_12mo"])
    n = len(pool)
    print(f"eligible pool: {n} players (topic-resolved, non-null trends, wiki_12mo > 0)")

    rng = random.Random(seed)
    picked: list[dict] = []
    for d in range(10):
        lo, hi = n * d // 10, n * (d + 1) // 10
        band = pool[lo:hi]
        if not band:
            continue
        for r in rng.sample(band, min(per_decile, len(band))):
            r = dict(r)
            r["wiki_decile"] = d + 1          # 1 = least-viewed, 10 = most
            picked.append(r)
    picked.sort(key=lambda r: (r["wiki_decile"], r["full_name"]))
    return picked


def probe_direct(pytrends: TrendReq, name: str) -> dict:
    """Payload [anchor entity, "<name> jersey"]. Returns mean + zero diagnostics."""
    kw = f"{name} {SUFFIX}"
    try:
        pytrends.build_payload([COMMERCIAL_ANCHOR, kw], cat=0, timeframe=TIMEFRAME,
                               geo="")
        df = pytrends.interest_over_time()
    except Exception as exc:                                  # noqa: BLE001
        return {"direct_query": kw, "direct_mean": "", "direct_nonzero_weeks": "",
                "direct_n_weeks": "", "direct_status": f"FETCH_FAIL:{type(exc).__name__}"}

    if df is None or df.empty:
        return {"direct_query": kw, "direct_mean": "0.0", "direct_nonzero_weeks": "0",
                "direct_n_weeks": "0", "direct_status": "EMPTY"}

    if kw not in df.columns:
        # Anchor scaled but the term is absent: below Trends' reporting threshold.
        n_weeks = len(df)
        return {"direct_query": kw, "direct_mean": "0.0", "direct_nonzero_weeks": "0",
                "direct_n_weeks": str(n_weeks), "direct_status": "BELOW_THRESHOLD"}

    s = df[kw].dropna()
    nonzero = int((s > 0).sum())
    return {
        "direct_query": kw,
        "direct_mean": f"{float(s.mean()):.4f}",
        "direct_nonzero_weeks": str(nonzero),
        "direct_n_weeks": str(len(s)),
        "direct_status": "ALL_ZERO" if nonzero == 0 else "OK",
    }


def probe_related(pytrends: TrendReq, mid: str) -> dict:
    """related_queries on the player's own entity. Commercial terms in top OR rising."""
    try:
        pytrends.build_payload([mid], cat=0, timeframe=TIMEFRAME, geo="")
        rq = pytrends.related_queries()
    except Exception as exc:                                  # noqa: BLE001
        return {"related_status": f"FETCH_FAIL:{type(exc).__name__}",
                "related_commercial_hits": ""}

    entry = (rq or {}).get(mid)
    if entry is None:
        return {"related_status": "UNAVAILABLE", "related_commercial_hits": ""}

    hits: list[str] = []
    any_rows = False
    for bucket in ("top", "rising"):
        df = entry.get(bucket)
        if df is None or getattr(df, "empty", True):
            continue
        any_rows = True
        for q in df["query"].astype(str):
            low = q.lower()
            if any(term in low for term in COMMERCIAL_TERMS):
                hits.append(f"{bucket}:{q}")
    if not any_rows:
        return {"related_status": "NO_ROWS", "related_commercial_hits": ""}
    return {"related_status": "OK", "related_commercial_hits": " | ".join(hits[:8])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-decile", type=int, default=3,
                    help="players sampled per wiki_12mo decile (default 3 -> ~30)")
    ap.add_argument("--seed", type=int, default=20260826)
    ap.add_argument("--sleep", type=float, default=SLEEP)
    args = ap.parse_args()

    players = sample_players(args.per_decile, args.seed)
    print(f"probing {len(players)} players x 2 calls, {args.sleep}s apart "
          f"(~{len(players) * 2 * args.sleep / 60:.1f} min minimum)\n")

    pytrends = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=1.5,
                        timeout=(10, 30))

    rows = []
    for i, p in enumerate(players, 1):
        row = dict(p)
        row.update(probe_direct(pytrends, p["full_name"]))
        time.sleep(args.sleep)
        row.update(probe_related(pytrends, p["query_mid"]))
        time.sleep(args.sleep)
        rows.append(row)
        print(f"[{i:2d}/{len(players)}] d{row['wiki_decile']:<2} "
              f"{row['full_name'][:24]:<24} direct={row['direct_status']:<16} "
              f"mean={row['direct_mean'] or '-':>8}  related={row['related_status']}")

    atomic_write_csv(OUT_PATH, rows, FIELDS)
    print(f"\nwrote {OUT_PATH}")
    report(rows)
    return 0


def report(rows: list[dict]) -> None:
    n = len(rows)
    usable = [r for r in rows if r["direct_status"] == "OK"]
    zero = [r for r in rows if r["direct_status"] in ("ALL_ZERO", "BELOW_THRESHOLD", "EMPTY")]
    failed = [r for r in rows if r["direct_status"].startswith("FETCH_FAIL")]

    print("\n" + "=" * 72)
    print("STAGE-0 VERDICT")
    print("=" * 72)
    print(f"anchor: {COMMERCIAL_ANCHOR!r}")
    print(f"direct '<name> {SUFFIX}':  {len(usable)}/{n} usable, "
          f"{len(zero)} at/below the quantization floor, {len(failed)} fetch failures")

    print("\nby wiki_12mo decile (1 = least viewed, 10 = most):")
    print(f"  {'dec':>3}  {'n':>2}  {'usable':>6}  {'median direct_mean (usable)':>28}")
    for d in range(1, 11):
        band = [r for r in rows if r["wiki_decile"] == d]
        if not band:
            continue
        ok = [r for r in band if r["direct_status"] == "OK"]
        means = sorted(float(r["direct_mean"]) for r in ok)
        med = f"{means[len(means) // 2]:.3f}" if means else "-"
        print(f"  {d:>3}  {len(band):>2}  {len(ok):>6}  {med:>28}")

    rel_ok = [r for r in rows if r["related_status"] == "OK"]
    rel_hits = [r for r in rel_ok if r["related_commercial_hits"]]
    rel_unavail = [r for r in rows if r["related_status"] in ("UNAVAILABLE", "NO_ROWS")]
    print(f"\nrelated_queries: {len(rel_ok)}/{n} returned rows, "
          f"{len(rel_hits)} contained a commercial term, {len(rel_unavail)} unavailable")
    for r in rel_hits[:10]:
        print(f"  {r['full_name'][:24]:<24} {r['related_commercial_hits'][:80]}")

    print("\nread this as:")
    print("  - usable concentrated in deciles 9-10 only -> star-tier-only, same fatal")
    print("    whole-pool-reach problem that killed Jersey Index. STOP.")
    print("  - usable spread down to ~decile 4-5 -> direct measure is viable, proceed")
    print("    to the full 973-player fetch (~2-3h).")
    print("  - direct dead but related_queries alive with commercial hits -> fall back")
    print("    to the ordinal measure; weaker claim, but survives the floor.")


if __name__ == "__main__":
    raise SystemExit(main())
