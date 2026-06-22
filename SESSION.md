# Session Handoff
Date: 2026-06-21
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build` (pushed).

LAST: **A13 (skill-vector expansion) FULLY SHIPPED — all 11 tasks, 11 commits, pushed.** Peer vector grown 3->6: added MoneyPuck 5v5 on-ice features cf_pct/xgf_pct/ozs_pct to (age, ppg, toi_per_game). New fetcher `fetch_moneypuck.py` (+ 15 unit tests), `raw/nhl_onice.csv` (774 rows). compute_oaq SKILL_COLS/load_inputs/OUT_COLS + docstring/results prose updated. A13 prereg amendment logged. **56/56 unit tests pass.** End-to-end regenerated.

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

OPEN QUESTION (owner to decide next session — both Reddit-independent):
- **Trends A11 re-run** — `raw/trends.csv` ambiguous (can't tell pre/post window-fix; `fetch_trends.py` hardcodes fixed window). Re-running is perishable + 429-prone, re-churns e2e. Decide: trust current file, or re-fetch then re-run compute_oaq + diagnostics. (Deferred from last session in favor of A13; A13 chosen + done.)

NEXT (exact): Either (a) wait on Reddit creds then re-run compute_oaq + diagnostics for informative OAQ, or (b) owner decides Trends A11 re-run. No further plan-driven build pending — A12 + A13 both shipped.

CARRY-FORWARD (still valid):
- 774 locked pool (497 F / 277 D, snapshot 2026-06-17). players.csv: group f1=F/d1=D; player_id 1..774; nhl_player_id per player.
- A13 source: MoneyPuck `https://moneypuck.com/moneypuck/playerData/seasonSummary/2025/regular/skaters.csv` cached at `raw/moneypuck_skaters_2025.csv` (3.5MB, committed; re-runs free, no network). Join nhl_player_id==playerId.
- compute_oaq deterministic (seed 20260526, 1000 bootstrap, ~2-3 min run). _common.py forces UTF-8; Windows console cp1252 (no non-ASCII in ad-hoc python -c). Scrapes share one sqlite cache/http_cache -> run SEQUENTIALLY.
- YouTube = Gate-4 validation ONLY, never a composite input (anti-circularity).
- Cosmetic debt: some .py docstrings still say "pilot2"; _common.CONTACT_UA still "marchand-index-pilot2/0.1"; fetch_wikipedia_intl.py docstring references pilot2/raw paths.

Deadline: abstract accepted for poster. Poster session 2026-09-12 (~12 wk runway). Roster snapshot locked; no live perishability.
