# Pilot pre-registration — The Marchand Index (CASSIS 2026 abstract)

**Author:** Adam Noakes (ana178@sfu.ca)
**Locked on:** 2026-05-20
**Submission target:** CASSIS, 2026-05-31
**Status of this document:** This pre-registration is committed to the project git repository **before any fetch script is written or run**. The intent is to remove every degree of freedom in the pilot that could enable post-hoc cherry-picking. If anything in this document is changed after fetch code lands, the change is logged in §10 (Amendments) with a date and reason, *not* edited silently.

---

## 1. Purpose of the pilot

Produce **one figure and one CSV** for §4 of the CASSIS abstract. The pilot is an **illustrative worked example** using a hand-curated 14-player set with restricted peer candidates (K=5 within the 14). It is **not** validation of the full leaguewide K=10 method.

The pilot exists to demonstrate that the methodology, applied honestly, *can* produce a non-trivial reordering of players when raw popularity is corrected for cap hit and market amplification. Whether it does so for *this particular 14-player set on the day we run it* is an empirical question whose answer is reported regardless of direction.

## 2. Locked player list (N = 14)

Identified by their canonical Wikipedia article slug. If any player is unavailable on any data source, NULL is recorded and sentinel handling (§5) applies.

| # | Player | Position | Team (current as of 2026-05-20) | Wikipedia slug (en.wikipedia.org/wiki/…) | Archetype axis |
|---|---|---|---|---|---|
| 1 | Connor McDavid | C | EDM | Connor_McDavid | Elite skill, modest off-ice |
| 2 | Nathan MacKinnon | C | COL | Nathan_MacKinnon | Elite skill, modest off-ice |
| 3 | Cale Makar | D | COL | Cale_Makar | Elite skill, modest off-ice |
| 4 | Leon Draisaitl | C | EDM | Leon_Draisaitl | Elite skill, modest off-ice |
| 5 | Sidney Crosby | C | PIT | Sidney_Crosby | Legacy BDS, modest CES |
| 6 | Auston Matthews | C | TOR | Auston_Matthews | Star scoring, large market |
| 7 | Nikita Kucherov | RW | TBL | Nikita_Kucherov | Star scoring |
| 8 | Brad Marchand | LW | FLA | Brad_Marchand | High-skill polarizing (namesake archetype) |
| 9 | Matthew Tkachuk | LW | FLA | Matthew_Tkachuk | High-skill polarizing |
| 10 | Brady Tkachuk | LW | OTT | Brady_Tkachuk | High-skill polarizing (sibling control for #9) |
| 11 | Ryan Reaves | RW | (verify current team via NHL API at fetch time) | Ryan_Reaves | Mid-skill role-player (extreme off-ice archetype) |
| 12 | Mitch Marner | RW | TOR | Mitch_Marner | Toronto-market amplification test (paired with #6) |
| 13 | Jack Hughes | C | NJD | Jack_Hughes_(ice_hockey,_born_2001) | Cultural crossover / viral |
| 14 | Connor Bedard | C | CHI | Connor_Bedard | Rising salience |

**No additions, no substitutions** after this commit. If a player's data is unavailable across ≥3 of 5 stable-core signals, the player is reported with `match_quality = low` in `pilot/oaq_pilot.csv` and excluded from the figure — but the row remains in the CSV with reasons documented.

## 3. Stable-core data sources (locked)

Five components feed the pilot engagement composite:

1. `wiki_12mo` — Wikipedia REST API pageviews-per-article, daily, summed across the most recent 365 days available at fetch time (cutoff = fetch date − 1).
2. `trends_12mo` — Google Trends 12-month rolling mean, query string = `"<First name> <Last name>"`, region = worldwide, no geo restriction.
3. `reddit_mentions_12mo` — PRAW search across `r/hockey` plus the team subreddit, query string = `"<Last name>"`, timeframe = last 365 days, deduped by submission ID.
4. `reddit_upvotes_12mo` — sum of `score` field across the comments/submissions matched in #3.
5. `instagram_followers` — `instaloader` Profile object's `followers` attribute, snapshot at fetch date, official verified handle for each player (handles enumerated in `pilot/players.csv` before fetch).

Exploratory sources (TikTok, X, YouTube) are NOT in the pilot composite and do not influence the figure. They may be fetched opportunistically and recorded in `pilot/social_followers.csv` for transparency, but they are out-of-scope for §4.

## 4. Composite formula (locked)

Each component is **z-scored across the 14-player set** (sample mean 0, sample standard deviation 1). The composite `engagement_raw` is a weighted sum of z-scores. Weights are renormalized from the full-spec CES weights in `NHL_Marchand_Index.md` after removing components that are out-of-scope for the pilot (cross-sub mentions, NHL official engagement). Locked weight vector:

| Component | Weight |
|---|---|
| `wiki_12mo` | 0.306 |
| `reddit_mentions_12mo` | 0.250 |
| `reddit_upvotes_12mo` | 0.167 |
| `trends_12mo` | 0.139 |
| `instagram_followers` | 0.139 |
| **Sum** | **1.001** (rounding artifact; do not rebalance) |

`engagement_raw(P) = Σ_c weight_c × z(component_c, P)`

**Sentinel handling:** if a player is NULL on any component, that component drops from the player's personal sum AND the remaining weights are renormalized **for that player only** (divide by sum of remaining weights). Documented in the CSV via a `dropped_components` column.

## 5. Cap hit (locked source)

`cap_hit_M` = player's 2025-26 NHL salary cap hit in $M, fetched via single `WebFetch` of PuckPedia or CapWages roster-wide salary page. If primary source fails, fallback is 14 individual `WebFetch` calls (one per player). Values are recorded with a `cap_hit_source_url` column so reviewers can audit.

## 6. Peer matching (locked, worked-example scope)

For each player P among the 14:

- Build skill vector = (PPG, TOI/G, age), standardized across the 14-player set; position is a hard filter (forwards-only or D-only).
- Compute Mahalanobis distance from P to each same-position other player among the 14, using sample covariance over the 14-set.
- K = **5 nearest peers** (or fewer if same-position count < 5 — sentinel `effective_K` column records the actual count).
- `peer_engagement_mean(P) = mean(engagement_raw across K nearest peers)`
- `OAQ_observed(P) = engagement_raw(P) − peer_engagement_mean(P)`

**This is a worked example. The full method is K = 10 across all ~700 active NHLers. The pilot's restricted peer pool is acknowledged in §4 of the abstract.**

## 7. Market-baseline / portable OAQ (locked)

`team_market_baseline_P` = **mean of `wiki_12mo` across the active roster of player P's team**, excluding P themselves. Roster is enumerated from the NHL public API (`api-web.nhle.com/v1/roster/<TEAM_CODE>/current`) at fetch time. Wikipedia pageviews are fetched for each rostered player.

`OAQ_portable(P) = (engagement_raw(P) − z(team_market_baseline_P)) − mean[(engagement_raw − z(team_market_baseline)) across K peers]`

Where `z(team_market_baseline)` standardizes the team baseline across all 14 pilot teams.

**Time-bounded fallback:** if active-roster enumeration + roster Wikipedia fetch exceeds 2 elapsed days (decision point: end of day 2026-05-23), the team_market_baseline fallback is the mean `wiki_12mo` across the team's top-12 most-viewed Wikipedia article subjects on the roster (smaller scrape footprint). The fallback is recorded in the CSV via a `market_baseline_method` column.

## 8. Marchand Index (locked)

`marchand_index(P) = OAQ_portable(P) / cap_hit_M(P)`

Reported with **bootstrap 95% CIs** computed by resampling Wikipedia daily-pageview vectors and Reddit comment lists with replacement, 1,000 draws per player, recomputing the full pipeline per draw.

## 9. Figure specification (locked, MUST be implemented as written)

Single figure, target output `pilot/figure.png`, rendered via matplotlib.

**Layout:** two adjacent vertical columns.

- **Left column:** the 14 players ranked top-to-bottom by `engagement_raw` (highest = top). Each row shows player name + their `engagement_raw` z-score on a small horizontal bar.
- **Right column:** the same 14 players ranked top-to-bottom by `marchand_index` (highest = top). Each row shows player name + their `marchand_index` value, with a thin error bar = bootstrap 95% CI, plus an annotated cap-hit value (`$X.X M`).
- **Visual link:** thin grey lines connecting each player's left-column position to their right-column position. Players whose rank changes substantially produce slanted lines; players who stay in similar positions produce near-horizontal lines.
- **Caption:** one sentence — "Left: ranking by raw engagement. Right: ranking by Marchand Index (OAQ_portable per $M of cap hit, 95% CI in error bars). The divergence between the two rankings is the methodological point of the index."
- **No color coding by archetype.** Reviewers should perceive the rankings as honest, not as illustrated to a narrative.

**The figure is fixed in spec before any data is fetched.** No "what if we rotate, color, sort differently" exploration after results land.

## 10. Pre-registered expected patterns (falsifiable, NOT pass/fail gates)

These are the patterns the method, *if it works on this 14-player set*, should produce. Each is reported with a `confirmed / disconfirmed / inconclusive` verdict in `pilot/results.md`, **regardless of direction**.

| ID | Pattern | Specific test |
|---|---|---|
| P1 | Marchand and Reaves appear in the top 5 of `marchand_index`. | Binary check on final ranked output. |
| P2 | Marner's `OAQ_observed − OAQ_portable` magnitude is materially larger than Reaves'. | Compare absolute gap values; "materially" defined as Marner gap ≥ 1.5× Reaves gap. |
| P3 | At least two top-5 rank flips between `rank_by_engagement_raw` and `rank_by_marchand_index`. | Set-symmetric-difference count among the top-5 sets. |

**Each pattern can fail and the abstract still ships.** Failure to observe a pattern is reported as a sensitivity finding (e.g., "P2 not observed: Marner/Reaves market-amplification gap was within 1.2×, suggesting the team-market baseline did less work on this 14-player set than expected"). Failure is informative, not catastrophic.

## 11. Fallback-to-schematic rule (locked)

If **two or more of P1, P2, P3 are disconfirmed**, the §4 figure becomes a **schematic illustration** using synthetic data that *demonstrates the method* (rank flip diagram + worked example for a hypothetical player), and §4 reports the actual pilot result honestly in 2-3 sentences with a sensitivity note. This protects against the temptation to "tune" the pilot to produce the pre-registered patterns.

If **exactly one of P1, P2, P3 is disconfirmed**, the real figure is used; the disconfirmed pattern is reported transparently in the caption.

If **all three are confirmed**, the real figure is used; optionally, one quotable number from the patterns is hoisted into the opening paragraph of the abstract.

## 12. What is explicitly NOT part of the pilot

- LLM theme classification (Wk 4–5 of full build)
- Three-validation gates (jersey list ρ, All-Star vote ρ, FA-signing event study — Wk 7–8)
- Full hypothesis tests H1–H4 (Wk 8)
- All ~700 NHLers leaguewide K=10 matching (Wk 6)
- Goalies
- Sentiment / polarization output dimensions

These remain in the abstract's §2/§3 method and validation plan as full-build commitments, not pilot deliverables.

## 13. Output file inventory

After the pilot completes:

- `pilot/players.csv` — 14 rows, hand-curated identifiers (locked at this commit)
- `pilot/raw/wiki_pageviews.csv` — fetched
- `pilot/raw/trends.csv` — fetched
- `pilot/raw/reddit_counts.csv` — fetched
- `pilot/raw/instagram_followers.csv` — fetched
- `pilot/raw/nhl_skill.csv` — fetched
- `pilot/raw/cap_hits.csv` — fetched
- `pilot/raw/team_rosters.csv` — fetched (for market baseline)
- `pilot/raw/team_market_baselines.csv` — derived
- `pilot/oaq_pilot.csv` — final per-player table
- `pilot/figure.png` — final figure (real or schematic, per §11)
- `pilot/results.md` — narrative of what was observed vs. expected, regardless of direction

## 14. Amendments

Any change to this document after the initial commit must be appended below with date + reason. Do not edit prior sections silently.

### A1 — 2026-05-20: Jack Hughes Wikipedia slug corrected

**Section affected:** §2 player table (row 13).
**Original slug:** `Jack_Hughes_(ice_hockey,_born_2001)`
**Updated slug:** `Jack_Hughes`
**Reason:** The original parenthetical-disambiguated article returns only ~3,000 pageviews/year, which is orders of magnitude too low for a top-tier NHL star. Empirical check shows the bare `Jack_Hughes` slug is now the primary-topic article on English Wikipedia and returns ~2.56M pageviews/year — consistent with the player's actual public salience. This is an identifier-mapping correction, not a change to the locked method, weights, peer-matching procedure, or expected-pattern hypotheses. Verified by direct Wikimedia API check before the players.csv edit was committed.

### A2 — 2026-05-20: NHL player IDs pre-populated; player search disambiguation

**Section affected:** §2 player table (new column `nhl_player_id`).
**Change:** Added the canonical NHL player ID for each of the 14 players to `players.csv`. Reason: the NHL search endpoint returns weakly-ranked results (e.g. "Mitch Marner" → first hit "Mitch Holmberg"; "Jack Hughes" → first hit a 1957-born retired defenseman). Pre-populating the IDs makes the pipeline deterministic instead of search-rank-dependent. IDs were verified by inspecting each `/v1/player/{id}/landing` response and confirming name + position + team match the intended player. This is identifier mapping, not a method change.

### A4 — 2026-05-20: Instagram follower counts unavailable; component falls through sentinel handling

**Section affected:** §3 (stable-core data sources), §4 (composite formula).
**Change:** `instagram_followers` is reported as NULL for all 14 players in the pilot. Reason: Meta has restricted anonymous access to Instagram's GraphQL profile-metadata endpoint (HTTP 403 Forbidden on instaloader without authentication). Authenticated scraping was rejected because (a) the project promises owner-time-zero manual data work, (b) authenticated scraping risks the owner's personal Instagram account.
**Effect on composite:** Per pre-reg §4 sentinel rule, when a component is NULL the weight for that component drops from the player's personal composite and the remaining weights renormalize. With Instagram NULL across all 14 players, the effective composite for every player is:
  - `wiki_12mo`: 0.306 / 0.861 = 0.355
  - `reddit_mentions_12mo`: 0.250 / 0.861 = 0.290
  - `reddit_upvotes_12mo`: 0.167 / 0.861 = 0.194
  - `trends_12mo`: 0.139 / 0.861 = 0.161
This is the locked sentinel behavior, not a method change. Instagram remains in the abstract §2 method description as a full-build component (different access paths are available with budget); the pilot section discloses that the pilot composite is Wikipedia + Trends + Reddit only.

### A3 — 2026-05-20: Mitch Marner team changed from TOR to VGK

**Section affected:** §2 player table (row 12 `team_code`), §10 expected pattern P2.
**Change:** Marner has been traded from Toronto to the Vegas Golden Knights since the conceptual draft of this project. The pre-reg locked his archetype axis as "Toronto-market test"; in execution, his team is VGK.
**Methodological note for P2:** The pre-registered test ("Marner |OAQ_observed − OAQ_portable| ≥ 1.5× Reaves' equivalent gap") was motivated by the *premise* that Marner is on a high-amplification market (Toronto). With Marner now on Vegas — a lower-amplification market for hockey attention — the predicted gap may be smaller than originally anticipated. This is reportable as-is: a disconfirmed P2 in this configuration would be a sensitivity finding, not a methodological failure. The 12-month attention window straddles his Toronto and Vegas tenures, so neither team baseline is a clean match. The archetype label has been amended to `toronto_market_test_post_trade` to reflect this.
