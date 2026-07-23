# Session Handoff
Date: 2026-07-22
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build` (pushed, clean).

LAST: **DATASET COLLECTION COMPLETE** (everything not owner-blocked), all snapshotted in `Full Project Files/final_dataset/` per-source folders + pushed:
- Wiki en+intl (A36): 774/764 rows redirect-augmented, 0 RESTATED; scraper 6-threaded + wikidata 429 serialization.
- Reddit (A42+A43): 771/771 ok; common-word guard (two-prong trigger: top-1000 English list + phrase-collision bigram w/ pool-first-name exemption); guard set 9 (but/back/power/point/stanley/york/connor/james/paul), 0.4/0.6 sensitivity identical; McDavid 2068 #1.
- Trends (A44): 771/771 non-null; anchor MID pinned /m/027h_8t (Google renamed entity types → franchise-name type test); Marchand row 0.977 via A35 secondary anchor.
- Mover dates (A38): 192/192 dated w/ 2 URLs (research_mover_dates.py bulk Wikipedia parse + 6 individual searches; sources in mover_dates_sources.md); 19 Utah rename artifacts excluded; derive_moves now applies A22 rename rule.
- Pool 771 (A41 applied); A40 batch text committed. `compute_oaq.load_inputs()` dry-load CLEAN: 32 fields × 771.
240 tests green. Amendments A40–A44 all text-before-code. NOT run: production compute_oaq (gated: Phase-1 hygiene + Gate-4 per airtight §E — deliberate).

STATUS: working

NEXT: Phase-1 hygiene per airtight plan §1.x (duplicate-vector scan 1.4, trends MID-dupe assert 1.5, etc. — see docs/airtight_execution_plan.md §I checklist) → then Gate-4 prep (blocked on owner YouTube key). No production compute before both.

OWNER (unchanged, 2 items): (a) eyeball marchand_index/raw/reddit_identity_pairs.md (A21 acceptance); (b) YouTube API key → U1 dry-run + Gate-4.

CARRY-FORWARD: 240 tests; pool 771; window [2025-04-18, 2026-04-17]; A12 weights unchanged; impl seed 20260526 / spec seed 20260522 (never harmonize); cache/reddit_corpus/ GITIGNORED LOCAL SOURCE OF RECORD (+ Utah .bak-20260722 copies); http cache backup cache/http_cache.backup-20260722.sqlite (594MB — deletable once A36 stable); english_top1000.txt pinned (never edit); raw/_a36_dryrun_*.csv untracked stale scratch (safe to delete, ask owner); _wiki_trans_*.html + run logs gitignored/local. A39 count constants post-A41: top-8 / top-78. Next free amendment number: A45.

Deadline: poster 2026-09-12 (~7.4 wk).
