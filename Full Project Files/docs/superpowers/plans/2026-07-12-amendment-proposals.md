# Amendment Proposals — A21–A29, A32–A35, G4-A1–A3 (DRAFTS)

**Execution status (2026-07-15):**

| Amendment | Text commit | Code commit |
|---|---|---|
| A21 | 112c5fe | ece1c68 |
| A22 | ab165c6 | ece1c68 |
| A23 (Arctic Shift rewrite) | 146aaeb | ece1c68 |
| A24 | f8d67e7 | a966fc7 (cap re-fetch with `contract_type` in progress) |
| A25 | e4449cf | cdb4c04 |
| A26 | e5f96c7 | 0f55ea0 |
| A27 | 2ddb75b | code in working tree, pytest verify pending |
| A28 | 506884c | 70b7a0d |
| A29 | 7e9d47a | 5458cf4 (re-fetch a168e56) |
| A30 (per D-2) | b0044ee | cac7e82 |
| A31 (U2 folded per D-3) | 473897f | 791e780 |
| A32 | 0d927e5 (D-2 clauses kept, markers stripped) | committed with the A32 test file (invariance panel; see git log) |
| A33–A35, G4-A1..A3 | pending — execute in order per §"How to execute" | — |

Owner decisions D-1/D-2/D-3 + U-slate + A41 pool dedup (774→771) approved 2026-07-13,
recorded in impl prereg §14 (commit 91ab66b). A29/A30/A31 must incorporate them as written
in the decision sheet and supplements.

**Date:** 2026-07-12. **Revised 2026-07-13:** A23 rewritten as the Arctic Shift source-switch amendment (the original cap-second-pass spec is superseded — the cap no longer exists under complete enumeration); A22 gains the UTA sub-rename rule; A35 clause 4(b) restated for archive score semantics. Evidence + supersession record: `2026-07-13-arctic-shift-source-switch.md`. **Status: ADVISORY DRAFT.** Nothing here is committed to any pre-registration file. These are ready-to-paste drafts prepared BEFORE the owner checks the boxes in `2026-07-11-decision-sheet.md`. Source of truth for the specs: `docs/airtight_execution_plan.md` v1.1 §B. House style matched to existing amendments A15–A20 in `marchand_index/preregistration.md` §14.

**Not drafted here (by design):**
- **A30** — waits on owner decision D-2 (market-proxy rebuild vs sensitivity-only).
- **A31** — waits on owner decision D-3 + U2 fold-in (the U2 window closes when A31 commits).

**One conditional dependency inside these drafts:** A32's disclosure sentence names `market_z_lockedv1` (the pre-A30 market proxy) as a locked-original variant. That clause assumes D-2 = "rebuild primary." If the owner picks sensitivity-only, delete the bracketed clause marked `[D-2 CONDITIONAL]` in the A32 draft — everything else stands.

---

## How to execute (for the implementing model)

Read this whole section before touching anything.

1. **Order:** amendments commit in numeric order A21 → A29, then (after owner decisions) A30, A31, then A32 → A35, then G4-A1..A3. Each amendment gets TWO commits: first the amendment text pasted into the prereg file, THEN the code that implements it. Never the other way around — the git timestamp on the text commit is the proof the rule was fixed before the code ran.
2. **Commit messages** (matches repo history):
   - text commit: `marchand_index: A<N> <one-line summary>`
   - code commit: `marchand_index: A<N> code + tests`
3. **Where the text goes:** A21–A35 append to `Full Project Files/marchand_index/preregistration.md` §14 (the impl prereg). G4-A1..A3 append to `Full Project Files/docs/preregistration.md` §11 (the spec prereg) under the **G4-A series** — do NOT use bare A-numbers in that file (its A10/A11 mirror impl numbering; bare continuation would collide with impl A12+).
4. **Dates:** every draft below carries the placeholder `2026-07-XX`. Replace with the actual commit date when pasting.
5. **Code-order exception:** A21's team-sub rule depends on A22's window-roster derivation. The TEXTS still commit in order A21 then A22 (text has no code dependency). For the CODE, either implement A22's roster function first or stub it, then wire A21 to it.
6. **Tests:** run from inside `Full Project Files/marchand_index/` with `pytest -q`. Baseline is 102 passing; every amendment below adds tests, target ~125+ by the end of Phase 0.
7. **Do not improvise.** If a draft's mechanical rule cannot be implemented as written (missing field, dead endpoint), stop and record the blocker — the A24 draft is the template for how a discovery-dependent rule pre-declares its own fallback.

---

## A21 — Reddit identity: non-discriminable names + team-sub attribution

### Plain English

The pool has several players who share a last name — and a few who share a FIRST name too (there are two Sebastian Ahos, and two Elias Petterssons who play on the SAME team). Our existing rule (A15) says: for shared surnames, only count a Reddit post if the first name also appears. But that rule breaks when the first names themselves collide — "Elias Pettersson" matches both Petterssons, so the evidence proves nothing. This amendment writes down exactly what counts as proof of identity in every collision case, and what to do when no proof is possible (count the post as "ambiguous," credit it to no one, and disclose how many posts we threw away). It also adds one common-sense rule: inside a team's own subreddit, a bare surname belongs to the guy who actually plays for that team — as long as only one of the name-sharers does.

### Draft amendment text (paste into impl prereg §14)

**A21 (2026-07-XX) — Reddit identity: non-discriminable first names + team-subreddit attribution. Logged BEFORE the 774-set production Reddit fetch (Reddit remains 0/774; no production Reddit data exists).**

A15 attributes a shared-surname submission to player P only when the text also carries first-name evidence for P. Two structural failure cases remain, found by the internal audit (E1) and panel review (J2-F5):

1. **Non-discriminable first names.** When two pool sharers' first names collide — identical ("Elias Pettersson" ×2) or prefix-nested ("Matt"/"Matthew") — A15's first-name test matches both players and discriminates nothing, silently double-attributing or misattributing.
2. **Team-context evidence unused.** A bare-surname post in a TEAM subreddit carries strong identity evidence (the team) that A15 ignores, needlessly discarding recall for shared-surname players — the same players A15 already dented.

**Corrected attribution rules (applied identically to all 774; extends A15, supersedes nothing):**

1. **Prefix-collision definition.** Within a shared-surname group, first names `a`, `b` PREFIX-COLLIDE iff `a.startswith(b) or b.startswith(a)` after accent-folding and case-folding. If a player's first name prefix-collides with another sharer's, first-name evidence is NON-DISCRIMINATING for that pair (it can no longer attribute a post between them).
2. **Team-subreddit context rule.** Within a TEAM subreddit, if exactly ONE pool sharer of the surname is on that team, bare-surname submissions attribute to him. "On that team" = the **A22 window-roster set** (the NHL-API `seasonTotals` derivation defined in A22), NOT the 2026-06-17 snapshot roster — a traded sharer counts for every team sub he was window-rostered in. If MORE than one pool sharer of the surname is window-rostered on that team, bare-surname submissions in that team's sub go to `ambiguous_mentions`. (This resolves the two Sebastian Ahos — CAR vs NYI — inside their respective team subs.)
3. **Fully non-discriminable pairs.** Where sharers collide on BOTH surname and (prefix-folded) first name AND the team rule cannot separate them (the two Elias Petterssons, both window-rostered on VAN): ALL matching submissions → `ambiguous_mentions`, attributed to NO ONE; both rows get a new flag `reddit_identity_ambiguous = true`; the discarded count is disclosed in `results.md`.
4. **r/hockey nickname-token rule.** In r/hockey, for prefix-colliding pairs, first-name evidence is non-discriminating (rule 1), so a matching submission is ambiguous UNLESS a TEAM NICKNAME token for exactly one sharer's team appears in the title/selftext. Token definition (mechanical): the final word of the team's full name from `raw/teams.csv`, accent/case-folded, matched as a whole token (e.g. "hurricanes", "islanders", "canucks"). 2–3 letter team codes are NOT used as tokens (false-positive prone: "LA", "SJ"). If nicknames of BOTH sharers' teams appear, the submission is ambiguous.

