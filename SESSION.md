# Session Handoff
Date: 2026-06-20
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST (this session): **Renamed `pilot2/` -> `marchand_index/` (real project home) via `git mv`. Started A12 plan: Task 1 (intl-wiki fetcher constants) written.**

DECISIONS LOCKED (this session, owner-approved):
- **Folder = `marchand_index/`** (no space, importable). Supersedes the old "Marchand Index/" idea. Owner directive: this is NO LONGER the pilot — do NOT put new files in any `pilot*` folder; everything organizes under `marchand_index/` as the eventual final product.
- Migrate-now ordering: rename happened BEFORE finishing A12/A13 (reorders prior SESSION step 5 to first).

MIGRATION STATE (critical):
- `git mv pilot2 marchand_index` DONE. History preserved. **UNCOMMITTED** — still staged as renames in working tree.
- Untracked files traveled OK: `marchand_index/fetch_wikipedia_intl.py`, `marchand_index/raw/trends.csv`, `marchand_index/tests/`.
- Verified: **zero runtime `"pilot2"` string literals** in code (all paths are `__file__`-relative via `_common.PILOT_DIR`/`RAW_DIR`) — move is functionally safe. Smoke-import test was INTERRUPTED before confirming; re-run it first next session.
- Cosmetic only: 17 `.py` files still say "pilot2" in docstrings/comments (non-functional). `.gitignore` still has stale `pilot2/cache/` rule (actual cache still covered by `**/http_cache*`).

A12 PROGRESS (plan: `docs/superpowers/plans/2026-06-20-ingestion-expansion.md`, 14 TDD tasks, executing-plans skill):
- Task 1 code written: `marchand_index/tests/__init__.py`, `marchand_index/tests/test_fetch_wikipedia_intl.py` (3 tests), `marchand_index/fetch_wikipedia_intl.py` (WHITELIST, WINDOW_START/END = A11 fixed 20250418/20260417, `window_strings()`).
- RED confirmed pre-move. GREEN run interrupted by the migration. Tasks 2-14 NOT started.
- Plan fully pre-verified against real code this session: WEIGHTS (l.86-92), load_inputs ig (l.163/177/213), bootstrap ig_fixed/comp_z (l.583/630), OUT_COLS (l.1408), main call (l.1438) all match. `write_results_md` has NO instagram column ref -> Task 10 is just a guard. Tooling present: pytest 9.0.3, requests_cache, numpy, pandas, matplotlib.

STATUS: working (mid-migration, mid-Task-1)

NEXT (exact order):
1. Re-run smoke import: `python -c "import sys; sys.path.insert(0,'marchand_index'); import compute_oaq, _common, fetch_wikipedia_intl; print('ok')"` then `python -m pytest marchand_index/tests/test_fetch_wikipedia_intl.py -q` (expect 3 passed).
2. Fix `.gitignore`: `pilot2/cache/` -> `marchand_index/cache/`. Commit the migration: "marchand_index: rename pilot2 -> marchand_index (real project home)".
3. Continue A12 plan Tasks 2-14, building into `marchand_index/` (NOT pilot2). Use commit prefix `marchand_index:` (plan text still says `pilot2:` — substitute). Per-task TDD: write test -> RED -> impl -> GREEN -> commit.
4. Task 6 has a real-network integration fetch (~774 players, Wikidata+Wikimedia, ~5-10 min) — run in background w/ `dangerouslyDisableSandbox: true`. Downstream compute_oaq/diagnostics integration runs (Tasks 8b/9b/11b/12b) need its output; they run fine with Reddit NULL (creds still blank — see blocker).
5. Then A13 plan (`docs/superpowers/plans/2026-06-20-skill-vector-expansion.md`), rebased on A12 edits to compute_oaq.py + preregistration.md.

CARRY-FORWARD (still valid):
- **Reddit OAuth creds STILL BLANK** in `marchand_index/.env`. Hard prereq ONLY for the FINAL end-to-end OAQ (Reddit ~0.44 of engagement weight). Building/unit-testing A12+A13 does NOT need it. compute_oaq runs with Reddit NULL defensively.
- **Trends A11 re-run still pending**: `marchand_index/raw/trends.csv` is OLD run-time-window file (uncommitted). `fetch_trends.py` now points at fixed window "2025-04-18 2026-04-17". Re-run + verify 774 rows.
- 774 locked pool (497 F / 277 D, snapshot 2026-06-17). `players.csv`: group f1=F/d1=D; player_id 1..774; nhl_player_id per player.
- A12 weights (sum 1.00): wiki_en(code key `wiki_12mo`) 0.29, wiki_intl_12mo 0.11, reddit_mentions 0.27, reddit_upvotes 0.17, trends 0.16. Instagram DROPPED. wiki_intl whitelist {sv,fi,cs,ru,de,sk,fr}, reuses A1 wikidata_qid from raw/wiki_pageviews.csv.
- A13 (next): add MoneyPuck 5v5 cf_pct/xgf_pct/ozs_pct to peer vector. CSV `https://moneypuck.com/moneypuck/playerData/seasonSummary/2025/regular/skaters.csv` (situation=='5on5'; icetime-weighted mean for traded players). Join nhl_player_id==MoneyPuck playerId.
- compute_oaq deterministic (seed 20260526, 1000 bootstrap). `_common.py` forces UTF-8; Windows console cp1252 (no non-ASCII in ad-hoc python -c). Scrapes share one sqlite `cache/http_cache` -> run SEQUENTIALLY.
- YouTube = Gate-4 validation ONLY, never a composite input (anti-circularity).

Deadline: abstract accepted for poster. Poster session 2026-09-12 (~12 wk runway). Roster snapshot locked; no live perishability.
