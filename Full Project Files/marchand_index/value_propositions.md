# Marchand Index — Downstream Value Propositions (BACKLOG)

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

---

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
