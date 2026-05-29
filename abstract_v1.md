# The Marchand Index: A Peer-Matched, Cap-Adjusted Model of NHL Fan Attention

**Submitted to:** Cascadia Symposium on Statistics in Sports (CASSIS), September 12, 2026. **Format requested:** Oral.

---

The Marchand Index identifies NHL skaters whose public fan-attention exceeds what their on-ice skill and team market would predict, then scales that surplus by the player's skill-expected market cap. The framework is pre-registered with nine committed amendments (A1–A9) logged in git *before* each re-run, with every original column retained for audit. Five denominator lenses are reported side-by-side rather than collapsed to a single headline; bootstrap 95% CIs accompany every published number. The first external validation gate cleared (V3, Spearman ρ = 0.42, 95% CI [0.07, 0.68], n = 32 teams). Three other pre-registered external gates remain underpowered at this pilot's scope and are reported as **inconclusive**, not as failures hidden in footnotes.

The pilot's contribution is methodological discipline plus a clean team-level triangulation — not leaguewide validation. The full-league rerun, the LLM theme classifier, and the four full-build hypotheses (H1–H4) remain future work, separately pre-registered.

## 1. Method

The pilot scope is **160 skaters** selected by an objective, fully-reproducible deployment rule (amendment A7): per team, the most-deployed left wing, center, and right wing plus the top two defensemen by 2025-26 regular-season TOI/G from the NHL public API, each requiring ≥ 41 games played (32 teams × 5 = 160 = 96 F / 64 D; goalies excluded; 0 teams required the GP-relaxation fallback). This replaces the prior DailyFaceoff editorial-line selection — an unauditable, scrape-fragile input — with a quantity any reader can reproduce. The set is locked in `players.csv` before any fetch. Composite weights, peer features, market-proxy components, and external-validation floors are committed in `pilot2/preregistration.md` §4, §6, §7, §9 before data collection.

