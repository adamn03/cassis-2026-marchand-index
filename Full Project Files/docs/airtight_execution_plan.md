# Airtight Execution Plan — Marchand Index Production Run
**Version: 1.1 — panel-chair APPROVED; final executability sweep applied 2026-07-07. Do not begin Phase 2 until owner decisions in §D are made and the §I checklist is green.**
Date: 2026-07-07

> **Execution status addendum (2026-07-15 — status only, plan body unedited):** §D decisions MADE 2026-07-13 (D-1 GO+U1, D-2 rebuild primary, D-3 sign-off+U2; recorded impl prereg §14, commit 91ab66b). Phase 0 in progress: A21–A26 committed (text+code), A27 text committed / code pending verify, A28+ pending in order. Reddit source switched to Arctic Shift (see `superpowers/plans/2026-07-13-arctic-shift-source-switch.md` — supersedes §B A23 spec, Task 1.8, and the §E creds trigger). Corpus pull under way (cache only — reddit_counts.csv still 0/774; governing rule intact). Tests: 141 committed (was 102 at v1.1). Supplements in force: free-data (A36/A37), cross-domain (A38/A39), idea-max §4 (A40), A41 pool dedup 774→771.
Built from: internal audit (E1–E9) + three-judge CASSIS panel (hostile statistician J1, NHL club practitioner J2, validation methodologist J3). Every step is written to be executable by a weaker model: exact file, exact rule, acceptance criterion, verification command.

## Governing rule
**Reddit is 0/774 fetched. No production results exist.** Every amendment logged before the Reddit fetch is cleanly pre-registered; the same change made after compute is post-hoc tuning. Phase 0 (amendments) and Phase 1 (data hygiene) MUST complete before any Reddit data lands. Amendment template = the existing one in `Full Project Files/marchand_index/preregistration.md` §14: date, what changed, mechanical rule, honest residuals, anti-tuning compliance paragraph. **Commit each amendment BEFORE writing the code that implements it.**

Paths below are relative to `Full Project Files/` unless absolute. Prereg-impl = `marchand_index/preregistration.md`. Prereg-spec = `docs/preregistration.md`. Run tests from inside `marchand_index/` with `pytest -q` (currently 102 passing).

---

## §A — Panel verdict summary

Internal E1–E9: all CONFIRMED by panel (E8, E9 amended — see A23, A30). Panel added 20+ findings. The three attacks that would have sunk the poster:

1. **The headline metric was never validated** (J1-N1): every gate tests OAQ; `marchand_index_hybrid` is touched by no pathway. → headline must be the OAQ validation finding (A31).
2. **"≥3 independent validation pathways" is currently unmet** (J3-F2): jersey V1a+V1b = ONE family; V2 underpowered at n=8; V3 is shared-method (same platform as 0.40 of composite weight). Honest count = 1. → Gate-4 GO is mandatory, V2 must be powered via ASG archive union, V3 relabeled "aggregation-consistency check" (A29, A33, Phase 3).
3. **Reddit (0.44 weight) measures "plays for a Canadian team"** (J2-F1): team-sub volume anti-correlates with metro population (WPG: 0.8M metro, Canadian-scale fanbase). One-sided λ gives WPG zero correction; portable OAQ credits fanbase intensity as personal attention. → market proxy rebuild (A30).

### Pathway independence classification (adopted from J3)
| Pathway | Class | Counts toward ≥3? |
|---|---|---|
| V1a+V1b jersey | Independent (heteromethod: purchase behavior). ONE family. V1b temporally impure (2 of 3 union lists predate window) — disclosed. | Yes (1) |
| V2 ASG | Independent method; n=8 uninformative until A33 union powers it | Yes (2) if A33 reaches n≥10 |
| V3 team wiki | Construct-overlapping, borderline shared-method | **No** — "aggregation-consistency check" |
| Gate-4 YouTube | Construct-overlapping-but-usable, heteromethod, only sub-star test | Yes (3) — **load-bearing** |

---

## §B — Phase 0: pre-registered amendments (no data dependencies)

Execute in order. Each step = (1) write amendment text, (2) commit, (3) implement code, (4) add tests, (5) commit code. Commit message convention (matches repo history): `marchand_index: A<N> <one-line summary>` for the amendment commit; `marchand_index: A<N> code + tests` for the implementation commit. Exception to strict order: A30 is written only AFTER owner decision §D-2.