**Honest residuals (disclosed in advance):** (i) rules 3–4 lower recall further for the affected players — the count of discarded ambiguous submissions ships in `results.md`, and the A15 `surname_shared` sensitivity cut already covers the class; (ii) nickname tokens cover team names only, not player nicknames — unchanged from A15(ii); (iii) non-pool namesakes remain out of scope per A15(iii).

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 fetched, so no player's resulting count could have influenced any rule; every rule is mechanical (string prefix test, pool-derived roster sets, fixed token definition), applied uniformly to all 774; subreddits, query, window (A11), dedup, 1,000-result cap, transport (A9), composite weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), and all validation floors (§9, A6/V3) are unchanged.

### Execution notes

- **Files:** `marchand_index/fetch_reddit.py` — `build_surname_map`, `make_evidence_check` (retained verbatim through the A23 matcher rewrite; the rules below run on the corpus-matched folded text). New columns: `reddit_identity_ambiguous`; `ambiguous_mentions` already exists from A15. Fixtures live as mini-corpus jsonl per A23 execution notes.
- **Dependency:** rule 2 calls A22's window-roster function. Implement A22's derivation first or stub it (`window_teams(player_id) -> set[team_code]`), then wire.
- **Tests (add all four):**
  (a) Pettersson pair → both ambiguous everywhere (team sub AND r/hockey);
  (b) Aho in r/canes → CAR Aho; Aho in r/hockey with "Hurricanes" in title → CAR Aho; bare "Aho" in r/hockey → ambiguous;
  (c) unique surname → behavior unchanged from A15;
  (d) "Matt"/"Matthew" prefix collision detected by the fold-and-startswith test.
  Plus one fixture test for a traded sharer (team-sub attribution follows the WINDOW roster, not the snapshot).
- **Acceptance:** pytest green; a dry-run script prints every non-discriminable pair derived from `players.csv` (expect the known ones: Petterssons, Ahos, any Matt/Matthew-class pairs). **OWNER STEP: owner eyeballs the printed pair list before the production fetch launches.**

---

## A22 — Reddit traded-player multi-sub coverage

### Plain English

Right now we search two places for each player: the league-wide subreddit (r/hockey) and his team's subreddit. Problem: players get traded. A guy dealt at the deadline spent most of the year being talked about in his OLD team's subreddit — which we never search. This amendment says: search the subreddit of every team he actually played for during our measurement year, worked out mechanically from the NHL's own stats records (no hand lists). Same post never counts twice.

### Draft amendment text (paste into impl prereg §14)

**A22 (2026-07-XX) — Reddit sub-selection: every window-rostered team's subreddit, derived from NHL-API seasonTotals. Logged BEFORE the 774-set production Reddit fetch.**

§3.3/A2 search `r/hockey` + the player's (single, snapshot-date) team subreddit. For a player traded inside the attention window, the months of discussion in his former team's sub are invisible — a structured undercount that hits exactly the players whose attention the index should measure across a move (J2-F3, HIGH).

**Corrected rule (applied identically to all 774):** for each player, query the team subreddits of EVERY team he was rostered on inside the window [2025-04-18, 2026-04-17], derived mechanically from the NHL API `seasonTotals` rows with season IDs `20242025` and `20252026`, `leagueAbbrev == "NHL"`, `gameTypeId == 2`, mapped to team subs via the existing team→subreddit mapping already used by `fetch_reddit.py` (in/derived from `raw/teams.csv` — reuse it, do not build a new one). 2024-25 season rows are included because the window's first ~2 months (Apr–Jun 2025) fall in that season's playoffs/offseason, when a player is still discussed in his then-current (now former) sub. `r/hockey` participation is unchanged. Submissions are deduplicated by submission id ACROSS subs, so a crosspost counts once. A new column `reddit_subs_searched` records the exact list per player.

**Sub-rename rule (added 2026-07-13):** a team's subreddit SET additionally includes any predecessor subreddit its fan community used inside the window following a franchise rebrand. Known case, fixed here: UTA = {`r/utahmammoth`, `r/UtahHockey`} — verified 2026-07-13 via archive probes: `r/UtahHockey` (the pre-rebrand community) was active from at least 2025-04-19 while `r/utahmammoth`'s earliest in-window post is 2025-04-30, so the window's first ~2 weeks of Utah discussion live only in the predecessor sub. Mechanical and identity-keyed; applies to whichever players this amendment window-rosters to UTA. This is the team-level analogue of the traded-player rule above.

**Honest residual (disclosed in advance):** a mid-season stint that produced no NHL `seasonTotals` row (e.g. an AHL loan sandwiched between NHL stretches with a team we'd otherwise miss) can still hide former-sub attention; disclosed, not repaired — the rule stays mechanical.

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 fetched; the sub list is derived from an objective NHL-API quantity fixed by history, not chosen per player; query, window (A11), dedup, cap, transport (A9), identity rules (A15/A21), weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), and all validation floors (§9, A6/V3) are unchanged.

### Execution notes

- **Files:** `fetch_reddit.py` sub-selection; helper `window_teams(player)` from NHL landing `seasonTotals` (the same landing JSON `fetch_nhl_skill.py` already parses — reuse the cached HTTP layer). Under the A23 corpus-first architecture multi-sub coverage costs nothing extra at fetch time — the corpus already holds every covered sub; this rule governs which subs COUNT for each player.
- **Tests:** fixture traded player (two NHL rows, two teams in-window) → both team subs counted, union deduped by id; untraded player → one sub, unchanged; UTA player → both `utahmammoth` and `UtahHockey` in his sub set.
- **Acceptance:** dry-run prints all players with >1 sub; sanity-check the list against known deadline moves before the matcher run.

---

## A23 — Reddit source switch: Arctic Shift archive, complete enumeration, local matching

*(Rewritten 2026-07-13. The original A23 spec — a top-sorted second pass to patch the 1,000-result cap — is superseded: under complete archive enumeration the cap does not exist, so the patch has nothing to patch.)*

### Plain English

The old plan searched Reddit's own API with owner credentials. Three problems: Reddit search returns at most 1,000 results per query (superstars get truncated — the original A23 existed only to patch this), it can't filter by date, and the credentials have been an owner blocker for months. We found and verified a better source: Arctic Shift, a free public research archive of Reddit (the successor lineage of Pushshift, which most published Reddit research uses). It lets us download EVERY submission in every subreddit we care about for exactly our locked year — no cap, no credentials, no truncation. We tested it hard: full coverage of our window in every needed subreddit, and 100% agreement with a second independent archive on an overlap slice. One catch found in testing: the archive's own search box misses posts (possessives like "McDavid's", and posts edited after creation), so we don't use its search — we download the raw posts and do the matching ourselves, locally, with the rules written down here first.

