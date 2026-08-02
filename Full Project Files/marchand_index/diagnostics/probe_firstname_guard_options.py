"""DIAGNOSTIC (2026-08-02) — Defect 1 fix options A / B / C. READ-ONLY.

`probe_surname_collision.py` established WHICH surnames collide with another
pool player's first name (13 of them) and roughly how contaminated each is.
This probe answers the follow-up: for each of the three candidate fixes, how
many mentions does the owning player KEEP and how many does he LOSE.

Per collision surname `sn` (owner = the single pool player carrying it as a
surname), every counting-sub submission containing the token is put in exactly
one state:

  S1  every occurrence of `sn` is immediately followed by the surname of a pool
      player whose FIRST name is `sn`  ->  proven first-name usage, not the owner
  S2  >=1 standalone occurrence AND the owner's A15 first-name evidence checker
      fires                             ->  proven owner
  S3  >=1 standalone occurrence, no first-name evidence  ->  UNKNOWN

The three options differ only in what they do with S3:

  A (P3 blanket)      keep S2                     drop S1 + S3
  B (bigram only)     keep S2 + S3                drop S1
  C (bigram + sub)    keep S2 + S3-in-own-team-sub; S3-in-r/hockey -> ambiguous
  C' (C, P1-strict)   as C, but a surname already guarded by A43 prong P1 (it
                      is a common English word) gets NO own-sub allowance —
                      own-sub context cannot resolve a token whose confuser is
                      an ordinary word rather than a specific rival player.
                      This is the Logan Stanley case: bare "stanley" in
                      r/winnipegjets is overwhelmingly "Stanley Cup".

"Today" is the live behaviour: unguarded owners keep everything (`attribute()`
single-member groups always win); already-guarded owners keep S2 only.

Fidelity notes:
  * Folding, tokenisation, counting-sub membership and the evidence checker are
    imported from fetch_reddit — not reimplemented — so the states line up with
    what a real re-run would do.
  * Counting subs come from `raw/reddit_subs_searched` (already-resolved A22
    window rosters), so this probe makes NO network calls.
  * No date filter, matching scan_corpus: the corpus is already window-scoped
    by fetch_reddit_corpus.
  * `today_recomputed` vs the live `reddit_mentions_12mo` is printed as a
    self-check on the probe. Large drift means this probe is wrong, not the
    pipeline.

S1 is reported under two bigram rules to show the choice is not knife-edge:
  tight = next token is the surname of a pool player whose first name is `sn`
  loose = next token is ANY pool surname

Run from inside marchand_index/:
    python diagnostics/probe_firstname_guard_options.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import RAW_DIR, load_csv, load_players          # noqa: E402
from fetch_reddit import (ALL_SUBS, CORPUS_DIR, build_surname_map,  # noqa: E402
                          fold, load_english_top1000, make_evidence_check,
                          match_fold)


def main() -> int:
    players = load_players()
    surname_map = build_surname_map(players)

    # folded first name -> [full names], folded surname -> [full names]
    first_names: dict[str, list[str]] = {}
    surnames: dict[str, list[str]] = {}
    for p in players:
        parts = p["full_name"].split()
        if not parts:
            continue
        first_names.setdefault(fold(parts[0]), []).append(p["full_name"])
        surnames.setdefault(fold(parts[-1]), []).append(p["full_name"])
    pool_surnames = frozenset(surnames)

    # The defect class: surname unique in the pool (so `attribute()` hands it
    # over unconditionally) AND also some pool player's first name.
    collisions = sorted(sn for sn in surnames
                        if len(surnames[sn]) == 1 and sn in first_names)

    by_name = {p["full_name"]: p for p in players}
    live = {r["full_name"]: r for r in load_csv(RAW_DIR / "reddit_counts.csv")}
    en1000 = load_english_top1000()

    owners: dict[str, dict] = {}
    for sn in collisions:
        full = surnames[sn][0]
        row = live.get(full)
        if row is None:
            print(f"  WARN no reddit_counts row for {full}; skipped",
                  file=sys.stderr)
            continue
        checker, _ = make_evidence_check(full, surname_map, force=True)
        owners[sn] = {
            "full": full,
            "pid": by_name[full]["player_id"],
            "subs": set((row.get("reddit_subs_searched") or "").split("|")) - {""},
            "guarded_today": (row.get("reddit_common_word_guard") or
                              "false").lower() == "true",
            "p1": sn in en1000,
            "live_mentions": int(row.get("reddit_mentions_12mo") or 0),
            "checker": checker,
            # surnames of the pool players who carry `sn` as a FIRST name
            "fn_surnames": frozenset(fold(n.split()[-1])
                                     for n in first_names[sn]),
            "seen": set(),
            "s1": 0, "s1_loose": 0, "s2": 0, "s3_own": 0, "s3_league": 0,
        }

    print(f"pool {len(players)} | collision surnames {len(collisions)} | "
          f"owners resolved {len(owners)}")
    print("collisions:", " ".join(collisions))

    target = frozenset(owners)
    scanned = 0
    for sub in ALL_SUBS:
        path = CORPUS_DIR / f"{sub}.jsonl"
        if not path.exists():
            print(f"  WARN missing corpus file {sub}.jsonl", file=sys.stderr)
            continue
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    post = json.loads(line)
                except json.JSONDecodeError:
                    continue
                scanned += 1
                title = post.get("title") or ""
                selftext = post.get("selftext") or ""
                toks = match_fold(f"{title} {selftext}").split()
                hits = frozenset(toks) & target
                if not hits:
                    continue
                pid = post.get("id")
                for sn in hits:
                    o = owners[sn]
                    if sub not in o["subs"] or pid in o["seen"]:
                        continue
                    o["seen"].add(pid)

                    occ = [i for i, t in enumerate(toks) if t == sn]
                    nxt = [toks[i + 1] if i + 1 < len(toks) else None
                           for i in occ]
                    # occ is non-empty here, so all() is not vacuous.
                    standalone = any(n not in o["fn_surnames"] for n in nxt)
                    if all(n in pool_surnames for n in nxt):
                        o["s1_loose"] += 1
                    if not standalone:
                        o["s1"] += 1
                    elif o["checker"](title, selftext):
                        o["s2"] += 1
                    elif sub == "hockey":
                        o["s3_league"] += 1
                    else:
                        o["s3_own"] += 1

    print(f"scanned {scanned} submissions over {len(ALL_SUBS)} subs\n")

    rows = []
    for sn, o in owners.items():
        s1, s2 = o["s1"], o["s2"]
        s3o, s3l = o["s3_own"], o["s3_league"]
        s3 = s3o + s3l
        total = s1 + s2 + s3
        today = s2 if o["guarded_today"] else total
        rows.append({
            "sn": sn, "who": o["full"], "total": total,
            "s1": s1, "s1_loose": o["s1_loose"], "s2": s2,
            "s3_own": s3o, "s3_league": s3l,
            "guarded": o["guarded_today"], "p1": o["p1"],
            "live": o["live_mentions"],
            "today": today, "A": s2, "B": s2 + s3, "C": s2 + s3o,
            "C_ambig": s3l,
            # C': a P1 (common-English-word) surname keeps the strict guard.
            "C2": s2 if o["p1"] else s2 + s3o,
            "C2_ambig": s3l + (s3o if o["p1"] else 0),
        })
    rows.sort(key=lambda r: -r["total"])

    print("STATE SPLIT  (counting subs only; S3 = the contested class)")
    print(f"{'token':<10}{'owner':<22}{'hits':>7}{'S1':>7}{'S1%':>6}"
          f"{'S2':>7}{'S2%':>6}{'S3':>7}{'S3%':>6}{'S3own':>7}{'S3lg':>7}")
    for r in rows:
        t = r["total"] or 1
        s3 = r["s3_own"] + r["s3_league"]
        print(f"{r['sn']:<10}{r['who']:<22}{r['total']:>7}"
              f"{r['s1']:>7}{r['s1']/t:>6.0%}{r['s2']:>7}{r['s2']/t:>6.0%}"
              f"{s3:>7}{s3/t:>6.0%}{r['s3_own']:>7}{r['s3_league']:>7}")

    print("\nMENTIONS UNDER EACH OPTION   (delta vs today in parens)")
    h_c2, h_amb = "C'", "C'->amb"
    print(f"{'token':<10}{'owner':<22}{'gd':>3}{'P1':>3}{'today':>7}"
          f"{'A':>14}{'B':>14}{'C':>14}{h_c2:>14}{h_amb:>9}")
    for r in rows:
        def d(v):
            return f"{v:>6} ({v - r['today']:+d})"
        print(f"{r['sn']:<10}{r['who']:<22}"
              f"{'Y' if r['guarded'] else '-':>3}{'Y' if r['p1'] else '-':>3}"
              f"{r['today']:>7}"
              f"{d(r['A']):>14}{d(r['B']):>14}{d(r['C']):>14}"
              f"{d(r['C2']):>14}{r['C2_ambig']:>9}")

    tot = {k: sum(r[k] for r in rows) for k in ("today", "A", "B", "C", "C2",
                                                "C_ambig", "C2_ambig")}
    print(f"\nTOTAL over {len(rows)} owners: today {tot['today']}  "
          f"A {tot['A']} ({tot['A'] - tot['today']:+d})  "
          f"B {tot['B']} ({tot['B'] - tot['today']:+d})  "
          f"C {tot['C']} ({tot['C'] - tot['today']:+d})  "
          f"C' {tot['C2']} ({tot['C2'] - tot['today']:+d})")
    print(f"  ambiguous routed: C {tot['C_ambig']}  C' {tot['C2_ambig']}")

    print("\nBIGRAM SENSITIVITY  tight vs loose S1")
    print(f"{'token':<10}{'tight':>8}{'loose':>8}{'diff':>8}")
    for r in rows:
        print(f"{r['sn']:<10}{r['s1']:>8}{r['s1_loose']:>8}"
              f"{r['s1_loose'] - r['s1']:>+8d}")

    print("\nPROBE SELF-CHECK  recomputed today vs live reddit_mentions_12mo")
    bad = 0
    for r in rows:
        drift = r["today"] - r["live"]
        flag = "" if abs(drift) <= max(2, 0.02 * max(r["live"], 1)) else "  <-- DRIFT"
        if flag:
            bad += 1
        print(f"{r['sn']:<10}{r['who']:<22}{r['today']:>7}{r['live']:>7}"
              f"{drift:>+7d}{flag}")
    print(f"{bad} of {len(rows)} owners drift beyond tolerance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