### A21 — Reddit identity: non-discriminable names + team-sub attribution
Sources: E1, J2-F5. Files: prereg-impl §14, then `marchand_index/fetch_reddit.py` (`build_surname_map`, `make_evidence_check`, lines ~116-180).
Rules:
1. For each shared-surname group, first names `a`,`b` PREFIX-COLLIDE iff `a.startswith(b) or b.startswith(a)` after accent/case folding. If a player's first name prefix-collides with another sharer's, first-name evidence is NON-DISCRIMINATING for that pair.
2. Team-subreddit context rule: within a TEAM subreddit, if exactly ONE pool sharer of the surname is on that team, bare-surname submissions attribute to him. "On that team" = the **A22 window-roster set** (NHL seasonTotals derivation), NOT the snapshot roster. If MORE than one pool sharer of the surname is window-rostered on that team, bare-surname submissions in that team's sub → `ambiguous_mentions`. This resolves the two Sebastian Ahos (CAR vs NYI) inside team subs. DEPENDENCY: A21 depends on A22's roster derivation — write A22's roster function first or stub it. Add a fixture test for a traded sharer.
3. Remaining non-discriminable cases (two Elias Petterssons, BOTH on VAN — same team sub, same first name): all matching submissions → `ambiguous_mentions`, attributed to NO ONE; both rows get `reddit_identity_ambiguous=true`; disclosed count in `results.md`.
4. In r/hockey, prefix-colliding pairs: first-name evidence non-discriminating → ambiguous unless a TEAM NICKNAME token for exactly one sharer's team appears in title/selftext. Token definition (mechanical): the final word of the team's full name from `raw/teams.csv`, accent/case-folded, matched as a whole token (e.g. "hurricanes", "islanders", "canucks"). Do NOT use 2–3 letter team codes as tokens (false-positive prone: "LA", "SJ"). If nicknames of BOTH sharers' teams appear, → ambiguous.
Tests: (a) Pettersson pair → both ambiguous everywhere; (b) Aho in r/canes → CAR Aho; Aho in r/hockey with "Hurricanes" in title → CAR Aho; bare "Aho" in r/hockey → ambiguous; (c) unique surname unchanged; (d) "Matt"/"Matthew" prefix collision detected.
Acceptance: pytest green; dry-run script prints all non-discriminable pairs from `players.csv` (expect the known ones). OWNER STEP: owner reviews the printed pair list by eye before the fetch launches.

### A22 — Reddit traded-player multi-sub coverage
Source: J2-F3 (HIGH). Files: prereg-impl; `fetch_reddit.py` sub-selection.
Rule: for each player, query team subs of EVERY team he was rostered on inside the window [2025-04-18, 2026-04-17], derived mechanically from NHL API `seasonTotals` rows (season IDs 20242025 and 20252026, `leagueAbbrev=="NHL"`, `gameTypeId==2`) mapped to team subs via the existing team→subreddit mapping already used by `fetch_reddit.py` (in/derived from `raw/teams.csv` — reuse it, do not build a new one). 2024-25 rows are included because the window's first ~2 months (Apr–Jun 2025) cover that season's playoffs/offseason, when a player is still discussed in his former sub. r/hockey unchanged. Dedup by submission id across subs. `reddit_subs_searched` column records the list.
Honest residual: mid-season attention in a former team's sub before an unrecorded (non-NHL-roster) stint is still missed; disclosed.
Tests: fixture traded player → two team subs queried, union deduped.
Acceptance: dry-run prints players with >1 sub (sanity: matches known deadline moves).

### A23 — Reddit cap censoring: second pass + lower-bound declaration
Sources: E8 (as amended by J1), J2-F11. Files: prereg-impl; `fetch_reddit.py`.
Rules: (1) any (subreddit, query) hitting the 1,000-result cap gets ONE additional pass with `sort=top&t=all`, union by id. Mechanics differ from the primary pass: top-sort is not chronological, so the A11 skip/stop paging shortcut does NOT apply — page to the cap, filter client-side by `created_utc` within the window, then union. (2) Pre-declare: capped players' `reddit_mentions/upvotes` are LOWER BOUNDS; z-scores for capped rows are floor estimates. (3) Pre-declare attenuation direction: censoring compresses star-tier ranks and biases V1a AGAINST the model ("conservative for us"). (4) Report: count of still-capped players overall and within the V1 overlap; sensitivity rank with capped players' Reddit components set to the capped maximum. (5) Star-tier rank sanity leans on wiki_en (uncensored).
Acceptance: unit test for union-dedup; results.md emits capped counts + sensitivity block.

