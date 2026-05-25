# The Marchand Index — Full-Build Pre-Registration

**Author:** Adam Noakes (ana178@sfu.ca)
**Locked on:** 2026-05-22
**Submission target:** CASSIS, 2026-05-31
**Scope of this document:** This pre-registration covers the **full-build** model (all ~700 active NHLers, K=10 peer matching, four validation gates). It is locked **before** the abstract is submitted and **before** any production modelling work begins. The companion file `pilot/preregistration.md` covers the locked 14-player pilot only; the pilot remains untouched by this document.

---

## 1. Why this document exists

The Marchand Index is a model that scores fan attention for NHL players after accounting for skill, market, and salary. Because every step of that pipeline involves judgement calls — which peers to compare against, how to control for market, what to validate against — a reader has a fair concern: were the design choices made to fit the result the author wanted?

This pre-registration removes that concern by writing every consequential choice down before any results are known. After this commit is published, the model is run on production data; the answers are reported regardless of direction. If the answers disagree with the hypotheses below, the disagreement is the finding.

## 2. What is locked here

| Section | What it locks |
|---|---|
| §3 | Four falsifiable hypotheses about how attention should behave (H1–H4) |
| §4 | Four validation gates the model must clear before any finding ships |
| §5 | Exact rules for splitting players into star / regular / depth bands (Gate 4) |
| §6 | The video sampling frame for Gate 4 (what counts as a held-out attention event) |
| §7 | Snapshot, deduplication, and minimum-data rules for Gate 4 |
| §8 | Null-result handling: when a finding gets downgraded if a gate fails |
| §9 | Bootstrap procedure for confidence intervals |
| §10 | Amendment log |

Nothing outside this list is treated as pre-registered. Composite weights inside the CES, theme prompt wording, and figure styling are tuneable; the *outcomes* they feed into are not.

## 3. Pre-registered hypotheses (H1–H4)

These are the four claims the model is built to test. Each is reported with effect size and 95% bootstrap CI as **confirmed / disconfirmed / inconclusive**, regardless of direction.

| ID | Plain-English claim | Test |
|---|---|---|
| **H1** | Polarizing players (the Marchand archetype: high positive AND high negative Reddit sentiment in the same player) draw more attention per cap dollar than skill-matched non-polarizing peers. | Peer-group comparison of `marchand_index` for polarizing vs. non-polarizing players, matched on on-ice profile. One-sided t-test with bootstrap CI. Expected: polarizers ≥ 1.5× peer median. |
| **H2** | Players whose conversation extends beyond hockey-only spaces (≥15% of mentions in non-hockey subreddits) carry more attention than their cap percentile predicts. | Linear regression: `OAQ_portable ~ crossover_pct` controlling for cap percentile. Effect size + CI. |
| **H3** | A documented viral off-ice event (relationship, fight, charity, controversy) produces attention that persists at least six months past the event, above the pre-event baseline. | Interrupted time-series on Wikipedia + Reddit + Trends. Pre/post t-tests at +30/+90/+180 days. |
| **H4** | Off-ice-driven attention is more theme-concentrated than skill-driven attention. Players with two or fewer dominant themes have higher Marchand Index than players whose attention is split across four or more themes, holding skill constant. | Spearman ρ between theme-concentration (Herfindahl index on theme shares) and Marchand Index, within skill quintiles. |

## 4. Validation gates

The model has to clear four independent checks before any headline number appears in the manuscript. Three test whether the index lines up with observable star-population outcomes that hockey people already accept as fan-attention signals (jersey lists, All-Star votes, signing impact). The fourth — new in this commit — tests whether the index still works **outside the star tier**, since the abstract specifically claims it detects fan attention for role and depth players.

