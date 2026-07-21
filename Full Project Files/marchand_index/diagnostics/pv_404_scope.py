"""Read-only diagnostic: measure the Wikimedia pageviews full-window 404 rate
across a sample of the 774 pool, and whether a persistent retry ladder on the
FULL window recovers the complete stored total (vs. the split-window fallback
silently truncating). No CSV writes, plain requests (no shared cache).

Usage: python diagnostics/pv_404_scope.py [N]   (default N=25)
"""
import csv
import sys
import time
from pathlib import Path

import requests

UA = "marchand-index-diag/1.0 (adam@sekoan.ca)"
PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
WS, WE = "20250418", "20260417"
MID_A, MID_B = "20251017", "20251018"
RAW = Path(__file__).resolve().parent.parent / "raw"


def pull(title, start, end, tries):
    slug = title.replace(" ", "_")
    url = f"{PV}/en.wikipedia/all-access/all-agents/{slug}/daily/{start}/{end}"
    for i, b in enumerate([0, 1, 2, 4, 8, 15, 30, 45][:tries]):
        if b:
            time.sleep(b)
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        except Exception:
            continue
        if r.status_code == 200:
            items = r.json().get("items", [])
            return sum(int(it["views"]) for it in items), len(items), i
    return None, 0, tries


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    rows = list(csv.DictReader(open(RAW / "wiki_pageviews.csv", encoding="utf-8")))
    fetchable = [r for r in rows
                 if r.get("wiki_match") != "none" and r.get("wikipedia_slug_chosen")]
    # even stride across the pool for a representative sample
    step = max(1, len(fetchable) // n)
    sample = fetchable[::step][:n]

    full_ok_first = 0     # full window 200 on first try
    full_ok_retry = 0     # full window 200 only after retries
    full_fail = 0         # full window never 200 in ladder
    recovered_by_retry = 0
    truncated_would_be = 0
    print(f"pool fetchable={len(fetchable)} sample={len(sample)} (stride {step})\n")
    print(f"{'name':<24} {'stored':>8} {'full':>8} {'try':>3} "
          f"{'h1':>7} {'h2':>7} {'split':>8} verdict")
    for r in sample:
        title = r["wikipedia_slug_chosen"].replace("_", " ")
        stored = int(float(r.get("wiki_12mo") or 0))
        full, fdays, ftry = pull(title, WS, WE, tries=8)
        if full is not None and ftry == 0:
            full_ok_first += 1
            verdict = "full-1st"
        elif full is not None:
            full_ok_retry += 1
            recovered_by_retry += 1
            verdict = f"full-retry@{ftry}"
        else:
            full_fail += 1
            verdict = "FULL-404"
        h1 = h2 = split = None
        if full is None:
            h1v, _, _ = pull(title, WS, MID_A, tries=6)
            h2v, _, _ = pull(title, MID_B, WE, tries=6)
            h1, h2 = h1v, h2v
            split = (h1 or 0) + (h2 or 0)
            if h1 is None or h2 is None:
                truncated_would_be += 1
                verdict += " TRUNC(1-half)"
            else:
                verdict += " split-ok"
        print(f"{r['full_name'][:24]:<24} {stored:>8} "
              f"{str(full):>8} {ftry:>3} "
              f"{str(h1):>7} {str(h2):>7} {str(split):>8} {verdict}")
    print(f"\nSUMMARY n={len(sample)}:")
    print(f"  full 200 first try : {full_ok_first}")
    print(f"  full 200 via retry : {full_ok_retry}")
    print(f"  full never 200     : {full_fail}")
    print(f"  of those, would truncate to 1 half : {truncated_would_be}")
    print(f"  split both-halves-ok               : {full_fail - truncated_would_be}")


if __name__ == "__main__":
    main()