### A24 — Denominator: rookie flag from contract type; market-rate fit on market contracts
Sources: E2, J2-F2, J2-F6. Files: prereg-impl; `marchand_index/fetch_cap_hits.py` (extract contract type); `compute_oaq.py` `compute_expected_cap` (~line 491) + rookie flag (~line 133).
Rules:
1. `is_rookie_deal` keyed on the CapWages `__NEXT_DATA__` contract-type/signing-status field (entry-level flag), NOT the price+age proxy. Field-discovery procedure (do this FIRST, before writing the amendment): dump `__NEXT_DATA__` for 3 known ELCs (Bedard, Celebrini) and 3 known veteran deals; identify the field that distinguishes entry-level (look for keys like `contractType`, `signingStatus`, `expiryStatus`, `entry_level`); record the exact key path in the amendment. If NO such field exists in the JSON, the amendment instead pre-declares the price+age proxy as the sole rule (status quo) with the misclassification risk disclosed — do not invent a heuristic. Where the field exists but is missing for individual rows, price+age proxy is the per-row fallback; `rookie_flag_source` column records which path fired. (Kills both misclassification directions: bonus-laden ELCs above $0.975M; cheap post-ELC RFA deals below it.)
2. expected_cap OLS fit ONLY on `is_rookie_deal == False` rows with finite predictors+cap; predict for ALL; floor $0.775M unchanged.
3. Fit on `log(cap_hit_M)`; back-transform via the **Duan (1983) smearing estimator** (simple `exp()` retained as a code-comment alternative, not computed). Linear-all-rows fit retained as audit lens. (Convention: Evolving-Hockey-style contract models price on log scale.)
4. Disclose: current-season stats stand in for platform-year; term/UFA-RFA status omitted; defensive D underpriced by PPG-based fit.
Tests: synthetic ELC-contaminated fixture → non-rookie log fit recovers market slope; Bedard/Celebrini/Hutson rows assert `rookie_flag_source=contract_type`.
Acceptance: printed before/after table of rookie expected_cap (all should rise or stay).

### A25 — Missingness taxonomy for sentinel renorm
Source: E3. Files: prereg-impl; fetchers (set `null_reason` per component: `no_entity_exists` vs `fetch_failed`); `compute_oaq.py` engagement assembly.
Rule: `fetch_failed`/blocked → weight renorm (current behavior; MCAR defensible). `no_entity_exists` (wiki_match=none with confirmed no page; trends with no topic AND empty series) → impute RAW value 0 before z-scoring, no renorm for that component.
Acceptance: unit test — no-page player scores strictly lower than under renorm; `results.md` lists every `no_entity_exists` row.

### A26 — Block bootstrap + propagated-uncertainty table
Source: E7. Files: prereg-impl; `compute_oaq.py` bootstrap.
Rule: wiki daily vectors resampled in 7-day circular blocks (Politis–Romano convention). Exact procedure: treat the 365-day vector as a ring; each draw samples 53 uniformly-random block start indices, concatenates the 7-day blocks, truncates to 365 days. Reddit pool resampling unchanged; seed 20260526 unchanged. `results.md` + poster carry a table: propagated (wiki days, reddit pool) vs NOT propagated (peer sets, trends values, market proxy, expected_cap fit).
Acceptance: unit test — autocorrelated synthetic vector yields wider CI under block than iid; deterministic under seed.

