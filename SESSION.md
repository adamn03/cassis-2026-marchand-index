# Session Handoff
Date: 2026-07-21
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: Found + fixed an A36 SILENT-TRUNCATION data-corruption bug, then attempted the A36 full data run (killed by owner mid-run). Fix committed + pushed.
- BUG: Wikimedia pageviews REST intermittently 404s a full-window per-article request even when the series exists (time-varying flake). Old split-window fallback returned the ONE surviving half when the other 404'd → truncated total → overwrote a good stored full-year series via the RESTATED path. Live: Brzustewicz 16153→6508 (lost half2), Whitecloud 85053→61129 (lost half1).
- FIX (commit **c77f4b5**, pushed): full-window 200 is all-or-nothing → stored non-blank total is authoritative. `fetch_daily_pairs` split fallback now requires BOTH halves; a one-half result returns None so the caller's `canon_total==0` UNRECOVERED guard KEEPS the stored series. Genuine recovery preserved (Nikishin full-404 but both halves → 38887 == stored). +5 fail-safe tests (fake session, monkeypatched sleep). **216 tests pass.** Added `diagnostics/pv_404_scope.py` (read-only 404-rate probe).
- A36 FULL DATA RUN: attempted twice today, killed both times (2nd by owner at 612/771 en, before intl). Atomic-write happens only AFTER both en+intl passes → **NO CSV was written; raw/wiki_*.csv are UNCHANGED** (verified: empty git diff). At kill: 19 UNRECOVERED / 0 RESTATED. UNRECOVERED clustered by consecutive team → API rate-limit bursts, all RECOVERABLE, all SAFE (stored kept). 0 RESTATED confirms fix: every clean fetch now matches stored exactly.

STATUS: working (fix shipped + green; data run just not executed yet)

BLOCKER: none.

NEXT: Execute the A36 full data run with the FIXED code:
`cd "Full Project Files/marchand_index" && python -u augment_wiki_redirects.py > _a36_full_run.log 2>&1 &` (≤2h). UNRECOVERED lines are now EXPECTED + SAFE (throttle flake → keeps correct stored full-year), NOT the old corruption — do not panic at them. Watch only RESTATED/Traceback. Cache is 24h: a re-run before ~2026-07-22 12:00 reuses today's cached 200s (much faster); after that it is a cold ~2h run.
Then per plan Task-2 step 6: verify 774 rows + 3 new cols (`n_redirect_titles`, `redirect_views_12mo`, `redirect_share`) in raw/wiki_pageviews.csv (+ intl), `pytest -q`, commit `marchand_index: A36 augmented wiki data (full 774 run)`.
OPTIONAL after the run: targeted recovery pass re-fetching ONLY the UNRECOVERED subset at slower pacing (restore redirect augmentation for stars, esp. McDavid/Tkachuk — their base totals are already correct; only the ~0.1% redirect share is missing). Low value; skip if time-pressed.
THEN the original amendment batch continues IN ORDER: A38 (cross-domain supplement `2026-07-07-cross-domain-improvements.md` — mover list + date research; A38 λ̂ = U7 second-finding candidate) → A39 → A40 (draft = idea-max review §4; U3 approved) → A41 pool dedup 774→771 (Andrae 499/637, Benoit 500/638, Colton 152/368; mechanical keep rule; owner-approved 2026-07-13).
ONLY after ALL texts committed: `python diagnostics/corpus_integrity_scan.py` (STILL UNTRACKED) → fetch_reddit.py → fetch_trends.py --a35-marchand-row (A35 clause-1 live re-anchor) → dry-load compute_oaq.load_inputs(). NO production compute_oaq (Phase-1 hygiene + Gate-4 per §E first).

GOVERNING RULE: every amendment text lands BEFORE fetch_reddit.py writes reddit_counts.csv — texts claim "Reddit is 0/774". Corpus jsonl cache (complete) ≠ production counts.

OWNER (2 items, unchanged): (a) eyeball marchand_index/raw/reddit_identity_pairs.md; (b) YouTube API key → unblocks U1 dry-run + Gate-4.

CARRY-FORWARD: 216 tests committed-green (was 211; +5 A36 fail-safe); V1b positives 14; V2 21 in-pool POWERED; pool 774 (771 after A41); window [2025-04-18, 2026-04-17]; A12 weights unchanged; impl seed 20260526 / spec seed 20260522 (never harmonize); corpus cache/reddit_corpus/ GITIGNORED LOCAL SOURCE OF RECORD — back up, never delete; wiki edge 404s are TRANSIENT/time-varying on valid titles (documented + now fail-safe handled); goals_per60 lives only in inputs (not OUT_COLS). Source docs: airtight plan v1.1 + 2026-07-12 proposals + free-data supplement (Tasks 1-4 consumed) + cross-domain supplement (A38/A39) + idea-max §4 (A40) + decision sheet.
Prior amendment shipments A31→A37 + G4-A1..3: see git log (commits d35aeca..09da65c). `_a36_full_run.log` + `diagnostics/_pv_scope.log` are gitignored; `raw/_a36_dryrun_*.csv` + `diagnostics/corpus_integrity_scan.py` remain untracked (pre-existing, not part of the fix).

Deadline: poster 2026-09-12 (~8 wk).