### Draft amendment text (paste into impl prereg §14)

**A23 (2026-07-XX) — Reddit source: the Arctic Shift archive (`arctic-shift.photon-reddit.com`) replaces authenticated live-search; complete in-window enumeration; matching performed locally. Supersedes the A9 transport (third transport-lineage change: A2 → A9 → A23). Logged BEFORE the 774-set production Reddit fetch (Reddit remains 0/774; no production Reddit data exists).**

A9's OAuth transport inherits three structural limits of Reddit's live search API: a 1,000-result cap per (subreddit, query) that right-censors star-tier players (E8/J1; J2-F11 — the defect this amendment slot originally existed to patch); no server-side date filtering (forcing the A11 newest-first skip/stop paging shortcut); and a credentials prerequisite (A9/A10) that has blocked the fetch since it was logged. The Arctic Shift archive removes all three.

**Rules (applied identically to all 774):**

1. **Source + enumeration.** The Reddit corpus = every submission in each covered subreddit whose `created_utc` falls inside the fixed A11 window [2025-04-18 00:00 UTC, 2026-04-18 00:00 UTC), retrieved from Arctic Shift `/api/posts/search` by date-windowed pagination (`limit=100`, `sort=asc`, cursor on `created_utc`). No result cap exists; the `MAX_RESULTS`/`reddit_capped` machinery is REMOVED (the flag was disclosure-only — no §4–§10 quantity ever consumed it; column dropped). The original A23 cap-mitigation design (top-sort second pass, lower-bound semantics, capped-sensitivity block) is moot and NOT adopted.
2. **Corpus scope.** 36 subreddits, fixed here: `r/hockey`; the 32 team subreddits (the existing `TEAM_SUB` mapping); `r/UtahHockey` (the A22 rename rule); plus `r/nhl` and `r/fantasyhockey`. COMPOSITE counting subreddits are unchanged — `r/hockey` + the player's A22 team-sub set; `r/nhl` and `r/fantasyhockey` feed the rule-5 descriptive columns only.
3. **Local matching.** Per-player matching runs locally over the downloaded corpus, never via the archive's `query` search endpoint (verified recall misses: apostrophe possessives — "McDavid's" — and edited posts; evidence in rule 6). Mechanical rule: NFKD accent-fold, case-fold, map every non-alphanumeric character (including `'` and `'`) to a space, then whole-token match of the player's folded surname against `title + " " + selftext`. The A15/A21 identity and evidence rules run on the same folded text, unchanged.
4. **Text + score semantics (pre-declared).** (a) `title`/`selftext` are the archive's creation-time capture: mentions added by post-creation edits (bot-updated game threads) are invisible — uniform across all 774; direction: removes bot-appended box-score mass mentions. (b) `score` is the archive's ~2.5-day post-creation re-crawl value, replacing the fetch-time read (months after the window) whose accrual confound A35.4(b) disclosed; votes are near-settled and uniformly timed. A35.4(b) is restated accordingly. (c) Submissions since deleted or removed from live Reddit ARE in the corpus (captured before removal) — a completeness gain over live search; disclosed.
5. **Descriptive columns (never composite).** `reddit_mentions_allsubs` (match count over the full 36-sub corpus) and `reddit_mentions_fantasy` (r/fantasyhockey only — separates fantasy-utility attention from identity-driven attention on case cards). Descriptive/robustness only; §4/A12 weights and component definitions unchanged.
6. **Verification evidence recorded at draft time (2026-07-13 live probes).** Window coverage: 13/13 months (r/hockey) and 32/32 team subreddits through window end. Independent-archive cross-check (PullPush, whose own ingestion died 2025-05-19) on r/hockey "McDavid" [2025-04-18, 2025-05-17]: 67/67 unique submissions present in Arctic Shift by id lookup; archive-search recall on the same slice 63/67 vs local-match 65/67 (the 2 residual = edit-added text, rule 4a). Candidate-sub volumes (Jan 2026): r/nhl 500+, r/fantasyhockey 500+; rejected: r/hockeyanalytics (0 posts — dead), r/hockeycirclejerk (62/mo, nickname-dominant), r/NHLHUT (game-card economy, not fan salience).

**Honest residuals (disclosed in advance):** (i) third-party archive dependency — mitigated by pulling the corpus to local cache immediately; the LOCAL CORPUS, not the API, is the source of record for the production run; (ii) rule 4(a) undercounts in-game bot-thread mentions, uniformly; (iii) archive completeness cannot be proven against Reddit ground truth — the two-archive id-level agreement in rule 6 is the strongest evidence available and is recorded here.

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 fetched, so no player's resulting count could have influenced any rule; the sub list, matching rule, and semantics are fixed in advance, mechanical, and uniform across all 774; query construct (surname), window (A11 fixed dates), submission-id dedup, identity rules (A15/A21), sub-selection (A22), weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), and all validation floors (§9, A6/V3) are unchanged. The A9/A10 credentials prerequisite is void.

### Execution notes

- **Files:** `fetch_reddit_corpus.py` (NEW — 36-sub corpus puller, per-sub jsonl cache, resumable, atomic); `fetch_reddit.py` (rewrite — OAuth transport + cap machinery deleted; becomes the local matcher; A15 functions, window constants, dedup, resume, snapshot retained).
- **Order:** A23 text commits before any corpus pull; corpus pull before matcher run.
- **Tests:** apostrophe possessive match (curly + straight); whole-token guard ("McDavidson" does not match "McDavid"); mini-corpus end-to-end fixture (jsonl → counts row); resume checkpoint.
- **Acceptance:** corpus integrity scan clean (36 subs × 13 months, zero empty months); McDavid cross-check slice ≥ 65 local matches; `reddit_counts.csv` = 774 rows, no `reddit_capped` column, descriptive columns present.

---

## A24 — Denominator: rookie flag from contract type; market-rate fit on market contracts

### Plain English

Part of the index divides attention by what a player SHOULD earn on the open market. We predict that number with a simple salary model — but the model must be trained only on real market contracts, not rookie deals (rookie pay is capped by league rules, not the market). Today we guess "rookie deal" from price + age, which misfires both ways: some rookie deals with bonuses look expensive, some cheap veteran deals look like rookie deals. The salary site we scrape embeds structured data that may label contract types outright. The rule: FIRST look at real examples and find that label; if it exists, use it (with the old guess as per-row backup); if it doesn't exist, keep the old guess and say so honestly — don't invent anything. Also two stats upgrades to the salary model itself: fit on log-dollars (standard for salary data, which is very skewed) and use the proper statistical correction (Duan smearing) when converting back to dollars.

### Draft amendment text (paste into impl prereg §14)

**A24 (2026-07-XX) — expected_cap: `is_rookie_deal` keyed on the CapWages contract-type field; OLS fit restricted to market (non-rookie) contracts on the log scale with Duan back-transform. Logged BEFORE the final compute; field-discovery evidence recorded below.**

