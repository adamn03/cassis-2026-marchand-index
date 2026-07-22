"""Corpus integrity scan (SESSION.md step 2, pre-production check).

Checks, per handoff:
  1. All 36 subs present as finalized .jsonl (no .part stragglers).
  2. 36 subs x 13 calendar months (2025-04 .. 2026-04): zero empty months.
  3. Every post inside [2025-04-18 00:00 UTC, 2026-04-18 00:00 UTC).
  4. No duplicate submission ids within a sub.
  5. McDavid sanity: r/hockey posts in [2025-04-18, 2025-05-18) whose folded
     token set contains "mcdavid" — count must be >= 65 (A23 verification
     benchmark: two-archive agreement run found 67).

Read-only. Exit 0 = corpus passes; exit 1 = failures listed.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

MI = Path(r"C:\Local Only\Ai projects\Sports Analytics Conference Projeccts") \
    / "Full Project Files" / "marchand_index"
sys.path.insert(0, str(MI))
from fetch_reddit import ALL_SUBS, match_tokens  # noqa: E402

CORPUS = MI / "cache" / "reddit_corpus"
UTC = dt.timezone.utc
LO = int(dt.datetime(2025, 4, 18, tzinfo=UTC).timestamp())
HI = int(dt.datetime(2026, 4, 18, tzinfo=UTC).timestamp())
MC_LO = LO
MC_HI = int(dt.datetime(2025, 5, 18, tzinfo=UTC).timestamp())

EXPECTED_MONTHS = (["2025-%02d" % m for m in range(4, 13)]
                   + ["2026-%02d" % m for m in range(1, 5)])   # 13 months

# Verified-real empty months (NOT corpus gaps): two independent Arctic Shift
# pulls (original + 2026-07-22 re-pull, byte-identical results) agree these
# sub-months contain zero submissions — the small Utah community migrated
# between its two subs mid-window (UtahHockey -> utahmammoth rename era).
# Disclosed residual; UTA attention flows mainly through r/hockey regardless.
ALLOWED_EMPTY = {
    ("UtahHockey", "2025-07"), ("UtahHockey", "2025-12"),
    ("UtahHockey", "2026-01"), ("utahmammoth", "2026-01"),
}

failures: list[str] = []
mcdavid = 0
total_posts = 0

print(f"{'sub':<20} {'posts':>8}  empty-months / issues")
for sub in ALL_SUBS:
    path = CORPUS / f"{sub}.jsonl"
    if not path.exists():
        failures.append(f"r/{sub}: MISSING (.jsonl not finalized)")
        print(f"{sub:<20} {'---':>8}  MISSING")
        continue
    seen: set[str] = set()
    months: dict[str, int] = {}
    dupes = out_of_window = torn = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                post = json.loads(line)
            except json.JSONDecodeError:
                torn += 1
                continue
            pid = post.get("id")
            if pid in seen:
                dupes += 1
                continue
            seen.add(pid)
            ts = int(post.get("created_utc") or 0)
            if not (LO <= ts < HI):
                out_of_window += 1
                continue
            d = dt.datetime.fromtimestamp(ts, UTC)
            months["%d-%02d" % (d.year, d.month)] = \
                months.get("%d-%02d" % (d.year, d.month), 0) + 1
            if sub == "hockey" and MC_LO <= ts < MC_HI:
                if "mcdavid" in match_tokens(post.get("title") or "",
                                             post.get("selftext") or ""):
                    mcdavid += 1
    total_posts += len(seen)
    empty = [m for m in EXPECTED_MONTHS if not months.get(m)]
    allowed = [m for m in empty if (sub, m) in ALLOWED_EMPTY]
    empty = [m for m in empty if (sub, m) not in ALLOWED_EMPTY]
    issues = []
    if allowed:
        issues.append(f"empty-allowed {allowed} (verified real, see header)")
    if empty:
        issues.append(f"EMPTY {empty}")
        failures.append(f"r/{sub}: empty months {empty}")
    if dupes:
        issues.append(f"{dupes} dupes(skipped)")
        failures.append(f"r/{sub}: {dupes} duplicate ids")
    if out_of_window:
        issues.append(f"{out_of_window} OUT-OF-WINDOW")
        failures.append(f"r/{sub}: {out_of_window} posts outside window")
    if torn:
        issues.append(f"{torn} unparseable lines")
        failures.append(f"r/{sub}: {torn} unparseable lines")
    print(f"{sub:<20} {len(seen):>8}  {'; '.join(issues) or 'ok'}")

print(f"\nTotal posts: {total_posts}")
print(f"McDavid r/hockey [2025-04-18, 2025-05-18): {mcdavid} (need >= 65)")
if mcdavid < 65:
    failures.append(f"McDavid check FAILED: {mcdavid} < 65")

if failures:
    print(f"\nFAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("\nPASS — corpus integrity ok.")
