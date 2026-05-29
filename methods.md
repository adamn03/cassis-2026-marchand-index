# The Marchand Index: Plain-Language Methods Guide

**What this document is:** A companion to the CASSIS 2026 abstract. It explains every abbreviation, every symbol, every method, and why each choice was made — written so that someone with no statistics background and no hockey background can follow along. If you can read a bank statement, you can read this.

---

## Glossary

Every abbreviation used in the abstract, in plain English.

| Term | Full name | Plain English |
|---|---|---|
| **OAQ** | Off-Ice Attention Quotient | How much fan attention a player gets *above* what his skill level would predict |
| **OAQ_observed** | — | OAQ including home-city effects (what attention looks like where the player currently plays) |
| **OAQ_portable** | — | OAQ with home-city effects removed (what attention would travel with the player if he changed teams) |
| **Marchand Index** | — | OAQ_portable divided by cap hit — how much attention surplus the team gets per dollar of salary |
| **CES** | Current Engagement Score | A single number combining all current fan-attention signals for a player this season |
| **BDS** | Brand Depth Score | A single number capturing a player's long-term, career-built reputation |
| **K=10** | K-nearest neighbors, K=10 | The 10 most statistically similar players used as a comparison group |
| **NHLe** | NHL Equivalency | A conversion factor that adjusts stats earned in junior or European leagues to NHL-level terms |
| **GAR** | Goals Above Replacement | An on-ice metric: how many extra goals a player contributes vs. a replacement-level player |
| **RAPM** | Regularized Adjusted Plus/Minus | An on-ice metric that adjusts for teammates and opponents to isolate a player's individual contribution |
| **Corsi** | — | A shot-attempt metric used to estimate puck possession |
| **5v5** | Five-on-five | Even-strength play — no power play or penalty kill, five skaters per side |
| **95% CI** | 95% confidence interval | The range of values likely to contain the true result; narrow = more certain, wide = less certain |
| **rho (ρ)** | Spearman rank correlation | A score from −1 to +1 measuring how well two ranked lists agree (0 = no agreement, 1 = perfect) |
| **F1** | Macro-F1 score | How accurately the AI classifier identifies themes across all categories (0–1; higher is better) |
| **kappa (κ)** | Cohen's kappa | How much the AI classifier agrees with human reviewers, beyond what pure chance would produce (0–1) |
| **p-value (p)** | — | The probability a result is just random luck; below 0.05 is the usual bar for "real, not a fluke" |
| **LLM** | Large Language Model | An AI text model used to read and categorize Reddit comments |
| **pGPS** | Peer Group Production Score | A published public tool for peer-matching hockey players (reference point only; we build our own) |
| **cap hit** | Annual average value | The salary-cap charge a team pays per season for a player under contract |

---

## Symbols and Notation

Every mathematical symbol that appears in the abstract or in the formulas below. If a formula ever looks intimidating, this table translates it back into ordinary words.

| Symbol | Said aloud | What it represents | What its value tells you |
|---|---|---|---|
| **P** | "player P" | A placeholder for whichever player we are calculating — like "x" in school algebra. | It's not a number; it just means "plug in any player here." |
| **Σ** | "sigma" / "the sum of" | An instruction to add up a list of things. | Not a value itself — it means "total these up." |
| **z** (z-score) | "z-score" | A number rewritten as *how many standard deviations above or below average* it is. | 0 = exactly average. +1 = one step above average. −2 = two steps below. This is how we put followers, searches, and pageviews on one common scale. |
| **K** | "K" | The number of comparison players (the peer group). We use K = 10. | Bigger K = steadier but blurrier comparison. Smaller K = sharper but noisier. 10 is the balance point. |
| **engagement_raw(P)** | — | Player P's combined raw attention score (CES + BDS) before any adjustment. | Higher = more total public attention, *before* we account for skill, market, or salary. |
| **OAQ(P)** | — | Player P's attention *above* what skill-matched peers get. | **Positive** = draws more attention than equally skilled peers. **Negative** = draws less. **Near zero** = exactly as expected for his skill level. |
| **cap hit_M(P)** | "cap hit in M" | Player P's salary-cap charge, in millions of dollars. | The denominator. A bigger salary makes the same attention surplus "cost more," lowering the Marchand Index. |
| **ρ** (rho) | "rho" | How well two ranked lists line up (Spearman correlation). | Runs −1 to +1. **0** = no relationship. **~0.3** = medium. **~0.5** = large. **+1** = identical order. **Negative** = the lists run opposite. |
| **κ** (kappa) | "kappa" | How much the AI agrees with a human labeller, beyond lucky guessing. | Runs 0 to 1. **0.41–0.60** = moderate agreement. **0.61–0.80** = substantial. (This is the standard Landis–Koch scale.) |
| **F1** | "F-one" | The AI classifier's accuracy across all theme categories at once. | Runs 0 to 1. Higher = more accurate. We require at least 0.60 before trusting it. |
| **p** (p-value) | "p-value" | The chance a result is just random noise rather than real. | **Below 0.05** = less than a 1-in-20 chance it's a fluke → we call it "statistically significant." |
| **95% CI** | "confidence interval" | The range that should contain the true value 95% of the time. | **Narrow** = we're confident. **Wide** = uncertain, more data would help. **If it crosses zero**, the result can't be told apart from "no effect at all." |