A4/A8 key `is_rookie_deal` on a price+age proxy (`cap_hit_M ≤ $0.975M AND age ≤ 25`). Two misclassification directions (E2, J2-F2, J2-F6): bonus-laden ELCs above $0.975M read as market deals and contaminate the market fit; cheap post-ELC RFA deals below it read as rookie deals and are wrongly projected. Additionally the A4 OLS fits raw dollars over a heavily right-skewed cap distribution, and (per A4) the fit set includes ELC rows the CBA prices by fiat, not the market.

**Rules (applied identically to all 774):**

1. **Field discovery FIRST (procedure + evidence recorded here at commit time).** Dump the CapWages `__NEXT_DATA__` JSON for 3 known ELCs (Bedard, Celebrini, Hutson) and 3 known veteran market deals; identify the field that distinguishes entry-level status (candidate keys: `contractType`, `signingStatus`, `expiryStatus`, `entry_level`); record the exact key path here: `__[FILL AT COMMIT: exact JSON key path]__`. **If NO such field exists**, this amendment instead pre-declares the price+age proxy as the sole rule (status quo) with the misclassification risk disclosed — no new heuristic is invented.
2. **Flag rule.** `is_rookie_deal` keys on the discovered contract-type field. Where the field exists but is missing for individual rows, the price+age proxy is the per-row fallback. A new column `rookie_flag_source ∈ {contract_type, price_age_proxy}` records which path fired for every row.
3. **Fit set.** The expected_cap OLS fits ONLY rows with `is_rookie_deal == False` and finite predictors + cap; it PREDICTS for ALL 774. The $0.775M league-minimum floor on predictions is unchanged.
4. **Log-scale fit.** The regression is `log(cap_hit_M) ~ PPG + TOI/G` (within position group, age still excluded per A4); predictions back-transform via the **Duan (1983) smearing estimator** (the naive `exp()` is retained as a code-comment alternative, not computed). The linear all-rows fit is retained as an audit lens. (Convention: Evolving-Hockey-style contract models price on the log scale.)

**Disclosures (in advance):** current-season stats stand in for platform-year stats; contract term and UFA/RFA status are omitted from the model; defensively-valuable defensemen are underpriced by a PPG-based fit. All three ship on the poster's limitations panel.

**Anti-tuning compliance (§13):** the flag keys on an external structural fact of the contract (its registered type), never on any player's attention, rank, or index value; the discovery procedure and its fallback are fixed here before the code runs; fit-set restriction and log/Duan mechanics are standard econometric practice adopted on reasoning grounds while Reddit is 0/774 and no final composite exists; peer features (§6/A13), λ (A5), the A8 hybrid headline pointer, weights (§4/A12), and all validation floors (§9, A6/V3) are unchanged. Prior expected_cap columns remain in git history per §13.

### Execution notes

- **Files:** `fetch_cap_hits.py` (extract contract-type field); `compute_oaq.py` — `compute_expected_cap` (~line 491), rookie flag (~line 133).
- **Order:** run the field-discovery dump BEFORE finalizing the amendment text — the key path gets pasted into the `[FILL AT COMMIT]` slot (or the fallback paragraph becomes operative). This is the one amendment whose text has a pre-commit discovery step.
- **Tests:** synthetic ELC-contaminated fixture → non-rookie log fit recovers the market slope; Bedard/Celebrini/Hutson rows assert `rookie_flag_source == "contract_type"` (skip if fallback branch became operative).
- **Acceptance:** printed before/after table of rookie `expected_cap` — every rookie's value should rise or stay (removing CBA-priced rows from the fit cannot lower a market-rate prediction for rookies).

---

## A25 — Missingness taxonomy for sentinel renorm

### Plain English

When a data source is empty for a player, we currently treat all emptiness the same way: drop that source and re-balance the rest. That's right when the fetch FAILED (we couldn't look), but wrong when the thing genuinely DOESN'T EXIST (we looked, there's no Wikipedia page). No page isn't "no data" — it's evidence of very low fame, and should count as a zero, not be skipped. This amendment splits the two cases.

### Draft amendment text (paste into impl prereg §14)

**A25 (2026-07-XX) — Missingness taxonomy: `no_entity_exists` imputes raw 0; `fetch_failed` keeps sentinel renorm. Logged BEFORE the final compute.**

§4's sentinel handling renormalizes weights over surviving components for ANY null. That treats two different situations identically (E3): (a) the source was blocked/failed — missingness unrelated to the player (MCAR; renorm defensible); (b) the entity does not exist — no Wikipedia article, no Trends topic and an empty series. Case (b) is itself attention information: absence of a page IS the low-fame signal, and renorming it away systematically overstates the engagement of exactly the low-attention players.

**Rules (applied identically to all 774):**

1. Every fetcher writes a per-component `null_reason ∈ {no_entity_exists, fetch_failed}` for each null it produces. Classification is mechanical: `wiki_match = none` with a confirmed no-page verdict → `no_entity_exists`; Trends with no topic MID AND an empty series → `no_entity_exists`; HTTP failures, blocks, rate-limits, parse errors → `fetch_failed`.
2. `fetch_failed` (and blocked-source) nulls → weight renorm, current behavior, unchanged.
3. `no_entity_exists` nulls → impute the RAW value 0 for that component BEFORE z-scoring; no renorm for that component. (The player's z-score on that component is then the z-score of zero raw attention — strongly negative, as it should be.)

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 and no final composite exists; the taxonomy keys on fetch-outcome facts, never on any resulting score; weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8/A24), and all validation floors (§9, A6/V3) are unchanged.

### Execution notes

- **Files:** all fetchers (add `null_reason`); `compute_oaq.py` engagement assembly (branch on the reason).
- **Tests:** unit test — a no-page player scores strictly LOWER than under renorm; a fetch-failed player is unchanged vs current behavior.
- **Acceptance:** `results.md` lists every `no_entity_exists` row (player, component).

---

## A26 — Block bootstrap + propagated-uncertainty table

### Plain English

Our confidence intervals resample a player's Wikipedia views day by day, as if each day were independent. They're not — attention comes in multi-day waves (a trade rumor spikes views for a week). Resampling independent days makes the intervals artificially tight. Fix: resample WEEK-long blocks instead, keeping the wave structure, which widens the intervals to their honest size. Also publish a table saying exactly which sources of uncertainty our intervals do and don't capture.

### Draft amendment text (paste into impl prereg §14)

**A26 (2026-07-XX) — §10 bootstrap: 7-day circular block resampling for the Wikipedia daily vector; propagated-uncertainty table. Logged BEFORE the final compute.**

§10 resamples the 365-day Wikipedia pageview vector iid by day. Daily pageviews are strongly autocorrelated (news cycles span days), and iid resampling of autocorrelated data understates variance — the published CIs would be too narrow in a direction that flatters precision (E7).

**Rules:**

