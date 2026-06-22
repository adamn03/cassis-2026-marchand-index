# Session Handoff
Date: 2026-06-22
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build` (pushed).

LAST: **Non-OAuth cleanup pass (Reddit still blocked).** (1) Resolved the Trends A11 open question — VERDICT: trust current `raw/trends.csv` as the post-A11 fixed-window fetch; do NOT re-fetch. (2) Cosmetic debt cleared: `pilot2/` path refs + `marchand-index-pilot2/` UA strings → `marchand_index/` across 19 files (.py + 2 non-locked .md). Locked `preregistration.md` + generated `results.md` UNTOUCHED; bare `(pilot2)` codename left intact (audit identity). 56/56 tests pass post-cleanup.

TRENDS VERDICT (resolved, evidence): old code `timeframe="today 12-m"` (run-anchored, confounded) through 2026-06-18 (a3cf9ee); fixed-window `"2025-04-18 2026-04-17"` code landed 2026-06-20 13:21 (0c3ccbe); current trends.csv fetch_date=2026-06-20, 774 rows, n_weeks=53 uniform. File postdates the fix and the only 06-20 re-fetch driver was A11 itself → it IS the post-fix fetch. Residual risk (fetch ran before 13:21 that day) is low + uncheckable from git/data alone; defer a 1-call spot-check (one 2026 deep-playoff player: stored value should EXCLUDE the playoff spike) to the mandatory post-Reddit e2e re-run. Re-fetching all 774 = perishable + 429-prone for ~zero expected gain.

STATUS: working

A13 RESULT DETAIL (committed):
- nhl_onice.csv: ok=704, thin=63, missing=7. All 774 peer-matched (NULL on-ice imputed to group mean inside `_standardize_skill`; raw CSV keeps NULL).
- **2 build deviations from plan (both fixed + documented in commits/prereg):**
  1. MoneyPuck `icetime` is SECONDS, pre-reg floor is 150 MINUTES. Convert /60 at ingest in main(). Pre-fix thin=0 (floor disabled); post-fix thin=63, floor min icetime 153 min.
  2. seasonSummary returns ONE pre-aggregated 5v5 row per playerId (940 rows=940 ids, 32 real teams, no TOT). Trade aggregation is a verified no-op on this source (spec risk #1 resolved empirically).
- expected_cap (A4) UNTOUCHED (asserted in test). 5v5 locked. QoC excluded (disclosed in amendment + poster).
- Plan was written for `pilot2/` paths; rebased to `marchand_index/` (renamed in commit 7c2d4fe). Prereg test assert needed plain "expected_cap (A4) unchanged" (no backticks) — adjusted that one line.

REDDIT-BLOCKED (hard carry-forward, NOT doable until creds land):
- Reddit OAuth creds STILL BLANK in `marchand_index/.env`. Reddit = 0/774 NULL in current run (~0.44 of engagement weight).
- Consequence: final OAQ magnitudes + BOTH A12 diagnostics UNINFORMATIVE right now. Pattern verdicts currently PA/PB inconclusive, PC/PD confirmed (Reddit-NULL state). **Re-run `compute_oaq.py` + both `diagnostics/*.py` after Reddit creds added** — A13 machinery is built, numbers become real post-Reddit.

OPEN QUESTION: none Reddit-independent remain. (Trends A11 — RESOLVED this session, see TRENDS VERDICT above.)

NEXT (exact): Wait on Reddit OAuth creds → add to `marchand_index/.env` → re-run `compute_oaq.py` + both `diagnostics/*.py` for informative OAQ. At that re-run, do the 1-call Trends spot-check (above). No further plan-driven build pending — A12 + A13 both shipped; cosmetic debt cleared.

CARRY-FORWARD (still valid):
- 774 locked pool (497 F / 277 D, snapshot 2026-06-17). players.csv: group f1=F/d1=D; player_id 1..774; nhl_player_id per player.
- A13 source: MoneyPuck `https://moneypuck.com/moneypuck/playerData/seasonSummary/2025/regular/skaters.csv` cached at `raw/moneypuck_skaters_2025.csv` (3.5MB, committed; re-runs free, no network). Join nhl_player_id==playerId.
- compute_oaq deterministic (seed 20260526, 1000 bootstrap, ~2-3 min run). _common.py forces UTF-8; Windows console cp1252 (no non-ASCII in ad-hoc python -c). Scrapes share one sqlite cache/http_cache -> run SEQUENTIALLY.
- YouTube = Gate-4 validation ONLY, never a composite input (anti-circularity).

Deadline: abstract accepted for poster. Poster session 2026-09-12 (~12 wk runway). Roster snapshot locked; no live perishability.
