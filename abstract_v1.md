# The Marchand Index: A Peer-Matched, Cap-Adjusted Model of NHL Fan Attention

**Submitted to:** Cascadia Symposium on Statistics in Sports (CASSIS), September 12, 2026. **Format requested:** Oral.

---

The Marchand Index identifies NHL skaters whose public fan attention exceeds what their on-ice skill and team market would predict, then scales that surplus by cap hit to estimate attention efficiency. In practical terms, it asks which players generate the most stand-alone fan-demand signal per salary-cap dollar. Public hockey analytics has strong measures of on-ice contribution, Expected Goals, GAR, RAPM, Corsi and its descendants, but the off-ice side remains under-modeled. To my knowledge, no public estimator isolates player attention with peer matching, market control, cap adjustment, uncertainty intervals, and pre-registered validation.

The model has two layers. The **Off-Ice Attention Quotient (OAQ)** is a player's public-attention residual after comparison to K=10 statistically similar skaters. The **Marchand Index** is the cap-adjusted version of that residual: market-adjusted OAQ divided by annual cap hit. This is not a revenue model, but attention is treated as a public proxy for fan demand, then tested against independent outcomes that should move with fan demand such as jersey demand, fan voting, signing-related team-account growth, and held-out video attention.

A pre-registered 14-player pilot, locked before data collection, provides early proof of concept that our adjustment layer changes the leaderboard it is designed to change. Within the pilot, only three of the five players topping the raw-engagement list remained in the top five after cap and market adjustment: Bedard, Hughes, and Crosby stayed; Marchand and McDavid were displaced by Brady Tkachuk and Kucherov. The pilot used only the free-path signals available at fetch time: Wikipedia pageviews and Google Trends, with Reddit and Instagram dropped under the pre-specified null-signal rule. It is therefore a worked example, not leaguewide validation. This supported finding is narrow but important: even in a small, hand-auditable set, the index is not just a popularity ranking.

At CASSIS, the presentation will report the completed leaguewide K=10 OAQ and Marchand Index for active NHL skaters, bootstrap confidence intervals, match-quality flags, pre-registered validation-gate verdicts, and case studies of players whose attention efficiency is unusually high or low.

## 1. Method

For each active NHL skater, the model computes a 12-month **Current Engagement Score (CES)** from the public attention signals: Wikipedia pageviews, Google Trends search interest, Reddit mention and vote volume, and Instagram follower count. The signals are standardized before combination because they live on different scales. Volume and sentiment are tracked separately; sentiment is excluded from CES so a polarizing player is not treated as less valuable simply because the attention is mixed. A career-long **Brand Depth Score (BDS)** captures established reputation through career Wikipedia traffic, jersey-list appearances, All-Star selections, service years, and captaincy. Raw engagement combines current attention and brand depth.

The key methodological choice is to compare each player only to similarly skilled peers, not to the league average. A league average would make depth players look invisible and stars look automatically valuable; a single best peer would be too fragile. K=10 is used as a stable comparison group large enough to reduce one-player noise but small enough to preserve role-specific comparisons. Peer similarity is computed with Mahalanobis distance over position, age, points per game, time on ice, 5v5 points/60, role band, and NHLe-adjusted production. Mahalanobis distance is used because the inputs are correlated, players with more points often play more minutes, and the distance should not double-count one kind of skill. If a player has no close peer group, the row is flagged `match_quality=low` rather than treated as a clean estimate.

\[
\text{OAQ}_{observed}(P) =
\text{engagement}_{raw}(P) -
\overline{\text{engagement}_{raw}}_{\text{K=10 peers}}
\]

`OAQ_observed` measures attention above skill-matched expectation in the player's current context. `OAQ_portable` additionally removes a team-market baseline before the peer comparison. Reporting both lenses is necessary because "who draws attention here?" and "what attention would travel with the player?" are different front-office questions. The headline metric is:

\[
\text{Marchand Index}(P) =
\text{OAQ}_{portable}(P) / \text{cap hit}_M(P)
\]

Cap hit is the denominator because NHL teams operate under a hard salary cap; raw attention without cost context is incomplete. Every published player score is shipped with a 95% bootstrap confidence interval so the leaderboard shows uncertainty rather than only point estimates. A supporting LLM classifier decomposes Reddit attention into themes such as skill, fighting, personality, style, controversy, charity, and relationship/viral attention, but it is not part of OAQ. Theme findings are reported only if a 300-comment hand audit clears the pre-declared accuracy floor.

## 2. Pilot Evidence

The pilot was designed as a stress test, not as a league sample. The 14 players were locked before data collection and chosen to span archetypes the model must handle: elite production, legacy reputation, polarizing identity, low-skill/high-attention role players, market-amplification cases, cultural crossover, and rising salience from a rookie baseline. The full model does not inherit this hand-curation; it runs on active NHL skaters.

