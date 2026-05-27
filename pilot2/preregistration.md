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

*No amendments at lock time.*