1. **Block resampling (Politis–Romano convention).** The wiki daily vector is resampled in 7-day CIRCULAR blocks. Exact procedure: treat the 365-day vector as a ring; each bootstrap draw samples 53 uniformly-random block start indices, concatenates the 53 seven-day blocks, truncates to 365 days. Applies to both `wiki_en` and `wiki_intl` daily vectors.
2. Reddit pool resampling is unchanged; seed `20260526` is unchanged.
3. **Propagated-uncertainty table.** `results.md` AND the poster carry a table stating what the CIs propagate (wiki daily vectors, Reddit submission pool) and what they do NOT (peer-set composition, Trends values, market proxy, expected_cap fit). The corresponding limitations line is already locked in the plan's §G set.

**Anti-tuning compliance (§13):** logged before the final compute on variance-honesty grounds; block length (7 days) is fixed in advance by news-cycle reasoning, not chosen for any interval's resulting width; seed, draw count (1,000), weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8/A24), and all validation floors (§9, A6/V3) are unchanged. Wider CIs are the expected and accepted consequence.

### Execution notes

- **Files:** `compute_oaq.py` bootstrap section.
- **Tests:** unit test — an autocorrelated synthetic vector yields a WIDER CI under block resampling than iid; a second test asserts bit-identical results across two runs under seed 20260526.
- **Acceptance:** propagated/not-propagated table emitted in `results.md`.

---

## A27 — Star-boundary matching bias: diagnostic + corrected lens

### Plain English

We score a player by comparing him to his 10 most similar peers. Problem at the very top: McDavid has no equals, so his "peers" are all slightly WORSE than him. If attention rises steeply with skill, comparing a star to slightly-worse peers automatically hands him surplus attention — a mechanical artifact, not a finding. This is a textbook, named bias in the matching literature. We don't change the headline; we (1) publish a per-player "how far above his peers is he really" gap measure, and (2) publish a bias-corrected version of the score as a side lens. If the corrected version reorders players a lot, we say so — that itself is a finding.

### Draft amendment text (paste into impl prereg §14)

**A27 (2026-07-XX) — Star-boundary matching-bias diagnostic (`peer_skill_gap`) + bias-corrected reporting lens (`OAQ_bc`). Primary unchanged. Logged BEFORE the final compute.**

K-nearest matching at a distribution boundary is biased: a player at the skill frontier has peers strictly below him, so any convex attention-in-skill relationship mechanically inflates his OAQ residual (E5; J1 CONFIRM — textbook boundary bias, Abadie & Imbens 2011). No results exist yet; the remedy is a pre-registered diagnostic + corrected LENS, with the primary untouched.

**Rules:**

1. **Diagnostic.** Every row ships `peer_skill_gap`: mean(player − peer) on each standardized skill feature (6 values), plus a scalar summary defined as the **mean of the absolute standardized per-feature gaps**.
2. **Bias-corrected lens (reporting-only).** `OAQ_bc = OAQ_observed − β̂ᵀ(x_P − x̄_peers)`, where β̂ comes from a within-position OLS of `engagement_raw` on the standardized 6-feature skill vector (Abadie–Imbens-style regression correction). `OAQ_portable_bc` applies the SAME β̂ (from the engagement_raw-on-skill regression — NOT refit on the market-adjusted quantity) to the portable residual.
3. **Status rule (A17 language, verbatim in application):** the raw OAQ remains the locked primary and the only basis for gate verdicts. The bc lens is robustness, reported regardless of direction. Spearman rank agreement primary-vs-bc is reported; agreement < 0.8 is itself a reported finding and a stated limitation — it does not license switching the headline to whichever lens reads better.

**Anti-tuning compliance (§13):** logged before the final compute on published-literature grounds (Abadie & Imbens 2011); the correction form and the β̂ source regression are fixed in advance, applied uniformly; the primary quantity, weights (§4/A12), peer construction (§6/A13), λ (A5), denominators (A4/A8/A24), and all validation floors (§9, A6/V3) are unchanged.

### Execution notes

