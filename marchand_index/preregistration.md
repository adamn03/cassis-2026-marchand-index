# Tier-1 pilot pre-registration — The Marchand Index (CASSIS 2026 abstract)

**Author:** Adam Noakes (ana178@sfu.ca)
**Locked on:** 2026-05-26
**Snapshot date D:** 2026-05-26 (roster + all attention/market/cap fetches keyed to the most recent 365 days available at fetch time)
**Submission target:** CASSIS, 2026-05-31
**Status of this document:** Committed to git **before any pilot2 fetch script is run or any pilot2 data file is written**. It supersedes neither `pilot/preregistration.md` (the locked 14-player v1 pilot, left untouched for audit) nor `docs/preregistration.md` (the full-build pre-reg). This is a **new, larger pilot** ("Tier-1": every team's top line + top pair). Any change after this commit is logged in §12 (Amendments) with date + reason — never edited silently.

---

## 1. Why this pilot exists

The v1 14-player pilot (`pilot/`) had two structural weaknesses for a stats-literate, overclaim-hostile audience:

1. **Peer pools were degenerate.** With 14 hand-picked extremes, a role player had no genuine same-tier peers, so OAQ residuals were unstable. Two of three pre-registered patterns were disconfirmed.
2. **Market baseline was non-robust.** The v1 market control was the **arithmetic mean of roster Wikipedia pageviews** (`pilot/fetch_team_baselines.py`). One superstar teammate (e.g. Will Smith → SJS, McDavid → EDM) inflates that mean and over-penalizes ordinary teammates. This is the "over-correction" disclosed in §2 of the abstract. Expanding the *scored* set does not fix it, because the baseline is computed over each team's full roster regardless of N. **The fix is a different baseline: an exogenous market-size proxy that roster composition cannot inflate.**

This pilot replaces the hand-picked set with a principled, reproducible population (top line + top pair on every team), uses K=10 peer matching (matching the full-build method), replaces the roster-mean baseline with an exogenous market proxy, and — critically — adds an **external validation** test so the pilot can demonstrate the model *finds results*, not merely that the leaderboard reorders.

The pilot is still a pilot: it is the top-tier slice of the league, not all ~700 active skaters, and it does not run the LLM theme classifier, Gates 3–5, or H1–H4. Those remain full-build work (`docs/preregistration.md`).

## 2. Locked player set (N = 160 target)

**Rule:** For each of the 32 NHL teams, take the **first forward line** (LW, C, RW) and the **first defensive pairing** (LD, RD) **exactly as displayed on DailyFaceoff's line-combinations page for that team on snapshot date D** (`https://www.dailyfaceoff.com/teams/<team-slug>/line-combinations`). 5 skaters/team × 32 = **160 skaters**. Goalies are excluded (no goalie slot is taken). This set is fixed once `pilot2/players.csv` is written from the D snapshot; no post-hoc additions or substitutions.

**Source of record + extraction:** DailyFaceoff embeds the line data in its page `__NEXT_DATA__` JSON (verified accessible 2026-05-26). Parsing is deterministic from that blob.

**Per-team fallback (pre-declared):** If DailyFaceoff does not render a usable first line + first pair for a team on D (page error, missing slot), that team's five skaters are taken from the **NHL public API** instead: the top-3 forwards and top-2 defensemen by 2025-26 regular-season **TOI per game** among rostered skaters with ≥10 GP. Which teams used the fallback is recorded in a `roster_source` column in `players.csv`.

**Identifier resolution (deterministic):** DailyFaceoff display name → NHL API player search (`search.d3.nhle.com`) → NHL `playerId` → `/v1/player/{id}/landing` to confirm name + position + team → Wikipedia slug (candidate slugs tried in fixed order, first with >0 pageviews kept) → CapWages slug (`name.lower()`, strip `.`/`'`, spaces→`-`). Every resolved row is human-verified once before the set is locked; ambiguous names (shared surnames, disambiguation pages) are resolved by NHL `playerId` and recorded with the chosen slugs in `players.csv`. A player whose identity cannot be resolved across NHL + Wikipedia is flagged `match_quality = low` and kept in the CSV with the failure documented (not silently dropped).

## 3. Stable-core data sources (locked)

Five components feed the engagement composite (identical to v1 `pilot/preregistration.md` §3 for cross-pilot comparability):

1. `wiki_12mo` — Wikimedia REST pageviews-per-article, daily, summed over the most recent 365 days (cutoff = D − 1).
2. `trends_12mo` — Google Trends 12-month rolling mean, query = `"<First> <Last>"`, worldwide.
3. `reddit_mentions_12mo` — PRAW search across `r/hockey` + the team subreddit, query = `"<Last name>"`, last 365 days, deduped by submission ID. The PRAW 1000-result search cap is accepted as a **relative** proxy for this top-tier set; teams/players exceeding it are flagged `reddit_capped = true` and the cap is disclosed.
4. `reddit_upvotes_12mo` — sum of `score` across the matched submissions/comments.
5. `instagram_followers` — instaloader follower snapshot. **Pre-declared expectation:** Meta's anonymous block (the v1 403) will likely recur; if so, Instagram is NULL across the set and sentinel handling (§4) applies, exactly as in v1.

Exploratory sources (TikTok, X, YouTube) are out of scope for this pilot's composite.

## 4. Composite formula (locked)

Each component is **z-scored across the 160-skater set** (sample mean 0, sd 1, ddof=1). `engagement_raw` is the weighted sum of z-scores. Weights are the v1-locked vector (renormalized full-spec CES weights):

| Component | Weight |
|---|---|
| `wiki_12mo` | 0.306 |
| `reddit_mentions_12mo` | 0.250 |
| `reddit_upvotes_12mo` | 0.167 |
| `trends_12mo` | 0.139 |
| `instagram_followers` | 0.139 |

`engagement_raw(P) = Σ_c weight_c × z(component_c, P)`

**Sentinel handling:** if a component is NULL for a player, it drops from that player's sum and the remaining weights renormalize **for that player only**. Documented per player in a `dropped_components` column. Brand Depth Score (BDS) is **not** added to `engagement_raw` in this pilot: its components (jersey-list appearances, All-Star selections, captaincy) overlap the external-validation outcomes in §7 and must stay out of the predictor to keep that test clean. This mirrors v1, which also scored on the CES-side composite only.

## 5. Cap hit (locked source)

`cap_hit_M` = player's **2025-26 cap hit in $M**, parsed from **CapWages** structured page data (`__NEXT_DATA__` JSON at `https://capwages.com/players/<slug>`). Extraction is deterministic: select the contract active in 2025-26 and read its 2025-26-season `capHit` field (not the headline AAV, which can differ for front-loaded / bonus-laden deals; not a future-season row). Recorded with `cap_hit_source_url` for audit.

**Why CapWages, not PuckPedia (the originally requested source):** PuckPedia is behind a Cloudflare JS challenge that blocks all $0 automated access (plain requests, browser-header requests, WebFetch, and headless Chrome all returned 403 / "Just a moment" on 2026-05-26). CapWages exposes the same NHL contract facts as parseable structured JSON; a 13/14 match against the v1 values plus a correct recovery of the one v1 error (Brad Marchand: CapWages `capHit` $5.25M vs v1's mis-parsed $3.8173M) confirms its accuracy. The owner approved this substitution on 2026-05-26.

**Validation (pre-declared):** every parsed `cap_hit_M` is bounds-checked (must be within [$0.7M league-min, $20M]); any value failing the bound, or any player whose CapWages page is unreachable, is flagged `cap_quality = low` and excluded from the Marchand Index leaderboard (kept in the CSV). A 10-player random sample is hand-verified against the live CapWages pages before compute.

## 6. Peer matching (locked)

For each skater P among the 160:

- **Hard position filter:** forwards (C/L/R/W) compared only to forwards; defensemen (D) only to defensemen. (Forwards ≈ 96, D ≈ 64 — both comfortably support K=10.)
- **Skill vector:** `(age, PPG, TOI/G)`, standardized across the 160-set (the v1 feature set, confirmed available from the NHL API landing endpoint). 5v5 points/60, if cleanly available from the API for ≥90% of the set, is added as a **reported robustness re-run only**; it is not part of the locked primary peer vector.
- **Distance:** Mahalanobis distance using the sample covariance of the skill vector within position group (inverse-covariance weighting; N is large enough for a stable estimate, unlike v1 which used standardized Euclidean).
- **K = 10 nearest peers** (sentinel `effective_K` records the actual count if a position group is somehow short).
- `peer_engagement_mean(P) = mean(engagement_raw across K peers)`.
- `OAQ_observed(P) = engagement_raw(P) − peer_engagement_mean(P)`.

## 7. Market proxy + portable OAQ (locked — the v1 fix)

The v1 roster-mean-Wikipedia baseline is **replaced** by an exogenous team market-size proxy that roster composition cannot inflate.

`MarketSize_team` = equal-weight mean of the z-scores (across the 32 teams) of:

1. `metro_population` — population of the team's home metropolitan area (static public figures; for the two-team markets NYC/LA, the metro population is shared — pre-declared, since both teams draw on the same market).
2. `arena_attendance` — average regular-season home attendance, most recent completed season (public).
3. `team_social_followers` — official **team** Instagram follower count (instaloader on 32 team handles).

**Graceful degradation (pre-declared):** any of the three components that cannot be fetched cleanly for all 32 teams (e.g. team Instagram 403) is dropped and `MarketSize_team` is the equal-weight z-mean of the surviving components. The component set actually used is recorded in `market_proxy.csv` and `results.md`. Metro population alone is the irreducible floor (always available).

`OAQ_portable(P) = (engagement_raw(P) − z(MarketSize_team(P))) − mean[(engagement_raw − z(MarketSize_team)) across P's K peers]`

where `z(MarketSize_team)` is standardized across the 32 teams. Both terms are on standardized scales, so the subtraction is meaningful (same structure as v1, exogenous baseline swapped in).

## 8. Marchand Index (locked)

`marchand_index(P) = OAQ_portable(P) / cap_hit_M(P)`

Every published `OAQ_observed`, `OAQ_portable`, and `marchand_index` ships with a **95% bootstrap CI** (§10) and a `match_quality` flag.

## 9. External validation (locked — the headline test)

This pilot tests `OAQ_portable` against **independent** attention outcomes not used anywhere in the composite. Both are reported with effect size + 95% bootstrap CI **regardless of direction**. These partially bank full-build Gates 1–2.

| ID | Outcome (independent) | Test | Floor / Target |
|---|---|---|---|
| **V1 (primary)** | NHL official top-selling-jersey list, most recent published | (a) Spearman ρ between `OAQ_portable` rank and jersey-list rank on the overlap; (b) AUC of `OAQ_portable` discriminating jersey-list members from non-members across the 160 | ρ ≥ 0.40 / 0.50 (Gate-1 floor/target) |
| **V2 (secondary)** | 2024 NHL All-Star fan-vote totals (last ASG before the 2024-25 4 Nations replacement) | Spearman ρ between `OAQ_portable` and 2024 fan-vote share, among the 160 who received 2024 votes | ρ ≥ 0.45 / 0.55 (Gate-2 floor/target) |

**Caveats locked in advance:** both outcomes are coarse and lagged (jersey list is ~top-25; 2024 ASG predates current roster moves). **Underpowered-overlap rule:** if the overlap for a test is < 10 players, that test is reported as **inconclusive (underpowered)**, not pass/fail. **Direction rule:** a ρ below floor is reported as an honest disconfirmation — the abstract then states the pilot did not establish external validity at the Gate floor and defers to the full-build gates; it is not quietly dropped.

## 10. Bootstrap procedure (locked)

1,000 draws per published quantity; pre-registered seed **20260526**. Each draw resamples (with replacement) the player's Wikipedia daily-pageview vector and Reddit submission/comment pool, recomputes `engagement_raw`, recomputes the K-peer mean and `MarketSize` adjustment from the same draw, recomputes `OAQ_observed` / `OAQ_portable` / `marchand_index` (cap hit not resampled), and takes the 2.5th / 97.5th percentiles. For V1/V2, each draw resamples the cohort at the player level and recomputes ρ; CI = 2.5th–97.5th percentile of the 1,000 ρ values.

## 11. Pre-registered expected patterns (falsifiable; reported regardless of direction)

| ID | Pattern | Test |
|---|---|---|
| **PA** | `OAQ_portable` aligns with independent jersey demand. | V1 Spearman ρ ≥ 0.40 (primary external gate). |
| **PB** | `OAQ_portable` aligns with independent fan voting. | V2 Spearman ρ ≥ 0.45 (secondary external gate). |
| **PC** | Cap/market adjustment reorders the leaderboard non-trivially. | ≥ 3 of the top-10 by `engagement_raw` are displaced from the top-10 by `marchand_index`. |

Each verdict (`confirmed` / `disconfirmed` / `inconclusive`) is written to `pilot2/results.md` with effect size + CI. Any pattern may fail and the abstract still ships — failure is reported as a sensitivity finding.

## 12. Figure specification (locked)

`pilot2/figure.png`, matplotlib, two panels:

- **Panel A — rank reordering:** top-N (N≈12) by `engagement_raw` vs top-N by `marchand_index`, real player names, cap hits annotated, thin grey lines linking a player's two positions; bold for hold-overs. No archetype color-coding.
- **Panel B — external validation:** scatter of `OAQ_portable` (x) vs the V1 primary outcome (jersey-list rank or membership) (y), with the Spearman ρ and its 95% CI annotated. If V1 is underpowered, Panel B uses V2; if both are underpowered, Panel B is omitted and §4 of the abstract reports the reordering only.

Figure styling (sizes, fonts) is tuneable; **what is plotted and how rankings are computed is fixed here.**

## 13. Anti-tuning commitments

- Composite weights (§4), peer features (§6), market-proxy components (§7), and external-validation floors (§9) are fixed before any pilot2 data is fetched. No adjustment after results are seen; any change is a §14 amendment logged *before* re-running, with the original numbers retained.
- Per-player intuitions ("did Bedard / a polarizing player rank where we hoped?") are spot-check signals only; they never feed back into weights, features, or floors.
- No revenue claims. Attention is a proxy for fan demand throughout.

## 14. Output inventory + amendments

**Outputs after the run:** `pilot2/players.csv` (160), `pilot2/raw/{wiki_pageviews,trends,reddit_counts,instagram_followers,nhl_skill,cap_hits}.csv`, `pilot2/market_proxy.csv` (32), `pilot2/external_outcomes.csv`, `pilot2/oaq_pilot.csv`, `pilot2/results.md`, `pilot2/results.json`, `pilot2/figure.png`.

**Amendments** (date + reason; earlier sections never edited silently):

**A1 (2026-05-27) — Wikipedia slug resolution hardened. Logged before re-running the wiki fetch.**
The §2 rule "candidate slugs tried in fixed order, first with >0 pageviews kept" produced two systematic measurement errors when run against the 160 set:
1. **Redirect undercount.** The Wikimedia pageviews API counts views to the *exact* title requested and does **not** follow redirects. For players stored under a nickname/un-accented slug that is a redirect to the canonical article (e.g. `Alex_Ovechkin` → *Alexander Ovechkin*; `Martin_Fehervary` → *Martin Fehérváry*), the rule kept the redirect (>0 direct-redirect hits) and captured only a tiny fraction of true pageviews (Ovechkin: 7,059 vs a six-figure canonical total).
2. **Wrong-entity match.** When the bare "First_Last" title is a *different real article*, the rule silently kept it (e.g. `Marco_Rossi` = the Italian football manager / a disambiguation page, not the NHL forward, who lives at *Marco Rossi (ice hockey)*).

**Corrected resolver (applied identically to all 160):** each candidate title — order: stored `First_Last`, then `First Last (ice hockey)` — is resolved through the MediaWiki API with `redirects=1` to its canonical title, and **accepted only if its linked Wikidata entity carries occupation (P106) = ice-hockey player (Q11774891)**; pageviews are then summed for that canonical title. Disambiguation pages and non-hockey entities are rejected. If no candidate satisfies the occupation test, the first non-disambiguation, non-missing canonical title is used and flagged `wiki_match = weak`; if none exists, `wiki_12mo` is NULL and `wiki_match = none` (sentinel renorm per §4). Each row records `wikipedia_slug_chosen`, `wikidata_qid`, and `wiki_match` for audit.

This is a uniform, mechanical data-collection fix. It does **not** alter composite weights (§4), peer features (§6), market-proxy components (§7), the Marchand Index (§8), or external-validation floors (§9), and is decided by article identity, not by any player's resulting rank.

**A2 (2026-05-27) — Reddit retrieval mechanism: public JSON endpoint instead of PRAW. Logged before the reddit fetch.**
§3.3 named "PRAW search." PRAW requires a registered OAuth app (client id/secret); none is available at the $0 constraint. Reddit's **unauthenticated public search JSON** (`https://www.reddit.com/r/<sub>/search.json?q=<last name>&restrict_sr=1&sort=new&t=year`) returns the identical search results PRAW wraps (same subreddits `r/hockey` + team sub, same last-name query, same trailing-year window, same per-submission `score`), paginated via the `after` cursor up to the pre-registered 1,000-result cap. This changes the **transport only**, not the data, query, window, dedup rule, or the `reddit_capped` flag. If Reddit rate-limits or blocks the endpoint for a player/sub, that contribution is NULL and `reddit_status` records `partial`/`null` (sentinel renorm per §4) — exactly the degradation §3.5 anticipated for blocked sources.

**A3 (2026-05-27) — V1 jersey-list operationalization, given data availability. Logged before computing V1.**
§9's footnote anticipated a "~top-25" official jersey list. In fact the only NHL/Fanatics best-selling-jersey rankings publicly retrievable at $0 are short PR lists (the NHLPA/NHL "most popular jerseys" pages are client-rendered SPAs; retrieval required web search). The two we verified:
- **2024-25 season (most recent), NHL League PR** (via RMNB, 2025-10-13): 1 Ovechkin, 2 Bedard, 3 Matthews, 4 McDavid, 5 Crosby.
- **NHL.com, 2023-10-10** (`/news/bedard-hughes-marchand-top-selling-nhl-jerseys-since-june`): 1 Bedard, 2 J. Hughes, 3 Marchand, 4 Crosby, 5 Pastrnak, 6 Bergeron, 7 Ovechkin, 8 Kaprizov, 9 MacKinnon, 10 Makar.

A single most-recent list is only top-5 → near-zero overlap with a 160-set dominated by mid-tier first-liners. To give V1 honest discriminating power, it is operationalized two ways, **both reported regardless of direction**:
- **V1a (rank; secondary):** Spearman ρ between `OAQ_portable` and the most-recent (2024-25) jersey rank over the in-sample overlap. Small n expected → likely underpowered.
- **V1b (membership; primary AUC):** AUC of `OAQ_portable` discriminating "appeared on an official NHL/Fanatics best-selling-jersey list in 2023-24 or 2024-25" (the **union** of the two verified lists) vs. non-members across the 160.

Both lists are independent of the model inputs (wiki/Reddit/Trends/IG). Membership uses **only** these two strongly-sourced official lists; no soft-sourced names are added to reach the §9 n≥10 threshold. The in-sample overlap n is reported; if n<10, V1b is labeled underpowered per §9. (Retrieval also confirmed the §3.5-class reality that the 2024 ASG fan vote, V2, was published as membership only — 12 fan picks, mostly goalies/non-first-liners — so V2 overlap is 4/160 and underpowered, reported as such.)

**A4 (2026-05-27) — Marchand Index denominator: skill-EXPECTED (market-rate) cap, not actual cap. Logged BEFORE re-running compute with the amended denominator.**
The §8 definition `marchand_index = OAQ_portable / cap_hit_M` is dominated by an artifact of the collective-bargaining agreement, not by attention efficiency. Entry-level contracts (ELCs) are capped at a CBA-fixed ceiling (~$0.95M for 2025-26) regardless of a player's actual skill or market value, so `1 / cap_hit_M` mechanically explodes for any rookie. In the initial pilot2 run the MI top-10 was 9 of 10 ELC players (median age 21); a player with one-fifth of Crosby's market-stripped attention surplus outranked him purely because his salary is CBA-capped. The §6 peer matching does not correct this: it standardizes the *attention* side (OAQ), and never touches the cap denominator.

**Corrected denominator (applied identically to all 160):** `cap_hit_M` is replaced by `expected_cap`, the player's predicted **market-rate** cap from an ordinary-least-squares fit of `cap_hit_M ~ PPG + TOI/G`, estimated **separately within each position group** (forwards, defensemen) over the 160-set, with the prediction floored at the 2025-26 league minimum ($0.775M). Player **age is deliberately excluded** from this regression: because age is a §6 peer feature, an age-aware expected cap would re-import the rookie-scale floor through young, cheap comparison players (verified — a ±5-year age band *lowers* a rookie's expected cap and *re-inflates* MI). The headline metric becomes:

`marchand_index(P) = OAQ_portable(P) / expected_cap(P)`

The original raw-cap quantity is **retained** as `marchand_index_rawcap` (the §8-original) for audit and as a secondary "current-season bargain" lens. This is a principled de-biasing of a known, a-priori-obvious structural artifact decided on reasoning grounds — not a post-hoc adjustment chasing any player's rank — and the original column is preserved per §13. It does **not** alter the composite weights (§4), the peer features or `OAQ_observed`/`OAQ_portable` (§6/§7), or the external-validation outcomes and floors (§9); only the Marchand Index denominator changes. Interpretation: because for players already on market contracts the fitted `expected_cap` ≈ `cap_hit_M` (the metric moves them little), while for ELCs it substitutes the player's market-rate value, `marchand_index` now measures intrinsic attention efficiency that is stable across the ELC→extension transition rather than rewarding temporary contract timing.

**A5 (2026-05-27) — §7 market correction: one-sided damped subtraction with λ = 0.5. Logged BEFORE re-running compute with the amended OAQ_portable.**
The §7 formula `OAQ_portable(P) = engagement_raw(P) − z(MarketSize_team(P)) − peer_mean(of same)` implicitly assumes that 100% of market-driven attention is non-portable — that a player who moves teams loses all of the engagement boost their team's market provided. Two structural failure modes emerged in the initial pilot2 run:

1. **Small-market amplification.** For players on teams with deeply negative `market_z` (SJS = −2.27, BUF ≈ −1.5, WPG ≈ −2.0), the locked formula subtracts a large negative number, *adding* the absolute value back to engagement regardless of whether the player has any above-replacement attention. Empirically: Mukhamadullin (SJS, `OAQ_observed` = −0.07) and Orlov (SJS, `OAQ_observed` = −0.19) rank in the MI top-10 driven *entirely* by the +2.27 SJS market subtraction; their measured attention is at or below their peer mean.
2. **Big-market under-credit.** For players on teams with positive `market_z` (TOR, MTL, NYR), the full subtraction discounts attention that empirically follows the player when they move (the Marner/Tavares "fans travel with the player" phenomenon).

The locked assumption is asymmetric in its damage: it bonuses small-market players with no genuine attention surplus and over-penalizes big-market players whose fan equity does partially travel.

**Corrected formula (applied identically to all 160):**

`OAQ_portable(P) = engagement_raw(P) − λ × max(0, market_z(P)) − peer_mean(of same)`

with **λ = 0.5**.

Two structural properties:
- **One-sided (`max(0, ·)`):** small-market players (`market_z < 0`) receive zero correction. Their measured engagement *is* their portable engagement — they had no market boost to discount.
- **Damped (λ < 1):** big-market players (`market_z > 0`) receive a partial discount of `λ × market_z`, not the full subtraction. This reflects the empirical reality that a fraction of market-driven attention is portable (fans travel with stars).

**λ justification (audience-defensible):** with no empirical anchor for the share of market-driven attention that is portable, we adopt the **maximum-entropy midpoint** λ = 0.5 — the unique unbiased prior between the bounds λ = 0 (no market correction at all) and λ = 1 (locked-method assumption that no attention travels). λ is committed *before* the re-run and is not grid-searched against any external metric. The full sensitivity ladder λ ∈ {0, 0.25, 0.5, 0.75, 1.0} is reported in `results.md` as a robustness check; the headline λ = 0.5 is the only number used in the abstract and figure.

**Locked-v1 retained:** the original two-sided full subtraction `OAQ_portable` is preserved as `OAQ_portable_lockedv1` in `oaq_pilot.csv` for audit, per §13. All three Marchand Index variants (`marchand_index`, `marchand_index_rawcap`, `marchand_index_hybrid`) are recomputed off the new A5 `OAQ_portable`.

**Anti-tuning compliance (§13):** A5 is decided on reasoning grounds about market mechanics (asymmetric damage of the locked assumption); λ = 0.5 is the maximum-entropy midpoint, not chosen after inspecting any player's rank; the original column is preserved; external-validation floors (§9) and the PA/PB tests are unchanged. PC's "≥3 displaced" verdict is recomputed off the A5 leaderboard. This does **not** alter §4 composite weights, §6 peer features, or §8/A4 denominator construction.

**A6 (2026-05-28) — V3 team-level triangulation validation gate. Logged BEFORE any team-level outcome data is fetched.**
§9 V1a/V1b/V2 are all reported underpowered against the §9 n≥10 rule (jersey-list overlap = 8/160 for V1b; ASG = 4/160 for V2; V1a rank-overlap = 4). The pilot's external validation is therefore inconclusive on all three pre-registered pathways, leaving PC (a within-set leaderboard reordering) as the only confirmed test. A reviewer can correctly say the pilot has not demonstrated external validity. The remedy is a fourth pathway that *cannot* be underpowered for this 160-set: team-level triangulation at n = 32 teams.

**V3 specification (locked):**
- **Outcome (independent of all model inputs):** team-level popularity proxy. As originally specified, the equal-weight z-mean of (a) team subreddit subscriber count + (b) team Wikipedia 12-mo pageviews. **Pre-fetch availability check (2026-05-28):** Reddit blanket-blocks `/r/<sub>/about.json`, `/about/.json`, `api.reddit.com/r/<sub>/about`, and `old.reddit.com/r/<sub>/about.json` with HTTP 403 across all user-agent strategies attempted at the $0 constraint (verified on 3 representative subs: r/leafs, r/canucks, r/penguins, all returning a 189,908-byte anti-bot challenge body). This is the §3.5-class blocked-source pattern the pre-reg anticipated and parallel to §7's "graceful degradation: drop the component, recompute on the survivors." V3 outcome is therefore **team Wikipedia 12-mo pageviews only** (Wikimedia REST API, canonical team article, no z-mean, single signal). This change is logged before any V3 computation runs. Team Wikipedia pageviews are public, fully independent of `engagement_raw` (player-keyed wiki, not team-keyed), and independent of `market_proxy` (`metro_population`, `arena_attendance`, `team_social_followers`).
- **Predictor:** for each of the 32 teams, sum of `OAQ_observed` across the team's 5 pilot players (1 line + 1 pair). `OAQ_observed` is the peer-matched residual that strips skill, so a positive correlation tests that **attention surplus beyond skill aggregates to a team-level fan-attention signal that is not captured by skill alone**. Sum of `engagement_raw` is *also* reported as a mechanical-baseline robustness check.
- **Test (V3):** Spearman ρ between the 32 team-summed `OAQ_observed` and the 32 team-popularity z-mean.
- **Pre-registered floor / target:** ρ ≥ 0.40 / 0.50 (mirrors V1's Gate floor; powered at n = 32 by §9's n ≥ 10 rule).
- **Pattern verdict PD:** confirmed if V3 ρ ≥ 0.40; disconfirmed if below; reported as honest disconfirmation in either direction with bootstrap CI.
- **Power:** n = 32 is above the §9 underpowered threshold; Spearman power at n=32, α=0.05 two-sided needs |ρ| ≥ ≈0.35 to reject ρ=0. The 0.40 floor exceeds this minimum-detectable effect, so a confirmed V3 is statistically meaningful.

**Honest construct-overlap disclosure (in advance):** team subreddit subscribers and team Wikipedia pageviews are both partially correlated with team market size, which is also captured in `market_proxy`. They are *independent of the model's input vector* (no player-keyed wiki/reddit/trends/IG, no metro_pop/arena_attendance), but they are *not* independent of the underlying construct of team-level fan attention. V3 therefore tests **whether peer-matched, market-adjusted player attention surplus aggregates to a team-level held-out attention signal**, not whether it predicts a wholly unrelated outcome. This is a triangulation gate, not a clean causal validation, and is reported as such.

**Anti-tuning compliance (§13):** V3 is logged before the team-outcome fetch; the floor (ρ ≥ 0.40) mirrors V1's and is not chosen after seeing the result; the outcome construction (equal-weight z-mean of two team-account signals) is fixed in advance; A5 is unchanged. No retroactive adjustment of V1a/V1b/V2 floors; those tests still report inconclusive per §9's underpowered rule. The new test is *added*, not substituted.

**A7 (2026-05-28) — §2 player-set selection rule: objective NHL-API deployment (TOI/G), position-split, replacing the DailyFaceoff line chart. Logged BEFORE any re-fetch or re-compute on the new set.**
§2 selected each team's five skaters from **DailyFaceoff's editorial line-combinations chart** (first forward line + first defensive pairing), with an NHL-API TOI/G *fallback* only when DF failed to render. For a stats-literate, overclaim-hostile audience this carries two defects:
1. **Subjective, non-reproducible input.** "First line" on DailyFaceoff is a human editor's depth-chart judgment that can change daily and cannot be independently reproduced from public data. The locked set therefore inherits an unauditable editorial choice at its foundation.
2. **Scrape fragility.** The selection depended on parsing DailyFaceoff's `__NEXT_DATA__` blob, an undocumented private structure that can break or change without notice.

**Corrected rule (applied identically to all 32 teams):** each team's five skaters are the **most-deployed skater at each position by 2025-26 regular-season time-on-ice per game (TOI/G)**, from the NHL public API (`/v1/player/{id}/landing`, `seasonTotals`, `gameTypeId == 2`):
- the **left wing** (positionCode `L`), **center** (`C`), and **right wing** (`R`) with the highest TOI/G;
- the **two defensemen** (`D`) with the highest TOI/G.

5 skaters/team × 32 = **160** (96 F / 64 D), unchanged in size and position balance (1 L + 1 C + 1 R + 2 D per team, vs the previous 3 F + 2 D). Goalies excluded.

**Eligibility floor:** a skater is eligible only with **≥ 41 games played** (half of the 82-game season) in the 2025-26 regular season, so a short high-minute call-up cannot win a position slot on a small sample. TOI/G and GP are aggregated across all current-season reg-season `seasonTotals` rows (GP-weighted TOI/G; summed GP) so a mid-season trade is handled correctly. If a position has **no** skater clearing the floor for a team (rare), the floor is relaxed for that one slot to the highest-TOI/G rostered skater at that position, and the relaxation is recorded in `roster_source`.

**Why this strengthens the pilot:** the foundation of the locked set becomes an objective, fully-reproducible NHL quantity (deployment), removing the editorial/scrape dependency and giving a cleaner "best-deployed-vs-best-deployed" peer-matching frame. Identifier resolution (NHL `playerId` → Wikipedia → CapWages), the composite (§4), peer features and OAQ (§6/§7), the A4 denominator, the A5 damped correction, and all validation floors (§9, A6/V3) are **unchanged**; only *which skaters populate the set* changes.

**Replacement, not robustness pair (owner decision 2026-05-28):** the A7 TOI set **supersedes** the DailyFaceoff set as the single locked set. The DailyFaceoff-built `players.csv` is retained in git history for audit; it is not carried as a parallel reported set. All downstream artifacts (raw fetches, `market_proxy.csv`, `oaq_pilot.csv`, `results.md/json`, `figure.png`) and the abstract's headline numbers are recomputed on the A7 set. The 32-team enumeration and `team_code` scheme (`raw/teams.csv`) are unchanged.

**Re-confirmation obligation (disclosed in advance):** PD/V3 (ρ = 0.418 on the DF set) is the pilot's only confirmed validation gate. Re-rolling the set re-rolls V3. The new V3 ρ is reported **regardless of direction** against the unchanged 0.40 floor; if it falls below floor it is reported as an honest disconfirmation per §9's direction rule, not quietly dropped.

**Anti-tuning compliance (§13):** A7 is decided on reproducibility/defensibility grounds and logged before any re-fetch or re-compute on the new set; the selection rule (max TOI/G per position, ≥41 GP) is mechanical and fixed in advance, not chosen after inspecting any player's resulting rank; composite weights (§4), peer features (§6), market-proxy components (§7), the A4 denominator, the A5 λ, and all validation floors (§9, A6) are unchanged. The previous set's numbers are preserved in git history per §13.

**A8 (2026-05-28) — §8 headline denominator: HYBRID (rookie-deal → `expected_cap`; all others → actual `cap_hit_M`), replacing A4's expected-cap-for-all (Lens 5) as the published headline lens. Logged BEFORE the full-Reddit final compute.**
A4 introduced `expected_cap` to remove a CBA artifact: entry-level contracts are hard-capped at ~$0.95M regardless of skill, so `1 / cap_hit_M` mechanically explodes for rookies who had **no legal path** to a market-sized deal. A4 applied `expected_cap` to **all 160** players (Lens 5) and named that the headline. On reflection this over-corrects. A **post-ELC** player's cap hit is a *freely negotiated market price*, not an artifact; dividing his attention surplus by a model-predicted `expected_cap` overwrites real contract information and **erases the exact signal the index exists to surface** — a player who out-produces his actual deal on attention. Concretely, a post-ELC near-minimum contract (e.g. a $1.0M deal that hybrid/raw ranks #1) is normalized away to mid-pack under expected-cap-for-all.

**Corrected headline (Lens 4, hybrid):**
- rookie-deal players (`cap_hit_M ≤ $0.975M AND age ≤ 25`) → denominator = `expected_cap` (CBA hard cap removed, because no market deal was legally possible);
- all other players → denominator = actual `cap_hit_M` (a freely negotiated price is the honest cost of the player).

The headline now answers: **which players generate the most fan-attention surplus per dollar of their actual deal — projecting only those contractually barred from signing one.** `expected_cap`-for-all (Lens 5) is retained and reported as the *intrinsic-efficiency* lens (attention per skill-deserved dollar); `marchand_index_rawcap` and the rookie-only / non-rookie lenses are unchanged. Five lenses are still reported side-by-side; only the **headline pointer** moves from Lens 5 to Lens 4.

**Re-evaluation obligation (disclosed in advance):** PC (top-10-by-engagement displacement) is recomputed against the hybrid headline and reported regardless of direction; the headline top-5 / top-10 changes accordingly.

**Anti-tuning compliance (§13):** A8 is a principled denominator-*scope* correction (projection is justified only where a market deal was legally impossible), applying a mechanical rule fixed in advance, and logged before the full-Reddit final compute. The provisional (86/160-Reddit) leaderboard was visible when the principle was articulated; the principle does not depend on any player's resulting rank, all five lenses remain reported so no ranking is suppressed, and the A4 expected-cap-for-all numbers are preserved as Lens 5 for audit. The rookie-deal flag definition, composite (§4), peer features (§6), A5 λ, the `expected_cap` OLS spec (A4), and all validation floors (§9, A6/V3) are unchanged.

**A9 (2026-05-28) — Reddit transport: authenticated OAuth (`oauth.reddit.com`) replacing the unauthenticated `www.reddit.com/.../search.json` endpoint. Transport only; logged before the affected players are re-fetched.**
A2 used Reddit's unauthenticated public search JSON. On 2026-05-28 that endpoint began returning HTTP 403 (a block page, not JSON) for this IP after fetch bursts, and a 20-minute no-contact cooldown did not clear it; `old.reddit.com` and browser-UA variants 403 identically. The 74 players newly added by the A7 set therefore could not be collected anonymously. A9 switches the transport to Reddit's authenticated OAuth API: a free **"script"** app's `client_id` + `client_secret` obtain an app-only bearer token (`client_credentials` grant) used against `oauth.reddit.com/r/<sub>/search`. This is **transport only** — identical to A2 in source (Reddit), subreddits (`r/hockey` + team sub), query (player last name), `sort=new`, 365-day window, submission-id dedup, and 1,000-result cap. The 86 players already collected anonymously (status ok/partial) are retained as-is; only the missing/NULL players are fetched over OAuth (the resume logic is unchanged). Cost remains **$0** (a Reddit account and app registration are free). Credentials are read from environment variables or a gitignored `pilot2/.env`; none are committed.

**Anti-tuning compliance (§13):** no change to the composite (§4), weights, peer features (§6), denominators (A4/A8), λ (A5), or validation floors (§9, A6/V3); the only change is the HTTP transport used to retrieve the identical Reddit quantity. Logged before the OAuth re-fetch runs.

**A10 (2026-06-17) — §2 player set: WHOLE-LEAGUE end-of-2025-26 roster snapshot replacing the 160-skater A7 Tier-1 set. Logged BEFORE any production fetch or compute on the new set.**
Context: the CASSIS abstract was accepted for a poster (session 2026-09-12). With the submission deadline passed, the owner directed expanding the pool from the curated Tier-1 slice (A7: each team's most-deployed L/C/R + top-2 D by TOI/G, 160 skaters) to **every rostered skater in the league**. This redefines the §2 player set only; the method (§4 composite + weights, §6 K=10 Mahalanobis peer matching, §7/A5 λ=0.5 one-sided damped market correction, §8/A8 hybrid headline denominator, §9/A6 V1/V2/V3 floors, §10 bootstrap, A9 OAuth transport) is **unchanged**.

**Snapshot (locked, perishable).** For each of the 32 teams, every skater in the `forwards` + `defensemen` groups of the NHL public roster endpoint `/v1/roster/{team}/current` (goalies excluded by design — §9 excludes them from headline analysis throughout, and K=10 peer matching breaks for the position). Captured **once** on **2026-06-17** and locked, because `/current` is overwritten by the 2026-07-01 free-agency window and the end-of-season state is then unrecoverable. Built by `fetch_rosters_league.py` (supersedes `fetch_rosters_toi.py`); `nhl_player_id` comes straight from the roster endpoint; the 32-team enumeration + `team_code` scheme (`raw/teams.csv`) and the `players.csv` schema are unchanged, so every downstream fetcher and `compute_oaq.py` run unmodified. Raw snapshot size: **788 skaters (506 F / 282 D)**, `roster_snapshot_date=2026-06-17`.

**Refinement (the qualification rule).** A mid-June `/current` pull is not a clean end-of-season active roster: per-team counts swing 18→33 because high-count teams' rosters include signed reserves / org-depth prospects, some of whom have **never played an NHL game**. A GP diagnostic over the 788 found **21 skaters with 0 NHL regular-season games in 2025-26**; of those, 14 have **0 career NHL games** (junior/AHL prospects — pure noise: no production, so they cannot be peer-matched, NaN engagement) and 7 are career NHLers who were absent/injured all season (**verified: Aleksander Barkov, FLA — no 2025-26 row, eight prior 50–82 GP seasons**; a naive "≥1 GP this year" filter would wrongly drop him). The locked qualification rule is therefore a **bright line, no arbitrary threshold**:

> A skater qualifies iff he is on a team's 2026-06-17 `/current` forwards/defensemen roster **AND has played ≥ 1 NHL regular-season game in his career** (`gameTypeId==2`, `leagueAbbrev=="NHL"`, summed over all `seasonTotals`). This subsumes "played ≥1 GP in 2025-26"; it keeps injured/absent career NHLers (Barkov) and drops never-played org depth.

**Final locked pool: 774 skaters (497 F / 277 D).** 14 never-played prospects dropped (Nico Myatovic, Stian Solberg, Noah Warren — ANA; Riley Fiddler-Schultz, Anton Wahlberg, Vsevolod Komarov, Radim Mrtka — BUF; Alex Gagne — COL; Aiden Fink — NAS; Tyler Boucher, Oskar Pettersson — OTT; Oscar Eklind — PHI; Cam Hebig — UTA; Trevor Connelly — VEG). 7 career NHLers with 0 GP in 2025-26 retained (Barkov, Graeme Clarke, Helge Grans, Ben McCartney, Scott Perunovich, Maksymilian Szuber, Jeremy Davies). The applied transform (`filter_pool_played.py`) re-sequences `player_id` 1..774 and writes a full **`pool_gp_audit.csv`** with all 788 rows + per-player `cur_gp_2025_26` / `career_nhl_gp` / `kept` / `drop_reason`; the pre-filter 788 snapshot also remains in git history. No fetch failures (0/788).

**Data-honesty safeguard — `small_sample` flag (descriptive, NON-exclusionary).** A new flag is set in `compute_oaq.py` for any skater with `< 20` NHL regular-season games this season (or a NULL games_played, i.e. a season-long absence). Flagged players stay in the pool and in **every** computation — the §10 bootstrap CIs already widen for thin signal — but the flag warns that the headline must not be quoted on a tiny-sample call-up. It ships beside `match_quality` in `oaq_pilot.csv` and `results.md`. This is criterion-6 honesty (an explicit limit-of-claim), not an exclusion.

**Effect on the method.** Peer pools grow from ≈96 F / 64 D to **497 F / 277 D**, so K=10 matching becomes *more* robust, not less. Composite weights (§4: wiki 0.306, reddit_mentions 0.250, reddit_upvotes 0.167, trends 0.139, instagram 0.139), peer features (§6: age, ppg, toi_per_game), the A4 `expected_cap` OLS, the A5 λ, the A8 hybrid headline, the A9 OAuth transport, and all validation floors (§9 V1/V2, A6 V3) are unchanged.

**Clean uniform re-pull.** Because `player_id` is set-relative, all attention/skill/cap sources are re-pulled fresh keyed to the new IDs (no cache reuse of old-ID rows). `raw/reddit_counts.csv` + `raw/reddit_detail.csv` are purged before any Reddit run (the documented resume pitfall: `load_resume` keys on `player_id`).

**Re-confirmation obligation (disclosed in advance).** Re-rolling the set re-rolls every validation pathway, including V3/PD (the pilot's confirmed gate on the A7 set). The new V1/V2/V3 numbers are reported **regardless of direction** against the unchanged §9/A6 floors; any fall below floor is an honest disconfirmation per §9's direction rule, not a quiet drop. `external_outcomes.csv` (jersey/ASG membership) and `team_outcomes.csv` are rebuilt for the 774 set before compute. **Reddit OAuth credentials remain the one hard prerequisite for the final compute** (0.417 of the engagement weight); no-credential sources (NHL skill, Wikipedia, cap hits, best-effort Trends) are fetched first.

**Anti-tuning compliance (§13):** A10 is a player-set redefinition decided on coverage grounds (whole-league claim) and logged **before** any production fetch or compute on the new set; the qualification rule (`/current` membership + career ≥1 NHL GP) is mechanical and fixed in advance, not chosen after inspecting any player's resulting rank; the `small_sample` threshold (20 GP) is a descriptive, non-gating flag; composite weights, peer features, denominators (A4/A8), λ (A5), OAuth transport (A9), and all validation floors (§9, A6) are unchanged; the pre-filter 788 snapshot and the full per-player keep/drop audit are preserved for inspection.

**A11 (2026-06-19) — Reddit attention window: a FIXED trailing-365-day window ENDING the last day of the 2025-26 regular season (2026-04-17 inclusive), replacing the fetch-anchored trailing-365-day window (§3.3-3.4, A2). Logged BEFORE the 774-set production Reddit fetch.**
§3.3-3.4 (and A2's "trailing-year window") defined the Reddit window as the most recent 365 days *as of the fetch moment* (`t=year` + a `created_utc ≥ now − 365d` client cutoff). Anchoring the window to run-time is unsafe for this set's compute date: the production fetch runs 2026-06-19, during the 2026 Stanley Cup playoffs, so a fetch-anchored window bakes the entire 2026 playoff run into "attention." OAQ peer-matches attention against **regular-season** production (§6 features = age, ppg, toi_per_game — no playoff stats), so playoff buzz enters the numerator with no matching production term. The bias is structured: it accrues to players whose teams *made the playoffs* (a team-quality signal) and is asymmetric across a re-fetch (playoff-run players gain buzz; eliminated players stay flat). The attack a hostile statistician makes — "your metric is partly just measuring who made the playoffs" — is correct under the fetch-anchored window and must be removed before the headline is computed.

**Corrected window (applied identically to all 774):** a **fixed** trailing-365-day window **ending the last day of the 2025-26 NHL regular season, 2026-04-17 inclusive** (api-web.nhle.com `standingsEnd` for season `20252026`; pulled, not fabricated). The window is therefore [2025-04-18 00:00 UTC, 2026-04-18 00:00 UTC) — identical for every player and independent of when the scrape runs. The window **length** (365 days) is unchanged from the pilot, so the `*_12mo` magnitude stays comparable; only the **endpoint** moves off the playoffs and onto the regular-season boundary, aligning the attention window with the regular-season production window OAQ matches against. This removes the made-the-playoffs confound and the re-fetch asymmetry, and makes the window pre-registerable as a fixed calendar interval rather than a moving one.

**Mechanism.** Reddit's search `t` parameter changes `year → all`: from a June fetch `t=year` only reaches ~back to June 2025 and would clip the window's early edge (Apr–Jun 2025). With `sort=new` the search returns newest-first, so the fetcher **skips** posts newer than the window end (the 2026 playoff/offseason posts), collects posts inside the window, and **stops** paging once a post falls below the window start (everything beyond is older). Subreddits (`r/hockey` + team sub), last-name query, submission-id dedup, the 1,000-result cap, and the `reddit_capped` flag are unchanged from A2/A9.

**Honest residual (limit-of-claim, criterion 6).** A 365-day window ending 2026-04-17 begins 2025-04-18, so its *oldest* ~2 months (mid-Apr → mid-Jun 2025) overlap the **2024-25** playoffs. The window therefore does not exclude playoff buzz entirely; it trades *current-season* playoff contamination (matched against 2025-26 production — the damaging case) for *prior-season* playoff buzz sitting at the decayed far edge of the window, uncorrelated with the 2025-26 team-quality signal the confound concerns. This residual is disclosed on the poster as a stated limitation, not hidden. A tighter regular-season-span-only window (≈6.5 months) was considered and rejected because it would break the pilot-comparable "12-month" magnitude for a second-order gain.

**Anti-tuning compliance (§13):** A11 is decided on confound-removal grounds and logged **before** the 774-set production Reddit fetch; the window endpoint is an objective external calendar date (NHL-API regular-season end), fixed in advance and applied uniformly to all 774, not chosen after inspecting any player's resulting attention or rank; the window length (365 d), composite weights (§4), peer features (§6), denominators (A4/A8), λ (A5), OAuth transport (A9), the §2/A10 774-pool, and all validation floors (§9, A6/V3) are unchanged. Reusing the stale 2026-05-27 anonymous Reddit cache (149 overlapping rows) is **abandoned** under A11: those rows were collected under the old fetch-anchored window, and mixing window vintages would violate the uniform-window commitment. The change strengthens criterion 1 (framing: decoupling the attention window from run-time to defeat a playoff-selection confound) and criterion 6 (explicit limit-of-claim on the residual prior-season overlap).

**A12 (2026-06-21) — Attention ingestion broadened: multi-language Wikipedia added as a flow component; Instagram/X follower count removed from the composite; GDELT news rejected on A11-window grounds. New §4 flow-weight vector logged BEFORE any new-source fetch. Anti-tuning: weights derived by demographic-coverage reasoning, prior vector retained.**

> Motivation: the §4 composite reached only English-language and engaged-fan-community demographics, leaving the whole-league (A10) coverage claim open to the "this just measures Anglophone Reddit fame" attack. A breadth flow is added — `wiki_intl_12mo` (pageviews summed over the fixed hockey-market edition set {sv, fi, cs, ru, de, sk, fr}, A11 window, Wikidata-QID reused from A1).
>
> The Instagram follower count — a lifetime STOCK that is noisy and inflatable (documented fake-follower rates; public sources disagree ~2×) and conceptually mismatched with the A11 flow window — is removed from the composite (prior weight 0.139 → dropped); X followers are not added. GDELT mainstream-news volume was considered and rejected: its DOC 2.0 API has a hard ~3-month rolling window that cannot honor the A11 12-month window, and a single source on a divergent window is not worth the integrity cost; the mainstream-reach demographic is carried instead by the broad-demographic YouTube validation gate.
>
> New §4 flow weights: wiki_en 0.29, wiki_intl 0.11, reddit_mentions 0.27, reddit_upvotes 0.17, trends 0.16 (sum 1.00). Prior vector (wiki 0.306, reddit_mentions 0.250, reddit_upvotes 0.167, trends 0.139, instagram 0.139) retained here for audit. Sentinel renorm (§4) applies unchanged to the new component; the dropped follower stock never participates. Peer features (§6), λ (§7/A5), denominators (A4/A8), OAuth transport (A9), the A10 774-pool + small_sample flag, the A11 window, and all validation floors (§9, A6/V3) are unchanged.
>
> **Letter reconciliation:** the sibling skill-vector amendment commits as the next free letter (A13).

**A13 (2026-06-21) — §6 peer (skill) vector: add MoneyPuck 5v5 on-ice play-driving + deployment features (CF%, xGF%, O-zone-start%) to `(age, PPG, TOI/G)`. Logged BEFORE any re-compute on the augmented vector.**

> Motivation: §6's peer vector measured only deployment and scoring, so the "skill-controlled" claim controlled nothing about on-ice play-driving. The three most-cited public on-ice control metrics are added so the OAQ residual is matched against a defensible skill profile.
>
> New peer vector (all 774): `(age, PPG, TOI/G, cf_pct, xgf_pct, ozs_pct)` from MoneyPuck's free season-summary skater CSV (2025-26 regular), filtered `situation=='5on5'`: `cf_pct=onIce_corsiPercentage`, `xgf_pct=onIce_xGoalsPercentage`, `ozs_pct=oZoneShiftStarts/(oZoneShiftStarts+dZoneShiftStarts)`. **5v5 is the locked situation** (even-strength; all-situations re-imports special-teams confound). **QoC deliberately excluded:** MoneyPuck exposes no QoC column, within-NHL opponent spread is small versus junior/college, and `ozs_pct` provides the deployment partial-control; the QoC gap is disclosed on the poster.
>
> Source/join: key `nhl_player_id` ↔ MoneyPuck `playerId` (identical NHL id space); name-fallback only where the id is blank. Traded players (one 5v5 row per team, no aggregate row) collapsed by icetime-weighted mean (cf_pct, xgf_pct) and summed-count ratio (ozs_pct). Written to `raw/nhl_onice.csv`. MoneyPuck credited per its non-commercial terms. (Build note: the 2025-26 season-summary CSV in fact returns one pre-aggregated 5v5 row per playerId — the icetime-weighted aggregation is a verified no-op on this source. MoneyPuck `icetime` is in seconds and is converted to minutes at ingest so the floor below applies in minutes.)
>
> Thin-sample: skaters below `ONICE_MIN_ICETIME_5V5 = 150` min 5v5 have the three on-ice features NULLed (`onice_status=thin`); existing §6 group-mean imputation fills them to position-group neutral before standardizing, so they are matched on stable box-score stats. No player dropped (A10 pool preserved). The descriptive `small_sample` (<20 GP) flag is unchanged.
>
> Distance unchanged: K=10, within-group standardization (ddof=1), within-group inverse-covariance (Mahalanobis); only the column list grows 3→6. Collinearity among PPG/CF%/xGF% is handled by inverse-covariance weighting; covariance is stable at 497 F / 277 D ≫ 6 dims.
>
> expected_cap (A4) unchanged — on-ice features deliberately NOT added to the `cap_hit_M ~ PPG + TOI/G` market-price regression; age remains excluded.
>
> **Re-confirmation obligation (disclosed in advance):** the peer vector enters OAQ_observed, OAQ_portable, all Marchand Index lenses, and every validation gate. Re-rolling the peer features re-rolls every validation pathway — V1a/V1b, V2, V3/PD are all re-reported regardless of direction against the unchanged §9/A6 floors; any fall below floor is an honest disconfirmation, not a quiet drop. PC recomputed off the new peer sets. Pre-amendment 3-feature vector and downstream numbers retained in git history (§13).
>
> **Anti-tuning (§13):** decided on construct-validity grounds, logged before any re-compute; features, situation (5v5), OZS% formula, and the 150-min floor are mechanical and fixed in advance, not chosen by effect on any player's rank; composite weights (§4/A12), market-proxy (§7), λ (A5), denominators (A4/A8), OAuth (A9), the A10 pool, and all validation floors (§9, A6) unchanged.

**A14 (2026-06-23) — en-Wikipedia attention window: align `wiki_en_12mo` to the A11 FIXED regular-season-end window [2025-04-18, 2026-04-17], replacing its run-time trailing-365-day window (§3.1). Logged BEFORE re-fetching the en-Wikipedia component.**

A11 moved the attention window off run-time and onto the fixed regular-season-end boundary to defeat a made-the-playoffs confound, but A11's text scoped the change to Reddit, and A12 applied the same fixed window to the new `wiki_intl_12mo` component. The **en-Wikipedia** component (§3.1 `wiki_12mo`, code key `wiki_12mo` = spec `wiki_en_12mo`) was never migrated: `fetch_wikipedia.py:window_strings()` still computed a trailing-365-day window ending D−1 (run time). At the 2026-06-17 fetch this recorded window [2025-06-17, 2026-06-17], which **includes the entire 2026 Stanley Cup playoffs** — exactly the contamination A11 removed elsewhere. Because `wiki_en_12mo` carries the **largest §4/A12 flow weight (0.29)**, the playoff-selection confound A11 was built to eliminate was still entering the headline through the single heaviest component, and A11's "applied uniformly to all 774" was violated for that component.

**Corrected window (applied identically to all 774):** the en-Wikipedia pageview window is the **fixed** A11 interval — start `20250418`, end `20260417` (the same `WINDOW_START`/`WINDOW_END` constants the wiki_intl fetcher uses), identical for every player and independent of when the scrape runs. Slug resolution (A1 occupation-checked resolver), the daily-vector capture for the §10 bootstrap, the 365-day window length, and the output schema are all unchanged; only the window endpoints move off the playoffs and onto the regular-season boundary, bringing en-Wikipedia into the same window as Reddit (A11), Trends, and wiki_intl (A12). Pageviews for a past calendar window are historical/deterministic (not perishable), so the re-fetch reproduces a fixed quantity.

**Anti-tuning compliance (§13):** A14 is a uniform, mechanical data-collection alignment decided on confound-removal grounds (it propagates A11's already-locked fixed window to the one component that was missed), logged **before** the en-Wikipedia re-fetch; the window endpoints are objective external calendar dates (NHL-API regular-season end, already fixed by A11), not chosen after inspecting any player's resulting pageviews or rank. Composite weights (§4/A12), peer features (§6/A13), market-proxy (§7), λ (A5), denominators (A4/A8), OAuth transport (A9), the §2/A10 774-pool, the A11 window definition, and all validation floors (§9, A6/V3) are unchanged. The pre-A14 run-time-window en-Wikipedia CSV is retained in git history per §13. The headline en-Wikipedia magnitude stays comparable (the window length is unchanged at 365 days; only the endpoint moves), and the same prior-season-overlap residual A11 disclosed (the window's oldest ~2 months touch the 2024-25 playoffs) applies identically and is disclosed on the poster.

**A15 (2026-07-03) — Reddit attribution: within-pool surname-collision filter. Logged BEFORE the 774-set production Reddit fetch (OAuth credentials not yet provisioned; no production Reddit data exists).**

§3.3/A2 count a submission toward player P if it matches a search for P's **last name** in `r/hockey` + P's team subreddit. Within the 774-pool this misattributes attention wherever two or more pool players share a surname: a "Hughes" search in `r/hockey` pools Jack, Quinn, and Luke Hughes; "Tkachuk" pools Matthew and Brady; Jones/Smith/Johnson pool stars with depth namesakes. The error is structured — it inflates the measured attention of a depth player who shares a surname with a star, which is exactly the OAQ-positive signature the index is built to detect — so it must be removed before the production fetch, not diagnosed after.

**Corrected attribution rule (applied identically to all 774):**

1. A surname is **shared** iff ≥ 2 players in the locked 774 pool have the same accent-folded, case-folded last token of `full_name`. The shared-surname list is derived mechanically from `players.csv` and recorded per player in a new `surname_shared` column.
2. For a player with a **unique** surname, attribution is unchanged (last-name search match suffices — the A2 rule).
3. For a player with a **shared** surname, a matched submission is attributed to P **only if** the submission's title or selftext (accent-folded, case-folded) also contains (a) a word starting with P's folded first name (so "Will" credits "William"; minimum 3 characters, exact match required for shorter first names), or (b) the pattern `<first-initial>. <surname>` / `<first-initial> <surname>` where that initial is unique among the pool players sharing the surname. Submissions matching the surname but no first-name evidence are counted in a new **`ambiguous_mentions`** column — disclosed, attributed to no one, excluded from `reddit_mentions_12mo` / `reddit_upvotes_12mo` and from the §10 bootstrap detail pool.

**Honest residuals (disclosed in advance):** (i) the rule lowers recall for shared-surname players relative to unique-surname players (team-subreddit posts often use bare surnames); the `surname_shared` flag ships in `reddit_counts.csv` so a sensitivity cut excluding shared-surname players can be reported. (ii) Nicknames ("Tkachuk brothers", "Chucky") are not resolved — mechanical rule only. (iii) Collisions with non-pool people (retired players, non-NHL public figures) are out of scope of this amendment and remain a disclosed limitation.

**Anti-tuning compliance (§13):** logged before any production Reddit data exists (0/774 fetched), so no player's resulting count could have influenced the rule; the rule is mechanical (pool-derived surname list + fixed textual-evidence test), applied uniformly; subreddits, query, window (A11), dedup, 1,000-result cap, transport (A9), composite weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), and all validation floors (§9, A6/V3) are unchanged.

**A16 (2026-07-03) — Google Trends: entity-topic queries with a fixed mid-tier anchor, replacing single-term raw-string queries. Logged BEFORE the corrective re-fetch; the existing `trends.csv` is superseded and retained in git history.**

Two measurement defects in §3.2 as implemented (`fetch_trends.py`, single-term `build_payload`):

1. **No cross-player comparability.** Google Trends normalizes a *single-term* series to that term's own peak = 100 within the window. The stored `trends_12mo` mean is therefore a within-player *shape* statistic (how spiky a player's own curve is), not a measure of relative search volume; z-scoring it across the 774 compares quantities that are not on a common scale. This affects §4/A12 weight 0.16.
2. **Homonym contamination.** The raw string `"<First> <Last>"` measures everyone with that name — "Will Smith" measures the actor, not the Sharks forward. No entity resolution exists on the string path.

**Corrected fetch (applied identically to all 774):**

1. **Entity resolution:** each player's query is the Google Trends **topic MID** returned by the pytrends `suggestions("<First> <Last>")` endpoint — the first suggestion whose type string contains "hockey" (case-insensitive). If no hockey-typed topic exists, the raw string is used and the row is flagged `trends_method = string` (vs `topic`); the flag ships in `trends.csv` for a disclosed sensitivity cut.
2. **Common-scale anchoring:** every fetch is a **two-term payload** `[ANCHOR, player]` over the fixed A11 window `2025-04-18 .. 2026-04-17`, worldwide. Google scales the pair jointly, so `trends_12mo := mean(player series) / mean(anchor series)` is comparable across players. The anchor is fixed in advance as the topic entity for **"Brad Marchand"** — a mid-magnitude, hockey-native term chosen so that neither depth players (quantized to 0 against a mega-term) nor superstars (that would quantize a tiny anchor to 0) lose resolution. If the anchor series mean is 0 in a batch (throttle artifact), the batch is retried; a player whose own series is empty is NULL per the §4 sentinel, unchanged.
3. Recorded per row: `query`, `query_mid`, `trends_method`, `player_mean_scaled`, `anchor_mean_scaled`, `trends_12mo` (the ratio), `n_weeks`, `fetch_date`.

**Honest residuals (disclosed in advance):** Trends integer quantization (0–100) leaves depth players coarse relative to the anchor; the ratio inherits Google's sampling noise (~±5% observed in V-A11-Trends); topic-MID coverage may be incomplete for low-profile players (`trends_method = string` fallback carries the homonym risk explicitly).

**Anti-tuning compliance (§13):** decided on measurement-validity grounds (the stored quantity is not the pre-registered construct "12-month search interest"); logged before the corrective re-fetch; anchor choice and MID rule are fixed in advance and identical for all 774, not chosen after inspecting any player's value; window (A11), weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), and all validation floors (§9, A6/V3) are unchanged. The superseded single-term `trends.csv` remains in git history per §13.

**A17 (2026-07-03) — log1p robustness lens on the engagement composite. Logged BEFORE the final (Reddit-era) compute; primary method unchanged.**

Attention components (pageviews, mention counts, upvote sums, search-interest ratios) are heavy-right-tailed across a whole-league pool: z-scores of raw sums are dominated by the star tier (observed: engagement_raw up to ≈ +7.5 on a weighted sum of z-scores), so depth-tier differences are compressed toward zero and OAQ residual variance is strongly tier-dependent. To show the headline is not an artifact of the raw scale, the final compute additionally reports a **log lens**: each §4/A12 component is transformed `x → log1p(x)` **before** z-scoring; weights, sentinel renormalization, peer sets (skill-side, untouched), λ (A5), and denominators (A4/A8) are identical. Reported: log-lens `engagement_raw` / `OAQ_portable` / Marchand-Index leaderboards, Spearman rank agreement between primary and log lens on each quantity, and the §9/A6 external-validation statistics (V1b, V2, V3) recomputed under the log lens as **point estimates**.

**Status rule (fixed in advance):** the raw-scale composite remains the locked primary and the only basis for gate pass/fail verdicts (PA/PB/PC/PD). The log lens is robustness, reported regardless of direction. If primary and log lens disagree materially (rank agreement on OAQ_portable < 0.8), that disagreement is itself reported as a finding and a stated limitation — it does not license switching the headline to whichever lens reads better.

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 fetched and no final composite exists, on distributional-reasoning grounds, not after inspecting any final number; the primary method, weights, floors, and verdict logic are unchanged; the lens adds reporting only.

**A18 (2026-07-03) — V3 baseline-comparison interpretation rule, pre-declared. No numeric or method change.**

V3 reports two team-level correlations: the gate predictor (sum of peer-matched `OAQ_observed`) and a mechanical baseline (sum of `engagement_raw`, no skill control). The interpretation of their comparison is fixed now, before the final (Reddit-era) numbers exist:

1. The **PD verdict** is determined solely by the OAQ-based ρ against the unchanged 0.40 floor. The baseline plays no role in the verdict.
2. The outcome (team Wikipedia pageviews) responds to *total* fame — skill-driven and surplus alike — so the mechanical baseline is **expected** to correlate at least as strongly as the skill-stripped predictor. `baseline ρ ≥ OAQ ρ` is therefore *not* evidence against the OAQ construct and will not be presented as such; conversely, it will also not be spun away if OAQ fails its own floor.
3. What the comparison informs is a **narrower claim**: whether attention surplus *beyond skill* still aggregates to a team-level attention signal. If OAQ ρ ≥ 0.40, that claim is supported regardless of the baseline's value. If OAQ ρ < 0.40, PD is reported as an honest disconfirmation with exactly this reading: skill-stripped attention surplus did not aggregate to the team level at gate strength on this outcome. No other post-hoc reframing is permitted.

**Anti-tuning compliance (§13):** interpretation-only; declared while Reddit is 0/774 and the final V3 is uncomputed; floors, outcome construction, and predictor are unchanged from A6.

**A19 (2026-07-03) — en-Wikipedia identity repair via NHL-ID reverse lookup (P3522), scoped to audit-flagged rows. Logged BEFORE the repair fetch.**

An identity audit of all 774 resolved rows (`audit_wiki_identity.py` → `raw/wiki_identity_audit.csv`, run 2026-07-03; cross-checks each `wikidata_qid` against Wikidata **P3522 = NHL.com player ID**, falling back to P569 birth year vs the NHL landing `birthDate`) found: **760 `ok_nhl_id`**, **3 `ok_dob`** (entity lacks P3522; birth years match), **1 `bad_nhl_id`**, **10 `unverified`** (all are the `wiki_match = none` rows — no slug was ever resolved). The audit was motivated by the structural gap-review finding that the A1 resolver can reject non-hockey entities but cannot reject the *wrong hockey player*; it was not triggered by any player's pageview value.

1. **Wrong entity (1):** pool player_id 695 **Elias Pettersson (D, NHL 8483678)** resolved to Q28057083 — **Elias Pettersson (C, NHL 8480012)**. Both are in the pool and both currently carry the center's slug and daily pageview vector, so the heaviest composite component (§4/A12 weight 0.29) is (a) attributed to the wrong human for the D-man and (b) double-counted across two players.
2. **Unresolved (10):** Hinds, R. Johnson, Wiebe, Savoie, M. Johansson, Romanov, Chmelar, Groulx, Haymes, C. Miller. Cause: the A1 candidate list (`"First Last"`, `"First Last (ice hockey)"`) dead-ends when even the "(ice hockey)" title is a disambiguation (multiple hockey players named Marcus Johansson / Ryan Johnson) or when the article title differs from the roster name ("Matt Savoie" vs "Matthew Savoie"). Established veterans among these have real pages, so their `wiki_en` attention is currently NULL — a recall loss, not a wrong-entity error.

**Corrected resolution rule (mechanical, identity-evidence only):** for every row whose audit verdict is `bad_*` **or** whose `wiki_match` is `none`, re-resolve by **reverse lookup**: Wikidata fulltext search `haswbstatement:"P3522=<nhl_player_id>"` (namespace 0); accept an entity **only if** its P3522 claim values contain the player's `nhl_player_id` exactly (re-verified via `wbgetentities`); the slug is that entity's **enwiki sitelink** title; the row is marked `wiki_match = nhl_id`. If no entity carries the ID or the entity has no enwiki sitelink, the row remains `wiki_match = none` with the §4 NULL-sentinel treatment, unchanged. Pageviews and the §10 daily vector are re-fetched for repaired rows only, on the unchanged A14 fixed window [2025-04-18, 2026-04-17]; `raw/wiki_pageviews.csv` and `raw/wiki_daily.csv` are rewritten atomically with only those rows changed. The audit is then re-run and must report 0 `bad_*`. Rows verified `ok_nhl_id` / `ok_dob` are **not touched**, even if a reverse lookup might return a different page. Any future *full* en-wiki re-fetch must use this P3522-first rule before the A1 name-candidate fallback.

**Honest residuals (disclosed in advance):** (i) P3522 coverage on Wikidata is incomplete — a player with a real en-wiki page but no P3522 statement stays `none` (undercount persists, disclosed); (ii) the 3 `ok_dob` rows rest on birth-year evidence only; (iii) pageview-API 404s for a repaired slug leave the row NULL per the existing sentinel.

**Anti-tuning compliance (§13):** the repair rule keys exclusively on identity evidence (NHL-ID equality on Wikidata), never on any pageview magnitude, rank, or downstream score; scope (the 11 rows) is fixed by the audit verdicts before the repair fetch runs; the window (A14), weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), pool (§2/A10), and all validation floors (§9, A6/V3) are unchanged. The pre-A19 `wiki_pageviews.csv` / `wiki_daily.csv` are retained in git history per §13. Reddit remains 0/774 fetched; no final composite exists.

**A20 (2026-07-03) — V1 jersey outcome: the newly published 2025-26 NHL top-selling-jersey list is adopted under A3's unchanged "most-recent" rule. Logged BEFORE the final (Reddit-era) V1 computation.**

A3 operationalized V1a on "the most-recent published official list" — at A3's logging date that was the 2024-25 NHL-PR top-5. The **2025-26 season list has since been published**: NHL Public Relations released the top-10 selling jerseys of the 2025-26 regular season on **2026-04-17/18** (retrieved 2026-07-03 via web search; the NHL-PR X post is re-reported with an identical top-10 by at least three independent outlets — HockeyFeed 2026-04-18, The Hockey News 2026-04-18, NHLTradeRumor 2026-04-19; the NHL does not publish unit figures, ranking only):

1 Bedard, 2 Ovechkin, 3 Crosby, 4 J. Hughes, 5 McDavid, 6 MacKinnon, 7 Makar, 8 Pastrnak, 9 Matthews, 10 Celebrini.

**Application (mechanical, per A3):**
- **V1a (rank; secondary):** the Spearman rank source becomes the 2025-26 top-10 (the most-recent list — A3's rule, not a new rule). All 10 names are in the locked 774 pool, so the overlap is n = 10, meeting the §9 n ≥ 10 threshold for the first time (V1a was structurally underpowered on the top-5 list).
- **V1b (membership; primary AUC):** the union definition extends to "appeared on an official NHL/Fanatics best-selling-jersey list in **2023-24, 2024-25 or 2025-26**" — the same union-of-official-lists construction, now over three verified lists. No soft-sourced names are added.
- **Window alignment (new, disclosed):** the 2025-26 list covers exactly the A11/A14 attention window [2025-04-18, 2026-04-17] — the first V1 outcome measured *within* the window rather than before it. The prior two lists remain in the V1b union as A3 defined; V1a's within-window alignment is a strengthening of construct match, not a floor change.

**V2 namesake guard (same rebuild, disclosed):** rebuilding `external_outcomes.csv` on the 774 pool exposed a join defect in the ASG-2024 membership match: the folded-name *backup* fired even when a row carried a non-matching `nhl_player_id`, so the pool's second Elias Pettersson (D, 8483678) inherited the center's (8480012) fan-vote membership. Corrected rule: the NHL id decides whenever present; the name backup applies only to blank-id rows. V2 in-pool overlap is the 8 skater fan-vote picks (goalies excluded by pool construction), still < 10 → underpowered per §9, exactly as pre-declared.

**Anti-tuning compliance (§13):** the list is published by NHL PR, independent of all model inputs (wiki/Reddit/Trends); its adoption is the mechanical application of A3's pre-locked most-recent rule to data that did not exist when A3 was logged; logged while Reddit is 0/774 fetched and before the final V1 is computed; floors (§9: ρ ≥ 0.40, AUC), verdict logic (PA), and all other components are unchanged. The pre-A20 `external_outcomes.csv` is retained in git history per §13.

**A21 (2026-07-13) — Reddit identity: non-discriminable first names + team-subreddit attribution. Logged BEFORE the 774-set production Reddit fetch (Reddit remains 0/774; no production Reddit data exists).**

A15 attributes a shared-surname submission to player P only when the text also carries first-name evidence for P. Two structural failure cases remain, found by the internal audit (E1) and panel review (J2-F5):

1. **Non-discriminable first names.** When two pool sharers' first names collide — identical ("Elias Pettersson" ×2) or prefix-nested ("Matt"/"Matthew") — A15's first-name test matches both players and discriminates nothing, silently double-attributing or misattributing.
2. **Team-context evidence unused.** A bare-surname post in a TEAM subreddit carries strong identity evidence (the team) that A15 ignores, needlessly discarding recall for shared-surname players — the same players A15 already dented.

**Corrected attribution rules (applied identically to all 774; extends A15, supersedes nothing):**

1. **Prefix-collision definition.** Within a shared-surname group, first names `a`, `b` PREFIX-COLLIDE iff `a.startswith(b) or b.startswith(a)` after accent-folding and case-folding. If a player's first name prefix-collides with another sharer's, first-name evidence is NON-DISCRIMINATING for that pair (it can no longer attribute a post between them).
2. **Team-subreddit context rule.** Within a TEAM subreddit, if exactly ONE pool sharer of the surname is on that team, bare-surname submissions attribute to him. "On that team" = the **A22 window-roster set** (the NHL-API `seasonTotals` derivation defined in A22), NOT the 2026-06-17 snapshot roster — a traded sharer counts for every team sub he was window-rostered in. If MORE than one pool sharer of the surname is window-rostered on that team, bare-surname submissions in that team's sub go to `ambiguous_mentions`. (This resolves the two Sebastian Ahos — CAR vs NYI — inside their respective team subs.)
3. **Fully non-discriminable pairs.** Where sharers collide on BOTH surname and (prefix-folded) first name AND the team rule cannot separate them (the two Elias Petterssons, both window-rostered on VAN): ALL matching submissions → `ambiguous_mentions`, attributed to NO ONE; both rows get a new flag `reddit_identity_ambiguous = true`; the discarded count is disclosed in `results.md`.
4. **r/hockey nickname-token rule.** In r/hockey, for prefix-colliding pairs, first-name evidence is non-discriminating (rule 1), so a matching submission is ambiguous UNLESS a TEAM NICKNAME token for exactly one sharer's team appears in the title/selftext. Token definition (mechanical): the final word of the team's full name from `raw/teams.csv`, accent/case-folded, matched as a whole token (e.g. "hurricanes", "islanders", "canucks"). 2–3 letter team codes are NOT used as tokens (false-positive prone: "LA", "SJ"). If nicknames of BOTH sharers' teams appear, the submission is ambiguous.

**Honest residuals (disclosed in advance):** (i) rules 3–4 lower recall further for the affected players — the count of discarded ambiguous submissions ships in `results.md`, and the A15 `surname_shared` sensitivity cut already covers the class; (ii) nickname tokens cover team names only, not player nicknames — unchanged from A15(ii); (iii) non-pool namesakes remain out of scope per A15(iii).

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 fetched, so no player's resulting count could have influenced any rule; every rule is mechanical (string prefix test, pool-derived roster sets, fixed token definition), applied uniformly to all 774; subreddits, query, window (A11), dedup, transport (A9 as superseded by A23), composite weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), and all validation floors (§9, A6/V3) are unchanged.

**A22 (2026-07-13) — Reddit sub-selection: every window-rostered team's subreddit, derived from NHL-API seasonTotals; sub-rename rule. Logged BEFORE the 774-set production Reddit fetch.**

§3.3/A2 search `r/hockey` + the player's (single, snapshot-date) team subreddit. For a player traded inside the attention window, the months of discussion in his former team's sub are invisible — a structured undercount that hits exactly the players whose attention the index should measure across a move (J2-F3, HIGH).

**Corrected rule (applied identically to all 774):** for each player, count the team subreddits of EVERY team he was rostered on inside the window [2025-04-18, 2026-04-17], derived mechanically from the NHL API `seasonTotals` rows with season IDs `20242025` and `20252026`, `leagueAbbrev == "NHL"`, `gameTypeId == 2`, mapped to team subs via the existing team→subreddit mapping already used by `fetch_reddit.py` (in/derived from `raw/teams.csv` — reuse it, do not build a new one). 2024-25 season rows are included because the window's first ~2 months (Apr–Jun 2025) fall in that season's playoffs/offseason, when a player is still discussed in his then-current (now former) sub. `r/hockey` participation is unchanged. Submissions are deduplicated by submission id ACROSS subs, so a crosspost counts once. A new column `reddit_subs_searched` records the exact list per player.

**Sub-rename rule:** a team's subreddit SET additionally includes any predecessor subreddit its fan community used inside the window following a franchise rebrand. Known case, fixed here: UTA = {`r/utahmammoth`, `r/UtahHockey`} — verified 2026-07-13 via archive probes: `r/UtahHockey` (the pre-rebrand community) was active from at least 2025-04-19 while `r/utahmammoth`'s earliest in-window post is 2025-04-30, so the window's first ~2 weeks of Utah discussion live only in the predecessor sub. Mechanical and identity-keyed; applies to whichever players this amendment window-rosters to UTA. This is the team-level analogue of the traded-player rule.

**Honest residual (disclosed in advance):** a mid-season stint that produced no NHL `seasonTotals` row (e.g. an AHL loan sandwiched between NHL stretches with a team we'd otherwise miss) can still hide former-sub attention; disclosed, not repaired — the rule stays mechanical.

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 fetched; the sub list is derived from an objective NHL-API quantity fixed by history, not chosen per player; the rename rule keys on a public franchise event, not on any player's data; query, window (A11), dedup, identity rules (A15/A21), weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), and all validation floors (§9, A6/V3) are unchanged.

**A23 (2026-07-13) — Reddit source: the Arctic Shift archive (`arctic-shift.photon-reddit.com`) replaces authenticated live-search; complete in-window enumeration; matching performed locally. Supersedes the A9 transport (third transport-lineage change: A2 → A9 → A23). Logged BEFORE the 774-set production Reddit fetch (Reddit remains 0/774; no production Reddit data exists).**

A9's OAuth transport inherits three structural limits of Reddit's live search API: a 1,000-result cap per (subreddit, query) that right-censors star-tier players (E8/J1; J2-F11); no server-side date filtering (forcing the A11 newest-first skip/stop paging shortcut); and a credentials prerequisite (A9/A10) that has blocked the fetch since it was logged. The Arctic Shift archive removes all three.

**Rules (applied identically to all 774):**

1. **Source + enumeration.** The Reddit corpus = every submission in each covered subreddit whose `created_utc` falls inside the fixed A11 window [2025-04-18 00:00 UTC, 2026-04-18 00:00 UTC), retrieved from Arctic Shift `/api/posts/search` by date-windowed pagination (`limit=100`, `sort=asc`, cursor on `created_utc`). No result cap exists; the `MAX_RESULTS`/`reddit_capped` machinery is REMOVED (the flag was disclosure-only — no §4–§10 quantity ever consumed it; column dropped). Cap-mitigation designs (top-sort second pass, lower-bound semantics) are moot and NOT adopted.
2. **Corpus scope.** 36 subreddits, fixed here: `r/hockey`; the 32 team subreddits (the existing `TEAM_SUB` mapping); `r/UtahHockey` (the A22 rename rule); plus `r/nhl` and `r/fantasyhockey`. COMPOSITE counting subreddits are unchanged — `r/hockey` + the player's A22 team-sub set; `r/nhl` and `r/fantasyhockey` feed the rule-5 descriptive columns only.
3. **Local matching.** Per-player matching runs locally over the downloaded corpus, never via the archive's `query` search endpoint (verified recall misses: apostrophe possessives — "McDavid's" — and edited posts; evidence in rule 6). Mechanical rule: NFKD accent-fold, case-fold, map every non-alphanumeric character (including `'` and `'`) to a space, then whole-token match of the player's folded surname against `title + " " + selftext`. The A15/A21 identity and evidence rules run on the same folded text, unchanged.
4. **Text + score semantics (pre-declared).** (a) `title`/`selftext` are the archive's creation-time capture: mentions added by post-creation edits (bot-updated game threads) are invisible — uniform across all 774; direction: removes bot-appended box-score mass mentions. (b) `score` is the archive's ~2.5-day post-creation re-crawl value, replacing the fetch-time read (months after the window) whose accrual confound A35 will disclose; votes are near-settled and uniformly timed. (c) Submissions since deleted or removed from live Reddit ARE in the corpus (captured before removal) — a completeness gain over live search; disclosed.
5. **Descriptive columns (never composite).** `reddit_mentions_allsubs` (match count over the full 36-sub corpus) and `reddit_mentions_fantasy` (r/fantasyhockey only — separates fantasy-utility attention from identity-driven attention on case cards). Descriptive/robustness only; §4/A12 weights and component definitions unchanged.
6. **Verification evidence recorded at commit time (2026-07-13 live probes).** Window coverage: 13/13 months (r/hockey) and 32/32 team subreddits through window end. Independent-archive cross-check (PullPush, whose own ingestion died 2025-05-19) on r/hockey "McDavid" [2025-04-18, 2025-05-17]: 67/67 unique submissions present in Arctic Shift by id lookup; archive-search recall on the same slice 63/67 vs local-match 65/67 (the 2 residual = edit-added text, rule 4a). Candidate-sub volumes (Jan 2026): r/nhl 500+, r/fantasyhockey 500+; rejected: r/hockeyanalytics (0 posts — dead), r/hockeycirclejerk (62/mo, nickname-dominant), r/NHLHUT (game-card economy, not fan salience).

**Honest residuals (disclosed in advance):** (i) third-party archive dependency — mitigated by pulling the corpus to local cache immediately; the LOCAL CORPUS, not the API, is the source of record for the production run; (ii) rule 4(a) undercounts in-game bot-thread mentions, uniformly; (iii) archive completeness cannot be proven against Reddit ground truth — the two-archive id-level agreement in rule 6 is the strongest evidence available and is recorded here.

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 fetched, so no player's resulting count could have influenced any rule; the sub list, matching rule, and semantics are fixed in advance, mechanical, and uniform across all 774; query construct (surname), window (A11 fixed dates), submission-id dedup, identity rules (A15/A21), sub-selection (A22), weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), and all validation floors (§9, A6/V3) are unchanged. The A9/A10 credentials prerequisite is void.

**A24 (2026-07-13) — expected_cap: `is_rookie_deal` keyed on the CapWages contract-type field; OLS fit restricted to market (non-rookie) contracts on the log scale with Duan back-transform. Logged BEFORE the final compute; field-discovery evidence recorded below.**

A4/A8 key `is_rookie_deal` on a price+age proxy (`cap_hit_M ≤ $0.975M AND age ≤ 25`). Two misclassification directions (E2, J2-F2, J2-F6): bonus-laden ELCs above $0.975M read as market deals and contaminate the market fit; cheap post-ELC RFA deals below it read as rookie deals and are wrongly projected. Additionally the A4 OLS fits raw dollars over a heavily right-skewed cap distribution, and (per A4) the fit set includes ELC rows the CBA prices by fiat, not the market.

**Rules (applied identically to all 774):**

1. **Field discovery FIRST (procedure + evidence recorded here at commit time).** The CapWages `__NEXT_DATA__` JSON was dumped 2026-07-13 for 3 known ELCs (Bedard, Celebrini, Hutson) and 3 known veteran market deals (MacKinnon, Pastrnak, Crosby). The field exists. **Exact key path: `props.pageProps.player.contracts[i].type`, where contract `i` is the contract whose `details[]` array contains the row with `season == "2025-26"` (the contract governing the season's cap hit — the same row `fetch_cap_hits.py` already reads `capHit` from).** Observed values: `"Entry-Level Contract"` on the governing contract of all 3 ELC probes; `"Standard Contract"`, `"Standard Contract (Extension)"`, `"35+ Contract (Extension)"` on all veteran probes (Hutson's future extension is a separate contract object whose `details` do not contain 2025-26; the governing-contract rule keys on the correct one). Mechanical classification: `is_rookie_deal = ("entry-level" in type.casefold())`.
2. **Flag rule.** `is_rookie_deal` keys on the discovered contract-type field. Where the field exists but is missing for individual rows (or the row's `cap_quality` pipeline never reached a contract object), the price+age proxy (`cap_hit_M ≤ $0.975M AND age ≤ 25`) is the per-row fallback. A new column `rookie_flag_source ∈ {contract_type, price_age_proxy}` records which path fired for every row.
3. **Fit set.** The expected_cap OLS fits ONLY rows with `is_rookie_deal == False` and finite predictors + cap; it PREDICTS for ALL 774. The $0.775M league-minimum floor on predictions is unchanged.
4. **Log-scale fit.** The regression is `log(cap_hit_M) ~ PPG + TOI/G` (within position group, age still excluded per A4); predictions back-transform via the **Duan (1983) smearing estimator** (the naive `exp()` is retained as a code-comment alternative, not computed). The linear all-rows fit is retained as an audit lens. (Convention: Evolving-Hockey-style contract models price on the log scale.)

**Disclosures (in advance):** current-season stats stand in for platform-year stats; contract term and UFA/RFA status are omitted from the model; defensively-valuable defensemen are underpriced by a PPG-based fit. All three ship on the poster's limitations panel.

**Anti-tuning compliance (§13):** the flag keys on an external structural fact of the contract (its registered type), never on any player's attention, rank, or index value; the discovery procedure and its fallback were fixed in the 2026-07-12 proposals draft before the probe ran, and the probe result is recorded verbatim above; fit-set restriction and log/Duan mechanics are standard econometric practice adopted on reasoning grounds while Reddit is 0/774 and no final composite exists; peer features (§6/A13), λ (A5), the A8 hybrid headline pointer, weights (§4/A12), and all validation floors (§9, A6/V3) are unchanged. Prior expected_cap columns remain in git history per §13.

**A25 (2026-07-13) — Missingness taxonomy: `no_entity_exists` imputes raw 0; `fetch_failed` keeps sentinel renorm. Logged BEFORE the final compute.**

§4's sentinel handling renormalizes weights over surviving components for ANY null. That treats two different situations identically (E3): (a) the source was blocked/failed — missingness unrelated to the player (MCAR; renorm defensible); (b) the entity does not exist — no Wikipedia article, no Trends topic and an empty series. Case (b) is itself attention information: absence of a page IS the low-fame signal, and renorming it away systematically overstates the engagement of exactly the low-attention players.

**Rules (applied identically to all 774):**

1. Every fetcher writes a per-component `null_reason ∈ {no_entity_exists, fetch_failed}` for each null it produces. Classification is mechanical: `wiki_match = none` with a confirmed no-page verdict → `no_entity_exists`; Trends with no topic MID AND an empty series → `no_entity_exists`; HTTP failures, blocks, rate-limits, parse errors → `fetch_failed`.
2. `fetch_failed` (and blocked-source) nulls → weight renorm, current behavior, unchanged.
3. `no_entity_exists` nulls → impute the RAW value 0 for that component BEFORE z-scoring; no renorm for that component. (The player's z-score on that component is then the z-score of zero raw attention — strongly negative, as it should be.)

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 and no final composite exists; the taxonomy keys on fetch-outcome facts, never on any resulting score; weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8/A24), and all validation floors (§9, A6/V3) are unchanged.

**A26 (2026-07-13) — §10 bootstrap: 7-day circular block resampling for the Wikipedia daily vector; propagated-uncertainty table. Logged BEFORE the final compute.**

§10 resamples the 365-day Wikipedia pageview vector iid by day. Daily pageviews are strongly autocorrelated (news cycles span days), and iid resampling of autocorrelated data understates variance — the published CIs would be too narrow in a direction that flatters precision (E7).

**Rules:**

1. **Block resampling (Politis–Romano convention).** The wiki daily vector is resampled in 7-day CIRCULAR blocks. Exact procedure: treat the 365-day vector as a ring; each bootstrap draw samples 53 uniformly-random block start indices, concatenates the 53 seven-day blocks, truncates to 365 days. Applies to both `wiki_en` and `wiki_intl` daily vectors.
2. Reddit pool resampling is unchanged; seed `20260526` is unchanged.
3. **Propagated-uncertainty table.** `results.md` AND the poster carry a table stating what the CIs propagate (wiki daily vectors, Reddit submission pool) and what they do NOT (peer-set composition, Trends values, market proxy, expected_cap fit).

**Anti-tuning compliance (§13):** logged before the final compute on variance-honesty grounds; block length (7 days) is fixed in advance by news-cycle reasoning, not chosen for any interval's resulting width; seed, draw count (1,000), weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8/A24), and all validation floors (§9, A6/V3) are unchanged. Wider CIs are the expected and accepted consequence.

**A27 (2026-07-13) — Star-boundary matching-bias diagnostic (`peer_skill_gap`) + bias-corrected reporting lens (`OAQ_bc`). Primary unchanged. Logged BEFORE the final compute.**

K-nearest matching at a distribution boundary is biased: a player at the skill frontier has peers strictly below him, so any convex attention-in-skill relationship mechanically inflates his OAQ residual (E5; J1 CONFIRM — textbook boundary bias, Abadie & Imbens 2011). No results exist yet; the remedy is a pre-registered diagnostic + corrected LENS, with the primary untouched.

**Rules:**

1. **Diagnostic.** Every row ships `peer_skill_gap`: mean(player − peer) on each standardized skill feature (6 values), plus a scalar summary defined as the **mean of the absolute standardized per-feature gaps**.
2. **Bias-corrected lens (reporting-only).** `OAQ_bc = OAQ_observed − β̂ᵀ(x_P − x̄_peers)`, where β̂ comes from a within-position OLS of `engagement_raw` on the standardized 6-feature skill vector (Abadie–Imbens-style regression correction). `OAQ_portable_bc` applies the SAME β̂ (from the engagement_raw-on-skill regression — NOT refit on the market-adjusted quantity) to the portable residual.
3. **Status rule (A17 language, verbatim in application):** the raw OAQ remains the locked primary and the only basis for gate verdicts. The bc lens is robustness, reported regardless of direction. Spearman rank agreement primary-vs-bc is reported; agreement < 0.8 is itself a reported finding and a stated limitation — it does not license switching the headline to whichever lens reads better.

**Anti-tuning compliance (§13):** logged before the final compute on published-literature grounds (Abadie & Imbens 2011); the correction form and the β̂ source regression are fixed in advance, applied uniformly; the primary quantity, weights (§4/A12), peer construction (§6/A13), λ (A5), denominators (A4/A8/A24), and all validation floors (§9, A6/V3) are unchanged.

**Decision record (2026-07-13) — owner decisions per `docs/airtight_execution_plan.md` §D and the 2026-07-11 decision sheet (§I checklist item "Owner decisions §D recorded in prereg"). Not an amendment; recorded for the audit trail. Logged while Reddit is 0/774 fetched (corpus pull in flight; no per-player production Reddit counts exist).**

- **D-1: Gate-4 GO, with the U1 rider** (10-player fail-fast dry-run after the G4-A1..A3 commits and the YouTube API key). Gate-4 is executed for the poster run as load-bearing pathway #3.
- **D-2: A30 market-proxy REBUILD PRIMARY** (sensitivity-only fallback declined). A30 text follows in this file; A32's `[D-2 CONDITIONAL]` clauses are retained.
- **D-3: A31 headline structure SIGNED OFF, with U2 folded into A31 before commit** (Hanley–McNeil precision statement + paired bootstrap ΔAUC).
- **U-slate: recommended slate accepted** — U1–U7 yes; U8 default-skip unless the U1 dry-run signals thin depth-band coverage.
- **Pool dedup APPROVED: 774 → 771** (supplement 2026-07-13 §4b — three duplicate persons: Andrae, Benoit, Colton, each one `nhl_player_id` under two snapshot teams). Logged as amendment A41 in this file before the production matcher run.

Owner actions still pending (not decisions): (a) eyeball `raw/reddit_identity_pairs.md` (A21 acceptance step); (d) YouTube API key (U1/Gate-4 prerequisite).

**A28 (2026-07-15) — Sensitivity re-run: `onice_status = thin` rows ineligible as peers. Logged BEFORE the final compute.**

A13 group-mean-imputes the three on-ice features for skaters under the 150-minute 5v5 floor. Imputation shrinks those rows to the position centroid, so the Mahalanobis distance understates their true covariance distance and they are systematically over-selected as peers (J1-N6; cf. Rosenbaum & Rubin 1984 on matching with imputed covariates).

**Rule:** one pre-registered sensitivity re-run in which `onice_status = thin` rows are INELIGIBLE as peers (they are still scored themselves, matched against non-thin peers). Spearman rank agreement vs the primary is reported for `OAQ_observed`, `OAQ_portable`, and the headline index. The primary is unchanged; the A17 status rule governs any material disagreement (< 0.8 → reported finding, no headline switch).

**Anti-tuning compliance (§13):** logged before the final compute; the eligibility rule keys on the pre-existing A13 thin flag, fixed before any result exists; K, distance, features, weights, λ, denominators, and all floors unchanged.

**A29 (2026-07-15) — V3 repaired (fixed window, redirect-summed titles, team-level bootstrap) and relabeled "aggregation-consistency check" (not an independent pathway). Logged BEFORE the V3 re-fetch and the final compute.**

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

**A30 (2026-07-15) — Market-proxy REBUILD (owner decision D-2, 2026-07-13): MarketSize_team = equal-weight z-mean of metro_population, team_sub_subscribers, attendance_pct_capacity. Old proxy retained as `market_z_lockedv1`. Logged BEFORE the final compute.**

Basis (J2-F1 HIGH, J2-F8, E9): Reddit carries 0.44 of composite weight, and team-subreddit volume anti-correlates with metro population (WPG: 0.8M metro, Canadian-scale fanbase). The locked metro+raw-attendance proxy cannot see hockey-market intensity, so the one-sided λ gives Canadian small-metro teams zero correction and portable OAQ credits fanbase intensity as personal attention. Raw attendance additionally measures arena size at sellout (J2-F8). Rebuilt while zero production results exist — the only window in which a primary change is free of tuning suspicion.

**Rules:**

1. **Components (equal-weight z-mean across the 32 teams, replacing the §7 pair):**
   (a) `metro_population` — unchanged (census figures per `market_proxy_sources.md`);
   (b) `team_sub_subscribers` — team-subreddit subscriber counts via the Arctic Shift subreddits endpoint (`/api/subreddits/search`, `subscribers` field). **Transport probe (2026-07-15, per the 2026-07-13 supplement §5):** the A9 OAuth transport is superseded (A23); `www.reddit.com/r/<sub>/about.json` and `old.reddit.com` both return HTTP 403 at $0; Arctic Shift returns 200 with `subscribers` plus a per-record `retrieved_on`. Observed snapshot vintages: most subs 2025-02-14/15; `utahmammoth` 2025-07-02 (subscribers = 59; sub created 2025-05). The vintage is recorded per row in `sub_retrieved_on`. **UTA rule:** subscribers = SUM over the A22 sub set {`UtahHockey`, `utahmammoth`} — one fanbase split by the rename.
   (c) `attendance_pct_capacity` — announced average home attendance (2024-25 figures already grounded in `market_proxy_sources.md`) ÷ arena seating capacity in hockey configuration (Wikipedia List of NHL arenas, retrieved 2026-07-15), replacing raw attendance.
2. **Preserved lenses:** the old proxy (metro + raw-attendance z-mean) is retained as `market_z_lockedv1` (audit lens, feeds A32's invariance panel); metro-only is retained as the E9 sensitivity (`market_z_metro_only`). λ ladder unchanged.
3. **Disclosures (in advance):** subscriber counts are archive-snapshot stocks of heterogeneous vintage (above) — acceptable for a slowly-varying market-size stock, unlike player-attention flows, and disclosed; UTA's count is genuinely post-relocation small AND vintage-limited (relocation novelty); announced attendance ≠ turnstile; the shared-metro overstatement for NYI/NJ is one-directional (over-discount) under one-sided λ = conservative.

**Acceptance:** 32/32 subscriber counts fetched; proxy correlation matrix printed (expect metro ⊥ sub-subscribers divergence for the Canadian teams).

**Anti-tuning compliance (§13):** the rebuild was approved by owner decision D-2 (recorded above, 2026-07-13) while Reddit is 0/774 and no production composite exists; every component keys on external structural facts (census populations, archive subscriber stocks, attendance/capacity ratios) — never on any player's attention, rank, or index value; the displaced proxy is preserved as a locked audit lens per §13, and A32's invariance panel must demonstrate (not assert) verdict-invariance to the swap; λ (A5), weights (§4/A12), peer features (§6/A13), denominators (A4/A8/A24), floors (§9), window (A11), and pool (A10) unchanged.

**A31 (2026-07-15) — Confirmatory hierarchy: V1b sole confirmatory primary; BH-controlled secondary family; baseline-comparison rule; registered headline structure; full gate-failure shipping matrix. U2 folded in per owner decision D-3 (Hanley–McNeil power statement + paired bootstrap ΔAUC). Logged BEFORE the final compute.**

Basis (J1-N1/N2/N3/N5, J3-F3/F4, J2-F4, E4): every existing gate tests OAQ while the headline metric `marchand_index_hybrid` is touched by no pathway (J1-N1); without a registered hierarchy, headline choice after results is a forking path. The headline becomes the OAQ validation finding; all MI lenses are demoted to a descriptive per-dollar panel.

**Rules:**

1. **V1b = sole confirmatory primary.** Floor AUC ≥ 0.70 / target ≥ 0.80 (Hosmer–Lemeshow "acceptable discrimination"). The 95% bootstrap CI is STRATIFIED at the player level — each of the 1,000 draws resamples the positives and the negatives separately, with replacement (unstratified draws can contain 0 positives → AUC undefined); seed 20260526; Hanley & McNeil 1982 cited; the small positive count → wide CI is disclosed. Interpretation rule for the primary itself: if point AUC ≥ 0.70 but the 95% CI includes 0.50, the verdict is "floor met on point estimate, not resolved from chance at n positives" — shipping-matrix row 2, decided now.
   **U2(a) — pre-computed power statement (Hanley & McNeil 1982 SE; recomputed mechanically by the same formula at the post-A37 positives count):** at n = 12 positives vs 762 negatives, SE₀(AUC = 0.5) = 0.084; the one-sided α = 0.05 critical point estimate is 0.638. Power = **0.77** against a true AUC of 0.70 and **0.98** against a true AUC of 0.80. The test can fail: any point AUC below 0.638 is unresolved from chance, and below 0.70 fails the floor outright. This statement ships in the validation panel.
2. **Secondary family = V1a, V2 (post-A33), V3 — Benjamini–Hochberg at q = 0.05 across exactly these three.** The pre-registered FLOORS still govern each test's pass/fail verdict; BH governs only the "statistically supported after multiplicity control" label a result may carry on the poster. PC is relabeled DESCRIPTIVE (not a validation). All lens/sensitivity tables are labeled descriptive robustness.
   **BH mechanics (pinned now, per the 2026-07-07 supplement Task 5, verbatim):** one-sided directions — V1a: ρ > 0; V2: statistic > its null (AUC > 0.5 / ρ > 0 per its post-A33 form); V3: ρ > 0. P-values by Monte-Carlo permutation, 100,000 permutations, seed 20260526, additive-smoothed `p = (1 + #{perm ≥ observed}) / (1 + 100000)` (Phipson & Smyth 2010). V1a permutes the n=10 outcome ranks; V2 permutes membership labels; V3 permutes the 32 team labels. BH step-up at q = 0.05 across exactly these three.
   **Descriptive companion (reporting-only):** V1b additionally reports the one-sided Mann–Whitney U p-value (asymptotic, continuity-corrected; `scipy.stats.mannwhitneyu(..., alternative="greater")`) beside the bootstrap CI. It is NOT a gate and appears only in the validation panel.
3. **Baseline-comparison rule (A18 extended to V1, locked verbatim):** report `engagement_raw` AUC and PPG AUC beside OAQ_portable's, plus OAQ_observed vs jersey as the construct-matched pairing (jersey sales are market-loaded; portable strips market). Interpretation fixed in advance: baseline ≥ OAQ is EXPECTED (the outcome responds to total fame) and is not evidence against the construct; OAQ clearing its own floor supports only the narrower surplus-retention claim. A pass with OAQ ≈ raw-fame baseline AND large `peer_skill_gap` correlation is the boundary-bias signature (E5) and is reported as such.
   **U2(b) — paired bootstrap ΔAUC (descriptive, not a gate):** on the SAME 1,000 stratified draws (same seed 20260526), report ΔAUC = AUC(OAQ_portable) − AUC(engagement_raw) and ΔAUC = AUC(OAQ_portable) − AUC(PPG) with percentile CIs — pairing removes shared draw noise from the comparison.
4. **V1a interpretation (E4/J2-F4):** the n=10 Spearman is reported with bootstrap CI + exact permutation p; a floor-pass whose CI spans 0 is "directionally consistent, underpowered for significance"; NEVER quoted standalone; never called "powered".
5. **Headline sentence structure (registered with placeholders; N adjusts mechanically to the post-A37 positive count and the post-A41 pool):** "OAQ_portable separated the N official jersey-list players from the other (pool−N) skaters with AUC = X.XX (95% bootstrap CI a–b); the list is star-tier only, ranking without units." A named case study may follow as ILLUSTRATION, never evidence. All MI lenses are demoted to a descriptive per-dollar panel; a within-cap-tier panel is added per J1-N8 (cross-tier ranks are not variance-standardized — heteroskedasticity disclosed).
6. **Definitions + gate-failure shipping matrix (complete; no ad-hoc downgrades outside this matrix).**
   Definitions: `V1b-strong` = point AUC ≥ 0.70 AND 95% stratified-bootstrap CI excludes 0.50. `V1b-point` = point AUC ≥ 0.70, CI includes 0.50. `V1b-fail` = point AUC < 0.70. `Secondary-pass` = ≥2 of {V1a, V2, V3} meet their pre-registered floors (BH governs only the multiplicity label, per rule 2). `G4-pass` = pooled outside-star floor met per docs/preregistration.md §8.

   | Row | V1b | Secondary | Gate-4 | Headline tier |
   |---|---|---|---|---|
   | 1 | strong | pass | pass | Full headline: "OAQ_portable separated the N official jersey-list players from the other (pool−N) skaters with AUC = X.XX (95% CI a–b), replicated across an independent fan-vote pathway and an outside-star YouTube generalization test." |
   | 2 | point | any | any | Downgraded: "directionally consistent, unresolved from chance at n positives" — no validation language in the headline; validation panel reports estimates + CIs only. |
   | 3 | strong | pass | fail | "OAQ_portable separated the N official jersey-list players from the other (pool−N) skaters with AUC = X.XX (95% CI a–b), replicated across the secondary fan-vote family. The pre-registered outside-star generalization test did not meet its floor: validity is claimed for the star tier only." Depth/Reaves-archetype framing removed; honest pathway count = 2, stated on the poster. |
   | 4 | strong | fail | pass | "OAQ_portable separated the N official jersey-list players ... with AUC = X.XX (95% CI a–b), and generalized to an outside-star YouTube attention test. The secondary fan-vote family did not clear its pre-registered floors and is reported as unsupported." Pathway count = 2 (jersey + YouTube). |
   | 5 | strong | fail | fail | Headline = the AUC sentence ONLY, no replication clause. Poster carries verbatim: "Validated on a single external pathway (jersey-list membership); no independent replication was achieved. The pre-registered ≥3-pathway standard was not met." |
   | 6 | fail | pass (and/or G4 pass) | any | No validation language in the headline under any combination. Validation panel reports all estimates + CIs; any secondary/G4 passes carry the fixed label "isolated secondary signal — not interpretable as validation absent the confirmatory primary." Index framed as an exploratory descriptive instrument. |
   | 7 | any | any | NO-GO / not run | OVERLAY row: take the tier from rows 1–6 using V1b + Secondary alone, then (a) delete any generalization clause, (b) cap the stated pathway count at 2, (c) add verbatim: "The pre-registered outside-star generalization test was not run; external validity outside the star tier is untested." |
   | 8 | fail | fail | fail/NO-GO | "The pre-registered validation gates were not met; the index is reported as an exploratory descriptive instrument with its validation estimates and CIs shown. No validated-metric claim appears anywhere on the poster." |

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 and no confirmatory statistic exists; floors adopt published conventions (Hosmer–Lemeshow bands; Hanley & McNeil SE) on reasoning grounds; the headline change is REPORTING structure — no quantity, weight, floor, λ, K, window, pool, or verdict-rule change to any computed number; the shipping matrix and sentence templates CONSTRAIN future claims and cannot flatter any result; U2's power statement is a formula evaluated at design constants, and the paired ΔAUC reuses the pre-registered draws and seed, reported regardless of direction. Owner decision D-3 (sign-off + U2, 2026-07-13) is recorded above; the U2 window closes at this commit per the decision sheet.

**A32 (2026-07-18) — Exploratory/confirmatory framing: pilot era declared design-generating; invariance panel across locked-original variants. Logged BEFORE the final compute.**

The 14-player v1 pilot and the 160-player pilot2 era (including the outcome-inspected A4/A5/A8 revisions) refined headline definitions on samples that overlap the locked 774 pool (J1-N4, J3-F1). Under the standard framing (Nosek et al. 2018, PNAS), that era is EXPLORATORY/design-generating; the 774 production run is the sole confirmatory test of the frozen design.

**Rules:**

1. **Required disclosure sentence (poster + results.md, verbatim):** "Headline definitions were amended after inspection of an overlapping pilot sample; they were locked before the production fetch and are pre-specified, not strictly confirmatory. Locked-original variants (raw-cap MI, two-sided λ=1 OAQ, and market_z_lockedv1 — the pre-A30 market proxy) are reported alongside, and validation verdicts are shown to be invariant (or not) across them."
2. **Invariance panel.** Recompute the V1b/V1a/V2/V3 point estimates under ALL locked-original variants — raw-cap MI (§8-original), two-sided λ=1 OAQ (§7-original), and market_z_lockedv1 (§7-original market proxy) — and report the deltas vs the primary in `results.md`. The market-proxy entry closes A30's residual anti-tuning exposure: pilot-era results were seen under the old proxy, so verdict-invariance to the proxy swap must be demonstrated, not asserted.

**Anti-tuning compliance (§13):** reporting-and-framing only — no quantity, weight, floor, or verdict rule changes; logged while Reddit is 0/774 and no confirmatory result exists; the variant list is the closed set of §13-preserved locked originals, fixed here in advance.

**A33 (2026-07-18) — V2 membership: union of official FAN-VOTE All-Star selections, 2022 + 2023 + 2024. Logged BEFORE the final compute.**

A3/A20 left V2 at the 2024 fan-vote membership: in-pool overlap n = 8 < 10 → underpowered per §9, contributing nothing to the pathway count (J3-F2).

**Rules:**

1. **Membership definition.** V2 membership = the union of players selected via an OFFICIAL FAN-VOTE component of the 2022, 2023, and 2024 All-Star selections, as named in NHL.com press releases. The fan-vote mechanism differs by year (captain votes, "Last Men In", full fan ballot); each season's exact mechanism is documented in `external_outcomes_sources.md`, and ONLY fan-voted names are taken — never league- or player-selected ones.
2. **Sourcing.** Per the A20 pattern: ≥2 independent URLs per season list, recorded in `external_outcomes_sources.md`.
3. **Join.** NHL-id-keyed per the A20 namesake guard (the id decides whenever present; name backup only for blank-id rows).
4. **Power rule.** If the in-pool overlap reaches n ≥ 10, V2 is powered under its EXISTING floor (§9: ρ ≥ 0.45 / target 0.55 — unchanged); if not, V2 stays underpowered as pre-declared. No floor moves either way.
5. **Disclosure.** The votes predate the attention window — same temporal-mismatch attenuation class as V1b's union lists; disclosed.

**Anti-tuning compliance (§13):** membership is defined by official external publications that predate this amendment and are independent of every model input; the union rule and fan-vote-only restriction are fixed before the overlap count is known; floors and verdict logic unchanged; logged while Reddit is 0/774 and no V2 statistic exists. The pre-A33 `external_outcomes.csv` is retained in git history per §13.

**A34 (2026-07-18) — Published-leaderboard display rule: `small_sample` / season-absent rows excluded from published panels, retained in data. Logged BEFORE the final compute.**

Rows with `small_sample = true` or NULL current-season GP (the A10 Barkov class) have attention floored by absence while their skill features are imputed toward the group mean — the arithmetic then produces a spurious negative-OAQ tail that reads as a finding but is an artifact of absence (J2-F7).

**Rule:** rows with `small_sample = true` OR null current-season GP are EXCLUDED from every PUBLISHED leaderboard and panel (poster, results.md tables). They remain in `oaq_pilot.csv` with all computed values, and the excluded count is disclosed alongside every published table. The injury-attention confound is added to the poster limitations set. This is a DISPLAY rule only: no quantity, gate, or bootstrap changes; flagged rows still participate in z-scoring, peer pools (subject to A28's sensitivity), and validation cohorts exactly as before.

**Anti-tuning compliance (§13):** display-layer only, keyed on the pre-existing A10 flag (locked 2026-06-17) and on GP nullity — objective absence facts, never on any player's resulting score; logged before any result exists; all computation, weights, floors, and verdicts unchanged.

**A35 (2026-07-18) — Small-items batch: anchor-degeneracy fix, log-lens escape-clause plug, goals-rate robustness, Reddit construct disclosures, nationality note. Logged BEFORE the final compute.**

Five clauses (J1-N9, J3-F7, J2-F12, J2-F14, J2-F10), one amendment:

1. **Trends anchor degeneracy (Marchand's own row).** A16 anchors every Trends fetch to the Brad Marchand topic entity, so his own row is anchor/anchor ≡ 1.0 — a degenerate self-measurement. Pre-declared secondary anchor for HIS ROW ONLY, named now: the Google Trends topic entity for **"Sidney Crosby"** (hockey-native, star-magnitude — adequate resolution against Marchand's own star-tier series). The ≡1.0 degeneracy is disclosed on his case card. Additionally, the count of depth players whose Trends series quantizes to zero against the anchor is reported.
2. **A17 escape-clause plug (verbatim, poster-binding):** "No log-lens number appears in the headline, abstract, or leaderboard panels under any outcome."
3. **Goals-rate robustness.** Pre-declared re-run with goals/60 replacing PPG in the peer skill vector (fame plausibly follows goals more than assists); reported as rank agreement vs primary ONLY — never as an alternative ranking (per §H forking-paths rule).
4. **Reddit construct disclosures (poster limitations):** (a) the fetch counts SUBMISSIONS only — comments and game-thread activity are invisible, and depth players' attention is disproportionately comment-borne; (b) *(restated 2026-07-13 per A23 rule 4b)* `score` is the archive's ~2.5-day post-creation re-crawl value — votes near-settled and uniformly timed; the earlier fetch-time accrual confound is removed, and the residual (votes accruing after ~2.5 days are uncaptured) is uniform in timing across all players; disclosed.
5. **Nationality note.** `wiki_intl` (weight 0.11) responds to nationality with no peer control — deliberate (national attention drivers are part of the signal being measured, not a confound to strip), disclosed on the poster.

**Anti-tuning compliance (§13):** clauses 2, 4, 5 are disclosures/prohibitions that constrain future claims and cannot flatter any result; clause 1's secondary anchor is named before any Trends-dependent result exists and applies to a single pre-identified row; clause 3 is a rank-agreement-only robustness re-run under the §H rule. Weights, floors, window, λ, denominators, pool, and verdict logic unchanged. Logged while Reddit is 0/774 and no final composite exists.

**A36 (2026-07-18) — Player Wikipedia pageviews: redirect-title summation (en + intl),
extending the A29-class team rule to the 774 player articles. Logged BEFORE the
augmentation fetch; Reddit remains 0/774.**

The Wikimedia pageviews API counts views against the exact title requested and does
not follow redirects (A1). The en fetch (§3.1/A1/A14) and intl fetch (A12) therefore
count only canonical-title views and drop views landing on redirect titles — a class
A1 itself measured (the `Alex_Ovechkin` redirect carried 7,059 in-window views). The
team-outcome amendment (A29) already adopts canonical+redirect summation for the 32
team articles ("views to a redirect title are legitimate views"); this amendment
applies the identical rule to the player articles, which carry §4/A12 weight 0.29
(wiki_en) + 0.11 (wiki_intl).

**Mechanical rule (applied identically to all 774; no identity re-resolution):**
1. Identity is LOCKED to the existing `wikipedia_slug_chosen` / `wikidata_qid` in
   `raw/wiki_pageviews.csv` (A1 + A19-audited) and the existing per-edition titles in
   `raw/wiki_intl_pageviews.csv` (`per_edition_json`). No slug is re-chosen; rows with
   `wiki_match = none` stay NULL, untouched.
2. For each canonical title, enumerate its redirect titles via the corresponding
   edition's MediaWiki API (`action=query&prop=redirects&rdlimit=max`, batched ≤50
   titles per request, following `continue`). Redirect titles containing
   "(disambiguation)" (case-insensitive, any language's title copied verbatim) are
   excluded.
3. Fetch in-window daily pageviews [2025-04-18, 2026-04-17] for the canonical title
   AND every enumerated redirect title; sum per calendar day (merge by the API item
   `timestamp`, not by list position — the API omits zero days). The player's
   `wiki_12mo` / `wiki_intl_12mo` becomes the summed total; the §10 bootstrap daily
   vector becomes the per-day-summed vector, **zero-filled to the full 365-day
   window** (index 0 = 2025-04-18 … index 364 = 2026-04-17; days the API omits are
   true zero-view days). Zero-filling aligns the stored vectors with the A26 block
   bootstrap, which already treats them as 365-day rings, and gives every vector a
   deterministic date index.
4. New audit columns in `raw/wiki_pageviews.csv`: `n_redirect_titles`,
   `redirect_views_12mo`, `redirect_share` (= redirect/total, 0 when total = 0);
   equivalents in `raw/wiki_intl_pageviews.csv` aggregated over editions. The top-10
   players by `redirect_share` and the pool-level mean share are reported in
   `results.md` so any surprise (an in-window rename) is visible — mirroring A29's
   per-team redirect-share report.
5. Any future full wiki re-fetch must include this summation (in addition to the
   A19 P3522-first identity rule).

**Honest residuals (disclosed in advance):** (i) a redirect retargeted mid-window
credits all its views to its fetch-date target (rare; direction unknowable at $0);
(ii) redirect enumeration reflects fetch-date redirect existence — redirects deleted
before fetch are missed (undercount persists, smaller); (iii) pageview-API 404 for a
redirect title contributes zero (clean skip).

**Anti-tuning compliance (§13):** uniform, mechanical data-collection completion
decided on measurement-validity and A29-consistency grounds; logged before the
augmentation fetch, while Reddit is 0/774 and no production composite exists; keyed
on article identity only, never on any player's resulting pageviews or rank;
weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), pool
(§2/A10), window (A11/A14), and all validation floors (§9, A6/V3) unchanged. The
pre-A36 `wiki_pageviews.csv` / `wiki_daily.csv` / `wiki_intl_pageviews.csv` /
`wiki_intl_daily.csv` are retained in git history per §13.

**A37 (2026-07-18) — V1b union completion: pre-declared retrieval sweep for ALL
official best-selling-jersey lists in seasons 2023-24 / 2024-25 / 2025-26. Logged
BEFORE the sweep runs; Reddit remains 0/774.**

A3/A20 define V1b membership as the union of official NHL/Fanatics best-selling-
jersey lists over the three named seasons, but only three lists have been retrieved
(A3's two + A20's 2025-26 top-10), giving n = 12 in-pool positives for the sole
confirmatory primary. This amendment pre-declares a retrieval sweep that completes
the union under the SAME class rule. It changes no floor, no test statistic, and no
definition — it completes data collection for an already-locked outcome.

**Qualification rule (mechanical; fixed before the sweep):** a list qualifies iff ALL of:
1. League-wide (not one team's store, not a per-team breakdown);
2. Attributed to NHL, NHL PR, NHLPA, NHL Shop, or Fanatics as the data source;
3. Player-level ranked list or top-N membership list;
4. Coverage period lies within one of the seasons 2023-24, 2024-25, 2025-26
   (full-season, partial-season, or since-a-stated-date lists all qualify);
5. Corroborated by ≥2 independent URLs (the A20 pattern), captured in
   `marchand_index/external_outcomes_sources.md`.

**Adoption is all-or-none:** EVERY list found that qualifies is adopted; no
discretionary selection. Membership = appeared on ANY adopted list (same union
semantics). Join is NHL-id-keyed per the A20 namesake guard. A list that fails any
clause is recorded in the sources doc with the failing clause, not silently skipped.

**Search manifest (fixed; execute every line; record hit/no-hit per line):**
- Web search: `site:nhl.com "best-selling" OR "top-selling" jerseys` (each season year pair)
- Web search: `NHL PR top selling jerseys 2024`, `... 2025`, `... 2026`
- Web search: `Fanatics NHL best selling jerseys list 2024 / 2025 / 2026`
- Web search: `NHLPA most popular jerseys 2024 / 2025 / 2026`
- Wayback Machine (web.archive.org): snapshots of `shop.nhl.com` "top sellers" /
  "best sellers" landing pages within each season's date range (note: retailer
  category pages are dynamic inventory, NOT ranked lists — they qualify ONLY if a
  snapshot shows an explicit ranked/top-N editorial list; record the verdict)
- Web search: `"top-selling jerseys" NHL midseason 2023-24 / 2024-25 / 2025-26`

**Outcome handling:** rebuild `external_outcomes.csv` with the enlarged union;
report old n (12) and new n; if the sweep finds nothing new, log the null result
here (sweep executed, zero qualifying additions) and V1b proceeds at n = 12
exactly as before.

**Honest residuals:** press-reported lists inherit outlet transcription risk
(mitigated by the ≥2-URL rule); partial-season lists overweight early-season
sellers; the union remains temporally impure for the two pre-window seasons
exactly as A31.3/§G already disclose.

**Anti-tuning compliance (§13):** the qualification rule and search manifest are
fixed and committed before any search result is seen; adoption is all-or-none, so
no name can be cherry-picked in or out; outcome lists are independent of all model
inputs (wiki/Reddit/Trends); logged while Reddit is 0/774 and no production OAQ or
V1b exists, so no result could have influenced the rule; floors, AUC construction,
bootstrap (per A31.1), weights, pool, window unchanged. Pre-A37
`external_outcomes.csv` retained in git history per §13.

**A38 (2026-07-21) — Empirical market-portability anchor: event-study diagnostic on
in-window team-changers. Logged BEFORE the Phase-2 compute; Reddit remains 0/774.
DESCRIPTIVE — not a validation pathway, no floor, cannot alter the λ = 0.5 primary.**

A5 committed λ = 0.5 as the maximum-entropy midpoint because no empirical anchor
existed for the share of market-driven attention that travels with a player. An
anchor is derivable from data already collected: skaters who changed NHL teams
inside the fixed window were observed under two market sizes, and their K=10 peer
sets (non-movers) provide the counterfactual attention path — the abnormal-attention
construction of the finance event-study literature (MacKinlay 1997).

**Mover set (mechanical):**
1. In-season movers: pool skaters with ≥2 distinct-team NHL `seasonTotals` rows for
   season 20252026 (`gameTypeId==2`, `leagueAbbrev=="NHL"`) — the A22 derivation.
2. Off-season movers: pool skaters whose last 20242025 NHL team differs from their
   first 20252026 NHL team (both season rows present).
3. Event date = the publicly reported transaction date, corroborated by ≥2
   independent URLs per mover (A20 sourcing pattern), recorded in
   `marchand_index/mover_dates.csv` with `move_type ∈ {trade, fa_signing, waiver}`.
   A mover whose date cannot be corroborated by 2 URLs is EXCLUDED and counted.
4. Eligibility: event date t must leave ≥30 in-window days on each side of the
   exclusion gap (below). Movers failing this are excluded and counted.

**Estimator (mechanical; wiki_en daily vectors only — the only component with
per-day resolution; disclosed):**
- Windows: pre = in-window days in [t−63, t−8]; post = in-window days in
  [t+8, t+63]. Days within ±7 of t are excluded (transaction-news spike).
- Per mover i: Δa_i = log1p(mean daily views in post) − log1p(mean daily views in
  pre), from the zero-filled 365-day `wiki_daily.csv` vector (dates implicit:
  index 0 = 2025-04-18).
- Peer control: Δa_peer_i = mean of the same quantity (same calendar windows) over
  i's `peer_player_ids` that are themselves non-movers; ≥5 usable peers required,
  else i is excluded and counted. Abnormal change: Δã_i = Δa_i − Δa_peer_i.
- Market change: Δm_i = market_z(new team) − market_z(old team), using the primary
  MarketSize_team at compute time (post-A30 if adopted; `market_z_lockedv1`
  version reported as a sensitivity row).
- Mover regression: OLS Δã_i = α + β·Δm_i + ε over all eligible movers.
- Cross-sectional market gradient: OLS log1p(wiki_12mo) ~ market_z + position
  indicator + the 6 standardized §6/A13 skill features (group-mean imputation as
  in compute) over all NON-movers; γ̂ = the market_z coefficient.
- **Empirical anchor: λ̂_emp = clip(β̂ / γ̂, 0, 1)** — the share of the
  cross-sectional market gradient that a mover's attention actually loses/gains
  when crossing markets (β̂ ≈ 0 → attention fully portable → λ̂_emp ≈ 0;
  β̂ ≈ γ̂ → attention fully market-attached → λ̂_emp ≈ 1). If γ̂ ≤ 0, λ̂_emp is
  reported as "undefined (non-positive market gradient)" with β̂ and γ̂ shown.
- Uncertainty: 1,000 bootstrap draws, seed 20260526; each draw resamples movers
  (for β̂) and non-movers (for γ̂) with replacement and recomputes λ̂_emp;
  percentile 95% CI. Secondary cut: trade-only movers (FA moves are
  self-selected destinations).

**Interpretation rule (fixed now):** the primary λ = 0.5 is unchanged under every
outcome. If the λ̂_emp 95% CI contains 0.5, the poster may state "the locked
midpoint is consistent with an empirical portability estimate from n=N in-window
team-changers." If the CI excludes 0.5, the poster states the tension verbatim
("the empirical anchor suggests λ nearer X; the pre-committed λ ladder shows the
headline's sensitivity") — and nothing else changes. This diagnostic does not
count toward the ≥3 validation pathways.

**Honest residuals (disclosed in advance):** post-move novelty (new-market
curiosity) inflates post-attention regardless of market direction, biasing β̂
toward 0, i.e. toward the portable conclusion — stated next to the estimate;
deadline-window movers have truncated post-windows (30-day minimum); n is small
(tens, not hundreds) — this is an anchor, not a validation; wiki-only resolution;
market_z is a proxy (A30 disclosures apply).

**Anti-tuning compliance (§13):** logged before the Phase-2 compute while Reddit
is 0/774, so no OAQ, validation, or λ-ladder result could have influenced the
design; mover set, windows, estimator, and interpretation are mechanical and fixed
in advance; weights (§4/A12), peer features (§6/A13), λ (A5), denominators
(A4/A8), pool (§2/A10), window (A11/A14), and all validation floors (§9, A6/V3)
unchanged. Output appears only in the designated descriptive diagnostics panel per
the poster forking-paths rule (§H of the airtight plan), which is extended to name
this diagnostic.

**A39 (2026-07-21) — Attention-concentration descriptive panel (superstar-economics
statistics). Logged BEFORE the Phase-2 compute; Reddit remains 0/774. DESCRIPTIVE —
no floor, no gate, not a validation pathway.**

Superstar economics (Rosen 1981 AER; Adler 1985 AER) predicts convex, highly
concentrated attention markets. The poster reports the following pre-registered
concentration statistics, computed once, in a single designated descriptive panel:

1. **Base quantity (fixed now): `wiki_12mo`** (post-A36, canonical+redirect,
   en-Wikipedia) — chosen because it is the one composite component with NO
   censoring (the Reddit 1,000-result cap floors star counts, A23), so star-tier
   concentration is measured, not truncated. The same statistics on
   `engagement_raw` are reported as a secondary row with the censoring caveat.
2. Top-share: share of the pool total held by the top 8 players (= ceil(1% of
   774)) and the top 77 (= ceil(10%)).
3. Gini coefficient of `wiki_12mo` across the 774 (discrete formula
   G = Σᵢ Σⱼ |xᵢ − xⱼ| / (2 n² x̄); NULL rows excluded and counted).
4. The same top-shares and Gini for `cap_hit_M` (cap_quality=low rows excluded
   and counted) — the payroll-vs-attention concentration contrast
   (tournament-theory framing, Lazear & Rosen 1981).
5. Between-team share of attention variance: R² of a one-way ANOVA of
   log1p(wiki_12mo) on team (SS_between / SS_total) — the driver-vs-constructor
   decomposition idea (Bell et al. 2016, F1), quantifying how much player
   attention is team-context before any market adjustment.
6. Bootstrap 95% CIs on every number: 1,000 player-level resamples, seed 20260526.

**Presentation rule (fixed now):** these are descriptive market facts, reported
with CIs in one panel; they support the Rosen/Adler framing of WHY a peer-matched
residual is the right construct, and make no validity claim about OAQ itself. No
concentration number may be promoted to the headline unless the headline slot is
already in shipping-matrix rows 6–8 (no validation language available), in which
case the concentration sentence MAY serve as the poster's quotable descriptive
fact — explicitly labeled descriptive.

**Anti-tuning compliance (§13):** logged before the Phase-2 compute while Reddit
is 0/774; statistic list, base quantity, exclusion rules, and presentation rule
fixed in advance; nothing in the composite, peer matching, denominators,
validation floors, or hypotheses changes. Output confined to a single designated
panel per the §H forking-paths rule, which is extended to name this panel.

**A40 (2026-07-22) — Descriptive measurement-quality batch (five clauses). Logged
BEFORE the Phase-2 compute; Reddit remains 0/774. DESCRIPTIVE — no floor, no gate,
not a validation pathway; nothing here can alter the headline under any outcome.**
(U3 of the 2026-07-11 idea-maximization review; owner-approved 2026-07-13 with the
U-slate, §14 decision record; text as drafted in that review's §4.)

1. **Split-half reliability of the engagement composite.** The wiki_en and
   wiki_intl daily vectors (post-A36, zero-filled 365-day, date-indexed) are split
   odd/even by day index; the Reddit submission pool is split odd/even by
   submission index after the A15/A21 attribution filter; trends and all non-flow
   quantities are held at their full-window values in both halves (no sub-window
   resolution exists; disclosed). engagement_raw is recomputed per half under the
   unchanged §4/A12 weights and sentinel rules; the Spearman correlation of the
   two half-composites across the pool is reported with its Spearman–Brown
   correction and a 1,000-draw player-level bootstrap CI (seed 20260526).
2. **Permutation-null calibration.** 1,000 whole-pool permutations of
   engagement_raw across the pool (seed 20260526); OAQ_observed, OAQ_portable, and
   the V1b AUC recomputed per draw; the null distribution is displayed beside the
   observed values in one designated calibration figure. Interpretation fixed now:
   this panel demonstrates pipeline calibration (a null input yields chance-level
   validation statistics); it is not a hypothesis test and carries no verdict.
3. **Market-attribution share (case cards only).** Each case-study card reports
   share_market = λ·max(0, market_z) / engagement_raw (0 when engagement_raw ≤ 0;
   flagged), labeled "share of measured attention attributable to team market
   under the locked λ = 0.5 correction." Arithmetic on already-registered
   quantities; illustration per A31.5, never evidence.
4. **Drop-one-peer sensitivity (case cards only).** For each case-study player,
   OAQ_portable is recomputed K times omitting one of the K=10 peers; the min–max
   range is shown as a secondary whisker beside the §10 bootstrap CI, labeled
   "peer-set sensitivity (not propagated in the primary CI — see A26 table)."
5. **Pool-survivorship limitation (poster §G addition, verbatim):** "The pool is
   the 2026-06-17 roster snapshot; skaters who exited the NHL before the snapshot
   are absent even where their in-window attention was real."

**Presentation rule (fixed now):** clauses 1–4 appear only in designated
descriptive panels per the airtight plan §H forking-paths rule, which is extended
to name them; none is eligible to become the headline under any outcome; no
number from this amendment is quoted standalone in the abstract-conformance copy.

**Anti-tuning compliance (§13):** logged before the Phase-2 compute while Reddit
is 0/774, so no composite, OAQ, or validation result could have influenced the
design; splits, permutation scheme, and card statistics are mechanical and fixed
in advance; weights (§4/A12), peer features (§6/A13), λ (A5), denominators
(A4/A8), pool (§2/A10), window (A11/A14), seed, and all validation floors (§9,
A6/V3, A31) are unchanged.

**A41 (2026-07-22) — Pool deduplication: 774 → 771 (three duplicate persons).
Logged BEFORE the production Reddit matcher run; Reddit remains 0/774
(equivalently 0/771 post-dedup — no per-player production counts exist).
Owner-approved 2026-07-13 (§14 decision record; supplement 2026-07-13 §4b).**

The A21 acceptance dry-run (`raw/reddit_identity_pairs.md`) found three duplicate
persons in the locked §2/A10 pool — identical `nhl_player_id` under two 2026-06-17
snapshot teams (mid-move roster artifacts). Without dedup, A21 rule 3 mechanically
flags each pair fully non-discriminable, zeroing both rows' Reddit counts — a pool
defect, not true ambiguity. (The two Elias Petterssons are distinct
`nhl_player_id`s — a real pair, not affected.)

| person | nhl_player_id | kept row | dropped row |
|---|---|---|---|
| Emil Andrae | 8482126 | 499 (PHI) | 637 (TOR) |
| Simon Benoit | 8481122 | 638 (TOR) | 500 (PHI) |
| Ross Colton | 8479525 | 152 (COL) | 368 (NAS) |

**Mechanical keep rule (fixed now, applied uniformly):** for each duplicated
`nhl_player_id`, keep the row whose team matches the player's 20252026 NHL
regular-season team in the NHL API landing `seasonTotals` (gameTypeId == 2,
leagueAbbrev == "NHL" — the A22/A38 derivation); drop the other row. The 2025-26
team is unique for all three persons (Andrae: Flyers; Benoit: Maple Leafs;
Colton: Avalanche), so the rule is decisive with no tie-break; each dropped row is
a post-window June-2026 move artifact (verified live 2026-07-22: `currentTeamAbbrev`
TOR / PHI / NSH respectively, all outside the A11 window). Rationale: every
attention quantity is measured on the A11/A14 window, which the 2025-26 season
spans; the kept row's team context is the one under which the in-window attention
accrued.

**Implementation (mechanical):** player_ids 637, 500, 368 are removed from
`players.csv` before the production matcher run. Per-source raw files keep any
already-fetched rows for the dropped ids (orphans; every loader joins on the pool,
so they are inert). `mover_dates.csv` is unaffected (none of the three derives as
an A38 mover — their moves post-date the window).

**Mechanical propagation (no re-decision):** N = 771 wherever the pool count
appears; count-typed constants defined by ceil rules re-evaluate on 771 — A39
top-share counts become ceil(1%·771) = 8 (unchanged) and ceil(10%·771) = 78
(was 77); the "774" in prior amendment texts is the historical pool at their
logging time and is not retro-edited.

**Anti-tuning compliance (§13):** logged while Reddit is 0/774 fetched; the keep
rule is derived from an objective NHL-API season quantity fixed by history, not
from any attention data (the duplicate rows' wiki vectors are byte-identical, so
no attention quantity could discriminate them anyway); applied uniformly to all
duplicated ids; weights (§4/A12), peer features (§6/A13), λ (A5), denominators
(A4/A8), window (A11/A14), seed, K, and all validation floors (§9, A6/V3, A31)
are unchanged; the pool (§2/A10) changes only by removing duplicate rows of
already-pooled persons.

**A42 (2026-07-22) — Common-word surname guard for the local Reddit matcher.
Logged AFTER the first matcher run and BEFORE any composite, OAQ, or validation
computation. Timing disclosed: `reddit_counts.csv` v1 existed when this was
written — the defect is only visible in fetched counts; the matcher is
deterministic from the frozen corpus and is re-run under this rule. No number
derived from Reddit counts (composite, OAQ, validation, or any §9/A31 quantity)
was computed before this text.**

**Defect (v1 evidence, recorded):** A15/A21 guard player-vs-player collisions
only. A folded surname token equal to a common English word matches ordinary
prose: v1 counted Daniil But 4,330 mentions ("...no NHL Hockey today but there
is AHL Hockey!"), Oskar Bäck 2,309 (fold "bäck"→"back"), Owen Power 2,268
("power play"), Brayden Point 1,793, Logan Stanley 1,555 ("Stanley Cup") — four
of the five above Connor McDavid (2,068), facially invalid.

**Rule (mechanical, applied uniformly):**

1. **Guard set.** DF(sn) = fraction of the frozen corpus's 250,004 submissions
   whose folded whole-token set (A23 `match_tokens`) contains folded pool
   surname sn. Guard set = {sn : DF(sn) ≥ 0.01}. The set, every DF value, and
   the set's stability under thresholds 0.005 and 0.02 are printed by the run
   and recorded in the matcher log; instability under those bounds would be
   disclosed.
2. **Attribution restriction.** A guarded surname's submission may attribute to
   a guarded player ONLY via the A15 first-name evidence check (folded
   first-name token prefix, len ≥ 3 / exact for shorter, or the unique-initial
   "X. Surname" pattern) — the identical checker already pre-registered for
   shared surnames, now forced for guarded players regardless of pool surname
   uniqueness. Team-subreddit context (A21 rule 2) and team-nickname
   co-occurrence (rule 4) are deliberately INSUFFICIENT for guarded surnames:
   hockey idiom co-occurs with team context ("Sabres power play", "Stanley Cup
   run"). A guarded member without first-name evidence is excluded from
   contention for that submission; remaining members proceed under unchanged
   A21 rules.
3. **Disclosure columns.** `reddit_common_word_guard` (true/false per player)
   and `guard_filtered_mentions` (submissions in the player's counting subs
   containing the guarded surname token but rejected for lack of first-name
   evidence).
4. **Bias direction (fixed interpretation):** conservative — casual
   surname-only references to guarded players ("Power was great tonight") are
   not counted; guarded players' Reddit counts are lower bounds. Stated on the
   poster limitations panel next to the Reddit cap disclosure (A23).

**Anti-tuning compliance (§13):** the rule consumes predictor-side corpus token
frequencies only — no outcome, composite, OAQ, validation, or hypothesis
quantity existed when it was fixed; the evidence checker it forces is the
unchanged A15 machinery; threshold set in advance of computing the guard set's
membership beyond the five facially-invalid names above; weights (§4/A12), peer
features (§6/A13), λ (A5), denominators (A4/A8), pool (§2/A10 as amended by
A41), window (A11/A14), seed, and all validation floors (§9, A6/V3, A31)
unchanged.

**A43 (2026-07-22) — Guard-trigger refinement: two-prong test replaces A42's
bare DF threshold. Logged after the A42-rule run and BEFORE any composite, OAQ,
or validation computation (that boundary still holds; the matcher remains
deterministic from the frozen corpus and is re-run under this rule).**

**Defect in the A42 trigger (v2 evidence, recorded):** DF ≥ 1% cannot separate
"surname is a common word" from "player is genuinely famous." v2 guarded
McDavid (DF 0.0141 — fans discussing him) and filtered 1,389 legitimate
surname-only McDavid submissions (2,068 → 679), and suppressed the three
Hughes brothers similarly. Its guarding of stanley ("Stanley Cup"), york
("New York"), and connor (first-name usage: "Connor McDavid") was correct.

**Rule (mechanical; replaces A42 rule 1's trigger; A42 rules 2–4 — the A15
evidence requirement, disclosure columns, and conservative-bias label — are
unchanged and now apply to the set below):** a folded pool surname sn is
guarded iff

1. **English-word prong:** sn appears in the repo-pinned
   `english_top1000.txt` (first 1,000 entries of the public
   google-10000-english frequency list, Google Trillion Word Corpus
   derivation; fetched 2026-07-22; committed with provenance header;
   never edited); OR
2. **Phrase-collision prong:** DF(sn) ≥ 0.01 (A42 definition, unchanged) AND,
   over every occurrence of sn in the corpus token stream, EITHER
   (a) ≥ 50% of occurrences are immediately followed by another pool surname
   (first-name usage: "connor mcdavid"), OR
   (b) a single adjacent-token bigram (previous or next side) covers ≥ 50% of
   occurrences AND its partner token is not a folded pool first name
   (partner-token exemption: "connor mcdavid" cannot guard mcdavid via the
   dominant "connor …" bigram, while "stanley cup" / "new york" do guard
   stanley / york — cup and new are not pool first names).

The run prints, and the matcher log records: both prongs' membership, DF
values, each prong-2 candidate's dominant bigram and shares, and the guard
set's stability under prong-2 occurrence-share thresholds 0.4 and 0.6;
instability would be disclosed. Expected corrections vs v2 (verified at run
time): mcdavid and hughes leave the guard (their counts revert to the A15/A21
machinery); but/back/power/point (prong 1), stanley/york/connor (prong 2)
remain guarded.

**Anti-tuning compliance (§13):** both prongs consume a fixed public wordlist
and predictor-side corpus token statistics only; no composite, OAQ, validation,
or hypothesis quantity has been computed at any point in the A42/A43 sequence;
the evidence checker is the unchanged A15 machinery; thresholds are round
numbers fixed in this text before computing prong memberships beyond the named
v2 evidence; weights (§4/A12), peer features (§6/A13), λ (A5), denominators
(A4/A8), pool (§2/A10 as amended by A41), window (A11/A14), seed, and all
validation floors (§9, A6/V3, A31) unchanged.

**A44 (2026-07-22) — Trends anchor MID pinned; A16 topic-type test extended
after Google renamed entity types. Logged BEFORE any composite, OAQ, or
validation computation (boundary unchanged).**

**Defect (live evidence, recorded):** A16 resolves topic entities as "first
pytrends suggestion whose type contains 'hockey'." Google now types the anchor
entity as **"Florida Panthers center"** (suggestions for "Brad Marchand",
verified live 2026-07-22: person MID `/m/027h_8t` listed with that type) — no
"hockey" substring, so anchor resolution silently fell back to the raw string
on the 2026-07-22 resume run. Four players fetched on that run (Dylan
Holloway, Bo Groulx, Daniil But, Maveric Lamoureux — pids recorded in the run
log) were measured against the STRING anchor while all earlier rows used the
TOPIC anchor; their stored ratios are cross-anchor inconsistent.

**Rule (mechanical):**

1. **Primary anchor MID pinned:** `/m/027h_8t` ("Brad Marchand" person
   entity, verified live 2026-07-22). No run-time resolution for the anchor;
   the pin removes the failure mode permanently.
2. **Topic-type test extended (player rows + secondary anchor):** a
   suggestion's folded type qualifies iff it contains "hockey" OR contains any
   of the 32 folded NHL franchise names (the fixed `raw/teams.csv` list) —
   "Florida Panthers center" qualifies via "florida panthers". First
   qualifying suggestion wins, as before; raw-string fallback and its
   `trends_method=string` disclosure unchanged.
3. **Repair (surgical, disclosed):** the four cross-anchor rows are nulled and
   re-fetched under the pinned anchor; every other stored row is untouched
   (their fetches used the topic anchor; V-A11-Trends verified the window).
   Marchand's own row continues to follow A35 clause 1 (secondary anchor),
   with the secondary anchor resolved under the extended type test.

**Anti-tuning compliance (§13):** transport/entity-resolution repair only; the
pinned MID is the same entity earlier runs resolved dynamically; the extended
type test consumes a fixed franchise-name list; no composite, OAQ, validation,
or hypothesis quantity has been computed; A16's ratio definition, window
(A11), weights (§4/A12), and all floors are unchanged.

---

**A47 (2026-08-01) — Trends raw-string fallback RETIRED; position tie-break for
shared full names; refusal reasons split for the A25 taxonomy. Logged BEFORE
any composite, OAQ, or validation computation (boundary unchanged).**

**Defect (measured from the stored file, recorded):** A16 clause 2, as amended
by A44, kept a raw-name fallback whenever no suggestion qualified — and A44
left `trends_method=string` as a "disclosed sensitivity cut" rather than a
refusal. A bare name string measures whoever else owns that name. 23 of 771
stored rows are on that path, and the resulting values are not a tail:

| rank /771 | `trends_12mo` | player | what the string measures |
|---|---|---|---|
| **1** | **9.6647** | Will Smith | the actor — 4.9x McDavid, 9.7x the anchor |
| 15 | 0.4298 | Garrett Wilson | the NFL wide receiver |
| 20 | 0.3766 | Alex Ovechkin | undercount — should sit top-3 |
| 28 | 0.3390 | Trevor Moore | ambiguous |
| 34 | 0.3105 | Ben Jones | the NFL center |
| 47 | 0.2251 | Taylor Ward | the MLB outfielder |
| 170 | 0.0703 | Brayden Point | undercount |

The error runs **both directions**: a common name imports a stranger's search
volume, while a hockey-only name loses the volume a topic MID aggregates
(Ovechkin, Point, Parayko, Perfetti, Beniers, Weegar are all string rows and
all rank implausibly low). The trigger is usually not "Google has no entity"
but throttling — `RetryError(... 'too many 429 error responses')` dominates
every stored run log, and `resolve_topic_mid` caught that exception and
returned the same empty string a genuine no-match returns.

**Second defect, same clause:** "first qualifying suggestion wins" cannot
separate two pooled players who share a full name. The Canucks' **Elias
Pettersson (C, `nhl_player_id` 8480012)** and **Elias Pettersson (D, 8483678)**
both carry MID `/g/11ddxds8fn` and an identical `trends_12mo = 0.222069`
(ranks 47-48/771). The D is credited with the C's search volume. `A41` deduped
the pool to 771 but left this pair as two distinct persons, correctly.

**Third defect, found by the A47 re-run itself (recorded):** A44 rule 2 tested
Google's entity type for a franchise name by raw-casefold substring against the
`raw/teams.csv` slugs. The slug `st-louis-blues` folds to `"st louis blues"`,
but Google writes **`"St. Louis Blues defenseman"`** — the period breaks the
substring. Verified live 2026-08-01: Colton Parayko, Dylan Holloway and Pius
Suter each return a correctly-typed St. Louis entity as their FIRST suggestion,
and all three were refused `no_hockey_topic` — the one refusal reason A25
imputes as raw 0. The punctuation miss would therefore have scored three real
NHLers as zero search interest. Both sides of the comparison are now folded to
accent-free, punctuation-free, single-spaced lowercase (`_strip_punct`); the
same folding is applied to the clause-1 position test.

**Rule (mechanical):**

0. **Type folding.** Before any test, a Google entity type and every franchise
   name are NFKD-normalized, stripped of combining marks, and reduced to
   alphanumerics and single spaces. "hockey" substring test unchanged.
1. **Selection.** Among pytrends suggestions, take those whose folded type
   qualifies under the A44 rule 2 test (as folded by clause 0).
   - exactly one qualifies -> its MID, `trends_method=topic`;
   - more than one qualifies -> **position tie-break**: keep the suggestions
     whose folded type contains a word for the player's `players.csv`
     position (`C` -> "center"/"centre"; `L` -> "left wing"; `R` -> "right
     wing"; `D` -> "defense"/"defence", which also cover
     "defenseman"/"defenceman" and the "-er" wing forms). Exactly one
     survivor -> its MID, `trends_method=topic_position`.
2. **Refusal replaces the string fallback.** No code path may query a raw
   name again. A refusal writes `trends_12mo` NULL, `query_mid` empty, and
   **stores no query string**, under exactly one reason:
   - `no_hockey_topic` — no suggestion qualified;
   - `ambiguous_topic` — the tie survived the position test;
   - `resolve_failed` — the `suggestions()` call raised or was blocked.
3. **A25 taxonomy amended for Trends (this is the load-bearing clause).** A25
   classified a NULL `trends_12mo` as `no_entity_exists` — **raw-0
   imputation** — from a blank `query_mid`. Every refusal above blanks the
   MID, so that inference would have scored a throttled Ovechkin as zero
   search interest. **A47 retires the Trends `no_entity_exists` branch
   entirely: all three refusal reasons are `fetch_failed` and renormalize
   (A25 rule 2), for any CSV vintage, with or without a `trends_method`
   column.**

   Including `no_hockey_topic`. A missing Google Trends **entity** reflects
   knowledge-graph coverage and namesake crowding, not absence of public
   interest — Will Smith (SJ, 4th overall 2023) has no hockey MID because the
   actor owns the name, and Google returns the actor, the Chris Rock incident,
   a Dodgers catcher, a book and a TV series before any hockey entity. Raw-0
   would assert nobody searches for him; renormalization says only that Trends
   did not measure him, which is what we observed. This is **exactly
   equivalent to imputing his weight-averaged z-score over the components that
   did resolve** (weights sum to 0.84, so `0.84m + 0.16m = m`) — no separate
   imputation step is needed or permitted.

   **Scoped to Trends.** `wiki_12mo` and `wiki_intl_12mo` keep A25's raw-0
   rule: a missing *article* really does mean no encyclopedic salience,
   whereas Trends entity coverage is sparse and namesake-driven.
4. **Secondary anchor.** A35 clause 1's secondary anchor (Sidney Crosby) is
   resolved under the same rule; if it refuses, the anchor-row re-measurement
   **aborts** rather than chaining the scale onto a raw string.
5. **Repair (surgical, disclosed).** Re-fetch exactly the rows that cannot be
   trusted: the 23 `trends_method=string` rows, plus **any set of rows sharing
   one `query_mid`** (a shared MID is prima facie an unbroken tie) — the two
   Pettersson rows. **25 of 771 re-fetched; the other 746 are untouched**,
   their MIDs and ratios bit-identical. The resume filter enforces this: a
   stored row is reused only if its value is non-null, its method is a
   resolution method, and its MID is unshared.

**Repair outcome (executed 2026-08-01; 25 rows, none of the other 746 moved):**

| player | before | after | method |
|---|---|---|---|
| Will Smith | **9.664671** | **NULL** | no_hockey_topic |
| Garrett Wilson | 0.429799 | NULL | no_hockey_topic |
| **Alex Ovechkin** | 0.376552 | **1.963329** | topic |
| Trevor Moore | 0.339031 | NULL | no_hockey_topic |
| Ben Jones | 0.310541 | NULL | no_hockey_topic |
| Taylor Ward | 0.225071 | NULL | no_hockey_topic |
| **Elias Pettersson (C)** | 0.222069 | **0.220028** | topic_position |
| **Elias Pettersson (D)** | 0.222069 | **0.002821** | topic_position |
| Liam O'Brien | 0.093793 | NULL | no_hockey_topic |
| Brayden Point | 0.070345 | 0.080395 | topic |
| Jeremy Davies | 0.060690 | NULL | no_hockey_topic |
| Dylan Holloway | 0.045455 | 0.052186 | topic |
| Colton Parayko | 0.035862 | 0.067701 | topic |
| Pius Suter | 0.020690 | 0.026798 | topic |
| Cole Perfetti | 0.020690 | 0.046544 | topic |
| Matty Beniers | 0.019310 | 0.035261 | topic |
| MacKenzie Weegar | 0.011034 | 0.032440 | topic |
| Aliaksei Protas | 0.008276 | 0.064880 | topic |
| Bo Groulx | 0.005510 | NULL | no_hockey_topic |
| Erik Cernak | 0.004138 | 0.014104 | topic |
| Adam Engstrom | 0.002849 | NULL | no_hockey_topic |
| Jared Wright | 0.000000 | NULL | no_hockey_topic |
| Max Shabanov | 0.000000 | NULL | no_hockey_topic |
| Dmitri Simashev | 0.000000 | NULL | no_hockey_topic |
| Hendrix Lapierre | 0.000000 | 0.001410 | topic |

Final file: 771 rows — 756 `topic`, 2 `topic_position`, 1
`topic_secondary_anchor`, **12 `no_hockey_topic`**, 0 `ambiguous_topic`, 0
`resolve_failed`. Every string row is gone. The Pettersson D was carrying the
C's volume at **78x** his own. The 13 rows that re-resolved to a topic all
moved **up**, confirming the string query was also losing the volume a topic
MID aggregates; Ovechkin gains 5.2x and the top of the distribution becomes
face-valid (Crosby, McDavid, Ovechkin, J. Hughes, Celebrini, Bedard, Marchand,
Matthews) where it was previously led by a film actor.

**Verification of the untouched 746.** The clause-0 folding only ever adds
qualifying suggestions, so rows resolved under the stricter pre-A47 test could
in principle have selected a different entity. Spot-checked live 2026-08-01
against the three STL rows most exposed to the period defect — Jordan Kyrou,
Robert Thomas, Pavel Buchnevich (the latter two typed "St. Louis Blues …",
which qualifies only after clause 0). All three re-resolve to the **same
stored MID**. Entity identity is stable across the rule change; the 746 are
not re-fetched.

**Residual, disclosed:** the 12 `no_hockey_topic` players carry no Trends
measurement and are scored on their remaining four components (0.84 of the
composite, renormalized). Live inspection confirms the refusals are genuine
absences rather than lookup failures — Google returns 5 suggestions for "Will
Smith" with no hockey entity at all, and "Trevor Moore" returns only the
comedian.

**Rejected alternative — the `"<name> hockey"` scale (tested, recorded).**
Before settling on renormalization we tested filling the 12 from a parallel
run querying `"<player name> hockey"` for every player against the same pinned
anchor, then rank-transferring onto the primary scale. A 7-player probe
(2026-08-01, 4 refused + 3 with known primary values) rejected it:

| player | primary | `"<name> hockey"` |
|---|---|---|
| Will Smith | — | **0.188999** |
| **Connor McDavid** | **1.972934** | **0.083216** |
| Trevor Moore / Garrett Wilson / Ben Jones | — | 0.000000 |
| Cole Perfetti | 0.046544 | 0.000000 |
| Erik Cernak | 0.014104 | 0.000000 |

The scale does not measure salience; it measures **how often a name requires
disambiguation**. Will Smith outranks McDavid on it 2.3x — precisely because
of the actor, i.e. the contamination A47 exists to remove, re-entering through
the query string. Five of seven probes return exactly 0, including three of
the four players the fill was meant to rescue, so the rank map is degenerate
where it is needed. Not adopted; no data from this probe enters any file. The
probe cost 7 live queries and is recorded here so the option is not re-opened.

**Limit of claim.** The position tie-break assumes Google types the competing
entities with distinct positions. Where it does not, A47 refuses rather than
guesses, and the player renormalizes — a lost measurement, never a borrowed
one. `no_hockey_topic` is still an inference that low Google salience implies
near-zero search interest; that was already A25's standing assumption and is
unchanged here.

**Anti-tuning compliance (§13):** entity-resolution and missingness-
classification repair only; no threshold was fitted, and the position map is
mechanical from `players.csv`. The refusal direction is pre-committed as the
conservative one (drop a measurement, never substitute a proxy). No composite,
OAQ, validation, or hypothesis quantity has been computed. A16's ratio
definition, the A11 window, the §4/A12 weights, and all floors are unchanged.
Tests: `tests/test_fetch_trends_a47.py` (25),
`tests/test_trends_null_taxonomy_a47.py` (8); suite 269 -> 302.
`tests/test_null_taxonomy_a25.py::test_trends_no_mid_is_no_entity` is renamed
and inverted to record the supersession; A25's wiki clauses are untouched.

---

**A48 (decided 2026-08-02, locked 2026-08-03) — First-name collision guard,
option C' (Defect 1) + `unmeasurable` reddit status (Defect 5).** Recorded
after a read-only diagnostic probe measured the candidate fixes on the live
corpus, and BEFORE the production re-run whose output it governs; no
composite, OAQ, validation, or hypothesis quantity has been computed.

**Defect (recorded).** 13 pool surnames are unique in the pool AND are another
pool player's FIRST name (`beck blake cole colton connor frank james joshua
paul quinn reilly shea thomas`). For a unique surname `attribute()` awards
every matching submission to its owner with no evidence check ("single-member
groups always win", A2), so every "Quinn Hughes" credited Jack Quinn and every
"Cole Caufield" credited Ian Cole. Root cause is a threshold artifact: A43
prong P2a implements the right idea but is gated on DF ≥ 0.01, and `quinn`
(0.0093), `cole` (0.0087), `thomas` (0.0052) sit under the gate. Only
`connor`/`james`/`paul` were guarded.

**Rule (mechanical).** Per submission containing collision surname `sn`
(owner = the single pool player carrying it as a surname), classify into
exactly one state over the ordered folded token stream:

1. **S1** — every occurrence of `sn` is immediately followed by the surname of
   a pool player whose first name is `sn` (tight bigram) → proven first-name
   usage; owner ineligible; disclosed in `guard_filtered_mentions`.
2. **S2** — ≥1 standalone occurrence AND the owner's A15 checker fires →
   owner eligible. **S1 takes precedence over S2** (verified: 14 r/hockey
   posts fire the checker via e.g. "Lauren Kyle (Connor McDavid's wife)" while
   every `connor` is bigram-bound; they are S1).
3. **S3** — ≥1 standalone occurrence, no first-name evidence → eligible ONLY
   in the owner's own team subreddit; otherwise disclosed in
   `ambiguous_mentions` and counted for nobody.

**Scoping (the `'` in C'):** (a) a collision surname in the pinned English
top-1000 (`james`, `paul` — P1) gets NO own-sub allowance: own-sub context can
resolve a rival-player confuser, not an ordinary-word confuser, which appears
in every sub equally (bare "stanley" in r/winnipegjets is "Stanley Cup", not
Logan Stanley). (b) The own-sub allowance applies ONLY to collision surnames,
never to P1/P2b guards generally — the other 6 guarded players are untouched
and the 13 are the complete blast radius.

**Supersessions (explicit, not buried).** For collision surnames A48
**overrides A42 rule 2** ("team context never suffices for guarded surnames")
and **overrides the A43 P2 guard**: `connor` was P2a-guarded and C' is
strictly MORE permissive for it. Defensible because per-post positional bigram
evidence is stronger than the token-level aggregate P2a uses; it is
nonetheless a real rule change and is recorded as one. Non-collision guarded
surnames keep A42/A43 semantics unchanged.

**Evidence (probe, 250,004 submissions, recorded before the re-run).** Options
measured: A = blanket guard (−63% of these players' real signal — rejected),
B = bigram only (−521), C = bigram + own-sub (−1,869), C' = C with P1-strict
(−1,970, 1,449 → ambiguous). C' selected. The tight-vs-loose bigram choice is
not knife-edge: ≤26 posts per name, 1 for `cole`; tight adopted. C' is also a
recall fix: the A42 guard had been deleting real Kyle Connor mentions
(280 → 364 under C').

**Verification (post-re-run).** Pipeline `reddit_mentions_12mo` equals the
probe's C' column **exactly for all 13**; the 771-row diff shows movement
confined to the 13 collision owners plus the two Defect-5 status flips below;
detail rows 163,937 → 161,947 (−1,990 = probe −1,970 + the probe's
root-caused self-check drift, connor −14 / paul −6). New disclosure column
`reddit_firstname_collision` marks the 13 rows.

**Defect 5 — `unmeasurable` (third status, same amendment).** A zero is
measured only if we looked and found nothing. If the surname appeared but
every occurrence was discarded, we failed to measure — that must not share a
status with a measured zero. New `reddit_status` value `unmeasurable`, set
mechanically when status would otherwise be ok/partial AND
`reddit_mentions_12mo == 0` AND (`ambiguous_mentions > 0` OR
`guard_filtered_mentions > 0`). Distinct from both `ok` (a player with 0
mentions and 0 discarded candidates is a genuine zero and stays ok) and
`null` (source unavailable); `unmeasurable` = source read, player inseparable
within it. Downstream `compute_oaq` NULLs both reddit columns and
renormalizes — the A47 Trends precedent (NULL → renormalize, never impute 0).
The **Wikipedia raw-0 exception stands** (a missing article does mean no
encyclopedic salience). Unlike `null`, an `unmeasurable` row keeps every
disclosure column populated. Measured blast radius on the regenerated file:
exactly the two VAN Elias Petterssons (433 ambiguous each, A21 rule 3
non-discriminable pair); Marcus Pettersson (94 mentions, 433 ambiguous)
correctly stays `ok` — ambiguity alone never triggers.

**Limits of claim (carried to the poster).** (a) The own-sub allowance
(~605 mentions) rests on a base-rate judgment, not labelled data: the owner
declined a ~20–30 min hand-label validation of S3-in-own-sub on 2026-08-02
("surname and/or team name mention is enough to make it accurate enough most
of the time") — a deliberate, disclosed trade; re-offer if the schedule
loosens. (b) Defect 6, recorded not fixed: the A15 checker fires on the first
name appearing anywhere in the post, so S2 carries a small residual
over-count (quantified only for `connor`: 14 r/hockey posts). C' is less
wrong, not right.

**Anti-tuning compliance (§13):** identity-resolution repair only. The option
choice used the probe's attribution counts (how many mentions each rule keeps
or discards), never any composite, ranking, or hypothesis quantity. Thresholds
introduced: none — the rule is evidence-conditional, not fitted. A11 window,
§4/A12 weights, and all floors unchanged. Tests:
`tests/test_fetch_reddit_a48.py` (25); suite 302 → 327.

---

**A45 (definition fixed 2026-07-31; recorded 2026-08-03) — Reddit attention
affiliation split (Phase A).** Recorded out of numeric order: the number was
reserved when the Phase A plan was written (2026-07-31), which fixed every
definition and threshold below; A47 and A48 were locked in the interim. This
amendment is appended BEFORE the corrected (all-subs) output is computed or
inspected.

**Provenance disclosure (not hidden).** A first `attention_affiliation.csv`
was computed 2026-07-31 from `raw/reddit_detail.csv`, which is scoped to each
player's A22 counting subs. Its own/neutral buckets were valid but the rival
bucket measured trade history by construction (551/771 players at
`rival_reach` 0, max 3, `other` share 3.1%). That file was never published
(untracked on purpose, `PUBLISH_DELIVERABLE = False`) and its diagnosis IS
Defect 2. The corrected input is `raw/reddit_detail_allsubs.csv`: every
attributed winner across all 36 corpus subreddits with venue kept, generated
AFTER the A48 collision guard so the first-name collision class never entered
rival venues (ordering pre-committed in SESSION 2026-08-02). No definition,
threshold, or bucket rule changed between the two runs — only the input scope
Defect 2 repaired.

**What it measures.** For each pool player, the share of their Reddit
attention originating from their own fanbase versus rival fanbases.
Descriptive companion output only: it does not enter `compute_oaq.py`, changes
no CES weight, and does not alter `OAQ_portable`. No sentiment, no LLM, no
causal claim.

**Buckets.** Each `(player_id, submission_id)` mention pair is assigned
exactly one bucket by the subreddit it appeared in: `own` — the sub belongs to
a team the player was on at that submission's timestamp; `other` — any other
team's sub; `neutral` — r/hockey, r/nhl, r/fantasyhockey. Team-at-time is
reconstructed from `players.csv` (end-of-window team) walked backwards through
`mover_dates.csv` rows with `status == "dated"`; `excluded_rename_artifact`
rows are dropped; both Utah subs map to UTA.

**Normalizer — submissions, not subscribers.** Every count is divided by the
collected submission count of its subreddit. Subscriber count is explicitly
rejected: r/BostonBruins has more subscribers than r/Habs (119,306 vs 101,589)
but ~1/5 the submissions, so a subscriber-normalized figure would encode
posting culture as player attention.
`own_share = own_intensity / (own_intensity + other_intensity)`, where each
intensity sums `mentions_in_sub / submissions_in_sub` over subs. Neutral
mentions are reported but excluded from `own_share`'s denominator.
`own_share_scored` (score+1 weighting) is a robustness check; the count-based
figure is primary.

**Publish gate.** `low_n = attributed_mentions < 30` (`LOW_N_MIN`, fixed in
the 2026-07-31 plan). `low_n` rows are excluded from every published ranking
and diagnostic table; the threshold will not be adjusted after inspection.
A48 `unmeasurable` players contribute no detail rows, so they appear with
`attributed_mentions = 0`, `low_n` true — consistent with their NULL
treatment in OAQ.

**Limits of claim.** Subreddit is a proxy for fanbase allegiance, not proof
(a rival fan can post anywhere). Neutral-venue pairs cannot be attributed;
shares are computed on the attributed remainder and reported as such. The
corpus covers submissions only, not comments. Collection volume differs
across subreddits; normalization fixes the arithmetic, not any sampling bias
in what was collected. Any use of `own_share` to interpret `OAQ_portable`
(open item #3B) is an observed association, not a correction.

**Anti-tuning compliance (§13):** definitions and the `low_n` threshold
predate the corrected output; the only post-hoc change is input scope
(Defect 2 repair). No composite, OAQ, validation, or hypothesis quantity is
touched. Tests: `tests/test_affiliation_a45.py` (29),
`tests/test_reddit_allsubs_a45.py` (4); suite 327 → 331.

---

**A46 (plan locked 2026-07-31; recorded 2026-08-03, BEFORE the sensitivity
report was run) — `market_z` social-component sensitivity (subscribers vs.
activity).**

**Motivation.** `market_z`'s social component under A30 is
`team_sub_subscribers`, a stock. Subreddit submission volume over the
measurement window is a flow, and the two are nearly independent — Spearman
**0.299** across the 32 teams (pre-measured 2026-07-31; reproduced exactly by
`build_market_activity.py` on 2026-08-03). r/BostonBruins carries more
subscribers than r/Habs (119,306 vs 101,589) but roughly a fifth of the
submissions. Whether `OAQ_portable` depends on that choice is an empirical
question, and open item #3B turns on the answer.

**What is added.** Two lenses in `compute_market_z`, alongside the existing
`market_z_lockedv1` and `market_z_metro_only`: `market_z_activity` (A30 with
`sub_submissions_window` in place of `team_sub_subscribers`) and
`market_z_social_blend` (A30 with the mean of the two social z-scores).

**What does not change.** `MARKET_COMPONENTS_A30` remains
`["metro_population", "team_sub_subscribers", "attendance_pct_capacity"]`.
`LAMBDA_BIGMARKET`, the one-sided `max(0, market_z)` correction, the CES
weights, and the peer-matching procedure are all untouched. Tests assert the
primary is bit-identical with and without the activity table present.

**Why activity cannot become primary.** In-window submission volume is
**endogenous** to the quantity being measured: a team having a strong season
draws more posts to its subreddit, and its players draw more mentions inside
those posts. Promoting it to a `market_z` component would partially control
for the outcome. It is therefore permanently a reporting lens, regardless of
what the sensitivity report shows. (A pre-window activity measure,
2024-04-18 to 2025-04-17, would be exogenous and could in principle serve as
a primary; that is NOT part of A46 and would need new collection and its own
amendment.)

**Data quality.** UTA records 81 in-window submissions against 2,171 for the
next-lowest team — the franchise rename split the subreddit mid-window.
Teams below `ACTIVITY_QUALITY_MIN = 500` submissions are flagged
`activity_quality = "low"` and excluded from any conclusion drawn from this
lens. UTA is the only such team.

**Decision rule, fixed in advance.** The sensitivity report is descriptive.
No gate verdict, headline number, or published ranking is computed from any
A46 lens. If the lenses show a large effect, the response is to **document
the dependence as a limit of claim**, not to switch specifications.

**Limits of claim.** Subscriber counts are frozen at 2025-02-14/15 while
activity spans the window (different vintages). Submission counts reflect
what was collected, not necessarily everything posted, and collection was
not stratified. The corpus covers submissions only, not comments.

**Anti-tuning compliance (§13):** lens registration only; no threshold
fitted (`ACTIVITY_QUALITY_MIN` separates one known data hole from the real
distribution and was fixed in the 2026-07-31 plan). No composite, OAQ,
validation, or hypothesis quantity computed. Tests:
`tests/test_market_activity_a46.py` (18); suite 333 → 351.

---

**A49 (decided 2026-08-06, locked 2026-08-06 BEFORE the re-run) — Peer
matching is position-locked to three classes; the Marchand Index headline
returns to the §8-original raw-cap denominator with entry-level contracts
reported in a separate panel.**

Two independent rule changes, locked together because both were decided in
the same owner review and both alter the headline. Neither is a threshold;
neither was selected by comparing outcomes across candidate settings.

---

**A49.1 — Peer matching: position-locked to C / W / D.**

§6 fixes a "hard position filter" of forwards-vs-forwards and D-vs-D. A49.1
tightens the forward half: peers are now drawn only from the player's own
**position class**, where the classes are

| Class | `position` values | Pool |
|---|---|---|
| `C` | `C` | 249 |
| `W` | `L`, `R` | 247 |
| `D` | `D` | 275 |

Left and right wings remain a single class — the owner's rule is "all wingers
with each other," and splitting L from R would halve each pool for no stated
reason.

**What does not change.** The skill vector, the standardization, the
Mahalanobis distance, the per-`group` sample covariance used to form it,
`K_PEERS = 10`, the `effective_K` sentinel, and the A28 thin-peer
sensitivity mode are all untouched. The candidate *filter* narrows; the
*distance* is computed exactly as before. Because `group` `d1` was already
all-D, defencemen's peer sets are bit-identical to the pre-A49 primary —
this amendment moves forwards only.

**Pool adequacy, checked before locking.** Smallest class is W at 247, so
every player retains a full K=10 and no row falls back to a reduced
`effective_K`. Verified: 0 rows with `effective_K < 10`.

**Why.** A centre and a winger with the same `(age, PPG, TOI/G, CF%, xGF%,
OZS%)` are not interchangeable comparators for *attention*: centres take
draws, are named in defensive-zone and matchup discussion, and are the
default subject of line-based coverage. Mixing them lets a high-attention
winger inflate a centre's `peer_engagement_mean` (and the reverse) through a
role difference the skill vector does not encode. This is a construct-validity
fix, not a fit improvement.

**Effect, measured on the pre-lock data and recorded here for honesty.**
Spearman vs. the pre-A49 primary: `OAQ_portable` 0.9209, headline MI 0.9164
across all 771. The ordering is substantially preserved; the amendment is not
a re-ranking device. Direction of the largest moves: elite wingers rise
(Marchand `OAQ_portable` 4.307 → 5.055; Ovechkin 6.843 → 7.082) and Crosby
displaces McDavid at `OAQ_portable` #1 (7.228 → 7.719 vs 7.306 → 6.893).
**These numbers were computed before the amendment was written and are
disclosed precisely because they are favourable to the project's namesake
case — the rule is justified by role validity above, and would stand had the
effect gone the other way.** No alternative class definition was scored
against outcomes.

---

**A49.2 — Marchand Index headline = `OAQ_portable / cap_hit_M`; entry-level
contracts reported separately.**

The headline Marchand Index returns to the **§8-original** definition:

`marchand_index_headline(P) = OAQ_portable(P) / cap_hit_M(P)`

computed on the **non-entry-level pool only**. Entry-level-contract players
(`is_rookie_deal == 1`, flagged per A24: CapWages `contract_type` containing
"entry-level", price+age proxy as per-row fallback) are **excluded from the
headline leaderboard** and reported in a **separate companion panel** that
uses the same raw `cap_hit_M` denominator. The two tables are never merged,
and no combined ranking is published as a headline.

**What this supersedes.** A8 promoted `marchand_index_hybrid` (rookie-deal →
`expected_cap`; everyone else → `cap_hit_M`) to headline. A49.2 **demotes
`marchand_index_hybrid` to an audit lens.** It continues to be computed,
bootstrapped, and published in `oaq_pilot.csv` and in the lens comparison in
`results.md`, so a reviewer can see exactly how much the denominator choice
moved the ranking. `marchand_index` (the A4 full-`expected_cap`
intrinsic-efficiency lens) is likewise retained as an audit lens. Nothing is
deleted.

**What does not change.** `OAQ_observed`, `OAQ_portable`, the CES weights,
`LAMBDA_BIGMARKET`, the market proxy, `expected_cap` itself (still computed,
still used by the demoted lenses), the A24 rookie flag and its fallback, the
`cap_quality = low` exclusion from every MI ranking, the A34 display rule,
and the bootstrap procedure.

**Why raw cap.** `expected_cap` is a per-group OLS prediction from `(PPG,
TOI/G)` — a *modelled* denominator. Dividing an attention surplus by a
modelled price makes the headline a ratio of two estimated quantities, and
puts a regression the audience cannot see between the data and the number
they are asked to remember. `cap_hit_M` is an observed, verifiable,
externally auditable price. For a room of professional statisticians, the
observed denominator is the defensible headline and the modelled one is the
sensitivity.

**Why ELC players are separated rather than adjusted.** An entry-level cap
hit is not a negotiated market price — it is a collectively-bargained
ceiling, and dividing by it produces a mechanically large ratio that says
more about the CBA than about the player. A8 addressed this by *imputing* a
price; A49.2 addresses it by *not comparing the two populations at all*. The
separation is the honest form: within the ELC panel the denominator is
uniform-ish and the ranking is meaningful; across the boundary it is not, so
no across-boundary claim is made.

**Consequent change to the PC pattern verdict (§11).** PC asks whether ≥3 of
the top-10 by `engagement_raw` are displaced out of the top-10 by the
headline MI. Under A49.2 the headline pool excludes ELC players, so the
comparison is re-specified to run **both** lists on the **same non-ELC
display pool** — top-10 by `engagement_raw` among non-ELC vs top-10 by
headline MI among non-ELC. Computing the engagement list pool-wide against
an ELC-free MI list would manufacture displacement from a pool mismatch and
inflate the verdict. The floor of 3 is unchanged. The ELC panel gets no PC
verdict of its own.

**Limits of claim (to be carried onto the poster).** The headline is
attention surplus per dollar of a player's *actual current* cap hit. It is
therefore sensitive to contract timing: a player in the final year of a deal
signed against an older cap ceiling scores higher than the same player one
year later, and nothing in the index corrects for that. The ELC panel is
reported for interest and is **not** claimed to be comparable to the
headline table. `marchand_index_hybrid` remains available as the lens that
answers "what if rookies were priced at projected market pay instead."

**Anti-tuning compliance (§13).** No threshold introduced or moved. Both
rules were fixed before the post-amendment production re-run. A49.1's
measured effect is disclosed above precisely because it favours the
namesake case; A49.2's effect on the leaderboard is reported in `results.md`
as a lens comparison, not used to choose between denominators. The
denominator choice rests on the observed-vs-modelled argument stated above,
which is independent of the resulting ranking. Tests:
`tests/test_position_lock_a49.py` (24); suite 351 → 375.

---

**A50 (defect found + fixed 2026-08-06) — Hyphen/apostrophe names are
multi-token keys and are matched as adjacent token SEQUENCES. Corrects a
silent false-zero defect in the A23 rule-3 matcher.**

**The defect.** A23 rule 3 folds corpus text with `match_fold`, which maps
every non-alphanumeric character to a space: "Nugent-Hopkins" in a post
becomes the two tokens `nugent hopkins`. The player-side key, however, was
built with `fold`, which only strips accents and case and therefore
*retains* the separator: `nugent-hopkins`. The matcher then tested
`token_set & surname_set`. A key containing a hyphen or apostrophe can never
equal any token produced by `match_fold`, so those players matched nothing —
and were written out with `reddit_status = "ok"` and
`reddit_mentions_12mo = 0`.

This is worse than exclusion. A `0` under status `ok` is consumed by §4 as a
**measured zero** and enters the composite at the full A12 Reddit weight
(0.27 mentions + 0.17 upvotes) instead of being NULL'd and renormalized.
Ten players carried a fabricated zero, including Ryan O'Reilly, Ryan
Nugent-Hopkins and Oliver Ekman-Larsson — none of whom are plausibly
zero-mention NHL players. Every `ok` row reporting zero mentions in the
pre-fix file was a separator name, except one genuine case (below).

**The fix.** Name keys are built with `name_key = match_fold`, putting both
sides of the comparison on the same fold. A key containing a space is
MULTI-TOKEN and is matched with `contains_sequence` — the tokens must appear
adjacent and in order. Single-token keys are byte-for-byte what `fold`
produced before A50 and take the unchanged set-intersection fast path. The
same correction applies to FIRST names, which had the identical defect
("Jean-Gabriel", "K'Andre", "J.T." could never satisfy the A15 first-name
evidence check), and to the A42 document-frequency pre-pass.

**Scope of change, measured.** 14 of 771 rows changed; **757 are
bit-identical on every column** (mentions, upvotes, unique authors,
ambiguous, guard-filtered, status).

| Row | Before → after (mentions) | Cause |
|---|---|---|
| Ryan O'Reilly | 0 → 431 | surname key |
| Ryan Nugent-Hopkins | 0 → 179 | surname key |
| Oliver Ekman-Larsson | 0 → 162 | surname key |
| Charle-Edouard D'Astous | 0 → 118 | surname key |
| Drew O'Connor | 0 → 107 | surname key |
| Jacob Bernard-Docker | 0 → 77 | surname key |
| Liam O'Brien | 0 → 65 | surname key |
| Logan O'Connor | 0 → 40 | surname key |
| Nicolas Aube-Kubel | 0 → 25 | surname key |
| J.T. Miller | 186 → 316 | first-name key (A15 re-attribution) |
| K'Andre Miller | 181 → 198 | first-name key (A15 re-attribution) |
| Colin Miller | 124 → 121 | first-name key (A15 re-attribution) |
| Pierre-Olivier Joseph | 33 → 41 | first-name key (A15 re-attribution) |
| Mathieu Joseph | 51 → 50 | first-name key (A15 re-attribution) |

The last five are second-order: `J.T.`, `K'Andre` and `Pierre-Olivier` are
first names that also failed to match, so the three Millers and two Josephs
were being disambiguated with the A15 evidence check partially blind.
Correcting it re-attributes submissions **between** members of those surname
groups; the group totals move, not just one row.

**One genuine zero remains.** Maksymilian Szuber (UTA) is `ok` with 0
mentions, 0 ambiguous, 0 guard-filtered — a fringe player with no separator
in his name. A true zero is a legitimate measurement and is NOT converted to
`unmeasurable`; the A48 Defect-5 ladder applies only when the corpus was
read and candidates existed but none survived. The test pins this survivor
**by name**, so any NEW name appearing as an `ok` zero fails the suite.

**Why this is a defect fix and not a design change.** §3.3-3.4 and A23 rule 3
pre-register matching on the player's **surname as a whole token** in the
folded text. A hyphenated surname *is* that surname; the implementation
simply failed to construct a key that could ever match, because the two
sides used different folds. No pre-registered rule, threshold, or hypothesis
is altered here — the rule is now implemented as written. Per §13 this is
recorded as an amendment anyway because it changes shipped numbers.

**Anti-tuning compliance (§13).** No threshold introduced or moved. The fix
was specified from the mechanism (two folds disagreeing), not selected by
comparing outcomes; the affected rows were identified before the fix was
written, by asking which `ok` rows reported zero. Direction of the change
was not a criterion — it was accepted before the re-run that any row could
move either way, and five rows did move down or sideways. Downstream:
`reddit_detail.csv` 161,947 → 163,302 rows; `reddit_detail_allsubs.csv`
224,510 → 226,535. `oaq_pilot.csv`, `results.md`, `results.json`
regenerated. Tests: `tests/test_reddit_multitoken_a50.py` (32); suite
375 → 407.

**Limits of claim.** The matcher still requires the separator to be rendered
as *some* non-alphanumeric character. A post writing "NugentHopkins" as one
word, or "Nuge" as a nickname, is still not counted — nickname recall was
never claimed and is unchanged by A50.

---

## A51 — Three-season attention window and pool expansion (2026-08-07)

**This is a genuine design change, not a defect fix.** It moves a
pre-registered window (A11/A14) and a pre-registered pool definition (A10).
The superseded rules are NOT edited in place; they stand as written above and
this amendment supersedes them going forward.

**What changed.**

| | Before (A10/A11/A14) | After (A51) |
|---|---|---|
| Window start | 2025-04-18 | **2023-10-10** (2023-24 NHL regular-season opener) |
| Window end | 2026-04-17 | 2026-04-17 — **UNCHANGED** |
| Window length | 365 days | **921 days** |
| Seasons covered (A22) | 20242025, 20252026 | **20232024, 20242025, 20252026** |
| Player pool | 771 | **973** (+202) |
| Skill/on-ice rows | 1 per player | 1 per player **per season** |

Because only the START moved, the A14 regular-season-end boundary — the rule
that keeps the 2026 playoff-selection confound out of the attention measure —
is untouched, and every observation collected under the 365-day window remains
inside the new window and remains valid. The Reddit corpus is gap-filled, not
re-pulled, for the same reason.

**Pool rule (supersedes A10's fixed 774/771).** A player is in the pool if he
was already in the 771, OR he recorded **≥ 20 games played in at least one of
the three window seasons** (MoneyPuck season-summary, `situation == 'all'`).
The threshold was fixed by the owner before the union was computed and was not
varied. Departed players now qualify: 94 last seen in 2023-24, 75 in 2024-25,
33 in 2025-26. Existing pool members are retained regardless of games played
(54 of the 771 do not meet the ≥20 GP bar in any season) so that no previously
published row silently disappears.

**Sub scope (extends A22/A23 rule 2).** The window now spans all THREE
identities of one franchise: Arizona Coyotes (2023-24, r/Coyotes), Utah Hockey
Club (2024-25, r/UtahHockey), Utah Mammoth (2025-26, r/utahmammoth). 36 → 37
subs. FIVE coordinated changes were required across three modules; omitting
any one silently truncates that fanbase's attention rather than failing
loudly. Two of the five were caught only after a run had already produced
wrong numbers (items 4-5 below), which is recorded here rather than quietly
corrected:

1. **Corpus scope** — r/Coyotes added to `fetch_reddit_corpus.ALL_SUBS`
   (3,398 posts pulled, 2023-10-10 .. 2026-04-17).
2. **Predecessor mapping** — A22's `PREDECESSOR_SUB` was single-valued
   (`{"UTA": "UtahHockey"}`) and is now list-valued
   (`{"UTA": ["UtahHockey", "Coyotes"]}`), so both predecessors enter the
   counting set and `sub_team_code` attributes both back to UTA.
3. **Franchise-name alias** — the NHL landing endpoint returns
   "Arizona Coyotes" for 2023-24 seasons, a name absent from `teams.csv`.
   Without an explicit alias to UTA those rosters resolve to no team code and
   r/Coyotes would never enter any player's counting set even once pulled.
   This is the failure mode that would have been hardest to notice: the data
   would be on disk and simply never counted.
4. **Market activity** — `build_market_activity.SUB_ALIASES` folded only
   `utahhockey → utahmammoth`. The first run after A51 therefore reported UTA
   at **665** in-window submissions against a true **4,063** — an 84%
   understatement that propagates through `market_z` into every published
   OAQ, not just Utah's. Now `{"utahhockey": "utahmammoth", "coyotes":
   "utahmammoth"}`; re-run confirms 4,063, `activity_quality=ok`.
5. **Affiliation** — `affiliation.EXTRA_SUB_ALIASES` had the same single-alias
   gap, and the franchise-name map lacked `"Coyotes": "UTA"`. Every
   Arizona-era mention would have been scored as neither own-fanbase nor
   rival, silently deflating `own_share` and `rival_reach` for the franchise's
   players. The affiliation run in flight was killed and restarted after the
   fix rather than allowed to finish and write wrong numbers.

Verified: `counting_subs({"UTA"})` → `['hockey', 'utahmammoth', 'UtahHockey',
'Coyotes']`; `sub_team_code` and `build_venue_map` map all three subs → UTA;
league subs → None; `market_activity.csv` UTA = 4,063.

**Generalisable lesson for §13.** A single franchise-identity change was
encoded independently in five places across three modules. Widening a window
across a rename does not fail loudly — it produces plausible, wrong,
*smaller* numbers. Any future window change must re-audit every
franchise-identity mapping, not just the corpus scope.

**Why the window moved.** The single-season panel yields 142 usable movers.
That is too thin for the two-way (player × team) attention decomposition the
project is moving toward — limited-mobility bias at that n inflates the
residual variance and biases the player/market covariance term — and it
supports no cross-season replication.

**Discovery/confirmation split — the reason this amendment matters most.**
Exploratory analyses were run against the 365-day data on 2026-08-07 BEFORE
this amendment was written (mover event study, the wiki-vs-followers
contrast, the attention/production age profile, a crude two-way
decomposition). Those results are hereby designated **EXPLORATORY** and the
2025-26 season is a **burned discovery sample**. No result derived from it may
be reported as confirmatory. The 2023-24 and 2024-25 seasons added here are
the **confirmation sample**; hypotheses and thresholds for the confirmatory
tests must be registered as a further numbered amendment BEFORE those seasons
are analysed. Reporting a discovery-sample finding as confirmatory would be
the exact failure §13 exists to prevent.

**Anti-tuning compliance (§13).** No threshold was moved to change an outcome.
The window start is a calendar fact (the 2023-24 opener), not a fitted choice;
the ≥20 GP pool bar was set by the owner in advance; the end day is unchanged.
No composite weight (A12) is altered. Direction of effect on any published
number was not a selection criterion and is not yet known — every downstream
number is expected to change and none has been inspected at the time of
writing.

**Downstream reconciliation still owed (NOT yet done).**
`compute_oaq.py` assumes one row per player in `raw/nhl_skill.csv` and
`raw/nhl_onice.csv`; both are now one row per player-season and it must filter
`season == '20252026'` before its next run or it will silently triple-count.
`trends_12mo`, `wiki_12mo`, `wiki_intl_12mo` and the Reddit counts are now
921-day totals, so the A12 composite and every published OAQ, CI and results
artifact are stale until regenerated. Test expectations keyed to 365/771 will
fail. These are recorded here as owed work, not as completed work.

**Limits of claim.** The expanded pool is built from players who met a games
threshold in-window, so it still under-covers players whose careers ended
before 2023-24 or who never reached 20 games; the panel is not a census of the
league. Attention series for departed players continue past their last NHL
game and are not truncated at departure.

---

## A52 — Three-season panel completion: source repairs and the season split (2026-08-08)

A51 widened the window; this amendment records what finishing that widening
actually required. Every item below is a **collection or shape** change. None
of them touches a hypothesis, a weight, a threshold or a peer rule, and no
result reported anywhere was used to choose any value here.

### 1. Source repairs

**Cap hits — the parser only ever asked for one season.** `find_2025_26_caphit`
hard-coded `"2025-26"`, so the 110 players returning "no 2025-26 detail" were
never missing from the source: CapWages keeps a player's full contract history
and the code simply never requested the other years. Generalised to
`find_caphit(player, season)` over `PANEL_SEASONS`.

**Buyout guard (new rule).** CapWages lists a bought-out or terminated
contract's **full original term**, not the years honoured. Zach Parise's 13-year
Minnesota deal still shows $7,538,462 through 2024-25 although he was bought out
in 2021 and retired after 2023-24 — so asking for his 2024-25 cap hit returns a
real-looking $7.5M for a season he did not play. A cap hit is now recorded only
for a season in which the player has `games_played > 0` in `nhl_skill.csv`;
otherwise the row is NULL with note `did not play this season`. This fired 193
times. It is a rule about **contract validity**, not about fit, and was written
before seeing which players it would remove.

**Slug overrides (15 added).** Two mechanical failures, both keyed by
`nhl_player_id` so the override is unambiguous: (a) CapWages slugs the name a
player goes by, which is not the NHL API's legal name, and it cuts both
directions (`Zachary Aston-Reese` → `zach-`, but `Alex Nylander` →
`alexander-`); no spelling rule generates these. (b) A shared name resolves to
whoever CapWages indexed first — `elias-pettersson` is the forward (8480012),
the defenceman (8483678) is `elias-pettersson-1`. Both members of the colliding
pair are pinned. The pre-existing `nhlId` equality check backstops all of it.

Result: real gaps (a player with `games_played > 0` and no cap hit) fell from
41 to 7. Coverage 99.51 / 99.76 / 99.88 % across the three seasons. The 7
residual are genuine — Dmitri Simashev has no CapWages page at all (KHL through
2024-25; four spellings probed), and six players have no contract row for a
season in which they played NHL games.

**Team outcomes — redirect series lost to network contention.** The A51 run
left CHI, NAS, NJ, NYI, WAS and WPG with `redirect_share=0.0000` and **zero**
redirect titles, including three of the four teams `robust_title_views` was
written to rescue. The recovery ladder was not at fault and the canonical
totals were correct; every *redirect* fetch failed, and `combine_view_totals`
drops a failed series (`None`) exactly as it drops a genuinely empty one (`0`),
so total failure rendered as "this team has no redirect traffic". Cause was
three scrapers hitting the Wikimedia edge concurrently — the identical calls
succeeded on a quiet link minutes later, recovering CHI from 1,411,476 to
1,491,100 (share 0.0534).

Two changes. The second-pass retry trigger, previously fired only by a missing
*canonical* series, now also fires on `redirect_titles == ""`; every one of the
32 articles has at least 7 live redirects (minimum observed: NSH at 7), so an
empty set is a failure signature and never a legitimate state. And a `--teams`
flag repairs named rows in place. The widened trigger earned itself on its
first run: WAS and WPG failed again on first pass and were rescued by it. Final
state 32/32, ex-UTA redirect share 0.0065–0.0534 (median 0.0124).

**Market proxy — UTA arena figure was the wrong sport.** `arena_attendance`
for Utah carried the Delta Center's **basketball** capacity (16,044) rather
than its hockey configuration (9,403 in 2024-25). Corrected, and real
per-season attendance columns added from `game_attendance.csv`.

**Movers.** A38 derived moves across one season boundary from `seasonTotals`,
which carries no dates, and sent all 192 rows to manual research. A51/A52
derives spells from the per-season **game log** (`gameTypeId 2`) instead: a move
is two consecutive spells with different franchises, bracketed to [last game
with old team, first game with new team]. In-season moves are dated at the
bracket midpoint (`status=dated_gamelog_bracket`); off-season moves straddle a
boundary, are not derivable from appearances, and keep `needs_date`. The 192
hand-researched rows are inherited **verbatim** — matched on
`(nhl_player_id, old_team, new_team)` — and were never regenerated. 565 rows,
405 movers, 0 game-log failures, 192 researched dates preserved.

**Usable-event rule (new).** Bracket width is recorded per row. Median is 6
days but p90 is 45 and max 112 — a player injured around his trade gets a wide
bracket whose midpoint can be weeks off. Event-study work must gate on
`bracket_days <= 7` (107 rows) plus the 192 exact researched dates = **299
usable events**; wide-bracket rows are unusable, not merely noisy, and are to be
dropped rather than down-weighted.

### 2. The season split (`split_seasons.py` → `raw/attention_by_season.csv`)

A51 left the dataset in two incompatible shapes: NHL-side files at one row per
player-season, attention files at one row per player for the whole window.
Nothing joined on `(player_id, season)`. `split_seasons.py` writes the missing
side — 2,919 rows, one per player per season, keys **identical** to
`nhl_skill.csv`, `nhl_onice.csv` and `cap_hits.csv` (verified set-equal; all
four panels now join 1:1).

Season bounds are the **regular season only**, read from
`game_attendance.csv` rather than hard-coded: 2023-10-10→2024-04-18,
2024-10-04→2025-04-17, 2025-10-07→2026-04-16. Off-season and playoff days fall
outside every season and are dropped — they belong to no season's on-ice
production, and assigning them would either double-count or require an
arbitrary rule. 68.8 % of window pageviews fall inside a regular season.

**Sliceable exactly:** `wiki_en`, `wiki_intl` (both stored as 921-day daily
vectors) and the Reddit counts (`reddit_detail.csv` joined to corpus
`created_utc`; **0 rows unmatched**).

**NOT sliceable — carried forward unchanged and flagged
`trends_season_invariant=1`:** Google Trends was fetched as one window-level
index per player and the weekly series was not retained; re-fetching per season
would re-scale every value against a different window maximum, making the three
seasons incomparable both to each other and to the existing column. Follower
counts are likewise a stock observed once, not a flow.

**Rule.** A season-invariant column repeated across three rows is **not evidence
about that season**. Any model consuming this file must drop those columns or
absorb them in a player-level term. Treating them as season-varying attributes a
career-level constant to a single year. The flag column exists so that mistake
must be made deliberately.

### 3. Owed downstream work (recorded as owed, not done)

`compute_oaq.py` still assumes one row per player and will **triple-count** when
handed the new panels; `oaq_pilot.csv` and `results.json` remain stale. How the
three seasons combine (pooled, per-season, or panel) is an open **design**
decision and is deliberately not settled here — settling it after seeing
season-level results would be exactly the tuning this file exists to prevent.
15 test fixtures keyed to A51 constants still fail.

### 4. Limits of claim

The repairs above change **coverage**, not measurement: no value that was
already present was altered (verified by diff — 0 regressions, 0 changed values,
34 newly filled on the cap-hit re-run; 26 of 32 team rows byte-identical). The
per-season attention panel is a re-aggregation of the same daily series, not a
new collection, and inherits every A51 limit including that attention series for
departed players are not truncated at departure.

**Generalizable lesson, second instance.** A51 recorded that widening a window
across a rename produces plausible, wrong, smaller numbers rather than an error.
A52 adds the same failure from a different cause: **parallelism introduced for
throughput silently corrupted a third job's data, and it rendered as zeros
rather than as failures.** In both cases the defect was invisible in the output
and only surfaced against an expected distribution. Any aggregate that can be
computed from a partial fetch needs a completeness signature — here, "every NHL
article has ≥7 redirects" — checked independently of the fetch's own success.


**A53 (decided 2026-08-31, locked 2026-08-31 BEFORE the lens compute) — Two
alternative peer vectors reported as ROBUSTNESS LENSES. §6/A13 peer features,
K, distance, and the headline are UNCHANGED.**

> **Status: this is not a vector swap.** The §6/A13 primary
> `(age, PPG, TOI/G, cf_pct, xgf_pct, ozs_pct)` remains the locked peer vector
> and the sole basis of every headline number. A53 adds two *additional*
> peer constructions, computed and reported alongside it, to answer two
> distinct challenges to the OAQ residual. Neither may become the headline
> without a further amendment, and that amendment could not be honest —
> `value_propositions.md` already records the v2 result, so any post-hoc swap
> is selection on a seen outcome. A53 exists so the alternatives are on the
> record as *evidence*, not as a replacement.
>
> **Motivation.** §6/A13's vector controls for age, scoring rate, ice time, and
> 5v5 on-ice share. Two objections survive it. (1) *"Your skill match is too
> coarse — PPG hides shooters vs. playmakers, and it ignores power-play
> deployment, which drives both points and coverage."* (2) *"Your residual is
> just accumulated fame. Attention is a stock; every one of your controls is a
> single-season flow."* Lens A answers (1); Lens B answers (2). They are
> reported separately and never merged, because they test different claims.
>
> **Lens A — production detail (12 features).** The §6/A13 six plus six. This
> reproduces, as committed code, the "peer-stack v2" construction whose result
> is recorded in `value_propositions.md` Part 1; that run existed only in
> memory and re-implemented A49 at 87.1% fidelity to stored `peer_player_ids`.
> Fixing that reproducibility gap is half the point of Lens A.
>
> | Feature | Definition | Source |
> |---|---|---|
> | `pp_toi_per_game` | `icetime`(5on4) ÷ 60 ÷ `games_played`(all) | MoneyPuck |
> | `ixg_per60` | `I_F_xGoals`(5on5) ÷ (`icetime`(5on5) ÷ 3600) | MoneyPuck |
> | `shots_per60` | `I_F_shotsOnGoal`(5on5) ÷ (`icetime`(5on5) ÷ 3600) | MoneyPuck |
> | `points_per60` | `I_F_points`(5on5) ÷ (`icetime`(5on5) ÷ 3600) | MoneyPuck |
> | `goal_share` | `I_F_goals`(all) ÷ `I_F_points`(all); points = 0 → NULL | MoneyPuck |
> | `games_played` | 2025-26 NHL regular season GP | `raw/nhl_skill.csv` |
>
> Rate denominators are 5v5 icetime, preserving A13's locked-situation rule;
> `pp_toi_per_game` is the one deliberate exception, since power-play
> deployment is the specific control the objection names and cannot be
> measured at 5v5. The GP denominator is taken from the `situation == 'all'`
> row so it is stable for players with near-zero special-teams ice.
>
> **Lens B — attention stock (10 features).** The §6/A13 six plus four. Every
> added feature is a career quantity from the **same** `api-web.nhle.com`
> `player/{id}/landing` response §6 already consumes — no new source, no new
> endpoint, no new licence question.
>
> | Feature | Definition |
> |---|---|
> | `career_gp_log` | `log1p(careerTotals.regularSeason.gamesPlayed)` |
> | `career_points_log` | `log1p(careerTotals.regularSeason.points)` |
> | `nhl_seasons` | count of distinct `seasonTotals` rows with `leagueAbbrev == "NHL"` and `gameTypeId == 2` |
> | `draft_overall_log` | `log1p(draftDetails.overallPick)`; **undrafted → 225** |
>
> `log1p` is fixed in advance on the reasoning that fame is concave in each
> quantity — the #1 pick differs from the #10 far more than the #200 from the
> #210, and the 1,200-point career from the 1,100-point career barely at all.
> **Undrafted = 225** is one past the final pick of a seven-round, 32-team
> draft: undrafted players are treated as maximally un-hyped at entry, which
> is the construct being controlled. Career totals include the 2025-26 season
> in progress; this is production, not attention, so it carries no leakage
> into the dependent variable.
>
> **Shared construction rules, fixed in advance.**
> - Imputation: unchanged from §6/A13 — group mean, then overall mean, applied
>   before standardization. Applies identically to every added feature.
> - Standardization: unchanged (within-group, ddof = 1).
> - Candidate filter: unchanged — A49.1 position class C / W / D.
> - K = 10: unchanged.
> - **Covariance shrinkage δ = 0.10**, `Σ̂ = (1−δ)·Σ + δ·(tr Σ / p)·I`, applied
>   to Lens A and Lens B. At p = 12 and p = 10 with collinear career and rate
>   features, the raw within-class covariance is not reliably conditioned and
>   `pinv` silently amplifies the smallest eigenvalue. δ = 0.10 matches the v2
>   construction being reproduced and is not tuned.
> - To keep the estimator from confounding the feature set, the **primary six
>   are also run under δ = 0.10**. Four peer builds are therefore reported:
>   `primary-pinv` (the shipped headline, reference), `primary-shrunk`,
>   `lensA-shrunk`, `lensB-shrunk`. The primary-pinv → primary-shrunk delta is
>   the estimator effect; the rest is the feature effect.
>
> **Comparison metrics, fixed in advance** (the v2 set, so the numbers are
> directly comparable to the ledger row), reported for every lens whatever
> they show: mean peer-set overlap with the primary (|∩| / K); share of
> players losing ≥ half their peers; Pearson and Spearman of `OAQ_portable`
> against the primary; top-25 and **bottom-25** retention on the headline
> Marchand Index; largest absolute rank move within the primary top-25; and
> the same for the full pool. The bottom tail is added to the v2 set because
> the writeup claims *both* tails and only the top was measured before.
>
> **Anti-tuning compliance (§13):** A53 changes nothing that produces a
> headline number — §4/A12 weights, §6/A13 peer features, §7/A5 λ, the
> A4/A8/A24/A49.2 denominators, the §2/A10/A41 pool, the A11/A14 windows, and
> the §9/A6 validation floors are all unchanged. Both lenses, all four peer
> builds, and every metric above are defined here before the comparison is
> computed, and all are reported regardless of outcome; no lens may be
> dropped for being unflattering. Lens A's feature list is fixed by
> reproducing an already-recorded construction rather than by choosing
> features now. Lens B's transforms and the undrafted sentinel are fixed
> above, before any career column has been joined to any attention column.
> The known risk this amendment does **not** dissolve is that v2's outcome is
> already known; A53's defence is that the primary is untouched and the lens
> is reported as evidence, never promoted.
**A55 (decided 2026-08-31, locked 2026-08-31 BEFORE the estimation is run) — λ
becomes an ESTIMATED quantity. The §7/A5 market damping constant is fit from
within-player club changes instead of assumed at the max-entropy midpoint.**

> **What is wrong with the current λ.** A5 set λ = 0.5 as the midpoint between
> bounds 0 and 1 because the true pass-through was unknown. That was the honest
> choice with no data; it is no longer the honest choice with data. λ is the
> only headline parameter in this project that was never measured, and it is
> the one that has drawn the most scrutiny.
>
> **The identification.** A club change is the natural experiment: the same
> player, the same season-to-season production controls, a different market. If
> market size supplies attention, a player moving to a larger market gains
> attention beyond what his own change in production explains, and a player
> moving to a smaller market loses it. λ is exactly that pass-through, so it can
> be read off the coefficient rather than assumed.
>
> **Correcting the record on the prior evidence, before it is used.** Three
> earlier probes reported this term as null (Δlog metro population b = −0.021,
> t = −0.37; Δlog team subreddit b = +0.080, t = +1.09; the λ portability
> probe), and A54 recorded a fourth. **Two of those readings are now known to
> be defective, and A54's is withdrawn** — see the correction appended to A54.
> The A54 player-level test correlated a 32-valued club variable against 682
> players, which dilutes a between-club signal into within-club variance; at the
> club unit the same quantity reads ρ = +0.341 (p = 0.056). The two trade probes
> each used a **single** market component — metro population and team subreddit —
> and A54 established that population alone carries ρ = +0.055 at club level,
> i.e. those probes instrumented the market with its weakest available measure.
> A55 does not claim the earlier probes were wrong to report what they found; it
> claims they were underpowered instruments for the quantity, and it replaces
> them with a directly specified estimator.
>
> **Estimator, fixed here in full before it is run.**
>
> - **Sample.** Every skater in the §2 pool with ≥ 20 NHL regular-season games
>   in *both* seasons of a transition and a different club in each. Two
>   transitions are pooled: 2023-24 → 2024-25 and 2024-25 → 2025-26. Club per
>   season is the club of maximum ice time in the MoneyPuck season file
>   (`situation == "all"`), which is a played-for club, not a roster snapshot.
> - **Outcome.** Δ of the §4/A12 engagement composite, each season's components
>   standardized **within that season's pool** before weighting, so the outcome
>   is in league-standard-deviation units — the same units `market_z` carries and
>   therefore the same units λ multiplies. `trends_12mo` is **excluded** from
>   this composite: the A52 panel stores a season-invariant Trends value, so it
>   contributes exactly zero to any Δ. The remaining four weights (wiki_en 0.29,
>   wiki_intl 0.11, reddit_mentions 0.27, reddit_upvotes 0.17) are renormalized
>   to sum to 1 under the §4 sentinel rule.
> - **Regressors.** Δ`market_z` (A54 composite), Δ PPG, Δ TOI/G, Δ destination
>   club points percentage, and a transition indicator. Points percentage is
>   computed from `raw/game_attendance.csv` regular-season results (2 points a
>   win, 1 an overtime or shootout loss) so that moving to a contender is not
>   credited to the market.
> - **λ̂** is the coefficient on Δ`market_z`. Its 95 % interval is a
>   **player-level bootstrap, 2,000 resamples, seed 20260526**, matching §10's
>   resampling convention.
>
> **Adoption rule, fixed in advance and binding whatever the number turns out
> to be.** λ is bounded on [0, 1] by construction (A5), so:
>
> 1. If λ̂ > 0 and its 95 % interval **excludes 0**, the primary λ becomes
>    `clip(λ̂, 0, 1)`.
> 2. Otherwise the primary λ **remains 0.5**, because a locked value should not
>    be traded for an estimate the data cannot distinguish from no effect.
>
> In **both** cases λ̂ and its interval are published, λ = 0.5 is retained as the
> pre-registered comparison, and the existing {0, 0.25, 0.5, 0.75, 1.0}
> sensitivity ladder is reported unchanged. No third path is available, and the
> rule is not conditioned on where any player lands.
>
> **Disclosed weaknesses.** (a) Club changes are not random: deadline moves
> travel with contention and demotions travel with decline. Δ PPG, Δ TOI/G and Δ
> destination points percentage are the controls, and they are imperfect —
> a trade is itself a signal about a player. (b) A move generates its own
> attention spike independent of destination; pooled, that lands in the
> intercept, but it biases λ̂ upward to the extent that transaction coverage
> scales with destination market size. (c) The mover subsample is a few hundred
> at most, so the interval will be wide and may well contain 0.5 — in which case
> this amendment vindicates the existing value rather than replacing it, which
> is an acceptable outcome. (d) λ̂ is estimated on a subsample of the same pool
> the headline is computed over; the circularity is one scalar fit on club
> changers and applied to everyone, and is disclosed rather than resolved.
>
> **Anti-tuning compliance (§13).** The sample rule, outcome construction,
> regressor list, interval method, seed, and the adoption rule above are all
> fixed in this entry before the estimator is run, and the adoption rule keys on
> the interval excluding zero — never on any player's resulting rank or on the
> shape of the leaderboard. Both outcomes are published. The §4/A12 composite
> weights, §6/A13 peer features, the A54 market composite, the A4/A8/A24/A49.2
> denominators, the §2/A10/A41 pool, the A11/A14 windows, the A34 display rule,
> and all §9/A6 validation floors are **unchanged**; only the value of λ can
> move, and only in the direction the pre-specified rule permits. Every pre-A55
> published number remains in git history per §13.

**A56 (decided 2026-08-31, after the A55/log-scale estimates were seen — stated
plainly) — λ set to 0. The market correction is REMOVED from the published
metric. A55's adoption rule is superseded as defective.**

> **The decision.** `LAMBDA_BIGMARKET` goes from 0.5 to **0**. `OAQ_portable`
> therefore becomes identical to `OAQ_observed`, and the published Marchand
> Index is the peer residual with no market term. Market size is not corrected
> for, and the page says so rather than implying the question does not exist.
>
> **Why, in one line:** a market effect on player attention is almost certainly
> real, and these three sources cannot measure it well enough to subtract.
>
> **The evidence, all of it, including what disagrees.** The pass-through was
> estimated on club changes (same player, before and after, controlling for
> change in PPG, TOI/G, destination points percentage, and transition;
> n = 170 movers over two transitions):
>
> | Source | A12 weight | b | 95 % CI | t |
> |---|---|---|---|---|
> | en-Wikipedia | 0.29 | **+0.147** | [+0.082, +0.211] | +4.65 |
> | intl-Wikipedia | 0.11 | +0.036 | [−0.012, +0.083] | +1.42 |
> | **Reddit mentions** | 0.27 | **−0.082** | **[−0.161, −0.007]** | **−2.25** |
> | Reddit upvotes | 0.17 | +0.071 | [−0.033, +0.180] | +1.37 |
> | **weighted average** | — | **+0.043** | **[−0.021, +0.108]** | **+1.40** |
>
> Two components are individually significant **in opposite directions**. The
> weighted average is +4.4 % per SD of market with an interval containing zero.
> A free-club-effects fit that assumes no market index at all correlates with
> the index at only Spearman +0.322 (p = 0.125), and its largest estimated
> effects (VAN +0.95 at index +0.47; WPG +0.71 at index −0.95) do not track it.
> Two estimators on two different scales agree on the magnitude: A55's
> composite-unit estimate is −0.008, the log-scale weighted average is +0.043.
> Both are ≈ 0, and neither is ≈ 0.5.
>
> **Why not λ = +0.043 rather than 0.** A point estimate whose interval spans
> zero, assembled from components that disagree in sign, is not a measurement.
> Applying it would import the sign conflict into every published figure while
> changing almost nothing. Zero is the honest summary of "we could not measure
> this."
>
> **A55's adoption rule is superseded.** It read: adopt λ̂ only if its interval
> excludes zero, otherwise retain 0.5. Applied here that yields *"the effect is
> indistinguishable from zero, therefore keep subtracting half a standard
> deviation"* — which is perverse, and the defect is in the rule, not in the
> estimate. The replacement is the obvious one: an unmeasurable correction is
> not applied. Recorded rather than quietly dropped, because the rule was
> pre-registered and got it wrong.
>
> **What is NOT claimed.** This is not a finding that market size does not
> affect attention. Wikipedia lookups rise materially with market size
> (+15.8 % per SD, interval excluding zero) and that is unlikely to be noise.
> The claim is narrower and about instruments: **en-Wikipedia and Reddit
> mentions respond to market size with opposite signs**, so a composite built
> from both cannot represent the effect, and no defensible single correction can
> be derived from them. That divergence replicates, in an unrelated setting, the
> Wikipedia/Reddit sign flip already recorded for international tournaments —
> the same two sources disagreeing about the same players for a second reason.
>
> **Consequences.** Market size is removed from the published dashboard as a
> correction and retained only as a stated limitation: real, uncontrolled, and
> unmeasurable with the present sources. `market_z` continues to be computed and
> stored, and the A54 reweighting stands — it is what made the pass-through
> estimable at all, and it is what the free-club-effects check was run against.
> The λ sensitivity ladder now spans a term fixed at zero, so it is retained in
> the data as an audit lens and dropped from published panels. Every pre-A56
> number remains in git history per §13.

**A57 (decided 2026-08-31) — §4 composite is variance-stabilized before
standardizing. Components are `log1p`-transformed, THEN z-scored, THEN weighted.
A35 clause 2's prohibition on log-scale headline numbers is EXPLICITLY
OVERRIDDEN. Weights, components, peers, pool, and denominators are unchanged.**

> **The defect.** §4 z-scores each component's **raw counts**. Those counts are
> extremely right-skewed — en-Wikipedia has skew **6.9**, median 90,616 views
> against a maximum of 4,236,819 — and a z-score does not fix skew, it only
> recentres it. The resulting composite has skew **6.10**, and
>
> > **the bottom 90 % of players occupy 11.5 % of the composite's range.**
>
> For nine players in ten the metric has almost no resolution. Everything
> downstream inherits it: a peer mean over ten players is dragged by any one
> outlier in the set, the cap-hit ratio is computed on a near-degenerate
> numerator, and bootstrap intervals are wide and asymmetric for most of the
> pool.
>
> **This is the probable cause of a limitation already on the record.**
> `value_propositions.md` reports peer-stack v2 moving Pastrnak 664 → 81 and
> Eichel 164 → 689 while the metric itself held at Pearson 0.955, and the
> project consequently claims "the tails, not the ordering". A scale on which
> 90 % of players are packed into a tenth of the range produces exactly that
> signature: the tails are stable because they are far apart, and the middle
> reshuffles because it is not spread out at all. A57 tests whether that
> limitation is a property of the league or an artifact of the scale.
>
> **Corrected construction.** For each §4/A12 component, in this order:
>
> ```
> z_c = zscore( log1p( max(x_c, 0) ) )          # was zscore( x_c )
> engagement_raw = sum_c  w_c * z_c              # weights unchanged
> ```
>
> Standardization now happens **after** the transform rather than on raw counts,
> so the composite is a standardized measure of proportional attention instead
> of a standardized measure of absolute counts. Nothing else moves: the §4/A12
> weights, the sentinel renormalization, §6/A13 peers, the A54 market composite,
> λ = 0 (A56), the A4/A8/A24/A49.2 denominators, the §2/A10/A41 pool, the
> A11/A14 windows, and the A34 display rule are all unchanged.
>
> The identical transform is applied inside `bootstrap_player_cis`, so resampled
> draws are stabilized the same way the point estimate is. Because `log1p` is a
> fixed function with no fitted parameter, there is nothing to re-estimate per
> draw and no leakage between draws.
>
> **Why `log1p`, chosen on a distributional criterion.** The candidate set was
> fixed as {raw, sqrt, log1p, Yeo-Johnson (ML-fit), rank-inverse-normal} and the
> selection criterion as **minimum absolute skew of the resulting composite** —
> a property of the marginal distribution, computed without reference to any
> player's rank or to any leaderboard:
>
> | transform | \|skew\| | bottom 90 % of range |
> |---|---|---|
> | raw (current §4) | 6.10 | 11.5 % |
> | sqrt | 2.38 | 31.0 % |
> | **log1p** | **0.30** | **62.3 %** |
> | Yeo-Johnson | 0.43 | 61.6 % |
> | rank-inverse-normal | 0.12 | 66.7 % |
>
> Rank-inverse-normal is **excluded a priori, not on its score**: it forces an
> exactly normal marginal by construction, so a skew criterion cannot
> discriminate it from any other rank-preserving map, and it discards magnitude
> entirely — two players a factor of fifty apart become adjacent ranks. Among
> genuine variance-stabilizing transforms, `log1p` minimizes the criterion, and
> it carries no fitted parameter, so there is no λ to estimate, none to leak
> into the bootstrap, and nothing that could be tuned.
>
> **A35 clause 2 is overridden.** That clause reads, verbatim and
> poster-binding: *"No log-lens number appears in the headline, abstract, or
> leaderboard panels under any outcome."* It was written when the log scale was
> a robustness lens (A17) sitting beside a raw-scale headline, and its purpose
> was to stop a second scale being quietly promoted because it read better. A57
> is not that: the raw scale is being retired because it has a demonstrated
> distributional defect, on a criterion computed without looking at any result.
> The clause is overridden explicitly and in full rather than worked around, and
> A17's raw-scale composite is retained as the audit lens, inverting the two.
>
> **Pre-declared consequence, and the test this amendment can fail.** The whole
> point is that mid-pack ranks may become defensible. That claim is falsifiable
> and is tested by re-running `diagnostics/peer_vector_lenses.py`: if peer-set
> churn still reorders the middle of the table under an alternative peer vector,
> the scale was not the cause, the "tails only" limitation stands unchanged, and
> A57 is reported as a failed repair that nonetheless fixed a real distributional
> defect. **The stability result is reported whichever way it comes out**, and
> the "tails only" caveat is only removed if the re-run supports removing it.
>
> **Anti-tuning compliance (§13).** The candidate set, the selection criterion,
> the a-priori exclusion of rank-inverse-normal, and the falsification test are
> all stated here before the rebuild runs. The criterion is a marginal-
> distribution statistic containing no player ranking. Every pre-A57 published
> number remains in git history per §13, and the raw-scale composite continues
> to be computed and stored so the two can be compared directly.

---


**A54 (decided 2026-08-31, locked 2026-08-31 BEFORE the re-compute) — §7 market
proxy: component weights changed from equal-thirds to social 0.40 / attendance
0.40 / population 0.20, and the social component broadened from Reddit alone to
Reddit + club Instagram + club X. λ = 0.5 is UNCHANGED.**

> **Full disclosure of what was known before this was written.** Unlike the
> earlier amendments, this one is decided with results visible. The evidence
> that motivated it is stated here in full, and the amendment is justified on
> that evidence rather than on any resulting leaderboard:
>
> | Market variant | ρ vs club total attention | p |
> |---|---|---|
> | equal thirds (the locked §7/A30 primary) | +0.261 | 0.15 |
> | 0.40 social / 0.40 attendance / 0.20 population | **+0.382** | **0.031** |
> | social only | +0.420 | 0.017 |
> | attendance only | +0.233 | 0.20 |
> | population only | +0.055 | 0.77 |
>
> Equal weighting gives one third of the proxy to metro population, which is
> the single least informative component available (ρ = +0.055 at club level,
> −0.011 at player level). The proxy is meant to measure how much attention a
> club's market supplies; a component uncorrelated with that quantity is not
> measuring it. Reweighting toward the components that do carry signal is a
> correction to a measurement instrument, decided on the instrument's own
> validation and not on any player's rank.
>
> **New market_size construction (all 32 clubs):**
>
> ```
> social      = z( z(log1p(team_sub_subscribers))
>                + z(log1p(team_ig_followers))
>                + z(log1p(team_x_followers)) )
> attendance  = z(attendance_pct_capacity)
> population  = z(log1p(metro_population))
> market_size = z( 0.40*social + 0.40*attendance + 0.20*population )
> ```
>
> Two mechanical changes ride along and are stated so they are not silent.
> (1) `metro_population` and the three follower counts are **log1p'd before
> standardizing**; all four are heavy-tailed across 32 clubs and a raw z-score
> lets one outlier market dominate. Attendance is a percentage and is not
> transformed. (2) Club **Instagram and X follower counts** join the social
> component from `raw/team_social.csv`, which is complete for all 32 clubs;
> §7's graceful-degradation rule (drop any component not present for all 32)
> is unchanged and now has nothing to drop.
>
> **λ is NOT changed.** λ = 0.5 remains the pre-registered damping constant.
> The evidence below argues it should be 0, and it is being left at 0.5 anyway,
> because it was locked before that evidence existed.
>
> **What this amendment does NOT fix, disclosed in advance.** The reweighted
> proxy is a better *club-level* instrument and still does **not** predict
> attention at the player level, which is the level the correction is applied
> at:
>
> | | ρ(market_z, engagement_raw), player level | p |
> |---|---|---|
> | equal thirds | +0.047 | 0.22 |
> | reweighted (this amendment) | +0.061 | 0.11 |
>
> This is the **fourth** independent failure of the market term (after the
> dated-trade Δlog metro-pop and Δlog team-subreddit designs, and the λ
> portability probe) and the most direct: the correction subtracts a quantity
> that has no measured relationship with the thing it corrects, and mechanically
> induces ρ(market_z, `OAQ_portable`) = −0.424. The likely reason is structural
> — Wikipedia is a global audience and the Reddit collection spans league-wide
> subreddits, so the composite is largely insensitive to where a player plays.
> Market effects are detectable at the club level and wash out at the player
> level. **Both facts are published**: the reweight is reported as an instrument
> improvement, and the player-level null is reported as a finding and a limit,
> with the λ = 0 column shown alongside the headline as robustness.
>
> **Anti-tuning compliance (§13).** This amendment is decided with results
> visible and says so; the mitigation is that the decision rule is external to
> the leaderboard. Weights are set from the club-level validation table above,
> which is computed against club total attention and contains no player ranking;
> the ordering (social > attendance > population) was specified by the owner
> before the validation was run, and the numbers confirmed rather than chose it.
> λ (A5), the §4/A12 composite weights, §6/A13 peer features, the A4/A8/A24/A49.2
> denominators, the §2/A10/A41 pool, the A11/A14 windows, the A34 display rule,
> and all §9/A6 validation floors are **unchanged**. The pre-A54 `market_z` is
> retained as `market_z_lockedv1` and `market_z_metro_only` for audit, and every
> pre-A54 published number remains in git history per §13.

> ---
>
> **CORRECTION appended 2026-08-31, same day, before any A54 number was
> published. The paragraph above beginning "What this amendment does NOT fix"
> is WITHDRAWN. Its claim of a "fourth independent failure" rests on a defective
> test and is not true.**
>
> The withdrawn test correlated `market_z` against `engagement_raw` **across
> individual players** and read ρ = +0.061 (p = 0.11) as evidence of no
> player-level market effect. `market_z` takes **32 distinct values**, one per
> club. Correlating a club-level variable against 682 individual outcomes
> dilutes a between-club signal into within-club variance — differences in skill
> and role inside one roster are far larger than differences between markets —
> so that statistic measures dilution, not absence. It should never have been
> run at the player unit, and no conclusion about λ should have been drawn from
> it.
>
> Re-run at the correct unit, on the same data and the same A54 composite:
>
> | Test | ρ | p |
> |---|---|---|
> | player unit (the withdrawn test) | +0.062 | 0.11 |
> | **club-mean skill-controlled residual** | **+0.341** | **0.056** |
> | club unit, top production tercile | +0.438 | 0.012 |
>
> And on the design that actually identifies the quantity — the same player
> before and after a club change, controlling for change in production
> (n = 83 movers, 2024-25 → 2025-26):
>
> | Term | b | t |
> |---|---|---|
> | **Δ market_z** | **+0.131** | **+3.15** |
> | Δ PPG | −0.114 | −0.27 |
> | Δ TOI/G | +0.090 | +2.89 |
>
> The market effect is present, positive at every production tercile among
> movers (+0.086 / +0.146 / +0.246 from bottom to top), and detectable only
> because A54's reweighting replaced single weak components with a composite:
> the earlier probes that read null instrumented the market with metro
> population alone, which A54 itself showed carries ρ = +0.055.
>
> **What survives of A54 and what does not.** The amendment's *rule* — the
> 0.40 / 0.40 / 0.20 reweighting and the broadened social component — stands
> unchanged, and is now better supported than when it was written, because the
> reweighted composite is what makes the effect visible at all. Only the
> withdrawn paragraph's *interpretation* is wrong. λ is **not** discredited;
> A55 estimates it directly. This correction is appended rather than edited into
> the original text, per the project rule that a pre-registered record is added
> to and never rewritten.
**Verification log (not amendments — no design decision, no tuning; recorded for audit).**

**V-A11-Window (2026-08-31) — the composite had silently drifted off the locked
A11/A14 window onto the 921-day collection window. Detected, repaired, and
re-run. No design decision; a locked rule was restored, so this is recorded
here rather than as an amendment.**

**The defect.** A11 (Reddit) and A14 (en-Wikipedia) lock the attention window at
a fixed **365 days ending 2026-04-17**. A51/A52 widened
`_common.WINDOW_START_DATE` to **2023-10-10** so the three-season panel could be
built from a single pass of collection. Every fetcher imports that constant,
so the `*_12mo` totals became **921-day** totals — two and a half seasons,
including two offseasons — while still named `12mo`, still described as a
12-month window in `results.md`, and still matched against a **single** season
of production in §6.

The error is not a rounding artifact. Verified on the pooled set:

| Column | stored (921 d) | true A11 (365 d) | ratio |
|---|---|---|---|
| `wiki_12mo` median | 81,716 | 32,293 | 2.53 |
| `wiki_intl_12mo` median | 14,318 | 5,712 | 2.51 |
| `reddit_mentions_12mo` median | 349 | 132 | 2.64 |

The stored value equalled the full 921-day sum for **956 of 973** rows.

**Why it is a bug and not an amendment.** A51 widened *collection*; nothing in
A51 or A52 amends the §3/A11/A14 window that defines the composite, and both
amendments state the composite is unchanged. The code diverged from a
pre-registered rule, which §14 resolves as "fix the code". Restoring A11 needs
no new amendment and grants no new latitude — it returns the composite to the
window that was locked before any of this data existed.

**The repair (`repair_window_a11.py`).** No re-fetch: the daily vectors already
carry all 921 days, and the A11 window is exactly their last 365 entries.

- `wiki_12mo` — recomputed as the tail-365 sum of `wiki_daily.daily_views`.
- `wiki_intl_12mo` — same, per edition, then summed across editions.
- `reddit_mentions_12mo` / `reddit_upvotes_12mo` — `reddit_detail.csv` carries no
  date, but the cached corpus retains `created_utc` per submission and joins on
  `submission_id` at **100.0%** (the recovery route already recorded as WORKS in
  `value_propositions.md`). Counts recomputed over submissions falling inside
  the A11 interval.
- A player whose daily vector is shorter than 365 days is **left untouched**
  rather than summed as though complete, which would understate him against a
  fully-observed pool.
- Pre-repair files retained as `raw/*.pre_a11repair.csv`.

**One component is NOT repaired, and it is disclosed rather than mixed.**
`trends_12mo` is a **mean** of a weekly index normalised to a fixed anchor
(A16/A44), not a window sum, so it does not scale with window length the way a
total does; and the weekly series was averaged away at fetch time and not
retained (`value_propositions.md`: "Google Trends weekly series — DEAD,
unrecoverable"), so a 365-day mean cannot be reconstructed without a re-fetch.
It therefore remains on the 921-day timeframe while the other four components
sit on 365 days. This is stated in the published methods; it is the one
component whose window does not match, it carries §4/A12 weight 0.16, and a
re-fetch storing the weekly series is the fix whenever Trends is next collected.

**Effect.** Every published number changes. The pre-repair figures are retained
in git history per §13. The peer vector, pool, denominators, λ (A56), the A57
transform, and the tier construction are all unchanged — only the four
component totals the composite is built from.

**V-A11-Trends (2026-06-26) — live spot-check confirming `raw/trends.csv` was fetched on the A11 fixed window, not a run-anchored one.** `fetch_trends.py:52` uses `timeframe="2025-04-18 2026-04-17"`, but the stored `trends.csv` carries `fetch_date=2026-06-20` and the fixed-window code only landed 2026-06-20 13:21 (commit `0c3ccbe`); whether the file predated the fix that day was not decidable from git/data alone. A single live `pytrends` call resolves it (the test is window-vintage, so one salient distinctive-name player suffices). **Player: Connor McDavid** (stored `trends_12mo = 24.7358`; he had a 2026 playoff run, so the two windows diverge maximally). Result: a fresh **fixed-window** [2025-04-18, 2026-04-17] fetch gives mean **26.13** (n=53) — **5.6 % from stored, within Trends sampling noise → MATCH**, i.e. the stored file used the fixed window. The same player's **run-anchored** (`today 12-m`) series shows the expected post-window playoff spike the fixed window correctly excludes — weeks 2026-04-19 = 32, **2026-04-26 = 47 (peak)**, 2026-05-03 = 33, all after the 2026-04-17 window end. Conclusion: the `trends` component (§4/A12 weight 0.16) is on the A11 window and **excludes the 2026-playoff confound**; the SESSION residual is closed by live evidence. No file or weight changes; verification only. (One live call; perishable, so not re-run across the set.)
