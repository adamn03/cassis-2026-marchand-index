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

MI = Path(__file__).resolve().parent.parent      # marchand_index/
sys.path.insert(0, str(MI))
from fetch_reddit import ALL_SUBS, match_tokens  # noqa: E402
import _common as _C  # noqa: E402

CORPUS = MI / "cache" / "reddit_corpus"
UTC = dt.timezone.utc
# A51: window bounds come from _common. Hardcoding the old 365-day window here
# made this scan report every legitimately-collected 2023-24/2024-25 post as
# OUT-OF-WINDOW — a false failure on correct data.
LO, HI = _C.window_epoch_bounds()
# The McDavid recall check is anchored to a FIXED calendar month that must stay
# inside the window regardless of where the window starts, so it keeps its
# original 2025-04-18..2025-05-18 span (the A23 threshold of 65 was measured on
# exactly that month and is not transferable to a different one).
MC_LO = int(dt.datetime(2025, 4, 18, tzinfo=UTC).timestamp())
MC_HI = int(dt.datetime(2025, 5, 18, tzinfo=UTC).timestamp())

# A51: derived from the window instead of a hardcoded 13-month list, which
# would have checked coverage of only the final third of the 921-day window.
def _months_in_window() -> list[str]:
    out, y, m = [], _C.WINDOW_START_DATE.year, _C.WINDOW_START_DATE.month
    while (y, m) <= (_C.WINDOW_END_DATE.year, _C.WINDOW_END_DATE.month):
        out.append("%04d-%02d" % (y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


EXPECTED_MONTHS = _months_in_window()   # 31 months as of A51

# Verified-real empty months (NOT corpus gaps): two independent Arctic Shift
# pulls (original + 2026-07-22 re-pull, byte-identical results) agree these
# sub-months contain zero submissions — the small Utah community migrated
# between its two subs mid-window (UtahHockey -> utahmammoth rename era).
# Disclosed residual; UTA attention flows mainly through r/hockey regardless.
ALLOWED_EMPTY = {
    ("UtahHockey", "2025-07"), ("UtahHockey", "2025-12"),
    ("UtahHockey", "2026-01"), ("utahmammoth", "2026-01"),
}

# A51: a subreddit cannot contain posts from before it was created. The window
# now reaches back to 2023-10, so the two later Utah subs are legitimately empty
# for their entire pre-creation span; without this the scan reports 24 false
# failures on a correct corpus. First observed post month per sub, verified
# against the corpus itself (earliest created_utc).
SUB_FIRST_MONTH = {
    "UtahHockey": "2024-04",    # created at the Arizona -> Utah relocation
    "utahmammoth": "2025-04",   # created at the Utah Hockey Club -> Mammoth rename
}


def expected_months_for(sub: str) -> list[str]:
    """Window months during which this sub actually existed."""
    first = SUB_FIRST_MONTH.get(sub)
    return [m for m in EXPECTED_MONTHS if first is None or m >= first]

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
    empty = [m for m in expected_months_for(sub) if not months.get(m)]
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
