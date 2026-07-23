# Session Handoff
Date: 2026-07-22
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build` (pushed).

LAST: Big data day. (1) **A36 wiki COMPLETE + committed**: 774 en + 764 intl rows, 3 redirect cols, 0 RESTATED, UNRECOVERED en 1 / intl 61 (stored kept, safe). Scraper now 6-thread both passes + wikidata sitelinks serialized w/ 429 backoff (mass-429 incident fixed). (2) A40+A41 texts committed; **A41 APPLIED: players.csv = 771** (dropped pids 637/500/368; keep rule = in-window 2025-26 team). (3) corpus_integrity_scan committed+PASSING (4 Utah empty months verified real via double-pull, allowlisted). (4) **A42 committed+run**: v1 matcher counted English words as surnames (But 4330 > McDavid); DF≥1% guard + A15 first-name evidence fixed that BUT over-guards genuinely-famous names — McDavid 2068→679, Hughes brothers suppressed. reddit_counts.csv v2 committed as INTERIM, NOT final. (5) final_dataset/ per-source folders (wiki/ done). (6) A38 mover_dates.csv skeleton committed (194 movers/211 rows, all needs_date). 234 tests green.

STATUS: working — one open design decision

BLOCKER: none hard; reddit finalization waits on owner approving **A43** (proposed, NOT implemented): two-prong guard replacing bare DF≥1% — (a) fixed top-1000 English wordlist prong (but/back/power/point), (b) phrase-collision prong: DF≥1% AND ≥50% occurrences in dominant neighbor-bigram ("stanley cup", "new york") or adjacent to pool surname ("connor mcdavid") — un-guards mcdavid/hughes, keeps the 7 junk names. Full guard-set evidence in `_reddit_matcher_run2.log` (gitignored, local).

NEXT: Get owner yes/no on A43 → write A43 prereg text (pattern: post-fetch/pre-compute disclosure like A42) → commit text → implement two-prong guard in fetch_reddit.py + tests → pytest → re-run `python fetch_reddit.py` (~4 min, deterministic) → verify McDavid ~2068 restored, But/Stanley/York still guarded → commit counts as final → copy to final_dataset/reddit/ + update README.
Then: fetch_trends.py full run (774→771 pool; hours, resumable, pytrends throttling) → A38 date research (2 URLs/mover, fill event_date+move_type) → A40 clauses post-compute.

OWNER (unchanged): (a) eyeball raw/reddit_identity_pairs.md; (b) YouTube API key → U1 dry-run + Gate-4.

CARRY-FORWARD: 234 tests green; pool 771 (A41 applied); window [2025-04-18, 2026-04-17]; A12 weights unchanged; impl seed 20260526 / spec seed 20260522 (never harmonize); cache/reddit_corpus/ GITIGNORED LOCAL SOURCE OF RECORD (Utah .bak-20260722 copies alongside); http cache backup `cache/http_cache.backup-20260722.sqlite` (594MB, can delete once A36 data verified stable); logs _a36_full_run.log/_a38_mover_run.log/_reddit_matcher_run*.log/_utah_repull.log gitignored; raw/_a36_dryrun_*.csv untracked scratch. A42 v2 reddit counts = interim (committed for audit; regenerate deterministically). Amendment numbering: next free = A43 (claimed by pending proposal). Governing "texts before reddit" rule: SATISFIED through A42; A43 follows the A42 post-fetch disclosure pattern (no composite/OAQ computed yet — that boundary still holds).

Deadline: poster 2026-09-12 (~7.4 wk).