| # | Gate | Plain-English question it answers | Pass condition |
|---|---|---|---|
| **1** | Jersey list correlation | "Do players the model says have high off-ice attention also actually sell jerseys?" | Spearman ρ between `OAQ_portable` top-50 and NHL annual top-20 jersey list. Aim ≥ 0.50, floor ≥ 0.40. |
| **2** | All-Star fan-vote correlation | "Do fans vote for the players the model says fans care about?" | Spearman ρ between `OAQ_portable` and All-Star fan-vote share, seasons 2022 / 2023 / 2024. Aim ≥ 0.55, floor ≥ 0.45. The 2024-25 NHL All-Star Game was replaced by the 4 Nations Face-Off, so that year is unavailable. |
| **3** | Free-agent signing follower growth | "When a team signs a player the model rates as a strong attention draw, does the team's social following actually grow more than usual?" | Difference-in-differences regression on top-50 FA signings since 2020: 60-day team-account follower delta ~ signed-player `OAQ_portable` + team FE + season FE + cap hit + position. Aim p < 0.05 positive; floor directionally positive. |
| **4** | **Stratified generalization (new)** | "Does the model still work when you take the obvious stars out of the picture? Or is it just rediscovering who's famous?" | See §5–§8. Outside-star pooled cohort must show Spearman ρ ≥ 0.25 between `OAQ_portable` and held-out attention residuals, plus directional checks on regular and depth sub-bands. |
| 5 | Theme classifier audit | "Is the automated theme labelling accurate enough to trust?" | Hand-label 300 stratified Reddit comments. Macro-F1 ≥ 0.60 floor / 0.70 aim. Cohen's κ ≥ 0.55 floor / 0.65 aim. Failing this gate suppresses theme-level findings only; the headline OAQ is unaffected. |

The fifth check is the LLM theme audit, not a separate attention validation — it sits with the four gates above because it shares the same ship-floor function.

## 5. Stratified Generalization — exact band rules (Gate 4)

The point of Gate 4 is to show the model is more than a star detector. To do that honestly, players have to be sorted into visibility bands using only information that has nothing to do with the model's own outputs. The rules below use percentile cutoffs (which automatically rebase as the cap and the league change) plus a small set of hard credentials (which catch ELC-contract stars and aging veterans whose cap or ice-time numbers don't reflect their actual public visibility).

**No OAQ, Marchand Index, Wikipedia, Reddit, Google Trends, Instagram, YouTube, or any attention-derived value is used in defining the bands.**

Position split for percentiles: forwards (F) and defensemen (D) are ranked separately. Goalies are excluded from headline analysis throughout this document.

### 5.1 Star band ("high-visibility")

A player is assigned to the star band if **any one** of the following is true at the season of analysis:

| Criterion | Threshold |
|---|---|
| Cap hit | Top 15% league-wide |
| TOI per game | Top 15% within position (F or D) |
| Points per 60 at 5v5 | Top 15% within position (F or D) |
| All-Star selection | At least one appearance in the most recent three completed seasons |
| NHL annual jersey list | Appears in the top 20 in at least one of the most recent three completed lists |

### 5.2 Depth band ("low-usage / role")

After the star band is removed, a player is assigned to the depth band if **either** of the following is true:

| Criterion | Threshold |
|---|---|
| Cap hit | Bottom 35% league-wide |
| TOI per game | Bottom 35% within position (F or D) |

Star-band players are removed first, so a low-cap player who hits any star credential (e.g. a high-points/60 ELC contract) stays in the star band.

### 5.3 Regular band

Every active NHLer who is neither star nor depth. This is the largest band in expectation.

### 5.4 Edge-case rule

A player is assigned to a single band per season of analysis. If a player meets both a depth criterion and a star criterion, the star band wins. Mid-season trades use the team affiliation as of the snapshot date in §7.

## 6. Sampling frame for Gate 4 (what counts as a held-out attention event)

Gate 4 tests `OAQ_portable` against a held-out attention signal — observable public attention events that are **not** part of the CES (Wikipedia, Google Trends, Reddit, Instagram). The signal of record is YouTube view counts on player-named videos, with a controlled regression layer that strips out the obvious confounds (clip type, clip age, channel, opponent, playoff context, clip length, position, ice time, points/60, cap hit, career length).

### 6.1 Channel allow-list (primary)

The primary channel set is constrained to channels with stable ownership, predictable upload behaviour, and minimal SEO contamination:

