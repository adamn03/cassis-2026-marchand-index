# The Marchand Index: A Peer-Matched, Cap-Adjusted Model of NHL Fan Attention

**Submitted to:** Cascadia Symposium on Statistics in Sports (CASSIS), September 12, 2026. **Format requested:** Oral.

---

The Marchand Index identifies NHL players whose public fan attention exceeds what their on-ice skill and team market would predict, then scales that surplus by cap hit to estimate attention efficiency. Public hockey analytics has comprehensively modelled the on-ice side — Expected Goals, GAR, RAPM, Corsi and its descendants — but no peer-matched, cap-adjusted, market-controlled estimator exists in the public literature for the off-ice component. We introduce the **Off-Ice Attention Quotient (OAQ)**: the residual between a player's measured public attention and the mean attention of their K=10 nearest neighbours in standardized on-ice space (Mahalanobis distance over PPG, TOI/G, points/60 at 5v5, role band, NHLe-adjusted production, age, position). The **Marchand Index** is OAQ divided by annual cap hit ($M). Market amplification is separated by reporting two flavours of OAQ — `OAQ_observed` (raw) and `OAQ_portable` (team-market-baseline-stripped, the attention component that would travel with the player if signed elsewhere); the portable variant is the headline. The estimator is paired with a pre-registered four-gate validation plan and an audited LLM theme classifier as a supporting interpretability layer.

A pre-registered 14-player pilot — locked before any data was fetched — provides early proof-of-concept that the adjustment layer can materially reorder attention rankings. Within the pilot, only three of the five players topping the raw-engagement list remain in the top five after cap- and market-adjustment: Bedard, Hughes, and Crosby stay; Marchand and McDavid are displaced by Brady Tkachuk and Kucherov. Even on a 14-player set, the index is not a relabelling of popularity.

## 1. Method

For each active NHLer $P$ we compute a 12-month **Current Engagement Score (CES)**: a z-scored weighted composite of Wikipedia pageviews, Google Trends search interest, Reddit mention and vote volume, and Instagram follower count. Volume and sentiment are tracked as separate dimensions; sentiment is excluded from the score itself so that polarizing players are not penalised for being controversial — precisely the players the index is built to surface. A career-to-date **Brand Depth Score (BDS)** captures established reputation: career Wikipedia traffic, jersey-list appearances, All-Star selections, service years, captaincy. The combined raw engagement is $\text{engagement\_raw} = 0.7 \cdot \text{CES} + 0.3 \cdot \text{BDS}$.

The central methodological move is comparing each player only to similarly skilled peers, not to the league. For player $P$ we identify K=10 nearest neighbours in standardized skill space using Mahalanobis distance with cohort-specific scaling. A fourth-line forward is compared only to other fourth-line forwards. When no close peers exist the row is flagged `match_quality=low` rather than reported as a noisy point estimate. The attention residual is

$$\text{OAQ}_{\text{observed}}(P) = \text{engagement\_raw}(P) - \overline{\text{engagement\_raw}}_{\text{K=10 peers}}.$$

`OAQ_portable` additionally subtracts each player's team-market baseline (mean engagement-per-roster-spot) before differencing. The **Marchand Index** is $\text{MI}(P) = \text{OAQ}_{\text{portable}}(P) / \text{cap\_hit}_M(P)$. Per-player 95% confidence intervals are computed by bootstrap resampling (1,000 draws over the per-player attention signal, recomputing the peer-group mean from the same draw).

A supporting interpretability layer decomposes Reddit attention into eight themes (skill, fighting, personality, style, off-ice life, controversy, charity, relationship/viral) via an LLM classifier. **The classifier is not part of the headline OAQ.** Before any theme finding is reported, the classifier is audited on 300 stratified hand-labeled comments; ship floor is macro-F1 ≥ 0.60 and Cohen's $\kappa \geq 0.55$. A failed audit suppresses theme-level findings only.

## 2. Pilot evidence (worked example, not validation)