- **Files:** `compute_oaq.py` (peer-gap computation sits next to the existing peer-matching block; the β̂ regression is per position group).
- **Tests:** synthetic fixture with convex attention-in-skill → bc lens removes the mechanical boundary positivity (frontier player's OAQ_bc ≈ 0 where raw OAQ > 0).
- **Acceptance:** `peer_skill_gap` columns in `oaq_pilot.csv`; rank-agreement statistic in `results.md`.

---

## A28 — Thin-sample peer-eligibility sensitivity

### Plain English

Players with too little ice time have their advanced stats filled in with the group average (we can't measure them reliably). Side effect: averaging pulls them toward the middle, which makes them look "similar" to everyone — so they get over-picked as peers. We add one re-run where such players can't serve as peers (they still get scored themselves) and report how much the rankings move.

### Draft amendment text (paste into impl prereg §14)

**A28 (2026-07-XX) — Sensitivity re-run: `onice_status = thin` rows ineligible as peers. Logged BEFORE the final compute.**

A13 group-mean-imputes the three on-ice features for skaters under the 150-minute 5v5 floor. Imputation shrinks those rows to the position centroid, so the Mahalanobis distance understates their true covariance distance and they are systematically over-selected as peers (J1-N6; cf. Rosenbaum & Rubin 1984 on matching with imputed covariates).

**Rule:** one pre-registered sensitivity re-run in which `onice_status = thin` rows are INELIGIBLE as peers (they are still scored themselves, matched against non-thin peers). Spearman rank agreement vs the primary is reported for `OAQ_observed`, `OAQ_portable`, and the headline index. The primary is unchanged; the A17 status rule governs any material disagreement (< 0.8 → reported finding, no headline switch).

**Anti-tuning compliance (§13):** logged before the final compute; the eligibility rule keys on the pre-existing A13 thin flag, fixed before any result exists; K, distance, features, weights, λ, denominators, and all floors unchanged.

### Execution notes

- **Files:** `compute_oaq.py` peer selection (an `exclude_thin_peers` flag).
- **Tests:** a thin player appears in NO peer list in sensitivity mode; still receives his own score.
- **Acceptance:** rank-agreement row in `results.md`'s sensitivity table.

---

## A29 — V3 repair: fixed window, team-level bootstrap, Utah dual-title, relabel

### Plain English

Our team-level cross-check (V3) has four problems. (1) Its team page-view data was fetched on a "past 365 days from whenever the script ran" window instead of our locked season window — code-confirmed bug. (2) Utah's team article was RENAMED mid-season (Utah Hockey Club → Utah Mammoth), and Wikipedia's view counter doesn't follow renames — we'd count only part of their views. We fix it for all 32 teams by mechanically finding every alternate title and summing. (3) Its uncertainty math resampled players; the right unit is teams. (4) Honesty: V3 uses Wikipedia to check an index that's heavily built FROM Wikipedia — that's not independent validation, so we rename it a "consistency check" and stop counting it toward our "3 independent validations" claim. Gate-4 (YouTube) takes its slot.

### Draft amendment text (paste into impl prereg §14)

**A29 (2026-07-XX) — V3 repaired (fixed window, redirect-summed titles, team-level bootstrap) and relabeled "aggregation-consistency check" (not an independent pathway). Logged BEFORE the V3 re-fetch and the final compute.**

Four defects (J1-N7 code-confirmed; J2 Utah landmine; J3 independence classification):

1. **Window.** `fetch_team_outcomes.py:89` computes a run-anchored trailing window — the same defect A11/A14 removed for player-keyed sources. Team pageviews must be on the fixed window.
2. **Renamed articles.** The pageviews API does not follow redirects (the A1 lesson). Utah's article was renamed "Utah Hockey Club" → "Utah Mammoth" INSIDE the window, splitting its views across two titles.
3. **Bootstrap unit.** V3's n = 32 exchangeable units are TEAMS; resampling players understates team-level variance.
4. **Independence.** V3's outcome (team Wikipedia pageviews) shares platform, window, and news shocks with the composite's heaviest component (wiki_en, weight 0.29+0.11 intl). Per the panel's independence classification it is construct-overlapping/shared-method and cannot count toward the ≥3-independent-pathways criterion.

**Rules:**

1. Team Wikipedia pageviews re-fetched on the EXACT fixed window [2025-04-18, 2026-04-17] (same `WINDOW_START`/`WINDOW_END` constants as the player wiki fetchers). `team_outcomes.csv` rebuilt.
2. **Redirect audit, all 32 teams (mechanical):** for each team's canonical article, enumerate redirect titles via the MediaWiki API `prop=redirects`; fetch in-window pageviews for the canonical title AND every redirect title; sum all non-zero series (views recorded against a redirect title are legitimate views). Report per-team redirect share so any surprise rename is visible. Utah is the known case: both "Utah Hockey Club" and "Utah Mammoth" contribute.
3. V3's bootstrap resamples TEAMS (n = 32), not players.
4. **Relabel.** V3 is titled "aggregation-consistency check" EVERYWHERE (results.md, poster, abstract) and is NOT counted toward the ≥3-independent-pathways claim. The A18 interpretation rule (verdict from the OAQ-based ρ against the 0.40 floor; baseline comparison informs the narrow claim only) is unchanged.

**Anti-tuning compliance (§13):** logged before the re-fetch; the window is the already-locked A11 interval; redirect enumeration is mechanical and identity-keyed, never magnitude-keyed; the floor (0.40), predictor, and A18 interpretation are unchanged — the relabel STRENGTHENS the honesty of the pathway count and cannot flatter any result. Prior `team_outcomes.csv` retained in git history per §13.

### Execution notes

- **Files:** `fetch_team_outcomes.py` (window constants, redirect enumeration, dual-title sum); `compute_oaq.py` V3 bootstrap; results/poster labels.
- **Tests:** window columns assert the fixed dates; a redirect-sum fixture (two titles, partial series each) sums correctly.
- **Acceptance:** re-fetched CSV window columns == fixed dates; UTA total ≥ its old single-title value; V3 CI produced from team-level draws; per-team redirect-share table emitted.
- **Sequencing:** this is Phase-1 task 1.9 — the re-fetch runs AFTER the A29 code lands.

---

## A32 — Exploratory/confirmatory split + pilot-overlap disclosure

### Plain English

Honesty amendment. Some of our definitions were refined after looking at pilot data on players who are also in the final 774. A strict statistician calls that "not purely confirmatory" — and they'd be right. So the poster says it out loud: pilot era = exploratory (design-generating), the 774 run = the one confirmatory test of the frozen design. And we prove the refinements aren't doing the heavy lifting: we re-run every validation under the ORIGINAL locked definitions too and publish whether the verdicts change.

### Draft amendment text (paste into impl prereg §14)

**A32 (2026-07-XX) — Exploratory/confirmatory framing: pilot era declared design-generating; invariance panel across locked-original variants. Logged BEFORE the final compute.**

The 14-player v1 pilot and the 160-player pilot2 era (including the outcome-inspected A4/A5/A8 revisions) refined headline definitions on samples that overlap the locked 774 pool (J1-N4, J3-F1). Under the standard framing (Nosek et al. 2018, PNAS), that era is EXPLORATORY/design-generating; the 774 production run is the sole confirmatory test of the frozen design.

**Rules:**

1. **Required disclosure sentence (poster + results.md, verbatim):** "Headline definitions were amended after inspection of an overlapping pilot sample; they were locked before the production fetch and are pre-specified, not strictly confirmatory. Locked-original variants (raw-cap MI, two-sided λ=1 OAQ`[D-2 CONDITIONAL:], and market_z_lockedv1 — the pre-A30 market proxy`) are reported alongside, and validation verdicts are shown to be invariant (or not) across them."
2. **Invariance panel.** Recompute the V1b/V1a/V2/V3 point estimates under ALL locked-original variants — raw-cap MI (§8-original), two-sided λ=1 OAQ (§7-original)`[D-2 CONDITIONAL:], and market_z_lockedv1 (§7-original market proxy)` — and report the deltas vs the primary in `results.md`. `[D-2 CONDITIONAL:]` The market-proxy entry closes A30's residual anti-tuning exposure: pilot-era results were seen under the old proxy, so verdict-invariance to the proxy swap must be demonstrated, not asserted.

**Anti-tuning compliance (§13):** reporting-and-framing only — no quantity, weight, floor, or verdict rule changes; logged while Reddit is 0/774 and no confirmatory result exists; the variant list is the closed set of §13-preserved locked originals, fixed here in advance.

### Execution notes

- **Files:** `compute_oaq.py` (invariance panel — recompute validation stats under each preserved variant column); poster copy.
- **D-2 conditional:** if the owner declines the A30 rebuild, delete the two `[D-2 CONDITIONAL]` clauses (there is then no `market_z_lockedv1` variant; the proxy IS the locked original). Everything else stands. Strip the `[D-2 CONDITIONAL:]` markers themselves when pasting either way.
- **Acceptance:** invariance panel emitted in `results.md` (one row per variant × validation test, delta vs primary).

---

## A33 — Power V2: All-Star fan-vote archive union 2022+2023+2024

### Plain English

Our second validation test asks: do high-scoring players on our index also get voted into All-Star games by fans? Right now we only use 2024's fan vote, which overlaps our 774 pool by just 8 players — statistically useless. Fix: pool the FAN-VOTED All-Stars from 2022, 2023, and 2024 (each year's official press releases, only the fan-chosen names — never coach/league picks). If that gets us to 10+ players, the test has teeth; if not, it stays labeled underpowered, as already promised.

### Draft amendment text (paste into impl prereg §14)

**A33 (2026-07-XX) — V2 membership: union of official FAN-VOTE All-Star selections, 2022 + 2023 + 2024. Logged BEFORE the final compute.**

A3/A20 left V2 at the 2024 fan-vote membership: in-pool overlap n = 8 < 10 → underpowered per §9, contributing nothing to the pathway count (J3-F2).

**Rules:**

1. **Membership definition.** V2 membership = the union of players selected via an OFFICIAL FAN-VOTE component of the 2022, 2023, and 2024 All-Star selections, as named in NHL.com press releases. The fan-vote mechanism differs by year (captain votes, "Last Men In", full fan ballot); each season's exact mechanism is documented in `external_outcomes_sources.md`, and ONLY fan-voted names are taken — never league- or player-selected ones.
2. **Sourcing.** Per the A20 pattern: ≥2 independent URLs per season list, recorded in `external_outcomes_sources.md`.
3. **Join.** NHL-id-keyed per the A20 namesake guard (the id decides whenever present; name backup only for blank-id rows).
4. **Power rule.** If the in-pool overlap reaches n ≥ 10, V2 is powered under its EXISTING floor (§9: ρ ≥ 0.45 / target 0.55 — unchanged); if not, V2 stays underpowered as pre-declared. No floor moves either way.
5. **Disclosure.** The votes predate the attention window — same temporal-mismatch attenuation class as V1b's union lists; disclosed.

**Anti-tuning compliance (§13):** membership is defined by official external publications that predate this amendment and are independent of every model input; the union rule and fan-vote-only restriction are fixed before the overlap count is known; floors and verdict logic unchanged; logged while Reddit is 0/774 and no V2 statistic exists. The pre-A33 `external_outcomes.csv` is retained in git history per §13.

### Execution notes

- **Files:** `fetch_external_outcomes.py`; `external_outcomes_sources.md`.
- **Research step:** find the per-season press releases + one independent corroboration each (2022 captains/"Last Men In"; 2023 fan ballot mechanics; 2024 already sourced by A20/A3-era work). Document mechanism per season IN the sources file.
- **Acceptance:** `external_outcomes.csv` rebuilt; in-pool overlap count printed; sources file carries ≥2 independent URLs per season.

---

## A34 — Published-leaderboard display rule

### Plain English

A player who missed the whole season (like Barkov, injured) has near-zero attention AND artificial skill stats (filled in with averages) — the math hands him a fake terrible score. Publishing that would be embarrassing and wrong. Rule: anyone flagged as tiny-sample or season-absent stays in the data files but is EXCLUDED from any published ranking table, with the exclusion count disclosed.

### Draft amendment text (paste into impl prereg §14)

**A34 (2026-07-XX) — Published-leaderboard display rule: `small_sample` / season-absent rows excluded from published panels, retained in data. Logged BEFORE the final compute.**

Rows with `small_sample = true` or NULL current-season GP (the A10 Barkov class) have attention floored by absence while their skill features are imputed toward the group mean — the arithmetic then produces a spurious negative-OAQ tail that reads as a finding but is an artifact of absence (J2-F7).

**Rule:** rows with `small_sample = true` OR null current-season GP are EXCLUDED from every PUBLISHED leaderboard and panel (poster, results.md tables). They remain in `oaq_pilot.csv` with all computed values, and the excluded count is disclosed alongside every published table. The injury-attention confound is added to the poster limitations set. This is a DISPLAY rule only: no quantity, gate, or bootstrap changes; flagged rows still participate in z-scoring, peer pools (subject to A28's sensitivity), and validation cohorts exactly as before.

**Anti-tuning compliance (§13):** display-layer only, keyed on the pre-existing A10 flag (locked 2026-06-17) and on GP nullity — objective absence facts, never on any player's resulting score; logged before any result exists; all computation, weights, floors, and verdicts unchanged.

### Execution notes

- **Files:** `compute_oaq.py` results-emit section.
- **Tests:** a flagged row is absent from emitted leaderboard tables, present with full values in the CSV.
- **Acceptance:** every published table's caption carries the exclusion count.

---

## A35 — Small-items batch (one amendment, five clauses)

### Plain English

Five small pre-commitments bundled into one amendment. (1) Brad Marchand anchors our Google Trends scale, so his own score against himself is meaningless — we pre-name a backup measuring stick (Sidney Crosby's Trends topic) for his row only, and put a warning on his case card. (2) One sentence that permanently bans quoting the log-scale variant as a headline number. (3) A promised robustness re-run using goals instead of points. (4) Plain-language admissions about what Reddit data can't see (comments are invisible; upvote counts keep moving after our window). (5) An admission that the international-Wikipedia component responds to a player's nationality — by design, and we say so.

### Draft amendment text (paste into impl prereg §14)

**A35 (2026-07-XX) — Small-items batch: anchor-degeneracy fix, log-lens escape-clause plug, goals-rate robustness, Reddit construct disclosures, nationality note. Logged BEFORE the final compute.**

Five clauses (J1-N9, J3-F7, J2-F12, J2-F14, J2-F10), one amendment:

1. **Trends anchor degeneracy (Marchand's own row).** A16 anchors every Trends fetch to the Brad Marchand topic entity, so his own row is anchor/anchor ≡ 1.0 — a degenerate self-measurement. Pre-declared secondary anchor for HIS ROW ONLY, named now: the Google Trends topic entity for **"Sidney Crosby"** (hockey-native, star-magnitude — adequate resolution against Marchand's own star-tier series). The ≡1.0 degeneracy is disclosed on his case card. Additionally, the count of depth players whose Trends series quantizes to zero against the anchor is reported.
2. **A17 escape-clause plug (verbatim, poster-binding):** "No log-lens number appears in the headline, abstract, or leaderboard panels under any outcome."
3. **Goals-rate robustness.** Pre-declared re-run with goals/60 replacing PPG in the peer skill vector (fame plausibly follows goals more than assists); reported as rank agreement vs primary ONLY — never as an alternative ranking (per §H forking-paths rule).
4. **Reddit construct disclosures (poster limitations):** (a) the fetch counts SUBMISSIONS only — comments and game-thread activity are invisible, and depth players' attention is disproportionately comment-borne; (b) *(restated 2026-07-13 per A23 rule 4b)* `score` is the archive's ~2.5-day post-creation re-crawl value — votes near-settled and uniformly timed; the earlier fetch-time accrual confound is removed, and the residual (votes accruing after ~2.5 days are uncaptured) is uniform in timing across all players; disclosed.
5. **Nationality note.** `wiki_intl` (weight 0.11) responds to nationality with no peer control — deliberate (national attention drivers are part of the signal being measured, not a confound to strip), disclosed on the poster.

**Anti-tuning compliance (§13):** clauses 2, 4, 5 are disclosures/prohibitions that constrain future claims and cannot flatter any result; clause 1's secondary anchor is named before any Trends-dependent result exists and applies to a single pre-identified row; clause 3 is a rank-agreement-only robustness re-run under the §H rule. Weights, floors, window, λ, denominators, pool, and verdict logic unchanged. Logged while Reddit is 0/774 and no final composite exists.

### Execution notes

- **Files:** clause 1 → `fetch_trends.py` (secondary-anchor fetch for the anchor player's row) + case-card copy; clause 3 → `compute_oaq.py` (peer-vector variant re-run); clauses 2/4/5 → results.md/poster copy blocks.
- **Tests:** clause 1 — anchor row uses the Crosby MID (fixture); clause 3 — variant run emits rank agreement, not a leaderboard.
- **Acceptance:** amendment text contains the verbatim clause-2 sentence; zero-quantization count emitted; disclosures present in the limitations block.

---

## G4-A1..A3 — Gate-4 amendments (spec prereg `docs/preregistration.md` §11)

**Numbering note (repeat of the plan's warning):** these go in `docs/preregistration.md` §11 as **G4-A1, G4-A2, G4-A3** — the spec-level series. Do NOT continue bare A-numbers in that file. Each entry cross-references `docs/airtight_execution_plan.md` and carries the standard anti-tuning paragraph. All three commit BEFORE any YouTube fetch. Conditional on owner decision D-1 = GO.

### G4-A1 — Relevance rule: last-name title match + shared-surname guard

#### Plain English

The YouTube test currently accepts a video if the player's FIRST or last name is in the title. First names are a trap: searching for Connor Bedard and accepting any "Connor" title scoops up Connor McDavid videos. Fix: the LAST name must be in the title. Players who share a last name with another pool player need extra proof (first name or team tag in the title). The two same-team, same-full-name Petterssons can't be told apart at all — they sit out this test, and we say so.

#### Draft amendment text (paste into spec prereg §11)

**G4-A1 (2026-07-XX) — §7.2 relevance criterion tightened: LAST-name title match; shared-surname disambiguation; identical-name exclusion. Logged BEFORE any Gate-4 YouTube fetch. Cross-ref: `docs/airtight_execution_plan.md` §B Gate-4 amendments (source E6).**

§7.2 admits a video if "the player's first or last name appears in the video title." A first-name match is not identity evidence in a league with repeated first names: a "Connor"-titled McDavid video would enter Bedard's dataset. Corrected rules, applied identically to every Gate-4 cohort player:

1. The video title must contain the player's LAST name (case-insensitive, accent-folded substring), replacing the first-OR-last rule.
2. Players whose surname is shared with another pool player (the impl-prereg A15 `surname_shared` derivation) additionally require the player's first name OR his team tag in the title.
3. Same-team identical-full-name pairs (the two VAN Elias Petterssons) are EXCLUDED from the Gate-4 cohort entirely and the exclusion is disclosed in the Gate-4 table.

All other §7.2 criteria (roster-period upload, 15s–30min duration, ≥500 views) are unchanged.

**Anti-tuning compliance (§10):** logged before any YouTube data exists, so no video, view count, or player result could have influenced the rule; the rule is mechanical (string matching against pool-derived name sets), applied uniformly; bands (§5), channel allow-list (§6.1), query format (§6.3), outcome (§6.4), regression (§6.5), coverage floors (§7.3), pass logic (§8.1), and seed (§9) are unchanged.

### G4-A2 — Censoring disclosure: selection on the outcome

#### Plain English

The YouTube test only counts videos with 500+ views and a name in the title. Depth players — the very group this test exists to check — are the most likely to have all their videos screened out by those filters. That's selection on the outcome, and it pushes the depth-band result toward "no effect." We can't remove the filters (they block junk), so we disclose the direction of the bias, in advance, in the results table itself.

#### Draft amendment text (paste into spec prereg §11)

**G4-A2 (2026-07-XX) — Pre-declared censoring disclosure: the ≥500-view floor + title-match select on the outcome and censor the depth band toward null. Logged BEFORE any Gate-4 YouTube fetch. Cross-ref: `docs/airtight_execution_plan.md` §B Gate-4 amendments (source J3-F8).**

§7.2's ≥500-view floor and title-relevance rule are selection filters applied to the OUTCOME variable (video attention). For depth players, whole video populations fall below the floor, so the depth band is right-truncated exactly where its signal would live. Pre-declared, before any fetch:

1. The direction of this bias — it biases the DEPTH BAND TOWARD NULL (attenuates any true OAQ–attention relationship among low-visibility players) — is stated in the published Gate-4 table, not in a footnote.
2. Per-band counts of players excluded for having zero qualifying videos are reported in the same table.
3. This disclosure does not alter the §8.1 pass logic; it pre-commits the interpretation that a depth-band null is partly attributable to outcome censoring and that a depth-band POSITIVE survives despite a bias working against it.

**Anti-tuning compliance (§10):** disclosure-only; declared before any data exists; it constrains interpretation in the direction of caution and cannot flatter a weak result into a strong one; floors, filters, bands, regression, pass logic, and seed unchanged.

### G4-A3 — A10 scope-note update: Gate-4 results will be claimed on the poster

#### Plain English

An earlier note in this document said the poster would NOT include the YouTube test. The review panel then determined we NEED it — it's one of our three independent validation legs. This amendment updates the scope note so the paper trail is consistent: the YouTube test's results, whatever they are, go on the poster.

#### Draft amendment text (paste into spec prereg §11)

**G4-A3 (2026-07-XX) — Scope-note update: Gate-4 results WILL be claimed on the CASSIS poster. Logged BEFORE any Gate-4 YouTube fetch. Cross-ref: `docs/airtight_execution_plan.md` §A (J3-F2 pathway classification).**

A10 recorded that Gate 4 "remains future work and is not claimed on the poster." The panel's pathway-independence classification (plan §A) made Gate-4 load-bearing: without it the poster's ≥3-independent-pathways criterion fails (V3 is reclassified as an aggregation-consistency check by impl-prereg A29; V1 is one family; V2's power depends on A33). Updated scope: Gate-4 IS executed for the poster run, and its results are claimed on the poster REGARDLESS OF DIRECTION, under the §8/§8.1 pass logic and null-result handling unchanged. The bands (§5), sampling frame (§6), snapshot/dedup rules (§7 as amended by G4-A1/A2), and seed (§9) govern; the §6.2.2 escalation rule governs any coverage shortfall — no improvisation.

**Anti-tuning compliance (§10):** scope declaration only, logged before any Gate-4 data exists; committing IN ADVANCE to publish regardless of direction is the anti-tuning act — it removes the option of quietly dropping an unflattering result; no threshold, band, filter, or verdict rule changes.

### Execution notes (all three)

- **File:** `Full Project Files/docs/preregistration.md` §11, appended after A11, as G4-A1/G4-A2/G4-A3.
- **Commit messages:** `marchand_index: G4-A<N> <one-line summary>` (text), then code for G4-A1 (the fetch-side relevance filter) lands with the Gate-4 fetcher work.
- **Gate:** owner decision D-1 = GO is the trigger. If D-1 = GO + U1 rider, the U1 10-player dry-run runs immediately after these commit (needs YouTube API key — owner task).
- **Note:** spec prereg seed is `20260522` (distinct from impl `20260526`); the drafts above deliberately do not restate seeds — do not "harmonize" them.

---

## Conformance checklist for this proposals doc (against plan §B)

| Item | Covered |
|---|---|
| A21 all 4 rules + 4 tests + owner-review step | yes |
| A22 seasonTotals derivation + dedup + column + UTA rename rule (2026-07-13) | yes |
| A23 (rewritten 2026-07-13): Arctic Shift source switch — enumeration, local matching, text/score semantics, descriptive cols, verification evidence. Original cap-second-pass spec superseded (cap no longer exists) | yes |
| A24 field-discovery-first + no-invented-heuristic fallback + log/Duan | yes |
| A25 two-way taxonomy + raw-0 imputation | yes |
| A26 ring/53-block procedure + propagation table | yes |
| A27 gap diagnostic + bc lens + same-β̂ rule + A17 status language | yes |
| A28 thin-ineligible sensitivity | yes |
| A29 window + redirect audit + team bootstrap + relabel | yes |
| A32 verbatim disclosure + invariance panel + D-2 conditional marked | yes |
| A33 fan-vote-only union + ≥2 URLs/season + id-keyed join + power rule | yes |
| A34 display-only exclusion + disclosure | yes |
| A35 all five clauses incl. named Crosby anchor + verbatim plug (4b restated 2026-07-13 for archive score semantics) | yes |
| G4-A1..3 in spec prereg, G4-A series, anti-tuning paragraphs | yes |
| A30/A31 correctly NOT drafted (owner decisions pending) | yes |
