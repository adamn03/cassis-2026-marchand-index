# Session Handoff
Date: 2026-07-21 (late)
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: (1) A36 full run relaunched with fixed code (c77f4b5) — owner stopped it at end of day at intl ~96/771; **en pass 771/771 COMPLETE and cached; 0 RESTATED, 0 Traceback, 2 UNRECOVERED (safe — stored kept)**. Atomic write never fired → raw/wiki_*.csv UNCHANGED (verified empty diff). All progress lives in the 24h http cache (entries from ~2026-07-21 evening).
(2) Parallel (zero cache/wiki contact) A38+A39 batch shipped in 7 LOCAL commits, NOT pushed (owner: "commit everything at the end" → no further commits without owner OK; push pending owner):
b7b7540 A38 prereg text · 0906d8e A39 prereg text · 298880b citation kit (docs/poster_related_work.md) · d179988 build_mover_list.py+tests · 2de0ecc lambda_portability.py+tests · 175044d attention_concentration.py+tests · 1decb65 airtight §E/§H/§I registration. **227 tests green** (was 216, +11). Both diagnostics' main() refuse to run pre-Phase-2. λ question settled with owner: λ=0.5 stays locked; A38 is Q&A armor, headline never moves.

STATUS: working

NEXT: Relaunch A36 ASAP on 2026-07-22 (daytime = warm cache from tonight; after ~evening it goes cold ~2h):
`cd "Full Project Files/marchand_index" && python -u augment_wiki_redirects.py > _a36_full_run.log 2>&1` (background). En pass replays from cache in minutes; intl ~30-60 min cold remainder. UNRECOVERED lines are EXPECTED+SAFE; watch only RESTATED/Traceback.
Then: verify 774 rows + 3 new cols (n_redirect_titles, redirect_views_12mo, redirect_share) in raw/wiki_pageviews.csv + intl → `pytest -q` (227) → stage A36 data (commit text: `marchand_index: A36 augmented wiki data (full 774 run)`) — ASK OWNER before committing/pushing anything (end-of-batch commit preference).
Then (cache now free): `python build_mover_list.py` (NHL API, writes mover_dates.csv skeleton) → A38 date research (2 URLs/mover, fill event_date+move_type, mover_dates_sources.md, plan Task 2 step 5) → A40 draft (idea-max §4; U3 approved) → A41 pool dedup 774→771 (Andrae 499/637, Benoit 500/638, Colton 152/368; owner-approved keep rule).
ONLY after ALL texts committed: corpus_integrity_scan.py (still untracked) → fetch_reddit.py → fetch_trends.py --a35-marchand-row → dry-load compute_oaq.load_inputs(). NO production compute_oaq (Phase-1 hygiene + Gate-4 per §E first).

GOVERNING RULE: every amendment text lands BEFORE fetch_reddit.py writes reddit_counts.csv — texts claim "Reddit is 0/774".

OWNER (2 items, unchanged): (a) eyeball marchand_index/raw/reddit_identity_pairs.md; (b) YouTube API key → unblocks U1 dry-run + Gate-4.

CARRY-FORWARD: 227 tests green; V1b positives 14; V2 21 in-pool POWERED; pool 774 (771 after A41); window [2025-04-18, 2026-04-17]; A12 weights unchanged; impl seed 20260526 / spec seed 20260522 (never harmonize); cache/reddit_corpus/ GITIGNORED LOCAL SOURCE OF RECORD — back up, never delete; wiki edge 404s transient + fail-safe handled; goals_per60 inputs-only. mover_dates.csv fetch was deliberately deferred (shares sqlite http-cache with A36 run — never run both). Citation kit entries UNVERIFIED (protocol runs at poster phase; never add citations from memory). Source docs: airtight plan v1.1 + 2026-07-12 proposals + free-data supplement + cross-domain supplement (A38/A39 now SHIPPED except mover dates + script execution) + idea-max §4 (A40) + decision sheet.
`_a36_full_run.log` + `diagnostics/_pv_scope.log` gitignored; `raw/_a36_dryrun_*.csv` + `diagnostics/corpus_integrity_scan.py` untracked (pre-existing).

Deadline: poster 2026-09-12 (~7.5 wk).
