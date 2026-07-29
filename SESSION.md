# Session Handoff
Date: 2026-07-24
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: Exploratory in-memory index runs (no files, sacred CSVs untouched) — eyeballed third-liners / top-D / top-overall by OAQ_portable. Two REVIEW-PENDING items surfaced + logged below: (#1) a skill-input DATA BUG — found, fixed, refetched, verified; (#2) an OPEN methodology question on OAQ_portable low-tail behavior — neutral dossier + Tests 1-4, decision left to stronger model. `fetch_nhl_api.py` patched + `raw/nhl_skill.csv` regenerated; NEITHER committed (owner's call, pending stronger-model review).

STATUS: working

## BUG (found + fixed this session) — CORRECTNESS VERIFIED pool-wide (764/764); stronger-model review now OPTIONAL. Safe to commit.
- **Symptom:** Liam Ohgren showed ppg=0.0 over 18 GP. Real 2025-26 = 69 GP / 18 pts (ppg 0.26).
- **Root cause:** `fetch_nhl_api.py` `extract_skill()` looped `seasonTotals`, took the FIRST row matching `season==CURRENT_SEASON & gameTypeId==2`, then `break`. Players with MULTIPLE 2025-26 NHL rows (mid-season trade or split stints) kept only stint #1 → truncated `games_played`, `points/ppg`, `toi_per_game`. Also had NO `leagueAbbrev` guard (could fold an AHL row with gameTypeId 2).
- **Detection:** skill `games_played` (18) disagreed with MoneyPuck `nhl_onice.mp_games_played_5v5` (69). MoneyPuck aggregates trades (`aggregate_traded()`); skill fetcher didn't — the mismatch exposed it.
- **Scope:** 58 pool players (~7.5%) with skill-vs-onice GP gap >=15. Corrupts `ppg` (a core peer-matching feature) -> wrong production twins -> wrong OAQ for them AND their peers. Victims incl. Q.Hughes, Panarin, Kadri, Marchment, Garland, Rossi, Sherwood, Laughton. Several polluted the exploratory "surprising" list — those results were artifacts.
- **Fix:** replaced first-match-`break` with SUM over all rows where `season==CURRENT_SEASON & gameTypeId==2 & leagueAbbrev=='NHL'`. `games_played=ΣGP`, `ppg=ΣP/ΣGP`, `toi_per_game`=games-weighted mean of rows reporting `avgToi`. `fetch_nhl_api.py:59-70` region.
- **Verification done:** summed result == `featuredStats.regularSeason.subSeason` EXACTLY for Ohgren (69/18, .261), Stecher (64/14, .219), Q.Hughes (74/76, 1.027). Idempotent for single-row players (sum of one == itself) -> no regression. No test imports `extract_skill`.
- **Refetch:** patch is pure PARSING (landing JSON already cached), re-ran full `python fetch_nhl_api.py` -> regenerated `raw/nhl_skill.csv`. COMPLETE + VERIFIED: skill-vs-onice GP-gap>=15 dropped 58 -> 0; Ohgren now 69 GP/.261, Q.Hughes 74 GP/1.027; `fetch_date` 2026-07-23.
- **Audit of other collectors (same bug class):** moneypuck/onice OK (`aggregate_traded`), cap_hits OK (nhlId-matched + year-keyed), market_proxy OK (fail-closed), wiki/trends/reddit OK (not multi-row-per-entity; already guarded A36/A42-43/A44). Only skill had the pattern.
- **POOL-WIDE VALIDATION (this session — CLOSES review pts 1-2):** summed skill == NHL `featuredStats.regularSeason.subSeason` EXACTLY for all **764/764** players who played 2025-26 (0 mismatches; the **77** traded/split players all included, NONE doubled → no pre-combined/total row exists in `seasonTotals` → double-count risk DEAD). `gameTypeId==2` seen across **10 leagues** (NHL, AHL, NCAA, OHL, SHL, OG, WJC-20, EHT, International-Jr, Spengler Cup) → `leagueAbbrev=='NHL'` guard CONFIRMED necessary + correct. The only 7 'mismatches' = players with NO 2025-26 NHL games (Barkov + 6 depth) where featuredStats shows a PRIOR season; code correctly returns NaN — that is issue-#3A, not a fix defect.

### FIX #1 STATUS: correctness VERIFIED (pool-wide) — stronger-model review now OPTIONAL/confirmatory
1. Double-count / pre-combined row: CLOSED — 764/764 played players match NHL published totals; 77 traded included, none doubled.
2. `leagueAbbrev=='NHL'` guard: CLOSED — 10 leagues use gameTypeId==2; NHL filter confirmed essential + correct.
3. TOI games-weighting: low-risk JUDGMENT only (exact GP/points match ⇒ same rows feed TOI); standard aggregation.
4. Peer reassignment post-fix: behavioral, observed sane in reruns.
→ Safe to COMMIT on this verification. Held uncommitted only by owner's earlier call, not by any open correctness question.

## OPEN METHODOLOGY QUESTION #2 — OAQ_portable at the low-production tail (STRONGER MODEL TO DECIDE)
Neutral record of an owner<->assistant exchange + the tests run. All numbers from in-memory exploratory runs on corrected data (post issue-#1 skill fix; no files, no production run). No conclusion locked — decision left OPEN.

**Trigger:** Logan Stanley (BUF, bottom-pair D; .342 ppg, 16.7 toi, 60 GP) ranks #10 of 275 D by OAQ_portable (0.78) — above Cale Makar (#35). Question: genuine signal or peer-matching artifact?

**How OAQ_portable is built (verified in code):** `OAQ_portable = adj_own − peer_adj_mean`; `adj = engagement_raw − 0.5·max(0,market_z)`; `peer_adj_mean = _peer_means(adj, peers)` over K=10 skill-matched peers; `engagement_raw = zscore(raw UN-LOGGED components)`. CAVEAT for any decomposition: the reported `peer_engagement_mean` column is `_peer_means(er)` (OBSERVED peer mean, used by OAQ_observed) — NOT the term portable subtracts. An early split (59/41) computed with it was WRONG; numbers below use `peer_adj_mean`.

**TEST 1 — components populated? (rule out data gap):** Makar wiki 377,994 / intl 83,728 / trends 0.326 / reddit 508 mentions, 84,222 upvotes -> er 1.343 (clean). Q.Hughes er 5.396 (wiki 1.42M), MacKinnon er 2.83, Stanley er 0.048 (wiki 63,868). No missing data.

**TEST 2 — absolute prominence vs relative OAQ (why Makar is #35):** by absolute engagement_raw among D: Q.Hughes #1 (5.40), Hutson #2, Schaefer #3, Makar #4 (1.34) — but Makar OAQ_portable rank = 35. Dahlin abs#6 -> OAQ #184; Bouchard abs#7 -> OAQ #217. Makar's peers are elite D (peer mean 1.02); he's attended ~as expected for tier -> near-zero over-index. OAQ measures over/under-attention, not fame.

**TEST 3 — own-adj vs peer-floor decomposition + A17 log-lens (log1p components before z):**
| Player | RAW oaq / D-rank / own:peer | LOG oaq / D-rank / own:peer |
|--|--|--|
| Logan Stanley | 0.78 / 10 / 6:94 | 1.10 / 10 / 34:66 |
| Ian Cole | 0.99 / 4 / 71:29 | 0.64 / 41 / 75:25 |
| Radko Gudas | 0.86 / 8 / 60:40 | 1.42 / 2 / 69:31 |
| Darnell Nurse | 0.91 / 6 / 53:47 | 1.09 / 11 / 80:20 |
| Aaron Ekblad | 0.89 / 7 / 65:35 | 1.12 / 9 / 87:13 |
| Quinn Hughes | 4.77 / 1 / 109:−9 | 1.84 / 1 / 136:−36 |
| Cale Makar | 0.36 / 35 / (oaq tiny) | 0.63 / 42 / — |
LOG top-10 D reorders materially: Hughes, Gudas, Jiricek, S.Dickinson, Xhekaj, Bichsel, Letang, Mailloux, Ekblad, Stanley (Ian Cole 4->41, Gudas 8->2). engagement_raw is z-scored on a right-skewed dist (median NEGATIVE); Stanley own z 0.048 = 75.7th pctile.

**TEST 4 — is Stanley genuinely out-buzzing his cohort, or is peer-mean outlier-dragged?** Stanley's 10 peers: own er 0.048 vs peer mean −0.316, MEDIAN −0.366 (median <= mean -> NOT outlier-dragged). Stanley beats 9/10 peers individually (only Walman +0.135 above him). Wiki: Stanley 63,868 vs peer-median 36,325 (~1.75x). Ian Cole: beats 10/10, own er 0.708 (but Cole's own wiki 33,523 < peer-median 37,116 -> Cole's buzz is reddit/trends-driven, not wiki).

**The two positions:**
- Assistant (initial): Stanley's score is 94% peer-floor -> floats up because peers are anonymous -> proposed a two-gate publish guard (own-share>50% AND own>=median).
- Owner (pushback): if Stanley genuinely generates more buzz than the players he's matched to, that IS the index doing its job — a low peer floor is a legitimate route to a high score, not an artifact. Product-wise it's a usable signal (buzz-per-skill acquisition target; or vs cap, an overpay cautionary example).
- Test 4 favors owner (9/10 beaten, median-robust, 1.75x wiki); assistant withdrew the artifact framing and the guard. Genuinely UNRESOLVED: cross-tier SCALE (+0.78 vs +4.78 not linearly importance-comparable under z-on-skew) and the RAW<->LOG rank instability in Test 3 (tail fragility).

**DECISIONS FOR STRONGER MODEL (decide independently; do not assume owner or assistant view):**
1. Stanley-class output — feature (real over-index) or artifact (scale/estimator)? Weigh Test 4 (feature) vs Test 3 raw<->log instability (caution).
2. Switch PRIMARY engagement RAW->log1p? A17 log-lens is reporting-only; primary locked RAW under A5/§13 anti-tuning commitment. Trade anti-tuning discipline vs demonstrated tail rank instability.
3. If kept RAW: is a presentation guard warranted (show absolute engagement / own-percentile beside OAQ so rank != fame)? Is peer-mean shrinkage / empirical-Bayes needed, or unnecessary given Test 4?
4. Sanity-check the corrected decomposition (adj_own vs peer_adj_mean) and the claim that the `peer_engagement_mean` column is NOT the term portable subtracts.

## OPEN ITEM #3 — two data-quality observations from the top-100 OAQ_portable list (STRONGER MODEL TO DECIDE)
Both surfaced eyeballing the top-100 (in-memory, corrected data). Numbers are real.

**3A — missing-skill STAR gets a headline OAQ via imputation.** 7 pool players have null skill inputs (ppg/toi/GP all NaN → `onice_status="missing"`, `small_sample=1`). 6 are depth (OAQ ~0/neg: Davies, Perunovich, Szuber, Grans, Clarke, McCartney). The 7th is **Aleksander Barkov (FLA) — ranks #15 overall at OAQ 2.01** despite NaN ppg/toi/GP (raw nhl_skill row all NaN — missed 2025-26, injury). Mechanism: missing skill → group-mean imputation for K=10 peer matching → Barkov peer-matches to average-skill players whose engagement sits far below his star-level engagement → large over-index. Bites ONLY for missing-skill STARS (depth players with missing skill have low engagement too → no inflation). 1 case in top-100 now (Barkov); recurs for any injured/absent star.

**3B — Montreal floods the top: 16 of top-100** (next: EDM 8, SJ 7, FLA 7); **16 of 26 Habs in pool = 62%**. OAQ_portable is meant to STRIP market so scores are portable. MON `market_z` mean = **0.359** (positive→discounted, λ·0.359≈0.18 removed) vs league mean −0.045, max 2.571. `market_z` (metro population + arena attendance) rates Montreal only mildly big, but Habs media/fan intensity far exceeds population → engagement not offset → 62% of the roster in the league top-100.

### For stronger model (issue #3):
9. 3A: rule on missing-skill-star handling — exclude from published tables (the `onice_status="missing"` / `match_quality` flag already exists), re-impute differently, or keep-with-flag?
10. 3B: is 16/26 MTL in top-100 (a) the market-strip UNDER-correcting — metro-pop/arena proxy misses fanbase intensity, so "portable" isn't portable and may need a fanbase-intensity term; or (b) real signal — Habs genuinely over-index vs production twins, which is what the index claims to measure (then document that portable still carries fanbase intensity)?

## OPEN ITEM #4 — DEGENERATE PEER SET for thin/small-sample rows with an extreme rate feature (STRONGER MODEL TO DECIDE)
Surfaced by owner eyeballing Kevin Rooney's (UTA, f1) K=10 skill peers — flagged incoherent: peer set spans **Brandon Hagel (1.04 ppg, 19.8 TOI, $6.5M star) down to Hayden Hodgson (0.00 ppg, 7.0 TOI)**. Owner: "Hagel is way better than these other players, that makes no sense." Investigated in-memory (no files). It's a real defect, DISTINCT from #2/#3.

**Rooney facts:** `games_played=1`, `ppg=1.000` (literally 1 point in 1 NHL game), `toi_per_game=9.73`, `onice_status="thin"`, `small_sample=1`, cap $0.775M. OAQ_portable −1.97 = **dead last #771/771**. `match_quality="ok"` (!).

**Mechanism (verified in code, `_standardize_skill`/`compute_peers`, SKILL_COLS=[age,ppg,toi_per_game,cf_pct,xgf_pct,ozs_pct]):**
1. **Garbage rate from 1 GP.** ppg=1.0 off ONE game is fed to the distance metric as a stable rate → Rooney's standardized ppg z = **+1.93** (≈96th pctile of f1 scoring). His extreme axis is an artifact.
2. **On-ice imputed to centroid.** cf/xgf/ozs all NaN (thin) → A13 group-mean impute → z≈0 on 3 of 6 features. Half his vector is forced to "average," so the corrupted ppg + age + low-TOI axes dominate the match. (This is the A13/A28 imputation-shrinkage interaction, but here it AMPLIFIES a bad rate rather than a missing one.)
3. **Empty neighborhood → least-bad = incoherent.** high-ppg + low-TOI is a near-empty region of f1 (high scorers normally play big minutes). Nearest-K Mahalanobis d2 = **28.9–87.6** (a normal player's peers sit ~<5). Hagel is actually one of the *closer* rows (d2=42.15) precisely because he's the only cohort that matches Rooney's fake +1.93 ppg (zdiff ppg −0.14) — but he's off by toi −2.51, cf −2.09, xgf −2.18. The metric trades "match ppg → stars" against "match role → depth," landing on a set spanning 0.00–1.04 ppg. Peer avg cap **$2.16M** / median $1.225M vs Rooney $0.775M — the incoherence is visible in $ too.
4. **No absolute-distance gate.** `match_quality="ok"` despite nearest peers being 5–9 Mahalanobis units out. The existing flag keys off something else; it does NOT catch a degenerate neighborhood.

### For stronger model (issue #4):
11. **Publish gate for thin/small-sample rows:** should `small_sample=1` / `onice_status="thin"` rows be EXCLUDED from published ranking (flags already exist)? Rooney's dead-last is an artifact, not signal. (Overlaps #3A missing-skill handling — unify the thin/missing/small-sample publish policy.)
12. **Guard rate features from low GP:** min-GP floor before ppg/toi are trusted, or shrink ppg toward group mean by GP (empirical-Bayes / `ppg_adj = (P + τ·μ)/(GP + τ)`)? 1 GP should not yield a 96th-pctile scoring z.
13. **Absolute peer-distance → match_quality downgrade:** flag/hold rows whose mean nearest-K d2 exceeds a threshold (Rooney 28.9–87.6 vs normal <5). Distinct from the existing `match_quality` logic, which passed him.
14. **A13 centroid-impute + corrupted rate interaction:** when 3/6 skill features are centroid-imputed, the remaining (possibly corrupted) features fully drive matching. Reconsider imputation, per-feature reliability weighting, or requiring a minimum count of OBSERVED features before a row is eligible for a peer list.

NEXT: #1 skill fix is CORRECTNESS-VERIFIED pool-wide (764/764 == NHL published totals) — safe to COMMIT whenever owner wants; stronger-model pass on it is optional/confirmatory only. Genuinely-open items for the stronger model are #2 (OAQ_portable low-tail behavior, Tests 1-4 + decisions 1-4), #3 (missing-skill-star imputation + Montreal market-strip, pts 9-10), and #4 (degenerate peer set for thin/small-sample + extreme-rate rows, pts 11-14) — all DEFERRABLE design questions, nothing changed, nothing pre-decided. Refetch done+verified; exploratory index runs already shown to owner (Ohgren dropped out of surprising list post-fix; top-100 reviewed). Still NO production `compute_oaq` run (gated: Phase-1 hygiene + Gate-4, per airtight plan §E).

OWNER (unchanged, 2 items): (a) eyeball `marchand_index/raw/reddit_identity_pairs.md` (A21 acceptance); (b) YouTube API key -> U1 dry-run + Gate-4.

CARRY-FORWARD: 240 tests; pool 771; window [2025-04-18, 2026-04-17]; A12 weights unchanged; impl seed 20260526 / spec seed 20260522 (never harmonize); cache/reddit_corpus/ GITIGNORED LOCAL SOURCE OF RECORD; english_top1000.txt pinned (never edit). Next free amendment number: A45. `fetch_nhl_api.py` patched (extract_skill trade-aggregation) — NOT yet committed; `raw/nhl_skill.csv` regenerated by refetch.

Deadline: poster 2026-09-12 (~7.4 wk).
