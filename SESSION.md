# Session Handoff
Date: 2026-06-23
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build` (pushed).

LAST: **Shipped Reddit-independent code-review fixes #1-#5 + #7.** (1) **#1 en-wiki window misalignment FIXED** — logged prereg amendment **A14**, aligned `fetch_wikipedia.py` to the fixed A11 window `[20250418, 20260417]` (was run-time `20250617..20260617`, playoff-inclusive), **re-fetched all 774** (now byte-identical window to wiki_intl/Reddit/Trends). (2) #3/#4 atomic writes (`_common.atomic_write_text` for results.md/json). (3) #5 wiki_intl bootstrap now stratified per-edition (was pooled → inflated CI). (4) #2/#7 wiki_intl transient errors now classified ok/absent/error → `intl_match {ok,partial,error,none}` via shared `fetch_edition_safe`. **61 tests pass** (56 + 5 new). Code `3e2af81`, data `dcba5e8`, both pushed. #6 skipped (lowest-value, correct as-is). Prior session: cleanup + xhigh review (`be41d69`); parked "attention→contracts" idea (below).

TRENDS VERDICT (RESOLVED — live evidence, not git inference): old code `timeframe="today 12-m"` (run-anchored, confounded) through 2026-06-18 (a3cf9ee); fixed-window `"2025-04-18 2026-04-17"` code landed 2026-06-20 13:21 (0c3ccbe); current trends.csv fetch_date=2026-06-20, 774 rows, n_weeks=53 uniform. **2026-06-26 spot-check (prereg V-A11-Trends) closes the residual:** live McDavid fixed-window fetch = 26.13 vs stored 24.7358 (5.6% = MATCH → stored used fixed window); run-anchored series shows the post-window 2026-playoff spike (Apr-26=47 peak) the fixed window correctly drops. Trends component is on the A11 window and excludes the playoff confound. No re-fetch of the set needed (perishable, deterministic past window).

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
- Consequence: final OAQ magnitudes + BOTH A12 diagnostics UNINFORMATIVE right now. **Re-run `compute_oaq.py` + both `diagnostics/*.py` after Reddit creds added** — A13 machinery is built, numbers become real post-Reddit.
- **2026-06-26 dry-run of `compute_oaq.py` on post-A14 code (Reddit-NULL, throwaway output discarded — NOT committed):** pipeline executes clean end-to-end, deterministic, no wiring bug → post-Reddit run is one clean pass. Current NULL-state verdicts (corrects the prior "PC/PD confirmed" carry-forward, which was pre-A14): **PA/PB inconclusive (underpowered, n=5/9), PC confirmed (9 of top-10 displaced), PD DISCONFIRMED** (V3 rho=0.3622 < 0.40 threshold; pre-A14 was confirmed — A14 stripping en-wiki playoff-buzz lowered playoff-team team-attention alignment below the line; mechanical baseline 0.4194 now > peer-matched 0.3622). **V1b AUC=0.9285 [0.829,0.988], POWERED** even Reddit-NULL (primary §9 jersey test holds). All NULL-state verdicts non-final — post-Reddit `OAQ_observed`/`engagement_raw` gain ~0.44 Reddit mass → V3/PC/PA/PB all shift.

CODE REVIEW FINDINGS (xhigh) — STATUS after 2026-06-23 fix session:
- **#1 (HIGH) — en-Wikipedia window misalignment — FIXED (A14, code `3e2af81` + data `dcba5e8`).** Was run-time window (recorded 20250617..20260617, playoff-inclusive) on the LARGEST §4 weight (0.29). Logged prereg **A14**, set `fetch_wikipedia.py` WINDOW_START/END = fixed A11 `[20250418, 20260417]`, re-fetched all 774. Verified: new CSV window 20250418..20260417, fetch_date 2026-06-23, 763 non-null / 10 unresolved (resolution is window-independent, split unchanged).
- **#2/#7 (MED/cleanup) — wiki_intl transient error == 404 — FIXED.** `fetch_wikipedia_intl.py`: new module fn `fetch_edition_safe` classifies ok/absent(404)/error(transient); `aggregate_player` sets `intl_match {ok, partial, error, none}` so a transient drop is visible (was silently summed away with intl_match=ok). Shared helper also kills the per-iteration closure + copy-pasted 404/sleep logic (#7). Effective only on the NEXT intl fetch (folds into the Reddit-era regen; existing intl window already correct).
- **#3/#4 (MED, CLAUDE.md) — non-atomic writes — FIXED.** results.md/results.json now use `_common.atomic_write_text` (.tmp→rename).
- **#5 (LOW, CI methodology) — intl bootstrap pooled editions — FIXED.** `load_wiki_intl_daily_by_edition` returns per-edition arrays; bootstrap resamples each edition at its own day-count and sums (was one pooled vector → between-edition compositional variance inflating the CI). Point estimate unchanged. Verified in isolation: pooled toy data spread 120-150 vs stratified constant 140.
- **#6 (LOW, cleanup) — SKIPPED.** `fetch_moneypuck.py:220 empirical_group_report` redundant 2nd groupby for a print — correct as-is, lowest value. Only open finding; pick up only if touching that file.
- REFUTED (not bugs): reddit_mentions bootstrap variance (correct count behavior); MoneyPuck file cache (intended deterministic snapshot); name-fallback `not pid.isdigit()` (matches contract); seconds→minutes (correct, once); 6-feat covariance (pinv guards).

OPEN QUESTION: none Reddit-independent remain. (Trends A11 — RESOLVED, see TRENDS VERDICT above.)

NEXT (exact): only the **Reddit track** remains (everything Reddit-independent is shipped) —
- Add OAuth creds to `marchand_index/.env` → purge `raw/reddit_counts.csv` + `raw/reddit_detail.csv` (A10 resume pitfall) → run `fetch_reddit.py` → **re-fetch intl** once (`fetch_wikipedia_intl.py`, to populate the new #2 `intl_match` flag; en-wiki already on A14 window, no re-fetch) → re-run `compute_oaq.py` + both `diagnostics/*.py`. (Trends spot-check DONE this session — see TRENDS VERDICT; no longer carried.)
- This is ONE compute_oaq regen consuming: corrected en-wiki (banked this session), re-fetched intl, new Reddit, #5 stratified CI. No double-churn.

CARRY-FORWARD (still valid):
- 774 locked pool (497 F / 277 D, snapshot 2026-06-17). players.csv: group f1=F/d1=D; player_id 1..774; nhl_player_id per player.
- A13 source: MoneyPuck `https://moneypuck.com/moneypuck/playerData/seasonSummary/2025/regular/skaters.csv` cached at `raw/moneypuck_skaters_2025.csv` (3.5MB, committed; re-runs free, no network). Join nhl_player_id==playerId.
- compute_oaq deterministic (seed 20260526, 1000 bootstrap, ~2-3 min run). _common.py forces UTF-8; Windows console cp1252 (no non-ASCII in ad-hoc python -c). Scrapes share one sqlite cache/http_cache -> run SEQUENTIALLY.
- YouTube = Gate-4 validation ONLY, never a composite input (anti-circularity).

DOWNSTREAM VALUE-PROP BACKLOG (owner-liked, build AFTER all data + 5 validation gates land — do NOT build yet):
- **Top-5 ranked ideas banked in `marchand_index/value_propositions.md`** (full briefs: mechanism, $0 data + verified feasibility tier, anti-circularity ID, quotable, build difficulty, why-worth-it, kill condition). Produced via analyst→leader→manager funnel, ranked STRENGTH-first then feasibility.
- Order: **#1 Sentencing Gap** (DoPS suspension vs published rubric; AMBER, LLM rubric-coding gated F1/κ) · **#2 Superstar Whistle** (penalty drawn-up/taken-down asymmetry + ref FE; GREEN, data verified) · **#3 Road Tax** (visiting-player OAQ → opponent home attendance, Hausman-Leonard; GREEN, ESPN attendance verified) · **#4 Contracts** (next-contract residual; owner's economic CLOSER — ranks #4 on strength only because cap feeds the OAQ denominator → needs contracts-OUT variant + temporal split) · **#5 DFS Price-vs-Crowd** (ownership residual at fixed DK salary; AMBER-RED, free ownership data is the existential risk — de-risk data FIRST).
- Each = an extra independent validation arm (criterion 2), NOT an index change. Feasibility tiers verified live 2026-06-26 (NHL API play-by-play/broadcast flags, ESPN attendance+refs, Wikimedia hist — all GREEN; card-price/DFS-ownership/betting-odds = RED).
- Cut-list (don't re-propose) recorded at the bottom of value_propositions.md.

Deadline: abstract accepted for poster. Poster session 2026-09-12 (~12 wk runway). Roster snapshot locked; no live perishability.
