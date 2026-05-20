# The Marchand Index: A Cap-Adjusted Off-Ice Attention Quotient for NHL Players

**Submitted to:** Cascadia Symposium on Statistics in Sports (CASSIS), September 12, 2026. **Format requested:** Oral.

---

NHL front offices increasingly weigh off-ice fan attention — jersey sales, ticket demand, social engagement, viral moments — alongside on-ice production when valuing players, yet no public, reproducible metric isolates a player's off-ice draw from their skill. We introduce the **Off-Ice Attention Quotient (OAQ)**: each player's public-attention residual against a K=10 peer group of skill-equivalent NHLers. Cap-adjusting OAQ yields the **Marchand Index**, a per-dollar measure of off-ice value. Market amplification is controlled by reporting both raw (`OAQ_observed`) and team-baseline-stripped (`OAQ_portable`) variants. We validate the composite against three independent observable outcomes (NHL annual jersey list, All-Star fan vote, free-agent signing event study), audit the LLM-derived theme classifier against 300 hand-labeled comments (macro-F1 + Cohen's κ), and pre-register four hypotheses before the model is run on production data.

## 1. Motivation

Public hockey analytics has comprehensively modeled on-ice value (xG, GAR, RAPM, Corsi-family). The off-ice side — what drives merchandise, ticket, sponsorship, and viewership demand — remains effectively unmodeled in public work. Front offices ask: *which players generate fan attention beyond what their production alone predicts, and which deliver that attention efficiently relative to cap hit?* The data to address this — Reddit, Wikipedia pageviews, Google Trends, public Instagram counts, NHL official social, public cap data — is free. The missing piece is a method that isolates the off-ice component from skill.

We do not claim to measure revenue. We measure **public attention as a proxy for fan demand**, validated against three observable revenue-correlated outcomes. The metric is named after Brad Marchand: a high-skill player whose public salience and polarizing identity exceed what peer-matched production predicts. He is the canonical case the index is built to detect.

## 2. Method

**Engagement composite.** For each of ~700 current NHLers — **including role and depth players, who are central to the thesis** — we compute two volume-only signals from publicly available social engagement sources: a 12-month **Current Engagement Score (CES)** — a weighted z-score over Wikipedia pageviews, Google Trends, Reddit mention and upvote volume, Instagram follower count, and additional platforms (TikTok, X, YouTube, NHL official accounts) where public data are available — and a career-to-date **Brand Depth Score (BDS)** — Wikipedia pageview mean, NHL jersey-list appearances, All-Star selections, service years, captaincy duration. Net sentiment and polarization are computed but stored as **separate output dimensions**; they are never folded into CES, because doing so systematically penalizes polarizing players (Marchand, Tkachuk, Reaves) — precisely the players the index is designed to surface.

**Peer matching.** For each player *P*, we identify K=10 nearest neighbors in standardized on-ice skill space (position, age, PPG, TOI/G, points/60 at 5v5, role band, NHLe-adjusted production) using Mahalanobis distance with cohort-specific feature scaling. Players whose median pairwise distance to their peer set exceeds the 75th percentile of NHLer-pair distances receive a `match_quality = low` flag; their OAQ is shipped but visibly caveated.

**OAQ — observed and portable.**
$$\text{OAQ\_observed}(P) = \text{engagement\_raw}(P) - \overline{\text{engagement\_raw}}_{\text{K=10 peers}}$$
**`OAQ_portable` subtracts the player's team-market baseline before peer comparison** — i.e. it estimates the attention that would travel with the player if signed elsewhere, stripped of their current team's media-market amplification. Both lenses are reported. `OAQ_observed` answers *"who is currently the biggest commercial asset?"*; `OAQ_portable` answers *"if signed elsewhere, what attention would this player bring?"* — the harder claim. **`OAQ_portable` is the headline metric** because it survives the strongest objection (*"isn't Marner just famous because he plays in Toronto?"*).

**Marchand Index.** $\text{MI} = \text{OAQ\_portable} / \text{cap\_hit}_M$. Reported with per-player bootstrap 95% CIs (1,000 resamples of the player's mention pool).

**Theme decomposition (validated).** An OpenRouter-hosted LLM classifies each Reddit comment into one of eight themes (`skill, fight, personality, fashion/style, off-ice life, controversy, charity/community, relationship/viral`). The classifier is **audited against 300 stratified hand-labeled comments before any theme-based finding is reported**: macro-F1 ≥ 0.60 and Cohen's κ ≥ 0.55 are required as ship-floor thresholds (targets 0.70 / 0.65). The confusion matrix and per-theme F1 are published in the supplementary report.

**Why not just rank by the NHL jersey list?** The jersey list is a coarse top-20 we use as a *validation target*, not as the metric — OAQ is continuous across ~700 players, isolated from skill, and decomposable into themes.

## 3. Validation plan and pre-registration

Four independent rigor gates, each with a target and a ship-floor:

| # | Gate | Floor / Target |
|---|---|---|
| 1 | Spearman ρ(`OAQ_portable` top-50, NHL annual top-20 jersey list) | ≥ 0.40 / ≥ 0.50 |
| 2 | Spearman ρ(`OAQ_portable`, All-Star fan-vote share), seasons 2022/2023/2024¹ | ≥ 0.45 / ≥ 0.55 |
| 3 | DID regression: 60-day team-account follower delta ~ signed-player `OAQ_portable` + team FE + season FE + cap-hit + position, top-50 FA signings since 2020 | directionally positive / p < 0.05 |
| 4 | Theme classifier: macro-F1, Cohen's κ on hand labels | 0.60 / 0.55 (F1); 0.55 / 0.65 (κ) |

¹ The 2024-25 NHL All-Star Game was replaced by the 4 Nations Face-Off; only 2022/2023/2024 fan-vote totals are available. This is stated transparently.

**Pre-registration.** Four hypotheses — on polarization, cultural crossover (mentions outside hockey subreddits), viral-event persistence (≥6-month attention decay), and theme concentration (Herfindahl on theme shares) — are committed to a public repository **before** the model is run on production data. All four are reported with effect sizes + 95% bootstrap CIs and a `confirmed / disconfirmed / inconclusive` verdict, regardless of direction. Failing to find a predicted effect is a publishable result.

## 4. Preliminary result and sensitivity finding (worked-example pilot)

*Pre-registered before fetch: `pilot/preregistration.md`, commit `9774a68` (2026-05-20). N=14 NHLers spanning skill (McDavid, MacKinnon, Makar, Draisaitl, Matthews, Kucherov), legacy (Crosby), polarization (Marchand, M. Tkachuk, B. Tkachuk), role-player archetype (Reaves), market-test (Marner — post-trade VGK), rising salience (Bedard, Hughes). Worked example with K=5 restricted peer candidates within the 14; **not** validation of the full leaguewide K=10 method. Composite signals available in the pilot: Wikipedia 12-mo pageviews + Google Trends 12-mo mean (Reddit and Instagram unavailable in the pilot window; pre-reg sentinel handling renormalized weights across available signals).*

The pilot pre-registered three falsifiable expected patterns. Honest report: **P3 confirmed (≥2 top-5 rank flips between raw-engagement ranking and Marchand-Index ranking); P1 and P2 disconfirmed**. Per pre-registered §11 of `pilot/preregistration.md`, two-of-three disconfirmation triggers a fallback to a schematic figure, and the actual result is reported as a sensitivity finding rather than as a headline number. **The disconfirmation is informative, not catastrophic** — it surfaces a real methodological tension the full build must address:

The pilot operationalized `team_market_baseline` as the **mean of rostered players' Wikipedia 12-month pageviews**, excluding the focal player. This proxy conflates two distinct things — *the team is in a large media market* and *the team has other star players with high individual profiles*. Concretely, Florida's roster mean is high partly because Matthew Tkachuk is on it; San Jose's roster mean is high partly because Macklin Celebrini is on it. The mechanism therefore **over-corrects** for Marchand (FLA) and Reaves (SJS), pushing both into negative `OAQ_portable` despite their being the archetype cases the index is built to surface. This is exactly the limitation foreshadowed in §5 ("team baseline does not separate 'this team has stars' from 'this team is in a large media market'"); the pilot makes it concrete. The full build replaces the proxy with a true media-market signal (team-account follower count + arena attendance + market-population control) and adds the validation gates described in §3.

The pilot also confirmed P3: rank flips between raw popularity and the Marchand Index occur in the top-5 even with the over-correcting baseline, demonstrating that the cap- and market-adjustment dimension is doing real work and is **not** a re-skin of popularity. A schematic version of the side-by-side rank diagram appears here; the actual pilot CSV, preregistration, and pattern-evaluation script are released alongside this submission.

## 5. Contribution and honest limits

**Contribution.** To our knowledge this is the first publicly reproducible peer-matched, market-controlled, cap-adjusted off-ice attention metric for NHL players, with a hand-validated LLM theme decomposition and pre-registered hypotheses. The full-build universe is all ~700 active NHLers; surfacing high-OAQ **role and depth players** (the Reaves archetype) is a primary intended finding, not an incidental one. The framework generalizes to any league with public engagement signals.

**Limits explicitly accepted.** (1) Attention proxies revenue; the dollar denominator on the revenue side is not ours to assert. (2) Market control is approximated, not perfect — `team_market_baseline` does not separate "this team has stars" from "this team is in a large media market". (3) X / Twitter engagement metrics are unavailable (free API removed); follower-count snapshots only. (4) Goalies are excluded from the headline analysis — peer matching breaks down on a categorically different skill profile. (5) Stars and rookies have few good peers; match-quality flags are shipped per-player. (6) The N=14 pilot is a worked example with restricted peer candidates; full leaguewide K=10 results are post-submission.

**Reproducibility.** Submission package includes the pilot pre-registration document (committed prior to fetch), pilot scripts, pilot CSV, and a public link to the project repository. The hand-labeled theme-classifier validation set is a Wk 5 build deliverable released later in the project timeline, not at submission.

## Selected references

- Vollman R. *Hockey Abstract* — NHLe coefficients.
- Bacon P. — Updated NHLe.
- Davis J. *Pick224* — pGPS peer-matching methodology.
- Imbens G., Rubin D. (2015). *Causal Inference for Statistics, Social, and Biomedical Sciences* — matching estimators.
- Reddit / Wikimedia REST / pytrends API documentation.

---

<sub>Adam Noakes · ana178@sfu.ca</sub>