**Player selection.** Names were locked in the pre-registration before any data was fetched. Each player has a canonical role within a target archetype and verifiable public-signal volume — all 14 returned non-trivial Wikipedia pageview and Google Trends signal across the 12-month window — rather than being a sample of the league. Elite skill with modest off-ice profile: McDavid (multiple Hart Trophies and Art Ross titles), MacKinnon (Hart 2024), Makar (Norris and Conn Smythe 2022), and Draisaitl (Hart and Art Ross 2020) — the canonical top-line cohort by every public production metric. Legacy reputation under declining production: Crosby (three Stanley Cups, two Hart Trophies, still in top-line minutes at 38). Top scoring paired across markets: Matthews (multiple Maurice Richard Trophies including 69 goals in 2023–24; Toronto) and Kucherov (Art Ross 2019 and 2024, Conn Smythe 2020; Tampa). Polarizing identity / namesake archetype: Marchand (multi-time All-Star, 2011 Stanley Cup, well-documented suspension record) and M. Tkachuk (2023 Stanley Cup Finalist with a widely covered agitator reputation), with B. Tkachuk as a same-style sibling control on a smaller-market team (Ottawa captaincy) — testing whether polarizing identity travels independent of platform. Extreme low-skill / high-off-ice: Reaves, a career enforcer (~15 NHL seasons) whose public engagement consistently outruns his on-ice production. Direct market-amplification test: Marner, who spent nine seasons in Toronto before a mid-window trade to Vegas — a natural experiment in whether attention follows the player or the market. Cultural-crossover salience: J. Hughes, whose high-profile cross-industry relationship has generated documented coverage outside hockey media. Rising salience from a near-zero baseline: Bedard (consensus #1 overall, Calder Trophy 2024). The set is sized to be hand-auditable and stresses every part of the methodology — peer matching, market control, and cap adjustment — against archetypes that adjacent on-ice metrics are known to misprice. The full model operates on all active NHL skaters and does not inherit this hand-curation.

**Pilot scope.** Only the signals available on the free path at fetch time were used — Wikipedia pageviews and Google Trends; Reddit and Instagram were both unavailable and dropped under the locked sentinel-renormalization rule. The pilot used K=5 peer matching within the 14 players, not the full-model K=10 across the league.

**Result.** Of three pre-registered falsifiable patterns, one was confirmed — the rank reordering described above — and two were disconfirmed in a single diagnostic direction: both traced to the pilot's operationalization of the team-market baseline as the roster-mean Wikipedia pageviews, which over-corrects when a player shares a roster with high-pageview teammates. The full pre-registration replaces this proxy with a direct market-size composite (team social-account followers + arena attendance + market-population control). The figure below shows the confirmed top-5 reordering; the lower ranks reflect the proxy flaw and are not visualized.

![](pilot/figure.png)

## 3. Validation plan and pre-registration

Four independent attention validations and one classifier audit are pre-registered ahead of any production modelling. **No validation gate is reported as passed below; these are the pre-declared targets.**

| # | Gate | Test | Floor / Target |
|---|---|---|---|
| 1 | Jersey-list ρ | Spearman ρ, `OAQ_portable` top-50 vs. NHL annual top-20 jersey list | ρ ≥ 0.40 / 0.50 |
| 2 | All-Star fan-vote ρ | Spearman ρ, `OAQ_portable` vs. fan-vote share, 2022 / 2023 / 2024¹ | ρ ≥ 0.45 / 0.55 |
| 3 | Signing event study | DID on top-50 FA signings since 2020: 60-day team-account follower delta ~ signed-player `OAQ_portable` + team FE + season FE + cap hit + position | Direction positive / *p* < 0.05 |
| 4 | Stratified generalization | Residual regression of held-out YouTube view counts (channel allow-list) on `OAQ_portable` with on-ice, clip, channel, market, and career-length controls; Spearman ρ on outside-star pooled cohort, with per-band sub-tests for star / regular / depth bands defined on non-attention variables only | ρ ≥ 0.25 / 0.35 (outside-star) |
| 5 | Classifier audit | Macro-F1, Cohen's κ on 300 stratified hand labels — gates theme findings only | F1 ≥ 0.60 / 0.70; κ ≥ 0.55 / 0.65 |

¹ The 2024-25 NHL All-Star Game was replaced by the 4 Nations Face-Off; 2022 / 2023 / 2024 fan-vote data only.

Four hypotheses are pre-registered with bootstrap CIs and reported regardless of direction. **H1:** polarizing players have a Marchand Index at least 1.5× their skill-matched non-polarizing peers. **H2:** cultural-crossover players (≥15% of mentions outside hockey subreddits) carry `OAQ_portable` above what their cap percentile predicts. **H3:** documented viral off-ice events produce attention persistence ≥6 months past the event. **H4:** off-ice-driven attention is more theme-concentrated than skill-driven attention. Pre-declared null-result triggers specify exactly which published claim is downgraded if which gate fails — for example, a Gate-4 failure on the outside-star pooled cohort removes the role/depth-player framing from the published findings.

## 4. Contribution and limits

**Contribution.** The Marchand Index is, to our knowledge, the first publicly reproducible, peer-matched, market-controlled, cap-adjusted off-ice attention estimator for NHL players, with a pre-registered four-gate validation plan, written null-result triggers, and an audited interpretability layer. The methodology — K=10 nearest-neighbour matching, dual market lenses, volume separated from sentiment, pre-registered downgrade rules — is portable to any professional league with public engagement signals.

**Limits.** Attention is a proxy for fan demand, not revenue. Stars and rookies have few close peers; `match_quality` is flagged per row and published with a prominent warning when low. Goalies are excluded from headline analysis; peer matching breaks down for the position. X/Twitter engagement is unavailable (free API removed); Instagram is follower-count snapshots only. The 14-player pilot is a worked example of the methodology, not a validation of the league. Gates that fail downgrade the published findings along pre-declared written rules.

**Selected references.** Vollman R., *Hockey Abstract* (NHLe). Bacon P., updated NHLe. Davis J., *Pick224* (pGPS peer-matching). Imbens G., Rubin D. (2015), *Causal Inference for Statistics, Social, and Biomedical Sciences* (matching estimators). Reddit / Wikimedia REST / pytrends API documentation.

<sub>Adam Noakes · ana178@sfu.ca</sub>
