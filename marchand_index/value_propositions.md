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

---

## Ideas considered and cut (recorded so they aren't re-proposed)

**Cut on strength/feasibility this round:** Halo Star / Three Stars (soft stakes), Situation-Room video-review (power-fatal subjective-challenge N), Fantasy ADP reach (coverage thins below fantasy tier + buzz leaks into Wiki/Reddit inputs), Sportsbook prop-market breadth (RED data + zero-variance risk if menus standardized), Award-futures name premium (star-tail only, reads as award-vote re-skin). **Existing ideas out-ranked into the backlog tail:** Cardboard Market / card price (anti-bot RED), Traction Curve (fuzzy outcome, heaviest multi-season lift), Eyeballs Test (~100 national games/season, power-fragile — note national-game ID itself is GREEN via NHL API `tvBroadcasts.market`).

**Prior brainstorm casualties (do not re-propose without strong reason):** national-TV game selection (can't separate player from team buzz), trade draft-pick return / galáctico (small N, imprecise pick charts), key-man attendance (non-random scratches), attention concentration / portfolio (sellout-censored variance), event poster billing (subjective, small N), bobblehead/giveaway selection (thin N, sponsor-driven), NHL.com editorial featuring (near-circular), tentpole event casting (small N + rotation rules), social-follower velocity (botted target), niche→mainstream news via GDELT (entity-match noise + Reddit-is-an-input).
