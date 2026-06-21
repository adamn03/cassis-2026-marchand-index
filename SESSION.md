# Session Handoff
Date: 2026-06-21
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: **A12 (ingestion expansion) FULLY SHIPPED — all 14 tasks, 6 commits, pushed.** Migration `pilot2 -> marchand_index` committed. intl-wiki fetcher built + integration fetch ran (764/764 intl_match=ok, 3470 daily rows). compute_oaq re-locked + bootstrap resamples wiki_intl + instagram dropped. 2 diagnostics + prereg amendment. End-to-end pipeline regenerated. **33/33 unit tests pass.**

STATUS: working

OPEN QUESTION (owner to decide next session — pick one to continue, both Reddit-independent):
1. **A13** (skill-vector expansion) — add MoneyPuck 5v5 cf_pct/xgf_pct/ozs_pct to peer vector. Plan: `docs/superpowers/plans/2026-06-20-skill-vector-expansion.md`. Rebase on A12 edits to compute_oaq.py + preregistration.md. Buildable now, no Reddit.
2. **Trends A11 re-run** — `marchand_index/raw/trends.csv` is AMBIGUOUS: fetch_date 2026-06-20, n_weeks=53, and `fetch_trends.py` already hardcodes `timeframe="2025-04-18 2026-04-17"`, but can't tell from data whether file was generated pre- or post-fix. Re-running is perishable + 429-prone and re-churns e2e outputs. Decide: trust current file, or re-fetch to guarantee fixed window (then re-run compute_oaq + both diagnostics).

REDDIT-BLOCKED (hard carry-forward, NOT doable until creds land):
- Reddit OAuth creds STILL BLANK in `marchand_index/.env`. Reddit = 0/774 NULL in current run (~0.44 of engagement weight).
- Consequence: final OAQ + BOTH A12 diagnostics are UNINFORMATIVE right now — reddit_robustness ladder all rho=1.0 (scaling NULL changes nothing), source_correlation reddit cells n=0. **Re-run `compute_oaq.py` + both `diagnostics/*.py` after Reddit creds added.**

A12 RESULT DETAIL (committed):
- Weights (sum 1.00): wiki_12mo 0.29, wiki_intl_12mo 0.11, reddit_mentions 0.27, reddit_upvotes 0.17, trends 0.16. Instagram DROPPED.
- intl whitelist {sv,fi,cs,ru,de,sk,fr}, QID reused from raw/wiki_pageviews.csv (764/774 have QID; 10 QID-less -> NaN -> sentinel-drop).
- Sanity: wiki_en<->wiki_intl Spearman 0.62; wiki_intl<->trends 0.14. Pastrnak 225887, Kaprizov 225683, Bedard 74857 (all intl_match=ok — NHL players have multi-lang stubs, so intl_match=none is rare, not a bug).
- oaq_pilot.csv now carries wiki_intl_12mo + intl_match, NO instagram_followers.

NEXT (exact): owner answers OPEN QUESTION above -> execute chosen path. If A13, read its plan + rebase on A12. If trends, re-fetch then re-run compute_oaq + diagnostics.

CARRY-FORWARD (still valid):
- 774 locked pool (497 F / 277 D, snapshot 2026-06-17). players.csv: group f1=F/d1=D; player_id 1..774; nhl_player_id per player.
- A13 detail: MoneyPuck CSV `https://moneypuck.com/moneypuck/playerData/seasonSummary/2025/regular/skaters.csv` (situation=='5on5'; icetime-weighted mean for traded players). Join nhl_player_id==MoneyPuck playerId.
- compute_oaq deterministic (seed 20260526, 1000 bootstrap). _common.py forces UTF-8; Windows console cp1252 (no non-ASCII in ad-hoc python -c). Scrapes share one sqlite cache/http_cache -> run SEQUENTIALLY.
- YouTube = Gate-4 validation ONLY, never a composite input (anti-circularity).
- Cosmetic debt: some .py docstrings still say "pilot2" (non-functional); fetch_wikipedia_intl.py docstring still references pilot2/raw paths.

Deadline: abstract accepted for poster. Poster session 2026-09-12 (~12 wk runway). Roster snapshot locked; no live perishability.
