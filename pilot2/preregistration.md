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