| Channel type | Includes |
|---|---|
| NHL official | NHL.com channel, NHL Network |
| Team official | The 32 NHL team YouTube channels |
| Major broadcasters | Sportsnet, TSN, ESPN, TNT Sports |

### 6.2 Fan-uploaded videos — sensitivity tier only, with escalation rule

Fan-uploaded compilations are excluded from the primary analysis because of name collisions, stolen / re-uploaded clips, and SEO spam. They are used in two situations only:

1. **Sensitivity analysis.** The full regression is re-run with fan-uploaded videos included, using a `channel_type ∈ {official, fan}` covariate. Reported alongside the primary result regardless of direction.
2. **Coverage-driven escalation.** If primary-channel coverage in the outside-star cohort falls below the floor in §7.3 (≥75 players with ≥3 primary events each), fan-uploaded videos are added to the primary set in a pre-registered order — first by deduplication against existing primary events, then by recency. The expansion stops the moment the floor is reached. The escalation flag and final channel mix are reported in the published Gate 4 table.

### 6.3 Query format

For each player, the YouTube Data API search query is exactly `"<First Last> NHL"`. Players whose name collides with another NHLer (maintained in `data/name_collision_list.csv`) get a team-abbreviation disambiguator appended, e.g. `"Sebastian Aho NYI"` vs. `"Sebastian Aho CAR"`.

Maximum 50 results retrieved per query. Top results are filtered for the relevance rule in §7.2.

### 6.4 Outcome variable

For each retained video, the outcome is `log1p(view_count_at_snapshot)`. Likes and comments are recorded as secondary outcomes but are not the primary signal — they are noisier and more vulnerable to channel-level engagement-baiting.

### 6.5 Regression specification

Within each band (star / regular / depth) and on the pooled outside-star cohort:

```
log1p(view_count) ~ OAQ_portable
                  + clip_type
                  + log(upload_age_days + 1)
                  + team_market_size
                  + channel_id
                  + opponent_team
                  + playoff_flag
                  + log(clip_length_seconds + 1)
                  + position
                  + TOI_per_game
                  + points_per_60
                  + cap_hit_M
                  + years_since_NHL_debut
```

The coefficient on `OAQ_portable` is the test statistic. The residual `log1p(view_count) − [all-controls-fit-without-OAQ]` is the Spearman-input series.

## 7. Snapshot, deduplication, and minimum-data rules

### 7.1 Snapshot date

All YouTube view counts are read between snapshot date D and D+1 — a single 24-hour window per data fetch. D is locked at the start of the Gate 4 fetch and reported in the Gate 4 table. Videos uploaded fewer than 30 days before D are excluded so view counts have time to stabilise.

### 7.2 Relevance criteria

A video enters the dataset if **all** of the following hold:

- The player's first or last name appears in the video title (case-insensitive substring match).
- The video was uploaded while the player was on an NHL active roster (no junior, college, Olympics-only, or pre-NHL footage).
- Video duration is between 15 seconds and 30 minutes (filters out static images, dead uploads, and full-game re-uploads).
- View count at snapshot is at least 500 (suppresses auto-generated stub videos).

### 7.3 Coverage floor and target

| Metric | Floor | Target |
|---|---|---|
| Outside-star players with ≥3 primary events each | 75 | 125 |
| Outside-star primary events total | 250 | 500 |

If the floor is not reached on the primary channel set, the escalation rule in §6.2.2 applies.

### 7.4 Deduplication

A duplicate is any pair of retained videos where (a) the `(channel_id, video_id)` is identical, or (b) all three of: title hash similarity ≥ 0.8 (normalised Levenshtein), absolute duration difference ≤ 60 seconds, and upload-date difference ≤ 7 days. When duplicates are detected, the highest-view-count copy is kept and the duplicate is flagged.

## 8. Null-result handling

Each gate has a pre-declared failure response. This list is the only way a published claim can be weakened; ad-hoc downgrades are not permitted.

