# Session Handoff
Date: 2026-06-22
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build` (pushed).

LAST: **Non-OAuth cleanup + xhigh code review.** (1) Resolved Trends A11 open question — trust current `raw/trends.csv` as post-A11 fixed-window fetch; no re-fetch. (2) Cosmetic debt cleared (`pilot2/`→`marchand_index/`, 19 files; locked prereg/results untouched). 56/56 tests pass. Committed + pushed `be41d69`. (3) Ran `/code-review` xhigh on the branch — **7 verified findings, none fixed yet** (owner deferred). See CODE REVIEW FINDINGS below. (4) Parked owner's "attention→contracts" idea (below).

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

CODE REVIEW FINDINGS (xhigh, 2026-06-22 — verified vs source, none fixed yet; owner to greenlight):
- **#1 (HIGH, Reddit-independent, FIXABLE NOW) — en-Wikipedia window misalignment.** `fetch_wikipedia.py:40-44 window_strings()` uses RUN-TIME window; recorded en window in `raw/wiki_pageviews.csv` = 20250617..20260617 (includes full 2026 playoffs). reddit/trends/`wiki_intl` use fixed A11 window 20250418..20260417. So `wiki_12mo` (LARGEST §4 weight 0.29) carries the playoff confound A11 was built to remove; A11's "applied uniformly to all 774" violated for the top component. `fetch_wikipedia_intl.py:5` acknowledges divergence but composite never reconciles. FIX = point `window_strings()` at fixed A11 window + re-fetch en wiki (pageviews are historical/deterministic, not perishable). **Changes a headline input → log a prereg amendment BEFORE re-fetch.**
- **#2 (MED, correctness) — wiki_intl transient error == 404.** `fetch_wikipedia_intl.py:99,192` — non-404 fetch error (5xx/timeout) is dropped from sum identically to absent article; player still `intl_match=ok`, no flag. Flaky-network re-run → different headline intl numbers silently. FIX = distinguish 404 (skip) from transient (flag/retry/`thin`).
- **#3/#4 (MED, CLAUDE.md violation) — non-atomic writes.** `compute_oaq.py:1420` (results.md) + `:1436` (results.json) use plain `path.write_text`; violates "Atomic file writes: .tmp -> rename." CSV at `:1507` does it right. FIX = shared `_common.atomic_write_text(path,str)` for all three (also fixes the open-coded-inline altitude smell).
- **#5 (LOW, CI methodology) — intl bootstrap pools heterogeneous editions.** `compute_oaq.py:284-298,667` concatenates all editions' daily vectors (de ~100x sk) then resample-sums → mis-scaled `wiki_intl_12mo` CI width (point estimate fine). Criterion-4 relevant.
- **#6 (LOW, cleanup) — `fetch_moneypuck.py:220` `empirical_group_report`** redundant 2nd groupby for a print; `aggregate_traded` already yields counts. (Also: trade aggregation is a verified no-op on this source — see A13 detail.)
- **#7 (LOW, cleanup) — `fetch_wikipedia_intl.py:192` `fetch_fn`** closure rebuilt per-iteration + copy-paste of en fetcher's 404/sleep logic; shared `_common` helper would fix #2 in both places at once.
- REFUTED (not bugs): reddit_mentions bootstrap variance (correct count behavior); MoneyPuck file cache (intended deterministic snapshot); name-fallback `not pid.isdigit()` (matches contract, avoids wrong-player); seconds→minutes (correct, once); 6-feat covariance (pinv guards).

OPEN QUESTION: none Reddit-independent remain. (Trends A11 — RESOLVED, see TRENDS VERDICT above.)

NEXT (exact): two independent tracks, both can start before Reddit creds land —
- (a) **Code-review fixes** (Reddit-independent): start with #1 — log prereg amendment for the en-wiki fixed-window change, then edit `fetch_wikipedia.py:window_strings()` + re-fetch en wiki; then #3/#4 atomic writes (trivial); #2 next. #5-#7 optional polish.
- (b) **Reddit** (blocked): add OAuth creds to `marchand_index/.env` → re-run `compute_oaq.py` + both `diagnostics/*.py` for informative OAQ; do the 1-call Trends spot-check at that run.
- NOTE: if #1 is fixed, the en-wiki re-fetch + the eventual Reddit re-run should be folded into ONE `compute_oaq` regen to avoid double-churning e2e.

CARRY-FORWARD (still valid):
- 774 locked pool (497 F / 277 D, snapshot 2026-06-17). players.csv: group f1=F/d1=D; player_id 1..774; nhl_player_id per player.
- A13 source: MoneyPuck `https://moneypuck.com/moneypuck/playerData/seasonSummary/2025/regular/skaters.csv` cached at `raw/moneypuck_skaters_2025.csv` (3.5MB, committed; re-runs free, no network). Join nhl_player_id==playerId.
- compute_oaq deterministic (seed 20260526, 1000 bootstrap, ~2-3 min run). _common.py forces UTF-8; Windows console cp1252 (no non-ASCII in ad-hoc python -c). Scrapes share one sqlite cache/http_cache -> run SEQUENTIALLY.
- YouTube = Gate-4 validation ONLY, never a composite input (anti-circularity).

PARKED IDEA (owner-liked, explore AFTER all data/metrics land — do NOT build yet):
- **Attention → player contracts (economic-benefit angle).** Test whether attention surplus predicts contract value beyond production — the "do players get paid for being talked about?" question. Owner wants this as a payoff story for why the metric matters.
- **Caveats to design around when picked up (these decide if it's publishable vs. a reviewer kill-shot):**
  1. CIRCULARITY (biggest): `cap_hit` already feeds the MI denominator (A4 expected_cap) AND the §7/A5 market correction. Regressing contracts on OAQ/MI as-is = predicting contracts with a metric partly built from contracts. Need a contracts-OUT OAQ variant or strict temporal split.
  2. CAUSAL framing: CLAUDE.md bans causal/revenue claims we can't back. "Affects contracts" → must be "associated with contract premiums." No "the index drives pay."
  3. Clean publishable form (captures ~80% of the idea, avoids both traps): does `OAQ_portable` at season T predict the RESIDUAL of the player's NEXT contract (T+1) after controlling for production (PPG/TOI/on-ice)? Temporal hold-out + production control = a legit 4th validation pathway (criterion 2) and a quotable economic finding (criterion 5), not a circular one. Needs next-contract data (CapWages/PuckPedia, free) — out of current scope.

Deadline: abstract accepted for poster. Poster session 2026-09-12 (~12 wk runway). Roster snapshot locked; no live perishability.
