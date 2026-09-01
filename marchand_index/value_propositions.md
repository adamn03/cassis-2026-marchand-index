# Marchand Index — Idea Ledger + Downstream Value Propositions

**Two parts. Read Part 1 before proposing anything new.**
- **Part 1 — Idea ledger:** every idea we have actually *tried*, with a verdict. Stops us re-running dead ends.
- **Part 2 — Backlog (#1–#7):** ideas designed but *not built*. Unchanged from the 2026-06-28 funnel.

**Status: NOT BUILT. Implement only AFTER the full index data lands (Reddit creds + final `compute_oaq` run) AND the 5 in-flight validation gates are in place.** These are *application / extra-validation* pathways — each tests whether the index's attention surplus has a concrete downstream consequence (a decision or a market price). They do **not** change the index itself.

**Purpose.** Move the poster's claim from "we measure attention" to "this attention number predicts/explains something with real decision or money value." Each idea that lands = another independent triangulation arm (CASSIS criterion 2).

**Selection method.** Generated + filtered through a multi-stage analyst → leader → manager funnel, **ranked strength-first, feasibility-second** (owner's rule): a powerful, hard-to-dismiss idea on harder data outranks a tidy idea on easy data. "Strength" = methodological novelty + real decision value + how hard a hostile professional statistician finds it to dismiss (clean identification, built-in placebo/falsifier, sample power, no circularity, no overclaim).

**Hard constraints inherited from CLAUDE.md (apply to every idea below):**
- $0 budget; free public data / polite scraping only.
- **No causal or revenue claims** — every result framed as *association with a public proxy* ("OAQ_portable is associated with X"), never "drives/causes $".
- **No circularity** — the target must not feed the index (Wikipedia / Reddit / Trends inputs, or salary/cap in the denominator) without a temporal split + production control.
- **LLM-derived features must pass macro-F1 ≥ 0.60 AND Cohen's κ ≥ 0.55** vs hand labels before appearing on the poster (relevant to #1 below).
- Distinct from the 5 in-flight validation gates: jersey-list AUC, All-Star fan-vote, team-Wikipedia pageviews, signing event-study, YouTube stratified-generalization.

**Index recap.** `OAQ_portable` (headline) = per-player attention surplus, stripped of on-ice production (K=10 peer-matched on age/PPG/TOI/on-ice) AND home-market size = "buzz a player generates beyond an equally-productive player in a neutral market." Bootstrap CIs on every score. Pool: 774 skaters, 2025-26.

**Feasibility tiers (verified live 2026-06-26):**
- **GREEN** = free + structured, confirmed reachable. NHL API (`api-web.nhle.com`): play-by-play penalties with `committedByPlayerId`/`drawnByPlayerId`/`typeCode`/`duration`/coords, rosters/TOI, schedule, `tvBroadcasts.market` (N/H/A national flags), venue. ESPN hidden API (`site.api.espn.com`): per-game attendance + the 4 officials/referees per game. Wikimedia pageviews API: daily, back to 2015-07 (already in pipeline). Google Trends (pytrends). In-repo joins: `player_id ↔ nhl_player_id ↔ team ↔ wikipedia_slug ↔ capwages_slug`.
- **AMBER** = free but manual/partial/prose: DoPS rulings pages, NHL.com awards/news, Hockey-Reference (rate-limited), Sports Media Watch viewership (prose), fantasy ADP, Polymarket player contracts.
- **RED** = fragile/anti-bot/paid: 130point/eBay card prices, betting-odds APIs (mostly paid/thin free), DFS contest ownership at scale, Nielsen/RSN, private endorsement data.

# Part 1 — Idea ledger (what we already tried)

**Purpose: never test the same idea twice.** Every idea that got real data pointed at it,
with a verdict. Add a row the day an idea gets tested — do not wait for a session wrap-up.
If an idea is not in this table, it has not been tried.

**Verdict scale**

| Verdict | Meaning |
|---|---|
| **WORKS** | Held up under the checks we threw at it. Usable. |
| **KINDA** | Real but weak, or descriptive only, or survives with a caveat big enough to matter. |
| **DEAD** | Tested and failed, or structurally broken. **Do not re-propose without new data or a new identification strategy.** |
| **UNTESTED** | Designed, agreed worth doing, no data run yet. |

> Everything in Part 1 is **exploratory** unless a row says otherwise. None of it is
> pre-registered, and the poster owes none of it — the accepted abstract (A10) claims the
> *method* at league scale, not any finding.

## Attention as an outcome

| Idea | What we actually tested | Verdict | Evidence |
|---|---|---|---|
| **Wiki/Reddit sign flip** during international tournaments | Same Feb 6–25 window across 2024 (control) / 2025 (4 Nations) / 2026 (Olympics), per Wikipedia language edition and per Reddit venue | **WORKS** — strongest candidate we have | A language public moves iff its country iced a team: en 0.95→2.14→4.12, sk 1.55→1.04→**15.64**, ru (banned) 1.06→1.08→1.54 as an unplanned placebo. Reddit moves the *opposite* way: team subs 0.96→0.65→**0.44**. Factor of 35 end to end, sign flips in the middle. Wiki/Reddit per-player multipliers correlate ρ=+0.535 — they agree on *who*, disagree on whether it was good |
| **Attention is unpriced** by clubs | Cross-sectional log(cap hit), n≈600; plus next-contract on 545 signings across 2 transitions | **WORKS** as a *bounded null* | Veteran re-signings: **−0.4% per +1 SD Wikipedia, CI [−6.5%, +6.5%]**. Same model: +1 SD TOI = **+43.8%**. Attention ≤ 1/6 of an SD of ice time. Not underpowered — bounded |
| ↳ its stack-dependence | Re-ran the same ΔR² against three different production stacks | **KINDA** — and it constrains the pitch | ΔR² +0.051 / +28.1% vs a MoneyPuck-xG stack, but +0.004 / +8.3% vs a kitchen sink. Most of the apparent attention premium is *unmeasured production*. Reportable as a methods result; kills any "bring your own stack" framing |
| **The pest hypothesis** — attention-heavy players are agitators | Spearman of `OAQ_portable` against PIM/60 and hits/60 (MoneyPuck, all situations), published-panel pool (A34 + `cap_quality` applied), n=681. Tested 2026-08-31 while looking for a dashboard finding | **DEAD** | ρ = **0.131** (PIM/60) and **0.012** (hits/60) — nothing. Top OAQ decile median PIM/60 1.63 vs 1.31 for the rest (1.25×) but **non-monotonic** (decile 8 = 1.60, decile 9 = 1.27), and hits run the **wrong way** (2.74 vs 3.67 = 0.75×). **Why it matters anyway:** the agitator-heavy *salary-adjusted* leaderboard (Rempe, Xhekaj, Cousins, Sherwood) is a **denominator effect** — cheap contracts, not pests. The attention residual itself has no agitator signal. Do not describe the index as "finding pests" |
| **Olympic attention concentration** | Share of Olympic excess captured by the top 1% / 5% of players | **KINDA** — descriptive, supports the sign flip | Top 1% took **50.9%** of Olympic excess vs 14.3% of baseline attention (top 5%: 84.1% vs 33.4%). 66.5% of players *lose* Wikipedia attention, 90% lose Reddit attention |
| **Event spike magnitude ranking** | Best-7-day window ÷ own 90-day pre-baseline, exogenous rosters | **WORKS** as measurement | Trade **12.15x** [10.50, 14.77] > Olympics **7.11x** [6.04, 8.71] > 4 Nations **5.76x** [4.83, 7.70]. League-wide, Feb 2026 = 627 views/player/day vs ~170 baseline (3.5x), *larger* than playoffs (248/271) |
| **The "ratchet"** — international attention persists a year out | Originally: spike ≥2x in Feb 2025 → attention at t+365, with production + mean-reversion controls. **Re-audited 2026-08-26 with exogenous rosters scraped from Wikipedia** (86 4 Nations, 133 Olympic) | **DEAD** | The +30.0% [+18.8%, +43.9%] was **Olympics contamination**: t+365 from Feb 2025 lands exactly on Feb 2026, and **73 of 86** 4 Nations players were also on an Olympic roster. Split them: 4N∩Olympic = **6.53x** in Feb 2026, 4N-only (n=13) = **1.10x [0.89, 1.39], null**. With exogenous treatment 4 Nations decays to nothing by +91–180d (DiD **1.03 [0.90, 1.12]**) and sits at **0.95 [0.89, 1.02]** by +181–270d. Mean-of-logs agrees |
| ↳ **"transaction attention evaporates, identity attention compounds"** (the Rosen vs Adler framing) | Same re-audit, exogenously dated trades as the contrast | **DEAD — the sign is reversed** | Trades persist *longer* than tournaments: DiD **1.19 [1.11, 1.39]** at +91–180d and **1.10 [1.05, 1.17]** at +181–270d, both significant, while 4 Nations is null at both. Caveat: a trade is a permanent state change (new team, new fanbase); that explains the persistence but does not rescue the original claim |
| **Endogenous "spiked ≥2x" treatment definition** | Used as the treatment rule for every annual-event ratchet estimate | **DEAD as a method** | It reads treatment off the outcome series. Reproduces a +19% "persistence" that exogenous rosters show is not there. Every estimate built on it inherits the flaw: IIHF Worlds 2024 +18.8%, Worlds 2025 +10.9%, Playoffs 2024 +28.4%, UFA Jul 1 +7.8%. **Replaced by roster scraping** — `4 Nations Face-Off` sections 5–8 and `Ice hockey at the 2026 Winter Olympics – Men's team rosters` parse cleanly off the Wikipedia API; match on diacritic-normalized slugs or you silently lose Pastrnak, Maatta, Tomasek |
| **RFA/UFA age gradient** in contract pricing | Split the next-contract regression by age band | **DEAD as stated** | Over-sold mid-session, then corrected: 22–26 b=−0.002 (t=−0.03), 27–30 +0.049 (t=1.21), 31+ +0.047 (t=1.18). One precise zero and two noisy zeros. Redoing it with `contract_type` instead of age is **UNTESTED** |

## Index construction

| Idea | What we actually tested | Verdict | Evidence |
|---|---|---|---|
| **Peer-stack v2** (6 → 12 skill features) | Rebuilt K=10 peers with PP-ice share, ixG/60, shots/60, goal share, points/60, GP + 10% covariance shrinkage | **KINDA — keep as robustness, do not adopt** | Peer sets churn almost completely (31.5% mean overlap, 92.0% of players lose ≥half their peers) but the metric barely moves: Pearson **0.955**, Spearman 0.750, top-25 retention 22/25. Reads as a robustness win — the residual is a property of the player, not of peer selection. But mid-pack ranks are indefensible (Pastrnak 664→81, Eichel 164→689): **claim the tails, not the ordering**. Swapping the locked vector after seeing results is exactly what the prereg prevents. Caveat: the A49 reimplementation is only 87.1% faithful to stored `peer_player_ids`, so ~13 pts of that churn is our own drift |
| **λ = 0.5 market-correction term** | Three independent designs, most recently dated trades | **DEAD** | Δlog metro pop b=−0.021 (t=−0.37), Δlog team subreddit b=+0.080 (t=+1.09), n=60. Failed in a **third** design. **A pre-registration amendment is still owed** — the term is pre-registered and the code still carries it |
| **Reddit daily panel recovery** | Whether `cache/reddit_corpus/*.jsonl` retained dates the pipeline discarded | **WORKS** (mechanical, not a finding) | `created_utc` on all **654,992** submissions, joins to `raw/reddit_detail.csv` at **100%** → 446,319 dated mentions, 971 players, 2023-10-10 → 2026-04-17. Validated vs A52: 2023-24 corr **1.0000**, exact sum match. Still in-memory only — **needs a persist script** |
| **Google Trends weekly series** | Whether the discarded weekly data could be recovered the same way | **DEAD — unrecoverable** | Weekly *was* fetched (`n_weeks=132`) then averaged to a 12-month scalar, and pytrends bypassed `http_cache.sqlite`. Nothing cached to recover. Only a re-fetch that stores the series fixes it |

## Merch / purchase-behavior pathway (probed 2026-08-27)

The hypothesis: attention is "useable" only if it converts into **costly action** — fans
spending real money on a specific player. Stronger than clicks because purchase is costly.
The hypothesis is sound and **remains untested**; both instruments failed, for different
reasons. Neither failure is evidence against the hypothesis.

| Idea | What we actually tested | Verdict | Evidence |
|---|---|---|---|
| **Google Trends commercial intent** — `"<player> jersey"` search volume as purchase intent | Stage-0 probe, 30 players stratified across all 10 `wiki_12mo` deciles, plus a superstar-tier check. `diagnostics/trends_commercial_intent_probe.py` | **DEAD — instrument floor, not a substantive null** | Trends quantizes to a 0–100 integer index, so anything below ~1% of the anchor rounds to zero. Non-zero weeks out of 132: Jack Hughes 91, Quinn Hughes 61, **Brad Marchand 31**, best-in-sample Matthew Schaefer 14, Corey Perry 7, **all 27 others ≤ 2**. Zero of 30 cleared 20 non-zero weeks; only 3 cleared 3. Usable for roughly the top 30–60 names in the league = the same fame-detector problem that killed Jersey Index. `related_queries` also dead: **29/30 returned no rows** (pytrends endpoint broken against current Google) |
| ↳ **anchor artifact — read this before re-probing Trends** | First run of the same probe returned 0/30, including the top decile | **Was a design bug, now fixed** | The string query had been anchored to the **Brad Marchand entity** (A16's `ANCHOR_MID`). An entity aggregates every search about a player, so a long-tail string scaled against one quantizes to zero by construction: `"Connor McDavid jersey"` scores mean **0.015** against the Marchand entity vs **25.6** against jersey-scale queries — 1700x. Any future commercial-intent work must anchor to a commercial-scale query (`"nhl jersey"`, non-zero 132/132 weeks), never to a player entity |
| **eBay API** — listing counts, `bidCount`, `watchCount` as revealed willingness-to-pay | Read the eBay Developers Program Terms of Use and API License Agreement in full, 2026-08-27 | **DEAD — licence, not access** | Four independently disqualifying clauses. (1) **Purpose limitation:** the licence is granted "solely for the purpose of facilitating your own or Your Users' use of eBay Services", and the "Authorized Use" list is exhaustive — research is absent, not merely restricted. (2) **Deletion requirement:** "All intermediate copies must be deleted when they are no longer required for the purpose for which they were created" — a retained research panel is exactly what this forbids. (3) **Derivative ownership:** eBay "shall own any content created or derived therefrom or any form of derivative works". (4) **No bulk distribution** of Restricted APIs data "either in raw or aggregated form", where "Restricted APIs" is defined as those providing "information about market trends, pricing strategies, sales volumes, **user behavior**" — bid/watch counts are user behavior. Collides with criteria 4 (reproducibility), 6 and 7 (shippable artifact). eBay grants written exceptions; chasing one is not a $0-budget move |
| ↳ sold prices specifically | Checked API availability 2026-08-27 | **DEAD — gated** | `findCompletedItems` restricted Oct 2020, Finding API **decommissioned Feb 2025**. Sold data now lives only in **Marketplace Insights**, a Limited Release API that eBay's own docs say is "restricted and not open to new users". Browse API returns active listings only |
| ↳ paid alternatives | PriceCharting, SportsCardsPro, Card Ladder | **DEAD — cost** | All API access is subscriber-only, no free tier. Fails the $0 constraint. PSA's public API is cert verification only — no population report, no prices |

**Where the hypothesis goes instead.** The costly-action test does not need a marketplace.
**#3 Road Tax** (Part 2) is the same claim — *fans spend money because of this specific
player* — measured on ticket purchases, with free structured ESPN attendance data,
home-team×season FE to strip the market, and peer-reviewed precedent (Hausman & Leonard
1997). Data we can retain, publish and own. **Do not re-open a merch pathway before Road
Tax has been run.**

## Killed on contact (tried, failed fast)

| Idea | Why it died |
|---|---|
| Junior-tournament attention → draft stock | Pre-draft Wikipedia coverage collapses: 2025 class R1 47%, R2 22%, R4 3%, R6–7 5% (2024 replicates). The ~48% with pages have them *because* they are already famous — circular |
| Archetype demand forecasting (retail analogy) | 3 seasons = 2 transitions. Not a time series |
| Da/Engelberg/Gao attention → overpay → reversal | No overpayment to revert. The first half is a null |
| Benefit-transfer of a revenue elasticity from another sector | Validity conditions fail (NHL revenue is contracted + shared; the purchasable unit is a team). Also breaks the project's own no-revenue-claims constraint. Replaced by structural comparison, not extrapolation |

## Designed, agreed, not yet run

| Idea | Why it matters | Status |
|---|---|---|
| **OAQ season-to-season stability** — Spearman ρ of the residual across 2023-24 → 2024-25 → 2025-26 | **Load-bearing.** If the residual is not stable, the "durable unpriced asset" thesis collapses and several rows above must be withdrawn | **UNTESTED.** Flagged three times, ~10 min of work. Blocked behind an owner decision: `compute_oaq.py` assumes one row per player and will triple-count the per-season panels — pooled / per-season / panel is unsettled |
| `fr` edition = Quebec, not France | The sign-flip table reads `fr` at 1.82 in Feb 2025 as Quebec. Untested inference | **UNTESTED.** Needs a check that francophone traffic concentrates on Canadian players |
| RFA/UFA redone with `contract_type` | Replaces the dead age-band split | **UNTESTED** |
| MI dispersion magnitude — "top decile delivers N× the attention per cap dollar of the median" | The quotable number (criterion 5) | **UNTESTED** |

## Data-integrity issues found (all still open)

| Issue | Status |
|---|---|
| **Johnny Gaudreau is in the roster pool** — died Aug 2024. His 2026-02-22 memorial spike (**2,130,333 views in one day**) is the single largest observation in the dataset | Real traffic, wrong pool. **Exclude and disclose** |
| `oaq_pilot.csv` has **771** rows vs A10's locked pool of **774** | Reconcile |
| `pytest` cannot collect `test_build_mover_list_a38.py` or `test_expected_cap_a24.py` (`ImportError: cannot import name 'find_2025_26_caphit'`) | The suite aborts before running unless both are skipped. Worse than the "15 stale fixtures" previously recorded |
| No birth-country field anywhere | `/player/{id}/landing` on the NHL API returns `birthCountry` **and** `draftDetails` (verified) — one free call per player fixes both |

---

# Part 2 — Backlog (designed, none built)

> **Status 2026-08-27 — parked, not cancelled.** These seven were designed as extra
> *validation pathways* for a CASSIS poster. The conference is off and the deliverable is
> now a GitHub writeup of the finished index, so none of them are on the critical path and
> **none should be started**. They remain here because the designs are sound and the
> analysis is real — #2 Superstar Whistle and #3 Road Tax in particular are GREEN-data,
> whole-pool, and would each stand alone as a follow-up project if the owner ever wants
> one. #4 Contracts is already answered (see its status note). Read Part 1 first.

## Ranking summary (strength-first)

| Rank | Idea | New? | Strength | Data tier | Build difficulty |
|---|---|---|---|---|---|
| 1 | Sentencing Gap (DoPS) | new | ~9 | AMBER | HARD (LLM rubric-coding, gated F1/κ) |
| 2 | Superstar Whistle (officiating) | new | ~8.5 | GREEN | EASY (join + FE regressions) |
| 3 | Road Tax (road attendance externality) | existing | high | GREEN | EASY-MODERATE (Tobit panel) |
| 4 | Contracts (next-contract residual) | owner's | high | GREEN | MODERATE (next-contract pull) |
| 5 | DFS Price-vs-Crowd (ownership residual) | new | ~8.5 | AMBER-RED | DATA-GATED (free ownership may not exist) |

`#4 Contracts` is the owner's stated economic payoff narrative. It ranks #4 on *strength* (not top-3) because salary feeds the OAQ denominator → "forecasting salary with salary" critique; the contracts-out + temporal-split variant mitigates but never fully erases it. **Recommendation: keep Contracts as the abstract's economic closer for narrative, regardless of its strength rank.**

### Round-2 additions (#6, #7) — banked 2026-06-28

Produced by a SECOND analyst→leader→expert funnel (owner asked for more team-decision ideas). 12 generated → leader cut to 4 → hostile field-leading-statistician gate cleared **2**. Both banked below. The owner added two scoring axes this round: **data-doability** (realist read on obtaining the data FREE at usable coverage, not just the GREEN/AMBER label) and **whole-pool reach** (does it produce a meaningful result for DEPTH players, not just stars — a direct answer to the "is this just a fame detector?" attack). Both winners are GREEN + in-pipeline + whole-pool, so they can ANCHOR rather than just validate.

| Rank | Idea | New? | Strength | Data-doability | Whole-pool reach | Build difficulty |
|---|---|---|---|---|---|---|
| 6 | Sticky Minutes (deployment rigidity) | new | ~8.5 | 9/10 GREEN | 7/10 | MODERATE |
| 7 | Generous Ledger (official-scorer favor) | new | 9/10 (after the team×home fix) | 7/10 GREEN | 8/10 | MODERATE |

**Shared load-bearing falsifier (build into BOTH):** the 8-theme off-ice placebo. A player whose OAQ is driven by *fashion / relationship_viral / off_ice_life* themes who STILL gets the long leash (Sticky Minutes) and STILL gets the scorer's pen at home (Generous Ledger) cannot be "the coach/scorer is correctly valuing hidden two-way skill." Making glamour-theme OAQ the placebo that must read live (and skill-theme OAQ the one that must wash out) converts the set's universal vulnerability ("stars are just better") into its signature rebuttal across two independent pathways. **Prerequisite:** the LLM theme classifier must clear its pre-locked macro-F1 ≥ 0.60 / κ ≥ 0.55 gate before the theme placebo can carry weight.

---

## #1 — The Sentencing Gap
- **Decision-maker:** NHL Department of Player Safety (suspension length + fine).
- **Pitch:** After DoPS's *own published* rubric (infraction type, injury caused, repeat-offender status), does a player's pre-incident buzz still bend the punishment?
- **Cross-domain analog:** Status/notoriety effects in criminal sentencing (high-status defendants buy leniency; high-publicity defendants sometimes draw exemplary harshness). DoPS = sentencing judge; suspension games/fine $ = sentence; OAQ_portable = defendant notoriety.
- **Mechanism:** Regress suspension length (games) and fine ($) on `OAQ_portable` **after** the rubric variables DoPS enumerates in every ruling (infraction category, injury, repeat status, on-ice call). OAQ enters as a residual against a *known* formula. Direction-agnostic (leniency vs exemplary-harshness are both findings; which dominates is the novelty).
- **$0 data:** DoPS rulings pages (public). **AMBER** — prose; pool 2018–2026 → ~250–350 rulings.
- **Identification:** Not circular (outcome shares nothing with index inputs/salary). Temporal split — OAQ measured in a window *before* the incident, so the suspension can't inflate the buzz that predicts it. Not overclaim — rubric controlled → residual labeled a "salience-associated disparity," not intent/corruption.
- **Quotable:** "Same infraction, same injury, same rap sheet — the most-talked-about players serve measurably fewer games than the league's own rubric prescribes."
- **CASSIS fit:** Novelty (index as institutional bias detector) + honest-limit. New independent pathway.
- **Difficulty: HARD.** Build requires an **LLM factor-coder** to extract rubric variables from ruling prose, gated at **F1 ≥ 0.60 / κ ≥ 0.55** vs hand labels before any number ships; then Tobit/Poisson of games+fine on OAQ residualized to the rubric, bootstrap CIs.
- **Why worth it (harder):** the only idea where the institution publishes its own scoring formula → cleanest possible residual design, and the highest-stakes/most-quotable finding on the board (an institutional dollars-and-games double standard) that no easier idea can structurally produce.
- **Kill condition:** abandon if the coder can't clear F1/κ, OR if after rubric controls the high-OAQ suspension count is so thin that bootstrap CIs span zero wider than the effect.

## #2 — The Superstar Whistle
- **Decision-maker:** on-ice referees (and NHL Hockey Ops officiating integrity).
- **Pitch:** Within production-matched cells and with referee fixed effects, high-OAQ players draw penalties/60 UP and take them DOWN — and the asymmetry is the tell.
- **Cross-domain analog:** NBA "superstar foul" bias (Anderson & Pierce) — refs' calls correlate with star status independent of the act. Penalty whistle = foul whistle; drawn penalty = the star's "and-one."
- **Mechanism:** Two outcomes — penalties drawn/60 and penalties taken/60 — within K=10 production-matched cells, adding **referee fixed effects** (4 officials/game from ESPN). The decisive move is the **asymmetry test**: a genuine agitator style pushes *both* up; salience bias pushes drawn UP and taken DOWN. That divergence is what "he just plays chippy" cannot explain. Bonus: which referee crews show the largest star effect.
- **$0 data:** **GREEN** — NHL play-by-play penalties (`committedByPlayerId`/`drawnByPlayerId`/`typeCode`/`duration`) + ESPN referee assignments. ~10k+ penalties/season. *Verified reachable 2026-06-26.*
- **Identification:** Not circular (penalty PBP independent of index inputs); production-matched + market-stripped; referee FE absorb crew tightness; lag OAQ to a prior window to kill "great game → buzz → friendly whistle next night." Report drawn AND taken so the agitator alternative is tested, not assumed away.
- **Quotable:** "The same body-check earns a star a power play and earns a depth guy two minutes in the box — the whistle follows the spotlight, both ways."
- **CASSIS fit:** Triangulation (officiating outcome, untouched by all gates) + the asymmetry as a built-in falsifier.
- **Difficulty: EASY.** All data free/structured, no LLM, no fragile scrape: join penalties to ref assignments, build production-matched cells, two FE regressions, bootstrap.
- **Why worth it (easy):** self-explanatory — GREEN data, huge N, falsifier baked into the design → near-certain clean, defensible result. The portfolio's bankable anchor.
- **Kill condition:** abandon if penalty↔referee join coverage is poor or cells too sparse after FE. If both rates move the *same* direction, that's a published null (mechanism refuted), not a build failure.

## #3 — The Road Tax
- **Decision-maker:** opponent's box office / league scheduling & gate-equity policy.
- **Pitch:** A visiting player's OAQ predicts the *opponent's* home attendance — a road-draw externality the home team banks and the star isn't paid for.
- **Cross-domain analog:** Hausman & Leonard (1997, *J. Labor Economics*) valued an NBA superstar by the road-gate externality he creates for rival teams. Visiting NHLer's `OAQ_portable` = candidate road externality; opponent's home gate = the externality realized.
- **Mechanism:** Regress per-game home attendance on the visiting roster's max/sum `OAQ_portable`, with **home-team × season fixed effects** absorbing home market + arena. Cleanest internal check: the *portable* (market-stripped) number should out-predict the market-included one on the road.
- **$0 data:** **GREEN** — ESPN hidden API returns per-game attendance + venue, structured. *Verified 2026-06-26 (NHL's own API has venue but NO attendance field — use ESPN).*
- **Identification:** Home-team×season FE remove the market (an index denominator component) + arena capacity; OAQ is already production+market-stripped → can't proxy visiting-team quality (add visiting points% as belt-and-suspenders). Not circular (attendance ∉ inputs). Not overclaim (attendance association, not "$ of gate").
- **Quotable:** "A marquee visitor is worth thousands of extra fans through the *opponent's* turnstiles — a gate externality the home club banks and the league doesn't price."
- **CASSIS fit:** Novelty (superstar-externality framing on a market-stripped index) + a genuinely new validation pathway (attendance) + per-claim CIs.
- **Difficulty: EASY-MODERATE.** Attendance panel + visiting-roster OAQ + home×season FE + **Tobit** for sellout censoring + clustered/bootstrap SEs. No LLM.
- **Why worth it (easy):** cheapest path to a textbook-defensible anchor — peer-reviewed precedent + cleanest market-strip + largest N on the board at low build cost.
- **Honest limitation (poster):** NHL attendance is sellout-censored → estimate is a conservative lower bound (Tobit), identified mainly off chronically non-sold-out buildings.
- **Kill condition:** abandon if ESPN attendance feed breaks/loses coverage, OR if sellout-censored fraction > ~70% (Tobit can't identify off a near-constant DV).

## #4 — Contracts (the economic closer)
> **STATUS 2026-08-26 — largely answered, and the answer was a null.** The Part 1
> next-contract test (545 signings) *is* this idea, run. Veteran re-signings return
> **−0.4% per +1 SD, CI [−6.5%, +6.5%]**. What remains unbuilt is the contracts-OUT OAQ
> variant. Honest framing is now about **cost, not value**: a club acquires the attention
> *without paying a premium for it*. The data cannot distinguish "clubs leave money on
> the table" from "attention is worth little to the club because revenue accrues
> league-wide."
- **Decision-maker:** GMs / arbitrators / player agents.
- **Pitch:** Does `OAQ_portable` at season T predict the *residual* of a player's NEXT contract (T+1) after controlling for production (PPG/TOI/on-ice)?
- **Cross-domain analog:** Rosen (1981) "Economics of Superstars" / galáctico marketability premium — clubs pay above sporting value for marketable assets.
- **Mechanism:** Temporal hold-out — regress next-contract value (or AAV) on production controls, take the residual, test association with prior-season `OAQ_portable`. A **contracts-OUT OAQ variant** (rebuild OAQ with cap stripped from the denominator + market correction) is required to blunt circularity.
- **$0 data:** **GREEN** — CapWages/PuckPedia (free); `capwages_slug` already in `players.csv`; current `cap_hits.csv` in repo. Needs a forward next-contract pull (free).
- **Identification:** Circularity is the central risk — `cap_hit` feeds the MI denominator (A4 `expected_cap`) AND the §7/A5 market correction. Mitigate with (a) contracts-out OAQ variant AND (b) strict temporal split (predict the FUTURE contract). Association framing ("associated with contract premiums"), never "the index drives pay."
- **Quotable:** "Attention surplus in one season is associated with a measurable premium on a player's *next* contract, beyond what his production explains."
- **CASSIS fit:** 4th validation pathway (criterion 2) + quotable economic finding (criterion 5).
- **Difficulty: MODERATE.** Forward next-contract data pull + a contracts-out OAQ rebuild + temporal-split regression.
- **Why worth it:** highest decision value of all five (it *is* the "why this matters" dollars story). Strength-ranked #4 only because of the salary-in-denominator circularity shadow; the contracts-out variant + temporal split is what makes it publishable. **Keep as the abstract's economic closer for narrative payoff even though it isn't a strength top-3.**
- **Kill condition:** abandon the headline if the contracts-out OAQ variant can't be cleanly separated from the cap denominator, or if next-contract N (players signing T+1 deals in window) is too thin for a stable residual.

## #5 — DFS Price-vs-Crowd Divergence
- **Decision-maker:** league/sponsor demand analysts (and the cleanest econometric identification of the set).
- **Pitch:** Give two players the same DraftKings salary (house-set production price) and the crowd still rosters the high-OAQ name far more — pure popularity demand at a fixed price.
- **Cross-domain analog:** Keynesian beauty contest (DFS tournaments: you roster who you think *others* will roster; salient names become "chalk") + price/volume divergence in equities (liquidity follows salience even when fundamentals don't move). DK salary = market-maker's production price; ownership % = crowd quantity demanded.
- **Mechanism:** Regress ownership % on DK salary (the price) and projected points (production); the residual is demand price/production can't explain. Test whether `OAQ_portable` predicts residual ownership. The salary *is* the production control — the book's own valuation.
- **$0 data:** DK salaries **GREEN**; actual contest ownership % **AMBER-RED** — no clean free API at scale; partial/delayed third-party post-contest data, or pre-contest projected ownership as a one-step-removed proxy.
- **Identification:** Ownership ∉ index inputs → not circular. Two-sided market means the production price is observed, not estimated (strongest control of the new set). Association only (DFS players aren't claimed to "see" the index). Use a pre-draft OAQ window to lock temporal order.
- **Quotable:** "On DraftKings, two players priced identically draw different crowds — the high-OAQ name gets rostered in materially more lineups for zero extra expected points."
- **CASSIS fit:** Triangulation (price + quantity in a two-sided market) — distinct revealed-preference pathway.
- **Difficulty: DATA-GATED.** Modeling is trivial; the entire build risk is sourcing free actual ownership % at scale. DFS leverage/chalk also confounds "pure attention."
- **Why worth it (conditional):** cleanest identification on the board *if* the data exists — an explicit price next to an explicit crowd quantity. Carries a real existential data risk.
- **Kill condition:** **de-risk data FIRST** — secure/scrape a retrospective free ownership source and ship a hand-collected proof-of-concept slate before committing. If free *actual* ownership doesn't exist at scale, abandon (projected ownership tests a crowd-*guess*, not a crowd-*action* — much weaker).

## #6 — Sticky Minutes (deployment rigidity)
- **Decision-maker:** Front office auditing whether coach deployment is win-maximizing or name-distorted ("are we playing the player or the brand?"). Deployment is a free, in-house lever — knowing it's status-skewed is edge. Secondary: player agents (usage manufactures the counting stats that price the next deal).
- **Pitch:** When a star slumps he sheds LESS ice time than an equally-cold nobody. `OAQ_portable` predicts the downside-asymmetric rigidity of a player's deployment — a salience-driven labor friction a team can fix to reclaim marginal wins.
- **Cross-domain analog:** Camerer & Weber (1999) NBA sunk-cost — high draft picks keep minutes controlling for performance (escalation of commitment); + Lindbeck–Snower insider/outsider theory. Salience replaces draft slot as the status protector.
- **Mechanism:** Player-game panel (~774 skaters × full season). Outcome = even-strength TOI_ig. Key term = within-player rolling-form deviation (demeaned 5–10-game points/60 or on-ice xG) × `OAQ_portable`, with player + opponent + game-state + season FE. Test the **downside asymmetry**: do high-OAQ players show lower TOI-sensitivity to *negative* form? Cluster/block-bootstrap by player. Optional robustness arm (from analyst D2): deployment-richness (PP1 share, OZ-start ratio, leverage TOI) + diminishing marginal-return — a side check, not the spine.
- **$0 data + tier:** NHL API PBP + TOI + rosters/schedule. **GREEN**, already in pipeline. cap_hit control GREEN.
- **Identification / anti-circularity:** Player FE absorbs the OAQ level and "stars are just better" mechanically — only the interaction SLOPE is identified, off within-player form variation (a second moment the K=10 matching never touches). TOI is a season-level matching variable → **condition on season-average TOI** to isolate the deployment slope from the matched level. Placebos: swap in team-market baseline → must be null; net-sentiment → must be null. **Headline-metric falsifier:** must hold for `OAQ_portable`, not just `OAQ_observed`.
- **Quotable:** "A slumping star keeps ~X% more of his ice time than an equally-cold teammate — the bench plays the name."
- **CASSIS fit:** Novel deployment-elasticity framing (criterion 1); a fully independent GREEN pathway with huge N (criterion 2); block-bootstrap CI (criterion 4); ships as an interactive deployment-rigidity notebook (criterion 7).
- **Difficulty: MODERATE.** Large clean GREEN panel; work is the rolling-form feature + the FE/interaction spec. No scraping, no LLM (except the optional shared theme placebo).
- **Why worth it:** The strongest *defensible* item on the round-2 board — the FE stack genuinely defeats the two mechanical rebuttals, Camerer–Weber is accepted precedent in another sport, and it is self-evidently a free in-house governance lever a front office acts on the same day. **Expert verdict: IMPRESSES (clears outright).**
- **Hardest objection + answer:** "The coach observes more than your rolling points/60 — the leash is *earned* two-way value, so OAQ just proxies real quality." The FE stack doesn't fully reach this; the **off-ice-theme placebo closes it**: a fashion/relationship-famous player keeping his minutes through a slump cannot be "hidden two-way value." Build the theme placebo as load-bearing.
- **Data-doability: 9/10** — highest in the set. Pure in-pipeline TOI + PBP; rolling-form is light feature engineering; zero scraping; one pull the repo already makes.
- **Whole-pool reach: 7/10** — every player has within-season form swings and TOI to vary, so the elasticity is estimable for depth AND stars. Asterisk: bottom-six TOI is floor-compressed (an 8–11-min 4th-liner physically can't shed much ice), so the depth elasticity is attenuated/noisier — "works for depth guys," but with that caveat, not flatly.
- **Kill condition:** form_dev × OAQ interaction CI includes 0 with player FE + cap_hit control, OR it survives only for `OAQ_observed` but NOT `OAQ_portable` (= market hype, not portable salience → fails the headline-metric test).

## #7 — Generous Ledger (official-scorer favor)
> **STATUS 2026-08-31 — still UNBUILT, and confirmed as the only route to the
> "does attention buy softer judgment" question.** Considered for the public dashboard
> and dropped: it needs **player × game** data split home vs road, and the repo currently
> holds only MoneyPuck season aggregates (`raw/moneypuck_skaters_2025.csv`, one row per
> player-situation, no venue split). The NHL play-by-play fetch below is real work, not a
> dashboard edit. A cheaper season-level substitute was tried and **died** — see the
> pest-hypothesis row in Part 1: `OAQ_portable` has no season-level association with PIM/60
> (ρ=0.131) or hits/60 (ρ=0.012), which says nothing about the *home-minus-road* effect
> this idea actually targets. The season-level null does **not** kill #7; it only confirms
> that the venue split is where the whole idea lives.
- **Decision-maker:** Acquiring analytics dept (discount a target's soft-stat totals before you trade for him) + league hockey-ops (official-scorer standardization). Secondary: agents who lean on inflated hit/takeaway totals in arbitration.
- **Pitch:** The discretionary half of the box score (hits, takeaways, giveaways, blocked shots, secondary assists) is awarded by a home-team official scorer's judgment. Test whether a player's discretionary rate bends with `OAQ_portable` specifically *at home*, where the scorer's pen lives; the hard half (goals, faceoffs, xG-shots) is the built-in placebo and must stay flat.
- **Cross-domain analog:** Home-scorer "rink-counting" bias in baseball/hockey official scoring + status bias in expert rating (prestige names scored more generously). The official-scorer cousin of referee bias — a genuinely NEW institution, distinct from the referee (#2) and DoPS (#1) surfaces the top-5 already own.
- **Mechanism:** Player × game. `discretionary_rate ~ OAQ_portable × home_flag + production_controls + opponent_FE + season_segment`, with player FE. Live coefficient = the OAQ×home interaction (within-player home-minus-road gap scaled by fame). Decisive move: the IDENTICAL spec on OBJECTIVE events must read null; neutral-site/outdoor games (no home booth) must attenuate.
- **$0 data + tier:** NHL API PBP (events by playerId/typeCode/home-away/venue + coords for xG). **GREEN**, in-pipeline.
- **Identification / anti-circularity:** Discretionary box events are not index inputs. Player FE + within-player home/road differencing isolates scorer discretion, orthogonal to season-level fame → cannot loop back into OAQ. Two internal placebos: objective-event null + neutral-site attenuation.
- **REQUIRED FIX (build from day 1 — this is what makes it clear the expert gate):** the home official scorer is a **team-level instrument** — one scorer per rink applied to every home game — so player FE does NOT remove it; the OAQ×home slope is otherwise a team-scorer × roster-composition artifact (high-OAQ players may cluster on generous-scorer teams). **Add a team-season×home effect (per-rink home-generosity term) and identify OAQ×home off TEAMMATES who share the same home scorer.** High-OAQ vs low-OAQ on the same bench, same rink, same scorer: if the famous one's home-road discretionary gap is larger, that's scorer favoritism net of the rink. Cheap (no new data); converts the single confound into the cleanest identification in the set.
- **Quotable:** "A star's hits and takeaways grow at home and shrink on the road; his goals don't — the soft box score bends toward the famous name, but only where the home scorer holds the pen."
- **CASSIS fit:** Novel institution (criterion 1 — the most methodologically novel item on the round-2 board); three internal checks = objective placebo + neutral-site placebo + home/road differencing (criterion 2); player-clustered bootstrap CI (criterion 4); quotable (5); honest "no intent claimed, only association in discretionary counts" (6).
- **Difficulty: MODERATE.** Discretionary-vs-objective taxonomy + xG model + the team×home spec — real but standard work; no new scraping, no LLM (except the optional shared theme placebo).
- **Why worth it:** Strongest *novelty* on the board (a brand-new institution) plus a concrete acquiring-team decision ("discount Player X's hit/takeaway totals by Y% before you trade for him"). **Expert verdict: CONDITIONAL → IMPRESSES once the team×home fix is in.** Without the fix the team-scorer confound is a legitimate committee-floor objection.
- **Hardest objection + answer:** "Stars genuinely hit/steal more and home teams play a different style — the gap is real hockey." A real-skill/style story makes the gap appear on OBJECTIVE events too and does NOT grade by OAQ; the signature requires the bend to be discretionary-ONLY and OAQ-graded. FE differences out style; the objective-event null falsifies skill; the team×home fix kills the scorer-clustering confound.
- **Data-doability: 7/10** — one clean PBP pull, partly in-pipeline; venue + home/away + typeCode are genuinely exposed in api-web.nhle.com. Extra work = the xG model + the discretionary/objective taxonomy + the team×home spec (standard, not novel).
- **Whole-pool reach: 8/10** — strongest-but-one. Grinders/depth players generate ample hits/blocks/takeaways (often MORE than stars), so the interaction is estimable pool-wide, not star-only. Directly rebuts "fame detector."
- **Kill condition:** OAQ×home on discretionary events has a 95% bootstrap CI overlapping zero (after the team×home spec), OR the same interaction is equally significant on objective events (catching real home-style/skill, not scorer discretion).

---

## Ideas considered and cut (recorded so they aren't re-proposed)

**Cut on strength/feasibility this round:** Halo Star / Three Stars (soft stakes), Situation-Room video-review (power-fatal subjective-challenge N), Fantasy ADP reach (coverage thins below fantasy tier + buzz leaks into Wiki/Reddit inputs), Sportsbook prop-market breadth (RED data + zero-variance risk if menus standardized), Award-futures name premium (star-tail only, reads as award-vote re-skin). **Existing ideas out-ranked into the backlog tail:** Cardboard Market / card price (anti-bot RED), Traction Curve (fuzzy outcome, heaviest multi-season lift), Eyeballs Test (~100 national games/season, power-fragile — note national-game ID itself is GREEN via NHL API `tvBroadcasts.market`).

**Prior brainstorm casualties (do not re-propose without strong reason):** national-TV game selection (can't separate player from team buzz), trade draft-pick return / galáctico (small N, imprecise pick charts), key-man attendance (non-random scratches), attention concentration / portfolio (sellout-censored variance), event poster billing (subjective, small N), bobblehead/giveaway selection (thin N, sponsor-driven), NHL.com editorial featuring (near-circular), tentpole event casting (small N + rotation rules), social-follower velocity (botted target), niche→mainstream news via GDELT (entity-match noise + Reddit-is-an-input).

**Round-2 cuts (2026-06-28 funnel — do not re-propose):**
- **Gravity Tax** (opponent-coverage / NBA "gravity": does a high-OAQ skater draw a heavier share of the opponent's shutdown unit?) — strongest cut, but identification leans on a CONTESTABLE shutdown-unit definition + a theme-placebo dependency, it's the HARDEST compute (shiftchart head-to-head matrices), and reach is star-tilted (depth players draw no shadow → degenerate). Salvage tweak: continuous "share of opponent's highest-TOI-against matchup" instead of a subjective shutdown-unit def — raises rigor/doability but does NOT fix the star-tilted reach.
- **Buzz Hangover** (attention-reversal: at fixed AAV/term/production, the higher-OAQ contract is the one later bought out / buried / retained-salary-traded) — power-fatal: a competing-risks hazard over only ~40 pooled rare regret events won't survive a hostile CI; dead-cap extraction is an AMBER per-player slog.
- **Jersey Index** (merch top-25 list as revealed willingness-to-pay) — best instant value of the cuts, but a Top-25 outcome is STAR-TIER-BY-CONSTRUCTION → near-zero whole-pool reach, makes the "fame detector" attack literally true; sporadic AMBER prose, ~25 names/release.
- **Marquee Window** (broadcasters allocate more premium national windows to high-buzz rosters) — TEAM-level outcome → no depth-player result (reach N/A); needs a heavy historical-lite OAQ rebuild as a gating dependency; only partially escapes the original national-TV cut.

**Round-2 survivors NOT banked (kept only as satellites — did not clear the hostile-expert bar standalone):**
- **Clause Premium** (at equal AAV/term/production, higher OAQ buys NTC/NMC control rights + signing-bonus share — Bebchuk-Fried non-price rents; orthogonal to #4 which is the dollar *level*). The single best *decision* on the board and respected economics, BUT whole-pool reach 3/10 (clauses are structurally star-tier-only → the "fame detector lives in the star tier" attack made literal) + data-doability 4/10 (NTC/NMC presence is roughly GREEN but clause STRENGTH + bonus-split are AMBER partial-coverage per-player parse, and cap_hit eats the OAQ variance on thin UFA rows). Keep ONLY as a paired star-tier satellite, bonus-share-led, framed conditional-on-UFA-eligibility — never an anchor.
- **Bankability Concordance** (OAQ_portable agrees with the intangible residual in EA NHL ratings, a free Q-Score). Whole-pool reach 8/10 + cheap one-time structured scrape, BUT it is convergent VALIDATION not a decision (fails the "useful to a team" half), AND EA is NOT independent of OAQ — EA's ratings team reads the same public narrative that drives the index inputs, so concordance is partly trivial. Keep ONLY as a cheap whole-pool "is OAQ real?" triangulation arm with the shared-narrative non-independence stated openly on the poster — never a headline.