---

## What We Are Trying to Measure

Hockey analytics has become very good at measuring what happens *on the ice* — goals, shots, possession, individual defensive value. What it has not measured is the *off-ice* component: which players generate fan interest that goes beyond what their skill level alone would produce?

This matters because two players with identical production can have very different value to their franchises. A player who generates outsized fan attention — through personality, polarizing identity, cultural crossover, or viral moments — is contributing something real that no on-ice metric captures.

**The core question:** For each NHL skater, how much fan attention do they generate *above what equally skilled peers generate*, and how much does that attention surplus cost the team per salary-cap dollar?

---

## Step-by-Step: How the Model Works

### Step 1 — Measure Fan Attention (CES and BDS)

**What this step does:** turns "how much are people paying attention to this player right now" into a single number.

We collect four public signals for each player:

- **Wikipedia pageviews** — how often people look up their Wikipedia page
- **Google Trends search interest** — how often people search their name online
- **Reddit mention and vote volume** — how often they are discussed in hockey communities
- **Instagram follower count** — the size of their social audience

**The problem these signals create, and how we fix it:** these numbers live on completely different scales (followers run from thousands to millions; Google Trends runs 0–100). You cannot just add them. So we first convert each one to a **z-score** — a value that says "how far above or below average is this player on this signal." This is like converting Celsius, Fahrenheit, and Kelvin all into one unit so they can be fairly combined.

The result is the **Current Engagement Score (CES)**: one number representing how much fan attention a player is drawing right now.

Importantly, *volume* (how much people are talking) is tracked separately from *sentiment* (whether the talk is positive or negative). A polarizing player who generates lots of heated discussion is **not** penalized for being controversial — the attention is real regardless of its tone.

We also compute a **Brand Depth Score (BDS)** for career reputation: career Wikipedia traffic, appearances on official jersey-sales lists, All-Star selections, years in the league, and captaincy. This stops a veteran with a quieter current season from being underrated just because he had a slow year.

**The output of this step — `engagement_raw`** — is a weighted combination of CES and BDS. In symbols:

> **engagement_raw(P) = Σ ( weight × z-score of each signal )**

In words: for player P, multiply each attention signal (after z-scoring) by how much we trust it, then add them all up. A higher `engagement_raw` means more total public attention — but it does *not* yet account for skill, market, or salary. That is what the next steps fix.

---

### Step 2 — Find Each Player's Peer Group (K=10 Nearest Neighbors)

**What this step does:** finds the 10 players most similar to player P *on the ice*, so we can later ask "does P get more attention than players just like him?"

The problem with raw engagement is that a high number might simply mean "plays in New York" or "is already the best player in the world." We want to know whether a player's attention *exceeds what his skill level and market would predict*.

To do that, we compare each player only to players with a similar on-ice profile. For any given player P, we find the 10 most statistically similar active NHL skaters based on:

- Position (forward or defenseman)
- Age
- Points per game
- Average time on ice per game
- Production at even strength (5v5 points per 60 minutes)
- Role band (star / top-6 / bottom-6 / depth forward, or top-pairing / mid-pairing / depth defender)
- NHLe-adjusted career production

A fourth-line grinder is compared only to other fourth-line grinders. An elite power forward is compared only to other elite power forwards. This is the only way to honestly isolate the off-ice component.

