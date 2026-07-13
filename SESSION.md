# Session Handoff
Date: 2026-07-13
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: Reddit source SWITCHED OAuth → Arctic Shift archive (creds blocker DEAD, verified live: full window coverage, 67/67 two-archive id agreement; PullPush not viable — dead since 2025-05-19). A21+A22+A23 texts committed to impl prereg §14 BEFORE code (112c5fe / ab165c6 / 146aaeb); corpus puller `fetch_reddit_corpus.py` + local-matcher rewrite of `fetch_reddit.py` shipped (ece1c68); tests 102 → 122 green. Corpus pull started: **r/hockey COMPLETE (52,252 posts)**, r/nhl in flight when session closed — resumable. Discovered: trends.csv is COMPLETE 774/774 (prior cut-off session finished it; 5 nulls: Marchand [anchor degeneracy — pending A35 Crosby anchor], Holloway, Groulx, But, Lamoureux).

STATUS: working

NEXT: 1) Resume corpus pull: `python fetch_reddit_corpus.py` from `Full Project Files/marchand_index/` (skips finished subs; ~35 remain, r/hockey was the big one; transient 422s auto-backoff — only investigate if a sub ABORTS after 5 retries). 2) After pull completes: integrity scan (36 subs × 13 months, zero empty months; McDavid r/hockey [2025-04-18, 2025-05-17] local-match count ≥ 65) → `python fetch_reddit.py` (~2 min, offline, deterministic) → `raw/reddit_counts.csv` (774 rows, no reddit_capped col) + `raw/reddit_detail.csv` → dry-load via compute_oaq `load_inputs()`. Do NOT run production compute_oaq (still gated on decision sheet + A24+ batch).

OWNER (4 items):
(a) Eyeball `marchand_index/raw/reddit_identity_pairs.md` (A21 acceptance step) — 4 non-discriminable groups, prefix-collisions, ~60 multi-sub traded players (spot-checked sane: Marner TOR+VEG, all UTA dual-sub).
(b) POOL DUPES decision: Andrae / Benoit / Colton each appear TWICE in the 774 (same nhl_player_id, two snapshot teams — confirmed MID-dupe scan). A21 mechanically zeroes their Reddit rows until a pool-dedup amendment (774→771). See supplement doc §4b. Matcher re-run after decision ≈ 2 min.
(c) 2026-07-11 decision sheet (D-1..3, U1–U8) still unchecked — gates A24–A35 batch, A30/A31, Gate-4.
(d) YouTube API key (U1 dry-run) — now the ONLY external prerequisite left in the project.

CARRY-FORWARD: 774 locked pool (3 dupe rows pending owner decision); fixed window [2025-04-18, 2026-04-17]; A12 weights unchanged (r_mentions .27 / r_upvotes .17 intact — descriptive cols reddit_mentions_allsubs / reddit_mentions_fantasy NEVER enter composite); seed 20260526; tests 122; corpus lives in `marchand_index/cache/reddit_corpus/` — GITIGNORED, LOCAL SOURCE OF RECORD, do not delete (archive-longevity insurance per A23 residual i); A23 supersedes A9 — no Reddit creds ever needed; A30 transport note (subscriber counts) open in supplement doc §5, resolve when D-2 decided; A24–A35 + G4-A1..3 drafts ready in `2026-07-12-amendment-proposals.md` (A30/A31 deliberately undrafted, await D-2/D-3); A36–A39 + A40 reserved by supplements/idea-max. Source-of-truth stack: airtight plan v1.1 + 2026-07-07 supplements + `2026-07-13-arctic-shift-source-switch.md` (records v1.1 supersessions: §B A23 spec, Task 1.8, §E "after creds").

Deadline: poster session 2026-09-12 (~8.5 wk runway).
