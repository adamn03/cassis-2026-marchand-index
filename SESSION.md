# Session Handoff
Date: 2026-07-18
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: Amendment batch A31→A37 + G4-A1..3 shipped, texts + code, 211 tests green. Commits (text/code):
- A31 code 791e780 (17 tests: stratified V1b + perm p + BH_secondary + results emit; NOTE SESSION's old BH fixture ".01/.04/.5→first two" was miscalculated — only first survives; test pins both).
- A32 0d927e5 / 4c61007 (invariance_panel: rawcap MI, OAQ_portable_lockedv1, NEW OAQ_portable_market_lockedv1 col = A5 rule on old proxy; V3 invariant-by-construction note; A32_DISCLOSURE pinned to prereg by test).
- A33 adb6314 / 3fd94bd (fan-vote union 2022 captains+LMI winners / 2023 final-12 / 2024; winners-only rule: Zibanejad IN, replacements Guentzel/Pavelski/Josi/Giroux OUT; asg2024_member column name kept carrying union + asg_fanvote_seasons col; 26 ids verified vs api-web, Terry=8478873; **V2 in-pool 21 ≥ 10 → POWERED first time**).
- A34 54ed0db / 6c4e10f (_a34_display_pool small_sample=1|null-GP filter on ALL published tables incl. λ-ladder display mask + log-lens; PC untouched; validation cohorts full-pool).
- A35 d35aeca / 806c2cc (fetch_trends SECONDARY_ANCHOR_NAME=Crosby + chain (M/C)·(C/M) via --a35-marchand-row [LIVE RUN NOT DONE — production phase]; zero_quant_count; goals_per60 from moneypuck merged in load_inputs; a35_goalsrate_agreement; disclosures block with verbatim log-lens ban).
- G4-A1 8a2eddb, G4-A2 a2c061c, G4-A3 675d8c8 (spec prereg §11, G4-A series, seed 20260522 untouched).
- A36 text ed63d77, code e9cc8b1 (augment_wiki_redirects.py + 3 tests; retry ladder + split-window fallback + UNRECOVERED-keeps-stored guard; 5-player dry-run clean).
- A37 text e9b8197 (one path fix: external_outcomes.csv not raw/), EXECUTED 09da65c (sweep manifest hit/no-hit in sources doc; adopted 2023-24 Fanatics thru-Feb top-5 → Panarin+Zibanejad; **V1b n 12→14**; failing candidates recorded w/ clause).

STATUS: working (211 tests green; tree clean except gitignored logs/dryrun csvs)

BLOCKER: none. A36 FULL 774 RUN INCOMPLETE — background run killed at ~110/771 en pass at session end. requests-cache (24h, cache/http_cache.sqlite) holds completed calls: rerun within 24h is cheap.

NEXT: `cd "Full Project Files/marchand_index" && python augment_wiki_redirects.py > _a36_full_run.log 2>&1 &` (est ≤2h; watch for UNRECOVERED>0 / RESTATED lines in log tail). Then per plan Task-2 step 6: verify 774 rows + 3 new cols in raw/wiki_pageviews.csv, pytest -q, commit `marchand_index: A36 augmented wiki data (full 774 run)` (code already committed e9cc8b1). Then batch continues IN ORDER: A38 (cross-domain supplement `2026-07-07-cross-domain-improvements.md` — mover list + date research; A38 λ̂ = U7 second-finding candidate) → A39 → A40 (draft = idea-max review §4; U3 approved) → A41 pool dedup 774→771 (Andrae 499/637, Benoit 500/638, Colton 152/368; mechanical keep rule; owner-approved 2026-07-13).
ONLY after ALL texts committed: python diagnostics/corpus_integrity_scan.py (STILL UNTRACKED) → fetch_reddit.py → fetch_trends.py --a35-marchand-row (A35 clause-1 live re-anchor) → dry-load compute_oaq.load_inputs(). NO production compute_oaq (Phase-1 hygiene + Gate-4 per §E first).

GOVERNING RULE: every amendment text lands BEFORE fetch_reddit.py writes reddit_counts.csv — texts claim "Reddit is 0/774". Corpus jsonl cache (complete) ≠ production counts.

OWNER (2 items, unchanged): (a) eyeball marchand_index/raw/reddit_identity_pairs.md; (b) YouTube API key → unblocks U1 dry-run + Gate-4.

CARRY-FORWARD: 211 tests committed-green; V1b positives now 14 (A31 power statement recomputes mechanically post-A37 — a31_power_statement(n_pos,n_neg) already wired); V2 21 in-pool POWERED; pool 774 (771 after A41); window [2025-04-18, 2026-04-17]; A12 weights unchanged; impl seed 20260526 / spec seed 20260522 (never harmonize); corpus cache/reddit_corpus/ GITIGNORED LOCAL SOURCE OF RECORD — back up, never delete; proposals-doc status table updated thru A32 (A33+ rows not yet added — cosmetic); wiki edge 404s TRANSIENT on valid titles → both team + player fetchers carry retry ladder + split-window fallback; goals_per60 lives only in inputs (not OUT_COLS). Source docs: airtight plan v1.1 + 2026-07-12 proposals + free-data supplement (Tasks 1-4 consumed) + cross-domain supplement (A38/A39) + idea-max §4 (A40) + decision sheet.

Deadline: poster 2026-09-12 (~8 wk).