**Why 10 peers and not more or fewer?**
Comparing to a single peer (K=1) is too fragile — one unusual player can distort everything. Comparing to the entire league (K=all) is too blunt — it puts a depth player next to Sidney Crosby. K=10 gives a stable, meaningful reference group without smoothing out the signal we are trying to find.

**How "similar" is measured — Mahalanobis distance.** Think of it as a smart measuring tape. A naive measuring tape would treat "points per game" and "time on ice" as two separate things — but players with more points usually also play more minutes, so counting both would double-count the same underlying skill. Mahalanobis distance (a) knows which stats move together and avoids double-counting them, and (b) puts every stat on the same footing so no single number dominates. The output is one distance value per pair of players: **small = very similar, large = very different.** The 10 smallest distances are P's peer group.

If a player has no close peer group — possible for genuinely one-of-a-kind players — his row is flagged **`match_quality = low`** and the result is published with a visible warning rather than hidden or silently removed.

---

### Step 3 — Compute OAQ (the Gap Between Expected and Observed)

**What this step does:** subtracts "what his peers get" from "what he gets." Whatever is left over is the off-ice attention that his skill does *not* explain.

> **OAQ_observed(P) = engagement_raw(P) − ( average engagement_raw of P's 10 peers )**

Reading that left to right: take the player's own attention score, subtract the average attention score of his ten most-similar peers, and keep the difference.

This difference is called a **residual** in statistics — the part of a result that the predictors (skill, age, role) did not explain. **What the value means:**

- **OAQ above 0** → the player draws *more* attention than equally skilled peers (the interesting case).
- **OAQ below 0** → the player draws *less* attention than equally skilled peers.
- **OAQ near 0** → the player draws exactly what his skill level would predict; nothing unusual off the ice.

**OAQ_portable** takes one extra step *before* the peer comparison: it subtracts a **market baseline** that captures home-city effects. A player in Toronto or New York gets natural media amplification that has nothing to do with who he is. Removing that baseline answers a different and arguably more useful question: *what attention would this player carry if you moved him to an average-market team?*

We report both lenses in the full build:

- **`OAQ_observed`** answers: *"Who draws attention here, in their current city?"*
- **`OAQ_portable`** answers: *"Who draws attention that belongs to them, not their market?"*

The headline output — the number on the leaderboard — is **`OAQ_portable`**.

---

### Step 4 — Compute the Marchand Index

**What this step does:** divides the portable attention surplus by salary, so two players can be compared on attention-per-dollar instead of raw attention.

> **Marchand Index(P) = OAQ_portable(P) ÷ cap hit_M(P)**

In words: take the attention surplus that would travel with the player, and divide it by what the team pays him (in millions of dollars). Two players with identical attention surplus but different salaries score differently — the one on the cheaper contract delivers more attention value per dollar, which is the right unit for a front office operating under a hard salary cap.

**A worked example (real numbers from the pilot):** Connor Bedard had an `OAQ_portable` of about **1.26** and a cap hit of **$0.95M**. So his Marchand Index is 1.26 ÷ 0.95 ≈ **1.32** — the highest in the pilot. A player with the *same* 1.26 surplus but a $9M salary would score only 1.26 ÷ 9 ≈ **0.14**. Same attention; very different value per dollar. That gap is the entire point of the index.

---

### Step 5 — Quantify Uncertainty (Bootstrap Confidence Intervals)

**What this step does:** attaches an honesty range to every number, so we never present a single figure as if it were exact.

Every player score is published with a **95% bootstrap confidence interval**.

**How bootstrapping works:** imagine re-running the entire calculation 1,000 times, each time on a slightly different random sample of the same data. You end up with 1,000 slightly different answers. The 95% confidence interval is the middle range that contains 950 of those 1,000 answers.

**What the interval's width means:**

- **Narrow interval** → the score is stable and reliable.
- **Wide interval** → the score is shaky; more data would sharpen it.
- **Interval that crosses zero** → we genuinely cannot tell whether the player is above or below his peers; the result is "not distinguishable from no effect."

This is not optional decoration. Reporting a single number without an uncertainty range would be misleading for a metric this new.

---

### Step 6 (Optional) — Theme Classification via LLM

**What this step does:** reads the *content* of fan discussion to explain *why* a player gets attention, not just *how much*.

An AI language model reads Reddit comments about each player and sorts them into categories: skill, fighting, personality, style, controversy, charity, relationship/viral.

**This step is gated** — meaning it is only allowed to appear in the results if it first passes an accuracy test. A human hand-labels 300 comments, and the AI must match that human well enough to clear two bars: **F1 ≥ 0.60** (overall accuracy) **and κ ≥ 0.55** (agreement beyond chance). If the AI does not clear both, theme findings are simply not reported — and the OAQ and Marchand Index scores are completely unaffected either way.

---

## How to Read a Result

When you see a published row, here is how to interpret it at a glance:

| You see… | It means… |
|---|---|
| **A positive OAQ** | This player draws more fan attention than equally skilled players. |
| **A negative OAQ** | This player draws less attention than equally skilled players. |
| **A high Marchand Index** | The team is getting a lot of attention surplus per salary dollar — efficient. |
| **A negative Marchand Index** | The player draws *less* attention than skill-matched peers, per dollar — the surplus is negative. |
| **A wide confidence interval** | Treat the exact rank with caution; the signal is noisy for this player. |
| **A `match_quality = low` flag** | This player is hard to peer-match (too unique); the score is shown but should not be over-read. |

The single most important habit: **read the confidence interval, not just the point estimate.** A player ranked #1 with a wide interval may not truly be ahead of #4.

---

## How We Check the Model Is Real: The Validation Gates

A model that only predicts its own outputs proves nothing. So before any headline finding is published, the model must pass five independent checks. **"Independent" is the key word** — each check tests the model against real-world data that was collected *separately* from the attention signals the model is built on.

Two ideas make these checks trustworthy:

1. **A floor and a target.** The **floor** is the minimum result required to publish the claim at all. The **target** is the level we are actually aiming for. If a gate misses its floor, the associated claim is removed or downgraded — not quietly kept.
2. **They were written down in advance.** Every floor and target below was locked into the project's records *before* the model ran on real data. This is the whole point: a threshold you commit to beforehand cannot be secretly bent to match whatever result came out. (For the technically minded: ρ thresholds use the standard correlation scale where ≈0.30 is a "medium" relationship and ≈0.50 is "large"; κ thresholds use the Landis–Koch agreement scale.)

| Gate | The plain-English question it answers | Floor / Target | Why these numbers |
|---|---|---|---|
| **1. Jersey sales** | Do players the model rates high on attention actually sell jerseys? | ρ ≥ 0.40 / 0.50 | 0.50 is a "large" correlation on the standard scale (the target). The floor sits at 0.40 — above "medium" — because jersey lists are noisy: they rank only the top 20, and sales reflect price and availability, not popularity alone. |
| **2. All-Star fan voting** | Do fans vote for the players the model says fans care about? | ρ ≥ 0.45 / 0.55 | Set one notch higher than Gate 1. Fan voting is a *more direct* measure of attention than buying a jersey, so the model should track it more tightly — hence the higher bar. |
| **3. Free-agent signings** | When a team signs a player the model rates highly, does the team's social following actually grow more than usual? | Direction positive / p < 0.05 | The floor is weak on purpose — just "the effect points the right way" — because the sample is small (top-50 signings since 2020) and follower growth is noisy. Demanding full statistical significance (p < 0.05) as the floor could fail on sample size alone, so significance is the *target*, not the floor. |
| **4. Outside-the-stars test** | Does the model still work once you remove the obvious superstars — or is it just rediscovering who's already famous? | ρ ≥ 0.25 / 0.35 | Deliberately lower. The outcome here is a *residual*: held-out YouTube view counts after stripping away clip type, channel, market, position, ice time, scoring, salary, and career length. After removing that much, a 0.25–0.35 correlation is a real signal. The low bar reflects a *harder* test, not a weaker claim. |
| **5. AI theme accuracy** | Is the automated theme labelling accurate enough to trust? | F1 ≥ 0.60 / 0.70 and κ ≥ 0.55 / 0.65 | F1 0.60 is our pre-declared minimum usable accuracy for a 7-category text task. The κ floor of 0.55 means "moderate" human–AI agreement and the target 0.65 means "substantial," on the standard Landis–Koch scale. Failing this gate hides the theme findings only — the headline OAQ is untouched. |

**The honest framing if anyone challenges these numbers:** they are pre-registered decision rules, not universal constants. Their value is that they were committed in advance, so they could not be reverse-engineered to fit the result.

---

## The Four Pre-Registered Hypotheses (H1–H4)

Separately from the gates above, we locked in four specific predictions before running the model. Each is reported with its effect size and confidence interval **regardless of whether it comes out true** — if a prediction is wrong, that disagreement is itself a finding, not something we hide.

| # | Plain-English prediction |
|---|---|
| **H1** | Polarizing players (the Marchand archetype — players who generate strong positive *and* strong negative reaction) draw more attention per salary dollar than equally skilled non-polarizing players. |
| **H2** | Players whose conversation spreads *beyond* hockey-only spaces (cultural crossover) carry more attention than their salary alone would predict. |
| **H3** | A documented viral off-ice moment (a relationship, a fight, a charity story, a controversy) produces attention that lasts at least six months past the event, not just a short spike. |
| **H4** | Off-ice-driven attention is more *concentrated* on one or two themes, while skill-driven attention is spread across many — so a player with a narrow theme profile tends to score higher on the Marchand Index, holding skill constant. |

---

## Why We Made Each Key Choice

| Choice | Why |
|---|---|
| K=10 peer matching instead of league-wide average | Comparing a 4th-line player to Connor McDavid is meaningless. Peer matching is the only way to isolate the off-ice premium from the on-ice signal. |
| Mahalanobis distance instead of simple difference | Accounts for correlations between variables and equal-weights all dimensions, so no single stat dominates the similarity calculation. |
| Volume separated from sentiment | Polarizing players generate real attention even if it is mixed. Penalizing them for controversy would conflate "unpopular" with "divisive," which are different things. |
| Dual OAQ lenses (observed + portable) | The market question and the portability question are genuinely different. A single number would force a choice and obscure the other answer. |
| Cap hit as the denominator | Teams operate under a hard salary cap. Attention per dollar is the relevant unit for front-office decisions — raw attention without a cost context is incomplete. |
| Bootstrap confidence intervals on every score | A point estimate with no uncertainty range overstates what we know. Noisy signals and imperfect proxies require visible error bars. |
| Pre-registration before data collection | Locks hypotheses and thresholds in advance. Prevents the model from being tuned after seeing results — a common and subtle form of bias in data-driven research. |
| Five independent validation gates | A model that only predicts its own outputs proves nothing. Testing against jersey sales, All-Star fan votes, signing events, YouTube residuals, and human labels — all collected independently of OAQ — is the only way to show the measure is capturing something real. |

---

## What We Explicitly Do Not Claim

- Attention is a proxy for fan demand, not a measure of revenue. We do not produce dollar figures.
- Goalies are excluded from headline analysis. The peer-matching method breaks down for the position because goalie skill metrics are structured differently from skater metrics.
- The Tier-1 pilot (160 skaters — every team's top forward line and top defensive pairing by TOI) is a top-tier slice, not all ~700 active skaters; it is a proof-of-concept. Leaguewide findings come from the full K=10 run and the validation gates.
- X/Twitter data is not available at no cost; Instagram is limited to follower-count snapshots. These gaps are acknowledged in the model, not ignored.
- If a validation gate fails, the associated claim is removed. We report the result shape the data support.

---

## Amendments to the locked Tier-1 pilot pre-registration (`pilot2/preregistration.md` §14)

Every method change after the original lock is logged with a date, a reason, and a "before re-running" timestamp. The original columns are preserved for audit.

- **A1 (2026-05-27)** — Wikipedia slug resolver hardened: redirects resolved through Wikidata occupation = ice-hockey player (Q11774891) to avoid redirect under-counts and wrong-entity matches. Mechanical data-collection fix; no method change.
- **A2 (2026-05-27)** — Reddit transport switched from PRAW to public JSON endpoint (`reddit.com/r/<sub>/search.json`). Same source, subreddits, query, window, dedup, and 1,000-result cap; transport only.
- **A3 (2026-05-27)** — V1 jersey-list operationalization split into V1a (rank Spearman, small overlap) and V1b (membership AUC, larger overlap). Both reported regardless of direction; both currently underpowered.
- **A4 (2026-05-27)** — Marchand-Index denominator switched from raw `cap_hit_M` to `expected_cap` from per-position OLS `cap_hit_M ~ PPG + TOI/G`, prediction floored at $0.775M, age excluded to avoid re-importing the rookie scale. Headline metric becomes intrinsic attention efficiency stable across the ELC→extension transition. Raw-cap quantity retained as `marchand_index_rawcap`.
- **A5 (2026-05-27)** — §7 market correction switched from full two-sided subtraction to **one-sided damped**: `OAQ_portable = engagement − λ × max(0, market_z) − peer_mean`, with λ = 0.5 as the maximum-entropy midpoint between λ = 0 (no correction) and λ = 1 (no portability). λ committed before the re-run; sensitivity ladder λ ∈ {0, 0.25, 0.5, 0.75, 1.0} reported as robustness. Locked-v1 retained as `OAQ_portable_lockedv1`. **Honest disclosure of asymmetric peer subtraction:** the peer mean is computed over each peer's own adjusted engagement, so a small-market player whose peers include big-market opponents has the comparison baseline pulled down. This is an explicit modeling choice that rewards above-replacement attention in low-amplification environments, not a bug.
- **A6 (2026-05-28)** — V3 team-level triangulation gate added at n = 32 teams. Outcome = team Wikipedia 12-mo pageviews (Reddit subreddit-subscriber endpoint blanket-blocked at $0; pre-fetch availability check documented, graceful-degradation per §3.5/§7). Predictor = sum of `OAQ_observed` across each team's five pilot players. Floor ρ ≥ 0.40 mirrors V1. **Result on the original DailyFaceoff set: ρ = 0.418, 95% CI [0.073, 0.682], n = 32 teams, PD confirmed.** Mechanical baseline (sum of `engagement_raw`): ρ = 0.410, CI [0.045, 0.682] — reported openly; peer-skill control does not significantly enhance the team-aggregate signal beyond raw attention. (V3 is re-rolled by A7; see A7 re-confirmation obligation.)
- **A7 (2026-05-28)** — Player set switched from the DailyFaceoff line-combinations scrape to a **TOI-based position split** built from the NHL public API: each team's top 3 forwards and top 2 defensemen by 2025-26 regular-season TOI per game among skaters with ≥ 41 GP (half-season), 5 × 32 = 160. This **replaces** the DailyFaceoff set as the single locked set (DailyFaceoff page rendering proved unreliable across teams; TOI is reproducible from one public endpoint and is the §2 pre-declared fallback rule promoted to primary). The DF-built `players.csv` is retained in git history for audit, not carried as a parallel reported set. **Re-confirmation obligation (disclosed in advance):** re-rolling the set re-rolls V3/PD — the only confirmed validation gate; the new V3 ρ is reported regardless of direction against the unchanged ρ ≥ 0.40 floor.
- **A8 (2026-05-28)** — §8 headline denominator switched to **hybrid**: rookie-deal players (cap ≤ $0.975M and age ≤ 25) use `expected_cap`; everyone else uses their actual `cap_hit_M`. Replaces A4's expected-cap-for-all (now the Lens 5 *intrinsic-efficiency* lens) as the published headline. Rationale: a post-ELC cap hit is a freely negotiated market price, not a CBA artifact — dividing attention surplus by a model-predicted `expected_cap` overwrites real contract information and erases the exact signal the index exists to surface (a player who out-produces his actual deal on attention). Projection is applied only where a market deal was legally impossible. Five lenses still reported side-by-side; only the headline pointer moves Lens 5 → Lens 4. **Re-evaluation obligation:** PC (top-10-by-engagement displacement) is recomputed against the hybrid headline and reported regardless of direction.
- **A9 (2026-05-28)** — Reddit transport switched from the unauthenticated `reddit.com/.../search.json` endpoint (which began hard-403'ing this IP) to Reddit's authenticated **OAuth API** (`oauth.reddit.com`, free "script"-app `client_credentials` bearer token). Transport only — identical source (Reddit), subreddits (`r/hockey` + team sub), query (player last name), `sort=new`, 365-day window, submission-id dedup, and 1,000-result cap. The 86 players already collected anonymously are retained; only the missing players are fetched over OAuth. Cost remains $0; credentials live in a gitignored `pilot2/.env`, none committed.

---

<sub>Companion to: *The Marchand Index: A Peer-Matched, Cap-Adjusted Model of NHL Fan Attention* — CASSIS 2026 submission · Adam Noakes · ana178@sfu.ca</sub>