| Gate fails | Response |
|---|---|
| Gate 1 (jersey list ρ < 0.40) | Halt; re-examine CES composite weights. No headline finding published until floor is met. |
| Gate 2 (All-Star ρ < 0.45) | Halt; re-examine market-baseline subtraction. No headline finding published until floor is met. |
| Gate 3 (FA signing direction not positive) | Halt; re-examine event-study controls. No headline finding published until floor is met. |
| **Gate 4 — outside-star pooled ρ < 0.25** | The general-use claim is suspended; the model is reported as star-population-validated only. The depth-player framing in the abstract / poster / manuscript is removed. |
| **Gate 4 — depth-band ρ < 0 OR depth-band bootstrap 95% CI entirely below zero** | The "Reaves archetype" framing in §5 of the abstract is removed in the final manuscript. The depth-player claim is reported as **exploratory, not validated**. |
| Theme-classifier audit (Macro-F1 < 0.60 OR κ < 0.55) | Theme-decomposition findings (poster §5) are suppressed. Headline OAQ + Marchand Index are unaffected. |

### 8.1 Pass logic for Gate 4 specifically

The model passes Gate 4 for general use if the outside-star pooled cohort produces Spearman ρ ≥ 0.25 between `OAQ_portable` and the regression residuals defined in §6.5. The depth-player claim attached to §5 of the abstract additionally requires either:

(a) depth-band Spearman ρ ≥ 0.25 on its own, OR
(b) the pooled outside-star cohort clears AND the depth-band point estimate is positive with a bootstrap 95% CI not entirely below zero.

Both band-level estimates (regular, depth) are reported regardless of which path establishes the claim.

### 8.2 Secondary robustness checks (reported, not gating)

- **Top-quartile vs. bottom-half ratio.** Outside the star band, the median residual attention of the top-quartile `OAQ_portable` players should be ≥ 1.25× the median residual attention of the bottom-half. Aim ≥ 1.50×.
- **OAQ_portable regression coefficient.** In the §6.5 regression, the coefficient on `OAQ_portable` should be positive after controls; aim p < 0.05, floor directionally positive with reported bootstrap CI.

These are robustness signals. They do not gate publication on their own — the ρ check in §8.1 does.

## 9. Bootstrap procedure

Every published OAQ, Marchand Index, and Gate-4 Spearman ρ is shipped with a 95% bootstrap CI.

- Per-player OAQ / Marchand Index: 1,000 draws. Each draw resamples the player's Wikipedia daily-pageview vector and Reddit comment / submission pool with replacement, recomputes engagement_raw, recomputes peer-group mean from the same draw, recomputes OAQ_observed and OAQ_portable, divides by the (unresampled) cap hit, takes 2.5th and 97.5th percentiles.
- Gate-4 Spearman ρ: 1,000 draws. Each draw resamples the outside-star cohort with replacement at the player level; the residual regression is refit per draw; ρ is recomputed per draw. CI is the 2.5th–97.5th percentile of the 1,000 ρ values.
- Random seed: pre-registered at the value `20260522` for full reproducibility. If a re-run is needed with a different seed (e.g. due to a hardware change), both runs are reported.

## 10. Anti-tuning commitments

The following are written down here so that any apparent post-hoc improvement is detectable in the git history:

- Composite weights inside the CES are not adjusted after Gate 4 results are known. If a re-weighting is judged necessary, it must be documented as an amendment in §11 *before* re-running Gate 4 on the new weights, and the original-weight Gate 4 numbers are retained for comparison.
- Band thresholds in §5 are not adjusted after Gate 4 results are known. The 15% / 35% / position-split rules are the gate. If a sensitivity analysis is judged necessary on alternative thresholds, the original thresholds remain the published gate.
- "Did Reaves rank where we hoped?" is not a tuning input. Per-player intuitions about specific players (Reaves, Marchand, Hughes, Bedard) are spot-check signals only; they do not feed back into model weights or gate thresholds.
- We do not claim revenue. Public attention is treated as a proxy for fan demand throughout. Jersey-list and signing-impact gates are the closest revenue-linked observables we use, and even those are reported as attention signals, not as dollar conversion.

## 11. Amendments

Any change to this document after the initial commit is appended below with date and reason. Earlier sections are not edited silently.

*No amendments at lock time.*