### A27 — Star-boundary matching bias: diagnostic + corrected lens
Source: E5 (J1 CONFIRM: textbook boundary bias, Abadie & Imbens 2011). Files: prereg-impl; `compute_oaq.py`.
Rule: (a) ship `peer_skill_gap` = mean(player − peer) on each standardized skill feature, plus the scalar summary defined as the **mean of absolute standardized per-feature gaps**; (b) reporting-only lens `OAQ_bc = OAQ_observed − β̂ᵀ(x_P − x̄_peers)`, β̂ from within-position OLS of `engagement_raw` on the standardized 6-feature skill vector. Primary unchanged. Report Spearman rank agreement primary vs bc; agreement < 0.8 is itself a reported finding (A17 status-rule language verbatim). `OAQ_portable_bc` uses the SAME β̂ (from the engagement_raw-on-skill regression — do not refit on the market-adjusted quantity) applied to the portable residual.
Acceptance: synthetic convex attention-in-skill fixture — bc lens removes mechanical boundary positivity; rank-agreement stat in `results.md`.

### A28 — Thin-sample peer-eligibility sensitivity
Source: J1-N6. Files: prereg-impl; `compute_oaq.py` peer selection.
Rule: sensitivity re-run with `onice_status=thin` rows INELIGIBLE as peers (still scored themselves; group-mean imputation shrinks them to the centroid → over-selected as peers, understates covariance — Rosenbaum & Rubin 1984 cautions). Report rank agreement vs primary.
Acceptance: test — thin player absent from all peer lists in sensitivity mode.

### A29 — V3 repair: fixed window, team-level bootstrap, Utah dual-title, relabel
Sources: J1-N7 (code-confirmed: `fetch_team_outcomes.py:89` is run-anchored), J2 landmine (Utah), J3 independence table. Files: prereg-impl; `fetch_team_outcomes.py`; results labeling.
Rules:
1. Team Wikipedia pageviews on the EXACT fixed window [2025-04-18, 2026-04-17] (same WINDOW_START/WINDOW_END constants as wiki fetchers). Re-fetch `team_outcomes.csv`.
2. Utah: article renamed "Utah Hockey Club" → "Utah Mammoth" INSIDE the window; pageviews API does not follow redirects (A1 lesson) → fetch BOTH titles, sum. Audit check for all 32 (mechanical): for each team's canonical article, enumerate redirect titles via MediaWiki API `prop=redirects`; fetch in-window pageviews for the canonical title AND every redirect title; sum all non-zero series (views to a redirect title are legitimate views). Report per-team the redirect share so any surprise (another rename) is visible.
3. V3 bootstrap resamples TEAMS (n=32 exchangeable units), not players.
4. Relabel V3 everywhere (results.md, poster) as "aggregation-consistency check" — NOT counted toward the ≥3 independent pathways. A18 interpretation rule unchanged.
Acceptance: re-fetched CSV window columns assert fixed dates; UTA total ≥ old value; V3 CI from team-level draws.