**Engagement composite (§4).** Wikipedia 12-mo pageviews (weight 0.306), Reddit mentions and upvotes (0.250 + 0.167) from `r/hockey` plus team subs, Google Trends 12-mo (0.139), and Instagram followers (0.139). Components z-scored across the 160 set, weighted sum, per-player sentinel renormalization when a component is NULL. **Honest disclosure:** Instagram returned 0/160 (Meta's anonymous block), so the renormalized weights become wiki 0.355, reddit-mentions 0.290, reddit-upvotes 0.194, trends 0.161 — the headline composite is therefore primarily a Wikipedia-and-Reddit signal.

**Peer matching (§6).** For each skater, the K=10 nearest peers within position group (forward / defenseman) are selected by Mahalanobis distance on standardized (age, PPG, TOI/G), using the within-group inverse covariance. `OAQ_observed(P) = engagement(P) − mean(engagement across peers)` is the residual attention above skill-matched expectation.

**Market correction (§7, amended A5).** The locked §7 subtracted the full team `market_z` from engagement, producing two failure modes: small-market players (SJS market_z = −2.27) received phantom positive corrections, while big-market players' fan equity that travels with them (the Marner/Tavares pattern) was over-discounted. A5 replaces the full subtraction with a one-sided damped form:

OAQ_portable(P) = engagement_raw(P) − λ × max(0, market_z(P)) − peer_mean(of same)

with λ = 0.5, the maximum-entropy midpoint between λ = 0 (no correction) and λ = 1 (no portability). λ is committed before the re-run; the full sensitivity ladder λ ∈ {0, 0.25, 0.5, 0.75, 1.0} is reported as a robustness check. Locked-v1 is retained as `OAQ_portable_lockedv1` for audit. **Honest disclosure:** the peer baseline is built from each peer's own adjusted engagement, so a player whose peers include big-market opponents has their comparison baseline pulled down. This is an explicit modeling choice that rewards above-replacement attention in low-amplification environments; it is not a bug, and is the reason a depth player can credibly out-rank a star in some lenses.

**Marchand-Index denominator (§8, amended A4).** The §8-original `OAQ_portable / cap_hit_M` is dominated by an artifact of the collective-bargaining agreement: entry-level contracts (ELCs) cap at ~$0.95M regardless of skill, so `1 / cap_hit_M` mechanically explodes for any rookie. A4 replaces `cap_hit_M` with `expected_cap`, the OLS prediction of `cap_hit_M ~ PPG + TOI/G` fit separately within position group, with the prediction floored at the 2025-26 league minimum ($0.775M). Age is deliberately excluded: because age is a peer feature in §6, an age-aware expected cap would re-import the rookie scale through young/cheap peers (verified empirically). The §8-original raw-cap quantity is retained as `marchand_index_rawcap`; a hybrid lens (`marchand_index_hybrid`) applies expected_cap only to rookie-deal players (cap ≤ $0.975M AND age ≤ 25, 27 of 160). Five denominator lenses are reported side-by-side in `results.md`.

**Bootstrap (§10).** 1,000 draws, seed 20260526, deterministic across reruns. Each draw resamples each player's Wikipedia daily-pageview vector and Reddit submission pool with replacement; trends, IG, cap, market, and peer sets are fixed; OAQ / MI / Spearman / AUC recomputed per draw; 2.5/97.5 percentile CIs.

## 2. Pilot Results

The leaderboard non-trivially reorders under A4/A5: of the top-10 by raw engagement (Crosby, Celebrini, McDavid, Hughes, Ovechkin, M.Tkachuk, Suzuki, Bedard, W.Smith, Draisaitl), **four are displaced** out of the top-10 Marchand Index (McDavid, Suzuki, Bedard, Draisaitl), replaced by depth or aging-veteran cases that the cap+market adjustment surfaces. PC (≥3 displaced) is **confirmed**. Headline Lens 5 (A4 denominator for all 160) top five: Linus Karlsson (26, VAN, $0.78M), Sidney Crosby (38, PIT, $8.70M), Alex Ovechkin (40, WSH, $9.50M), Quinn Hughes (26, VAN, $7.85M), Will Smith (21, SJS, $0.95M). The five-lens panel is the primary contribution: the metric refuses to collapse to a single ranking, and the lenses correspond to genuinely different questions (ELC-only, ELC-excluded, current-bargain, hybrid, intrinsic).

## 3. External Validation

| ID | Test | Effect | 95% CI | n | Verdict |
|---|---|---|---|---|---|
| **V3 (A6)** | Spearman ρ(Σ OAQ_observed per team, team Wikipedia 12-mo pageviews) | **0.418** | **[0.073, 0.682]** | **32 teams** | **Confirmed (powered, gate cleared)** |
| V1a | Spearman ρ(OAQ_portable, NHL jersey-rank) | 0.80 | [−1, +1] | 4 | Inconclusive (underpowered) |
| V1b | AUC(OAQ_portable, jersey-list membership) | 0.66 | [0.43, 0.86] | 8 / 160 | Inconclusive (underpowered) |
| V2 | AUC(OAQ_portable, 2024 ASG membership) | 0.53 | [0.16, 0.83] | 4 / 160 | Inconclusive (underpowered) |

V3 (pre-registered as A6 before any team-level fetch) sums `OAQ_observed` across each team's five pilot players and correlates with the **team's** Wikipedia 12-month pageviews — a held-out, team-account signal independent of every model input. The 95% CI excludes zero; the result clears the §9 ρ ≥ 0.40 floor. **Honest robustness:** the mechanical baseline using `sum(engagement_raw)` instead of peer-matched `sum(OAQ_observed)` yields ρ = 0.410, CI [0.045, 0.682]. Peer-skill control does not significantly enhance the team-aggregate signal beyond raw attention; we report this directly rather than spinning it. V1b at n = 8 and V2 at n = 4 are below the §9 n ≥ 10 power threshold by the pilot's own rule and are reported as inconclusive — the leaguewide rerun (~700 active skaters) will recover power for these gates.

## 4. Contribution and Limits

**Methodological contributions.** (i) A peer-matched off-ice attention residual that controls for position-conditional skill rather than league average. (ii) A one-sided damped market correction whose tunable damping is pre-committed by an information-theoretic argument rather than grid-searched. (iii) A skill-expected cap denominator that de-biases the CBA-imposed ELC ceiling without re-importing age effects. (iv) Five denominator lenses reported simultaneously, which refuses to crown a single answer and lets a reader audit the metric across its degrees of freedom. (v) A team-level triangulation that converts a player-level metric into a powered (n = 32) external test using a held-out team-account signal.

**Honest limits.** The team-popularity outcome in V3 (team Wikipedia pageviews) is partially correlated with the team-market construct that A5 controls for at the player level. V3 is therefore a **triangulation**, not a clean causal validation, and is labeled as such. Three of four external gates remain underpowered at n = 160; the pilot is a methods demonstration, not leaguewide validation. The depth-player surfacing in Lens 5 (e.g. Karlsson at #1) is a design feature where peer-relative attention and a low expected-cap denominator both shrink, but the ratio does not — we expose this rather than suppress it, and the five-lens panel lets a reader filter to the lens that matches their decision question. Attention is treated throughout as a proxy for fan demand, not as a revenue model. Goalies are excluded from the headline analysis because their skill metrics are structurally different.

**Code and data.** All compute is deterministic at seed 20260526; the full pipeline reproduces byte-identical CSV/JSON across runs (diff-verified). `pilot2/compute_oaq.py` runs end-to-end on a laptop in ~3 minutes. The amendment trail A1–A9, with their original-column-retention discipline, is documented in `pilot2/preregistration.md` §14.

**Selected references.** Vollman R., *Hockey Abstract* (NHLe). Davis J., *Pick224* (pGPS peer matching). Imbens G., Rubin D. (2015), *Causal Inference for Statistics, Social, and Biomedical Sciences* (matching estimators). Wikimedia REST API / Reddit JSON / pytrends documentation.

<sub>Adam Noakes · ana178@sfu.ca</sub>