The pilot confirmed the rank-reordering pattern: raw-engagement top five were Marchand, Bedard, McDavid, Hughes, and Crosby; Marchand Index top five were Brady Tkachuk, Bedard, Hughes, Kucherov, and Crosby. Two pre-registered pilot patterns were disconfirmed in the same diagnostic direction. Both traced to the pilot market-baseline proxy, which used roster-mean Wikipedia pageviews and therefore over-corrected players sharing a roster with high-pageview teammates. For that reason, the pilot lower ranks are treated as diagnostic only; the full build reports both observed and portable OAQ, publishes match-quality flags, and lets the validation gates determine the final claim shape.

The figure below reports only the supported pilot finding: top-five rank reordering after cap and market adjustment.

![](pilot/figure.png)

## 3. Validation Plan

The full-build validation plan is pre-registered ahead of production modeling. No gate is reported as passed here; these are pre-declared tests and cutoffs that determine whether claims are published, downgraded, or removed. The thresholds are decision rules, not universal constants; their value is that they are written down before seeing leaguewide results.

| # | Gate | Test | Floor / Target |
|---|---|---|---|
| 1 | Jersey-list correlation | Spearman rho, `OAQ_portable` top-50 vs. NHL annual top-20 jersey list | rho >= 0.40 / 0.50 (target = large-effect benchmark; floor set above medium) |
| 2 | All-Star fan-vote correlation | Spearman rho, `OAQ_portable` vs. fan-vote share, 2022 / 2023 / 2024 | rho >= 0.45 / 0.55 (one notch above Gate 1: fan vote is a more direct attention measure) |
| 3 | Signing event study | Difference-in-differences on top-50 free-agent signings since 2020: 60-day team-account follower delta on signed-player `OAQ_portable`, team fixed effects, season fixed effects, cap hit, and position | Direction positive / p < 0.05 (small, noisy signing sample; significance is the target, not the floor) |
| 4 | Stratified generalization | Held-out YouTube view-count residuals, with channel, clip, market, career-length, and on-ice controls; Spearman rho on the outside-star pooled cohort, with star / regular / depth sub-results reported | rho >= 0.25 / 0.35 outside-star (lower bar: outcome is a residual after heavy on-ice + market controls) |
| 5 | Theme classifier audit | Macro-F1 and Cohen's kappa on 300 stratified hand labels; gates theme findings only | F1 >= 0.60 / 0.70 (pre-set usability floor); kappa >= 0.55 / 0.65 (Landis-Koch moderate / substantial) |

The first three gates test whether OAQ aligns with fan-attention outcomes that hockey people already recognize: jersey demand, fan voting, and team-account growth around signings. Gate 4 addresses the most obvious failure mode: a model that merely rediscovers stars. Players are pre-sorted into star, regular, and depth bands using only non-attention variables, with percentile rules that automatically rebase as the league changes. YouTube outcomes are independent of CES, BDS, OAQ, and the Marchand Index. A failed Gate 4 removes the role/depth-player framing from the final findings. The classifier audit gates theme interpretation only; failed theme labeling cannot invalidate the headline OAQ.

Four hypotheses are also pre-registered and reported with effect sizes and confidence intervals regardless of direction: polarizing players should outperform matched non-polarizing peers on the Marchand Index; cultural-crossover players should carry more portable attention than cap percentile alone predicts; documented viral events should produce attention persistence at least six months beyond the event; and off-ice-driven attention should be more theme-concentrated than skill-driven attention.

## 4. Contribution and Limits

The contribution is a public, reproducible estimator for attention efficiency: skill-matched off-ice attention, market-adjusted for portability, then scaled by cap hit. The method is intentionally modular. Peer matching, dual market lenses, confidence intervals, validation gates, and optional theme interpretation. The same framework can transfer to other professional leagues with public engagement signals.

The limits are explicit. Attention is a proxy for fan demand, not revenue. Goalies are excluded from headline analysis because their skill metrics are structurally different from skater metrics. Stars and rookies can have weak peer groups, so match quality is published beside every player score. X/Twitter is unavailable on the free path, and Instagram is limited to follower-count snapshots. The pilot is a proof-of-concept only; the leaguewide K=10 run and validation gates determine our final findings.

**Selected references.** Vollman R., *Hockey Abstract* (NHLe). Bacon P., updated NHLe. Davis J., *Pick224* (pGPS peer matching). Imbens G., Rubin D. (2015), *Causal Inference for Statistics, Social, and Biomedical Sciences* (matching estimators). Reddit / Wikimedia REST / pytrends API documentation.

<sub>Adam Noakes · ana178@sfu.ca</sub>