### A30 — Market proxy rebuild (OWNER DECISION #2 — recommended YES)
Sources: J2-F1 (HIGH), J2-F8, E9. Files: prereg-impl; `fetch_market_proxy.py`; `market_proxy_sources.md`.
Recommended rule (amends the locked primary — defensible ONLY because zero production results exist and the confound is first-order on 0.44 of composite weight):
1. `MarketSize_team` = equal-weight z-mean of: (a) `metro_population` (unchanged), (b) `team_sub_subscribers` — team subreddit subscriber count via the A9 OAuth transport (`oauth.reddit.com/r/<sub>/about`), which unblocks the component class A6 had to drop; this is the HOCKEY-market size metro pop cannot see, and it is Reddit-side control for a Reddit-heavy composite, (c) `attendance_pct_capacity` — announced attendance ÷ arena capacity, replacing raw attendance (raw = arena size at sellout, J2-F8). Sources, both $0 and URL-documented in `market_proxy_sources.md` per the A20 pattern: attendance = Hockey-Reference 2024-25 season attendance table (ESPN's page is bot-walled, per existing sources doc); capacities = the Wikipedia NHL-arenas list already cited there.
2. Old proxy (metro + raw attendance) retained as `market_z_lockedv1` audit lens; metro-only retained as sensitivity (E9). λ ladder unchanged.
3. Disclosures: subscriber count is a stock read at fetch date (market size is a slowly-varying stock — acceptable, unlike player-attention flows); announced ≠ turnstile; shared-metro overstatement for NYI/NJ is one-directional (over-discount) under one-sided λ = conservative; UTA carries relocation novelty.
Fallback if owner declines: keep locked primary, ship team-sub-subscribers version as pre-registered sensitivity + poster disclosure that the primary cannot see fanbase intensity. (Weaker: the confound then sits in the HEADLINE quantity.)
Acceptance: 32/32 subscriber counts fetched; proxy correlation matrix printed (expect metro ⊥ sub-subscribers divergence for Canadian teams).

### A31 — Confirmatory hierarchy, V1b floor, baselines, headline structure
Sources: J1-N1/N2/N3/N5, J3-F3/F4, J2-F4, E4. Files: prereg-impl; `compute_oaq.py` validation section (~line 850); poster copy.
Rules:
1. **V1b = sole confirmatory primary.** Floor AUC ≥ 0.70 / target ≥ 0.80 (Hosmer–Lemeshow "acceptable discrimination"); bootstrap CI is STRATIFIED at the player level — each of the 1,000 draws resamples the 12 positives and the 762 negatives separately, with replacement (unstratified draws can contain 0 positives → AUC undefined); seed 20260526; Hanley & McNeil 1982 cited; 12 positives → wide CI disclosed. Interpretation rule for the primary itself: if point AUC ≥ 0.70 but the 95% CI includes 0.50, the verdict is "floor met on point estimate, not resolved from chance at n=12 positives" — this outcome maps to shipping-matrix row 2 below, decided now.
2. V1a, V2 (post-A33), V3 = secondary family, Benjamini–Hochberg across them. BH mechanics (fixed now): compute a one-sided p-value for each secondary test (V1a: exact permutation p for Spearman at n=10; V2: bootstrap p for its statistic; V3: permutation p for Spearman at n=32); apply BH at q = 0.05 across the three. Division of labor: the pre-registered FLOORS still govern each test's pass/fail verdict; BH governs only the "statistically supported after multiplicity control" label a result may carry on the poster. PC relabeled DESCRIPTIVE (not a validation). All lens/sensitivity tables labeled descriptive robustness.
3. **Baseline-comparison rule (A18 extended to V1, locked verbatim):** report `engagement_raw` AUC and PPG AUC beside OAQ_portable's, plus OAQ_observed vs jersey as the construct-matched pairing (jersey sales are market-loaded; portable strips market). Interpretation fixed in advance: baseline ≥ OAQ is EXPECTED (outcome responds to total fame) and is not evidence against the construct; OAQ clearing its own floor supports only the narrower surplus-retention claim. A pass with OAQ ≈ raw-fame baseline AND large `peer_skill_gap` correlation is the boundary-bias signature (E5) and is reported as such.
4. **V1a interpretation (E4/J2-F4):** n=10 Spearman reported with bootstrap CI + exact permutation p; floor-pass with CI spanning 0 = "directionally consistent, underpowered for significance"; NEVER quoted standalone; never called "powered".
5. **Headline sentence structure (registered with placeholders):** "OAQ_portable separated the 12 official jersey-list players from the other 762 skaters with AUC = X.XX (95% bootstrap CI a–b); the list is star-tier only, ranking without units." Named case study follows as ILLUSTRATION, never evidence. All MI lenses demoted to a descriptive per-dollar panel; within-cap-tier panel per J1-N8 (cross-tier ranks not variance-standardized — disclose heteroskedasticity).
6. Gate-failure shipping matrix — the amendment must CONTAIN this matrix (a weaker model must not invent it). Skeleton, all 8 rows filled in the amendment; the two extreme rows worded now:
   | Row | V1b | Secondary family (BH) | Gate-4 | Headline tier |
   |---|---|---|---|---|
   | 1 | pass, CI excludes 0.50 | pass | pass | Full headline: "OAQ_portable separated the 12 official jersey-list players from the other 762 skaters with AUC = X.XX (95% CI a–b), replicated across an independent fan-vote pathway and an outside-star YouTube generalization test." |
   | 2 | pass on point, CI includes 0.50 | any | any | Downgraded: "directionally consistent, unresolved from chance at n=12" — no validation language in the headline; validation panel reports estimates + CIs only. |
   | 3–7 | (fill all intermediate combinations in the amendment) | | | |
   | 8 | fail (< 0.70) | fail | fail/NO-GO | "The pre-registered validation gates were not met; the index is reported as an exploratory descriptive instrument with its validation estimates and CIs shown. No validated-metric claim appears anywhere on the poster." |
   No ad-hoc downgrades outside this matrix.
Acceptance: amendment text contains the floor, the BH family, the baseline rule, the sentence template, the shipping matrix. Code emits baseline AUCs + BH-adjusted table.

### A32 — Exploratory/confirmatory split + pilot-overlap disclosure
Sources: J1-N4, J3-F1. Files: prereg-impl; poster copy.
Rule: pilot era (14-player; 160-player incl. the outcome-inspected A4/A5/A8 revisions) = EXPLORATORY, design-generating (Nosek et al. 2018 PNAS). The 774 run = the sole confirmatory test of the frozen design. Required disclosure sentence (poster + results.md): "Headline definitions were amended after inspection of an overlapping pilot sample; they were locked before the production fetch and are pre-specified, not strictly confirmatory. Locked-original variants (raw-cap MI, two-sided λ=1 OAQ, **and `market_z_lockedv1` — the pre-A30 market proxy**) are reported alongside, and validation verdicts are shown to be invariant (or not) across them." Implement the invariance panel: recompute V1b/V1a/V2/V3 point estimates under ALL locked-original variants including the old market proxy; report deltas. (The market-proxy entry is what closes A30's residual anti-tuning exposure: pilot-era results were seen under the old proxy.)
Acceptance: invariance panel emitted in `results.md`.

### A33 — Power V2: ASG fan-vote archive union 2022+2023+2024
Source: J3-F2. Files: prereg-impl; `fetch_external_outcomes.py`; `external_outcomes_sources.md`.
Rule: V2 membership = union of players selected via an OFFICIAL FAN-VOTE component of the 2022, 2023, 2024 All-Star selections, as named in NHL.com press releases (the fan-vote mechanism differs by year — captains vote, "Last Men In", full fan ballot; document each season's exact mechanism in `external_outcomes_sources.md` and take only fan-voted names, never league/player-selected ones). Sources URL-documented per the A20 pattern (≥2 independent URLs per season); NHL-id-keyed join per the A20 namesake guard. If in-pool overlap reaches n ≥ 10, V2 is powered under its existing floor; else stays underpowered as pre-declared. Temporal mismatch (votes predate window) disclosed as attenuation, same class as V1b's.
Acceptance: `external_outcomes.csv` rebuilt; overlap count printed; sources file updated with ≥2 independent URLs per season list.

### A34 — Published-leaderboard display rule
Source: J2-F7. Files: prereg-impl; `compute_oaq.py` results emit.
Rule: rows with `small_sample=true` OR null current-season GP (Barkov class: attention floored by absence, skill features imputed → fake negative OAQ tail) are EXCLUDED from every PUBLISHED leaderboard/panel (kept in CSV with all values; count disclosed). Injury-attention confound added to limitations.
Acceptance: test — flagged row absent from emitted leaderboard tables, present in CSV.

### A35 — Small-items batch (one amendment, five clauses)
Sources: J1-N9, J3-F7, J2-F12, J2-F14, J2-F10.
1. Trends: Marchand's own row gets a pre-declared secondary anchor, NAMED NOW: the Google Trends topic entity for **"Sidney Crosby"** (hockey-native, star-magnitude — adequate resolution against Marchand's own star-tier series; applies to the anchor player's row only). ≡1.0 degeneracy disclosed on his case card. Depth-player zero-quantization count reported.
2. A17 escape-clause plug (verbatim): "No log-lens number appears in the headline, abstract, or leaderboard panels under any outcome."
3. Goals-rate robustness: pre-declared re-run with goals/60 replacing PPG in the peer vector (fame follows goals); reported as rank agreement only.
4. Reddit construct disclosures: submissions-only (comments/game-threads invisible; depth players disproportionately comment-borne); `score` read at fetch time (post-window vote accrual partially re-imports the playoff confound — first-order uniform, disclosed).
5. Nationality note: intl-wiki (0.11) responds to nationality with no peer control — deliberate (attention drivers are the signal), disclosed.

### Gate-4 amendments (in `docs/preregistration.md` §11) — log as **G4-A1, G4-A2, G4-A3**
Sources: E6, J3-F8, A10-scope. Before ANY YouTube fetch. Numbering scheme: use the **G4-A series** in docs/preregistration.md (spec-level series, distinct from the impl A-series; do NOT use bare A-numbers in that file — its existing A10/A11 entries mirror impl numbering and bare continuation would collide with impl A12+). Each entry cross-references this plan and carries the standard anti-tuning paragraph.
1. §7.2 relevance: title must contain the player's LAST name (kills "Connor"-matches-McDavid-videos-for-Bedard). Pool-shared surnames additionally require first name or team tag in title. Same-team identical-full-name pairs (Petterssons) excluded from Gate-4 cohort, disclosed.
2. Censoring disclosure: ≥500-view floor + title-match select on the outcome and censor depth players; state the direction (biases the depth band toward null) in the Gate-4 table.
3. Update the A10 scope note: Gate-4 results WILL be claimed on the poster (it is now load-bearing pathway #3).

---

## §C — Phase 1: data hygiene (parallel with Phase 0; all before Reddit fetch)

| # | Task | Detail | Acceptance |
|---|---|---|---|
| 1.1 | Finish Trends | `raw/trends.csv` at 331/774 (4 null) as of 2026-07-07. Re-run `python fetch_trends.py` (resumable ~9s/player) to 774/774 non-null. Targeted `git add raw/trends.csv` only. | 774 rows, 0 null |
| 1.2 | cap_quality triage (121/774 = 16%) — OWNER-ASSISTED | Bucket failure causes from `raw/cap_hits.csv` (slug 404 / parse / bounds). Pattern-scan slugs for accents, suffixes, "Jr.". Model produces the slug-correction candidate table; OWNER approves before re-fetch. Report missingness pattern vs age/cap tier (J1-N10) + exclusion count on poster. | low < 5% of pool; pattern table in results.md |
| 1.3 | ELC cap-field audit | Check Bedard/Celebrini/Hutson `cap_hit_M` vs $0.975M — if any exceed it, J2-F2(a) was live; A24 contract-type flag fixes it; record in amendment. | 3 rows verified |
| 1.4 | Duplicate-vector scan | Exact-equality scan across 774 of component raw vectors, peer sets, engagement_raw (Ben Jones / Nathan Walker identical-OAQ anomaly = join-bug signature). Root-cause any hit. | verdict in SESSION.md |
| 1.5 | Trends MID duplicates | Assert no duplicate `query_mid` across 774 (two Sebastian Ahos likely share one hockey-typed suggestion → wrong-entity, invisible to `trends_method` flag). Any duplicate → resolve by hand, flag. | 0 unexplained dupes |
| 1.6 | MoneyPuck join audit | Row-count join audit vs 774; verify one-row-per-playerId holds for deadline-traded players; state `oZoneShiftStarts` semantics (shift starts ≠ faceoff starts) on poster. | audit table |
| 1.7 | Case-study roster verification | Against locked `players.csv`: Marner (reportedly VGK), Reaves (in pool at all?), Marchand (FLA, champion framing), Hughes/McRae (verify or cut). Rebuild the 8-card list from players actually in the 774; Marner card reframes to "did attention travel out of Toronto?" if traded. If Reaves is absent, his archetype slot is filled post-compute by an equivalent low-skill/high-attention pool player — allowed because cards are ILLUSTRATION, never evidence (A31.5); label the selection as post-hoc editorial on the card. | card list matches pool |
| 1.8 | Reddit fetch readiness | Backoff + resume verified BEFORE launch (app-only OAuth = tight rate limits; 774 × multi-sub × t=all pagination = days). Sequential fetchers (shared sqlite http_cache). | dry-run 5 players clean |
| 1.9 | V3 re-fetch | After A29 code lands: re-fetch `team_outcomes.csv` fixed-window, Utah dual-title. | window asserted, UTA summed |

## §D — Owner decisions required (blockers, in order)
1. **Gate-4 GO/NO-GO.** Panel verdict: GO is mandatory — without it the ≥3-pathways criterion fails (J3-F2). ~8 fetch-days free quota, long-lead; starts right after the Gate-4 amendments, independent of Reddit.
2. **A30 market-proxy rebuild** (primary change vs sensitivity-only). Recommendation: rebuild primary — the Canada confound is first-order on 0.44 of weight and no results exist yet. Fallback documented in A30.
3. **A31 headline structure** sign-off (validation-finding headline; MI demoted to panel).

## §E — Phase 2: production compute (after creds + Phases 0-1 complete)
Sequential: purge `raw/reddit_counts.csv` + `raw/reddit_detail.csv` → `python fetch_reddit.py` (A15+A21+A22+A23) → `python fetch_wikipedia_intl.py` re-fetch (intl_match flag) → ONE `python compute_oaq.py` (seed 20260526; emits primary + all pre-registered lenses/sensitivities/invariance panel) → both `diagnostics/*.py` → verdicts written per A31 shipping matrix. NO weight, floor, or rule changes after this point; anything discovered post-compute is reported, not fixed.

## §F — Phase 3: Gate-4 (long-lead, starts immediately after Gate-4 amendments)
Band assignment (non-OAQ vars, prereg-spec §5) + YouTube fetch under §6/§7 as amended. OAQ side joins when Phase 2 completes. Escalation rule §6.2.2 governs coverage shortfall — no improvisation.

## §G — Poster limitations (complete set — every line must appear, poster-ready)
- Attention ≠ revenue; jersey list is a ranking without units — no dollar claims.
- Single season, single fixed window [2025-04-18 → 2026-04-17]; no out-of-window replication.
- Demographic skew: English Wikipedia + 7 hockey-market editions, Reddit (young/English/engaged), Google Trends; X/Instagram/TikTok dark.
- External validity established for the star tier (jersey family); outside-star validity per Gate-4 result.
- V3 shares platform, window, and news shocks with the heaviest input — reported as consistency check, not independent validation.
- Headline definitions pilot-informed on an overlapping sample; locked pre-production; locked-original variants + invariance panel reported (A32).
- λ = 0.5 market-portability is an unanchored maximum-entropy assumption; full λ ladder shown.
- Market proxy approximate (components + degradation per A30); expected_cap OLS deliberately crude (log-cap ~ PPG + TOI/G, non-rookie fit; term/UFA-RFA omitted; platform-year proxied by current season).
- Reddit: 1,000-result cap censors star counts (lower bounds; direction conservative); submissions-only, comments invisible; scores as-of-fetch; shared-surname filter lowers recall for those players (sensitivity cut shipped); non-pool namesakes persist; identical-name pairs unattributable (disclosed count).
- Bootstrap CIs understate: peer sets, Trends, market proxy, expected_cap fit not propagated (block-bootstrap wiki + reddit only).
- Window's oldest ~2 months overlap the 2024-25 playoffs (residual prior-season buzz).
- V1b union outcome: 2 of 3 jersey lists predate the attention window (temporal mismatch, attenuating); the V2 ASG union shares this class.
- Goalies excluded; ≥1 career NHL GP only; <20 GP flagged and excluded from published leaderboards (injury-attention confound); cap_quality=low rows excluded from MI panel (count + pattern disclosed).
- No quality-of-competition control; F/D split only (no C/W stratum); nationality uncontrolled in intl-wiki by design.
- Star-boundary matching bias possible; peer_skill_gap diagnostic + bias-corrected lens reported (A27).
- Themes, sentiment, polarization (H1–H4): pre-registered for the full build, NOT tested or claimed here; the index name is illustrative framing, not a tested polarization claim (J3-F5).
- Observational; no causal claims.

## §H — Forking-paths labeling rule (poster, verbatim)
"One primary estimate per claim: raw-scale composite, λ = 0.5, hybrid denominator, seed 20260526. Every other variant (λ ∈ {0,.25,.75,1}, raw-cap/expected-cap lenses, log lens, bias-corrected lens, surname-excluded cut, market-proxy variants, goals-rate peer vector) appears only in a single designated robustness panel, reported as direction-of-change vs primary, never as a ranking, and none was eligible to become the headline under any outcome."

## §I — Conformance checklist (verify before Phase 2)
- [ ] A21–A35 + Gate-4 amendments committed BEFORE their code, each with anti-tuning paragraph
- [ ] All tests green (target ~125+, from 102)
- [ ] Phase-1 acceptance criteria all met (trends 774/774, cap low <5%, dupes resolved, cards verified)
- [ ] Owner decisions §D recorded in prereg
- [ ] V1b floor + shipping matrix locked; headline template locked
- [ ] Gate-4 fetch launched (long-lead)
- [ ] SESSION.md updated to point at this plan
