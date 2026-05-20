# The Marchand Index — A Cap-Adjusted Off-Ice Attention Model

*Conference poster + live demo. Sports Analytics Conference, 2026.*

---

## Project branding

| Element | Value |
|---|---|
| Project / poster title | **The Marchand Index** |
| Formal metric name | **OAQ — Off-Ice Attention Quotient** |
| Tagline | *"Which NHL players generate fan attention beyond what their skill-matched peers produce — and which deliver that attention most efficiently relative to cap hit?"* |
| File slug | `NHL_Marchand_Index.md` |

**Why "Marchand":** Brad Marchand is a high-skill player (100+ point seasons, multiple All-Star, Cup-winning piece) whose **public salience and polarizing identity exceed what comparable production alone would predict**. He's not "mid-skill"; he's the canonical case of a star whose off-ice gravity outstrips even high on-ice output. Naming the index after him makes the concept instantly intuitive to anyone in hockey analytics, and survives hostile questioning from anyone who actually watches hockey.

## Context

We are building a free, data-driven model that quantifies **off-ice fan attention** for every current NHL player, then expresses it relative to their cap hit. The poster is the deliverable; the underlying Excel, scripts, and CLI are the artifact. A live demo runs at the booth.

**The honest reframe (poster section 1).** We do not measure revenue. We do not have internal team financials. What we measure is **public attention as a proxy for fan demand**. Calling this "ROI" overclaims because the dollar denominator is missing on the revenue side. Calling it **Fan Demand Premium** is methodologically honest and survives any hostile question from a finance-background judge.

**Prompted by:** owner's observation that players like Ryan Reaves generate jersey/engagement value out of proportion to skill, and viral moments like Jack Hughes / Tate McRae visibly lift the Devils' brand. The hypothesis: there is a measurable, cap-adjustable "off-ice premium" that NHL front offices are not systematically pricing.

**Intended outcome:** a conference poster that introduces the Marchand Index as a defensible new metric, validated against three independent proofs, with an audited theme-decomposition layer and a live front-office demo.

## Mission

1. Build a multi-source public-attention composite (CES + BDS) for every current NHL player. **Attention volume separated from favorability and polarization.**
2. Compute each player's OAQ via **K-nearest matched peer group (K=10)** — skill held constant by design across multiple peers, robust against any single bad match.
3. **Control for market amplification.** Report both `OAQ_observed` (raw, market-included) and `OAQ_portable` (market-stripped via team-baseline subtraction). Headline metric for the poster is the harder claim (`OAQ_portable`).
4. Cap-adjust → **Marchand Index = OAQ ÷ cap_hit_M**. Reported with bootstrap 95% CI per player.
5. **Decompose attention into 8 themes** via LLM classification of Reddit comments. **Hand-validate the classifier** on 300 stratified comments (F1 + Cohen's kappa) before reporting results.
6. Validate the composite against three independent proofs: NHL annual jersey list, All-Star vote shares (available seasons), event-study deltas around major signings.
7. Pre-register 4 testable hypotheses BEFORE running the model. Report confirmed / disconfirmed / inconclusive.
8. Produce 8 named player case studies with photos, theme breakdowns, both OAQ flavors, and error bars.
9. Ship a live demo (acquisition recommender, trade-return CLI, FA pipeline planner) at the booth.

## Hard Constraints

- **$0 budget.** Free APIs / public scraping only (polite, rate-limited, cached). Free-tier OpenRouter for LLM classification.
- **Local-only.** Windows + Python + SQLite + Excel/CSV/PDF output. No cloud, no paid services.
- **Vault defaults apply** — see `C:\Local Only\Ai projects\CLAUDE.md`. OpenRouter base URL = `https://openrouter.ai/api` (NO `/v1` suffix).
- **Atomic file writes.** `.tmp` → rename per vault convention.
- **No private data.** Endorsement deals, ticket revenue per game, internal team financials are out of scope.
- **No causal claims we can't back.** Coach / GM / dev-staff retention is downstream of org health — we provide the inputs, we don't predict the decisions.
- **No revenue claims.** We measure attention. Attention correlates with revenue (jersey list ρ proves this) but the dollar number itself is not ours to assert.
- **Pre-registration discipline.** Hypotheses locked before model is run on production data. Findings are reported regardless of direction.
- **Classifier validation before use.** Hand-label sample required for any LLM-derived feature that appears on the poster (theme decomposition, sentiment classification).
- **Confidence reported per player.** Match-quality score and bootstrap CI shipped alongside every OAQ value. Low-confidence players flagged.

## Pre-registered hypotheses

Locked **before** any modeling on production data. Stored in `docs/preregistration.md`, committed at start of Week 3.

| ID | Hypothesis | Test |
|---|---|---|
| H1 | Polarizing players (high pos AND high neg Reddit sentiment in same player) generate ≥1.5× the Marchand Index of skill-matched non-polarizing peers. | Peer-group comparison of `marchand_index` for polarizing vs. non-polarizing players matched on on-ice profile. One-sided t-test with bootstrap CI. |
| H2 | Cultural-crossover players (≥15% of mentions outside hockey subreddits) have OAQ_portable ≥ 2× their cap percentile predicts. | Linear test of OAQ_portable ~ crossover_pct controlling for cap percentile. Effect size and CI reported. |
| H3 | Players with documented viral off-ice moments (relationships, fights, charity, controversy) show attention persistence ≥6 months past event, above pre-event baseline. | Interrupted time-series on Wikipedia + Reddit + Trends. Pre/post t-tests at +30/+90/+180 days. |
| H4 | Off-ice-driven attention is more theme-concentrated than skill-driven attention. Players with ≤2 dominant themes show higher Marchand Index than players with ≥4 themes, controlling for skill. | Spearman ρ between theme-concentration (Herfindahl on theme shares) and Marchand Index, conditional on skill quintile. |

Findings (confirmed / disconfirmed / inconclusive) become Section 4 of the poster.

## Success Metrics

### Model validation gates

| Metric | Aim | Ship gate |
|---|---|---|
| Spearman ρ between OAQ_portable top-50 and NHL annual top-20 jersey list | ≥ 0.50 | ≥ 0.40 |
| Spearman ρ between OAQ_portable and All-Star fan-vote share (available seasons: 2022, 2023, 2024) | ≥ 0.55 | ≥ 0.45 |
| Historical signing backtest: avg 60-day team-account follower delta for top-50 signings since 2020 | clearly positive, p < 0.05 | directionally positive |
| **LLM theme classifier — macro-F1 across 8 themes (hand-labeled 300 sample)** | **≥ 0.70** | **≥ 0.60** |
| **LLM theme classifier — Cohen's kappa vs. hand labels** | **≥ 0.65** | **≥ 0.55** |
| Coverage — % of current ~700 NHLers with non-null OAQ AND match_quality ≥ threshold | ≥ 90% | ≥ 80% |
| Spot-check 4 players: McDavid, Crosby, Marchand, Hughes — all rank as expected on Marchand Index | 4/4 | 3/4 |

If any ship gate fails: do not print the poster. Iterate on weights / sentiment / theme classification.

### Poster quality gates

| Criterion | Target |
|---|---|
| Headline finding (one quoted number, computed from data) | ✓ |
| Three independent validation proofs | ✓ |
| Pre-registered hypotheses doc committed before model run | ✓ |
| LLM theme classifier validation reported (F1 + kappa) | ✓ |
| ≥8 named case studies with photos, theme breakdowns, error bars, both OAQ flavors | ✓ |
| Method section explains K-NN peer matching + market control clearly enough to be re-implemented | ✓ |
| Limitations explicitly listed on the poster (not in a footnote) | ✓ |
| Working live demo (recommender + trade CLI + FA planner) | ✓ |

## Scope

| Layer | v1 (poster + demo) | v1.5+ |
|---|---|---|
| Player universe | All ~700 current NHLers + top ~100 draft-eligibles | Historical NHLers since 2010 |
| Time window | Rolling 12 months (CES) + career-to-date (BDS) | Multi-year engagement curves |
| Engagement sources | Reddit, Wikipedia pageviews, Google Trends, IG follower snapshots, NHL official social engagement, NHL jersey rankings, **All-Star vote totals (available seasons only — 2024-25 ASG was skipped for 4 Nations)** | Twitter/X engagement (paid), endorsement scrape, podcast appearances |
| Theme decomposition | 8 themes via OpenRouter LLM, **hand-validated on 300 stratified comments** | Theme drift over time; theme prediction from new viral events |
| Cap data | PuckPedia / CapWages | Historical contracts |
| Market control | **Team-baseline-subtracted (portable) + raw (observed), both reported** | Multi-year market drift |
| Validation | 3 proofs: jersey list + All-Star + event study | Direct revenue correlation (if surfaceable) |
| Demo | Acquisition recommender, trade-return CLI, FA pipeline | Web dashboard; rebuild-archetype classifier |

## Poster composition

| Section | Real estate | Content |
|---|---|---|
| Header | 10% | Title: **The Marchand Index** + subtitle + author. ONE quoted headline number. |
| 1. The honest reframe | 7% | "We do not measure revenue. We measure attention as a proxy for fan demand. Here is the precise limit of our claim." |
| 2. Method | 20% | Data sources (icons) → composite CES + BDS (volume-only) → **K=10 peer matching** + **market baseline control** → OAQ (observed + portable) → cap-adjust → Marchand Index. Worked example: Marchand vs. his K=10 peer group. |
| 3. Validation | 16% | Three side-by-side plots: OAQ_portable vs. jersey list rank, OAQ_portable vs. All-Star vote share (available seasons), event-study delta around top-50 signings. **Classifier validation: F1 + κ for theme labels.** Pre-registration doc citation. |
| 4. Pre-registered findings | 13% | H1–H4 results: confirmed / disconfirmed / inconclusive. Effect size + 95% CI per hypothesis. |
| 5. Theme decomposition | 13% | Stacked-bar visualization of theme shares for 8 case study players, with F1-per-theme footnote so judges can see classifier quality. |
| 6. Case studies + demo callout | 14% | 8 player cards: photo, OAQ_observed ± CI, OAQ_portable ± CI, Marchand Index, theme breakdown, named closest peer (for story), cap context. "Live demo at booth" footer. |
| 7. Limitations | 5% | What we don't claim. Market control caveats. Goalie exclusion. Twitter gap. Sample-size flags. |
| Footer | 2% | Future work + acknowledgments + repo URL. |

## Architecture (folder layout)

Project root: `C:\Local Only\Ai projects\Sports Analytics Conference Projeccts\Marchand Index\`

```
Marchand Index/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example
├── SESSION.md
├── docs/
│   ├── preregistration.md             # H1–H4 locked before modeling (Wk 3)
│   ├── methodology.md
│   ├── case_studies.md
│   ├── classifier_validation.md       # hand-labels, F1, kappa report
│   └── poster_layout.md
├── poster/
│   ├── layout.pptx OR layout.tex
│   ├── figures/
│   └── photos/
├── ingest/
│   ├── reddit/                        # PRAW client + sentiment + theme classification
│   ├── wikipedia/
│   ├── google_trends/
│   ├── instagram/
│   ├── nhl_jersey_rankings/
│   ├── nhl_official/
│   ├── allstar_votes/                 # available seasons only
│   ├── puckpedia/
│   ├── hockeydb/
│   ├── eliteprospects/                # shared w/ draft model
│   ├── nhl_api/                       # on-ice stats for peer matching
│   ├── attendance/
│   └── forbes/
├── data/
│   ├── reddit.sqlite                  # mentions + sentiment + theme tags
│   ├── wikipedia.sqlite
│   ├── allstar_votes.sqlite
│   ├── puckpedia.sqlite
│   ├── eliteprospects.sqlite          # shared with draft model
│   ├── theme_labels_hand.csv          # gold labels for classifier validation
│   ├── processed/
│   │   ├── player_engagement.csv      # joined per-player signal table (volume-only)
│   │   ├── player_favorability.csv    # separate: net sentiment per player
│   │   ├── player_polarization.csv    # separate: polarization HHI per player
│   │   ├── player_themes.csv          # theme-decomposition by player
│   │   ├── team_market_baseline.csv   # for market control
│   │   ├── peer_groups.csv            # K=10 peer assignments per player
│   │   ├── player_scores.csv          # CES, BDS, OAQ_observed, OAQ_portable, Marchand Index, CIs
│   │   ├── case_studies.csv
│   │   ├── historical_signings.csv
│   │   └── prereg_results.csv
│   └── cache/
├── features/
│   ├── ces.py                         # Current Engagement Score — VOLUME ONLY (no sentiment in weights)
│   ├── bds.py                         # Brand Depth Score
│   ├── favorability.py                # net sentiment as separate dimension
│   ├── polarization.py                # HHI of pos/neg balance as separate dimension
│   ├── themes.py                      # 8-theme LLM classification
│   ├── theme_validation.py            # F1 + kappa against hand labels
│   ├── cross_sub.py
│   ├── hometown.py
│   ├── captaincy.py
│   ├── trajectory.py
│   ├── viral_events.py
│   └── skill_baseline.py              # on-ice features for peer matching
├── model/
│   ├── peer_matching.py               # **THE METHOD** — K=10 NN peer-group matching
│   ├── market_baseline.py             # per-team attention baseline for portable adjustment
│   ├── oaq.py                         # OAQ_observed + OAQ_portable per player
│   ├── confidence.py                  # match-quality + bootstrap CI per player
│   ├── marchand_index.py              # OAQ / cap_hit_M
│   ├── validation_jersey.py
│   ├── validation_allstar.py          # available seasons only
│   ├── validation_event_study.py
│   ├── prereg_tests.py                # H1–H4 with bootstrap CIs
│   ├── team_classifier.py             # demo only
│   ├── acquisition_recommender.py     # demo only
│   ├── trade_eval.py                  # demo CLI
│   └── fa_pipeline.py                 # demo only
├── output/
│   ├── excel_export.py
│   ├── poster_figures.py
│   ├── case_study_cards.py            # error bars + both OAQ flavors
│   └── cli.py
├── scripts/
│   ├── build_engagement_set.py
│   ├── run_theme_classification.py
│   ├── validate_theme_classifier.py   # hand-label evaluation
│   ├── compute_peer_groups.py         # K=10 NN matching
│   ├── compute_market_baseline.py
│   ├── compute_oaq.py                 # observed + portable
│   ├── compute_confidence.py          # bootstrap CIs + match quality
│   ├── compute_marchand_index.py
│   ├── run_validations.py             # all three validation proofs
│   ├── run_prereg_tests.py
│   ├── render_poster_figures.py
│   └── export_workbook.py
└── tests/
```

## Data pipeline

### Per-player signal sources (free)

| Source | What | Frequency |
|---|---|---|
| Reddit (PRAW) | Mentions, upvotes, comment sentiment, cross-sub mentions, **theme classification** | Monthly full + weekly incremental |
| Wikipedia | Daily pageviews, viral-event spike detection | Daily |
| Google Trends (pytrends) | Search interest 12-mo + 5-yr | Monthly |
| Instagram (instaloader) | Public follower count, post count | Monthly snapshot |
| NHL official | Top-engaged @NHL + team-account posts; player-tag count | Monthly |
| NHL jersey rankings | Annual top-10 + top-20 (validation only) | Once per season |
| **All-Star vote totals (AVAILABLE seasons only)** | Per-season fan vote shares. **NOTE: 2024-25 had no ASG (4 Nations Face-Off instead) — use 2022, 2023, 2024 and 2026 if it happens.** | Once per available season |

### Per-team signal sources (for market control + demo + event study)

| Source | What |
|---|---|
| Forbes annual valuations | Team valuation, revenue |
| HockeyReference attendance | Per-season home attendance avg |
| HockeyDB | Coach + captaincy history |
| EliteProspects | Each team's drafted-player NHL outcomes |
| PuckPedia | Team cap structure, contract expiry |
| Team-account social platforms | Follower count over time (for event study + market baseline) |

### Cap + contract source

PuckPedia (or CapWages fallback). Polite scrape, monthly.

### Sentiment + theme classification pipeline

**Two-pass LLM analysis on Reddit comments** (OpenRouter free tier):

**Pass 1 — Sentiment.** Each comment → positive / negative / neutral. Aggregate per player:
- `pos_count`, `neg_count`, `neu_count`
- `net_sentiment = (pos - neg) / total` → **stored as `favorability_score`, NOT in CES weights**
- `polarization_score = min(pos, neg) / max(pos, neg)` → **stored as separate dimension**

**Pass 2 — Theme.** Each comment → one of 8 themes:

| Theme | What it captures |
|---|---|
| `skill` | On-ice ability, stats, plays |
| `fight` | Fights, hits, physicality, enforcer reputation |
| `personality` | Humor, charisma, media presence, interviews |
| `fashion_style` | Suits, hair, off-ice fashion |
| `off_ice_life` | Family, hobbies, lifestyle outside hockey |
| `controversy` | Suspensions, public spats, polarizing actions |
| `charity_community` | Charitable work, community presence |
| `relationship_viral` | Significant other in news, viral moments, cultural crossover |

Per-player aggregation: % of total mentions tagged with each theme. Theme concentration = Herfindahl index.

### LLM classifier validation (new — Wk 5)

Before any theme-based finding is reported:

1. **Stratified hand-label sample:** 300 Reddit comments, ~40 per theme, drawn proportionally to expected theme prevalence (skill is the largest bucket, so it gets more).
2. **Two annotators** (owner + one peer reviewer where possible) label independently; if budget for two is unavailable, single-annotator labels are explicitly flagged.
3. **Compute:**
   - Per-theme precision, recall, F1
   - Macro-F1 across all 8 themes
   - Cohen's kappa (LLM vs. gold labels)
   - Confusion matrix (which themes get confused with which)
4. **Quality gate:** Macro-F1 ≥ 0.70 (aim) or ≥ 0.60 (ship floor). κ ≥ 0.65 (aim) or ≥ 0.55 (ship floor).
5. **If gate fails:** iterate on the classifier prompt, swap to a different OpenRouter model, or hand-curate a few-shot prompt with positive examples per theme. Re-validate.
6. **Report:** `docs/classifier_validation.md` with full F1 table + confusion matrix. Poster Section 3 footnote cites the macro-F1 and κ values.

### Scrape resilience

`requests-cache` everywhere. robots.txt + 1–3 sec sleep. Graceful degradation on missing components.

## Feature engineering

### Current Engagement Score (CES) — VOLUME ONLY (rolling 12 months)

**Critical change from earlier draft: `net_sentiment` is REMOVED from CES weights.** Including sentiment in the base score would punish polarizing players (Reaves, Marchand, Tkachuk-types) for being controversial — exactly the players the model is designed to find.

Per-player z-scored composite within `(position, season)`:

| Component | Weight | Source |
|---|---|---|
| Reddit mention count | 0.18 | reddit.sqlite |
| Reddit upvote sum on player-tagged posts | 0.12 | reddit.sqlite |
| Cross-subreddit mention count | 0.18 | cross_sub.py |
| Wikipedia 12-mo pageview total | 0.22 | wikipedia.sqlite |
| Google Trends 12-mo mean | 0.10 | google_trends/ |
| Instagram follower count | 0.10 | instagram/ |
| NHL official engagement (player-tagged posts) | 0.10 | nhl_official/ |

Weights sum to 1.00. Reallocated cleanly from the prior draft after removing `net_sentiment`.

**Favorability and polarization are separate output dimensions** (`player_favorability.csv`, `player_polarization.csv`), reported alongside OAQ but never folded into it.

### Brand Depth Score (BDS) — career-to-date

| Component | Weight |
|---|---|
| Career Wikipedia pageview mean (per year played) | 0.30 |
| NHL jersey-list appearances (count of years in top-20) | 0.20 |
| Career All-Star selections | 0.10 |
| Years of NHL service | 0.15 |
| Instagram follower count (total) | 0.15 |
| Career captaincy duration | 0.10 |

Skill leakage in BDS (All-Star + service years) is acceptable because BDS is *meant* to capture longevity-driven brand. Leakage is removed by the peer-matching step downstream.

### Composite engagement raw

`engagement_raw = 0.7 × CES + 0.3 × BDS`

### OAQ — Off-Ice Attention Quotient (THE METRIC)

**Method: K-nearest matched peer group (K=10) — robust replacement for single-twin matching.**

For each player P:

1. **Build skill vector:** position, age, PPG, TOI/G, points/60 at 5v5, role band, league context, NHLe-adjusted production.
2. **Find K=10 nearest neighbors** of P in standardized skill space using Mahalanobis distance with cohort-specific feature scaling. Require minimum match quality (median pairwise distance below 75th percentile of all NHLer distances). Players who fail the quality threshold get OAQ = NaN with a `match_quality=low` flag.
3. **Compute peer-group attention:** `peer_engagement_mean = mean(engagement_raw across K=10 peers)`.
4. **OAQ_observed(P) = engagement_raw(P) − peer_engagement_mean(P)**.

Interpretation: OAQ_observed is the attention delta between a player and the *average* attention of their 10 closest skill-equivalent peers. Because skill is held constant *by design across a group*, OAQ_observed is the cleanest possible measure of "extra attention not explained by skill," and is robust against any single bad match.

**For storytelling (poster + case study cards): the K=1 closest peer is shown by name** alongside the K=10 group statistics. K=10 is the metric; K=1 is the human-readable story.

### Market amplification control — both lenses reported

The methodological pushback worth addressing head-on: Toronto / Montreal / Boston / NY / Chicago players get amplified attention by playing in a larger media market. A naive OAQ rewards them for being on the Leafs rather than for being who they are.

**But fully stripping market effect over-corrects.** Marner's Toronto-market amplification partly *follows him* if he's traded; his name recognition outside hockey wouldn't reset. So we report **both** lenses:

1. **`team_market_baseline`** per team = median engagement-per-roster-spot of that team's full active roster.
2. **`OAQ_observed`** = engagement_raw(P) − mean(engagement_raw across K=10 peers). The "raw" attention delta — market-included.
3. **`OAQ_portable`** = (engagement_raw(P) − team_market_baseline_P) − mean((engagement_raw − team_baseline) across K=10 peers). Market-stripped — the harder, more conservative claim.

**Headline metric for the poster = `OAQ_portable`** because it survives the strongest judge attack ("but isn't Marner just famous because he's a Leaf?").

**Excel + demo + case study cards = BOTH columns**, side by side. Users can pick their lens depending on the question:
- "Who's currently the biggest commercial asset?" → `OAQ_observed` (market-included)
- "If we sign Player X here, what attention would they bring?" → `OAQ_portable`

### Marchand Index (the cap-adjusted output)

`marchand_index = OAQ_portable / cap_hit_M`

Reported with **bootstrap 95% confidence interval** per player. Bootstrap procedure: resample player's mention pool with replacement 1000 times, recompute peer-group mean from resampled peer mentions, recompute OAQ_portable, take 2.5th and 97.5th percentiles.

For prospects (no cap hit): use predicted entry-level slot from draft position bucket.

Players with Marchand Index ≥ +1.0σ above median = **Marchand-positive** (commercial bargains).
Players with Marchand Index ≤ −1.0σ below median = **Marchand-negative** (high cap, low off-ice draw).

### Match quality + confidence

Per player:
- `match_quality_score` = median Mahalanobis distance to K=10 peers, percentile-ranked
- `match_quality_flag` ∈ {high, medium, low}; low = OAQ shown but with prominent warning
- `mention_sample_size`: count of Reddit comments used. Low N → wider bootstrap CI; flagged.
- `oaq_portable_ci_95`: bootstrap interval, shipped alongside the point estimate

Stars (few similar-skill peers) and goalies (categorically different) tend to land in `medium` or `low`. The poster case study cards show error bars; the Excel ships every value with its CI.

### Other features (supporting)

| Feature | Why |
|---|---|
| `polarization_score` | HHI of pos/neg sentiment balance — captures Reaves/Marchand archetype |
| `favorability_score` | Net sentiment, reported as a separate dimension (NOT in CES) |
| `captain_flag` | C / A / former-C |
| `hometown_alignment_flag` | Born within team's local market |
| `cross_sub_count` | Mentions outside hockey subreddits — cultural crossover |
| `trajectory_class` | YoY CES delta: rising / falling / steady |
| `viral_event_flag` | Spike in pageviews + Reddit + Trends within last 90 days |

### Team Commercial Health (TCH) — demo only

NOT on the poster body. Per-team composite for the demo's team classifier: team-account followers, attendance %, Forbes valuation, roster-aggregated OAQ_portable, dev-success proxy.

## Models

### Peer-Group Matching (poster Section 2)

**Inputs:** player skill vector, full population skill vectors, K=10.
**Method:** k=10 nearest-neighbor matching in standardized skill space. Mahalanobis distance with cohort-specific feature scaling. Match quality threshold: median distance to K=10 below 75th percentile of all pairwise distances among regular NHLers.
**Output:** K=10 peer set per player, named K=1 peer for storytelling, OAQ_observed + OAQ_portable.
**Diagnostics:** match quality distribution, peer coverage rate, OAQ distribution, sanity-check player → named-peer table.

### Three validations (poster Section 3)

**Validation 1 — Jersey list ρ.** Spearman ρ between OAQ_portable top-50 and NHL annual top-20 jersey list (sentinel-encoded for non-listed). Aim ≥ 0.50, floor ≥ 0.40.

**Validation 2 — All-Star vote ρ.** Spearman ρ between OAQ_portable and All-Star fan-vote share. **Available seasons only: 2022, 2023, 2024.** (2024-25 had no ASG — 4 Nations Face-Off replaced it. If 4 Nations published fan voting for lines/captains, we may use as a supplementary signal, but it's not equivalent to ASG fan vote.) Aim ≥ 0.55, floor ≥ 0.45. **This is the cleanest single proof point** when available — fan votes are pure attention by definition.

**Validation 3 — Event study (signings).** For top-50 FA signings since 2020:
- Pull signing team's account follower count + engagement at signing − 30 days, +30 days, +60 days, +90 days.
- Difference-in-differences regression: follower delta ~ signed_player_OAQ_portable + team_FE + season_FE + cap_hit_paid + position.
- Pre-registered direction: high-OAQ_portable signings should generate larger team-account follower deltas.
- Effect size + 95% CI reported.

Outputs: `validation_report.md` + 3 figures.

### Pre-registered hypothesis tests (poster Section 4)

`prereg_tests.py` runs H1–H4. Each returns: test statistic + p-value, effect size + 95% bootstrap CI, verdict (confirmed / disconfirmed / inconclusive), one-sentence summary.

Output: `prereg_results.csv` + 4 small figures.

### Theme classifier validation (poster Section 3 footnote)

`validate_theme_classifier.py` runs the hand-label evaluation:
- Load gold labels from `data/theme_labels_hand.csv`.
- Run classifier on same comments.
- Compute precision/recall/F1 per theme, macro-F1, Cohen's kappa.
- Confusion matrix.
- Output: `docs/classifier_validation.md`.

Macro-F1 + κ get cited as a small footnote on Poster Section 3 ("Theme classifier validated on N=300 hand-labeled comments: macro-F1 = X.XX, κ = Y.YY"). This is the rigor signal that distinguishes "themes computed by LLM" from "themes computed by validated LLM classifier."

### Case study renderer (poster Section 6)

`case_study_cards.py` produces 8 standardized cards:
- Player photo
- OAQ_observed ± 95% CI **and** OAQ_portable ± 95% CI (side by side bars)
- Marchand Index ± 95% CI
- Cap hit
- Theme stacked bar (8 themes, with theme-level F1 footnote)
- Named K=1 closest peer
- Match quality flag (visible)
- One sentence: "Why this player is on the poster."

Featured 8 (final list subject to data sanity):
1. **Brad Marchand** — namesake; high-skill, high Marchand Index, controversy-driven
2. **Ryan Reaves** — extreme OAQ_portable, low skill
3. **Matthew Tkachuk** — controversy + skill blend
4. **Brady Tkachuk** — sibling comparison (same skill cohort, different markets)
5. **Jack Hughes** — relationship_viral case (with McRae moment timeline)
6. **Mitch Marner** — Toronto-market test (compare OAQ_observed vs. OAQ_portable to demonstrate market control)
7. **Connor Bedard** — rising-trajectory case
8. **Sidney Crosby** — legacy BDS, modest CES, high cap — Marchand Index modest

Cards arranged 2×4 on the poster.

### Demo-only models

`acquisition_recommender.py`, `trade_eval.py` (CLI), `fa_pipeline.py`, `team_classifier.py` — booth-only.

## Output deliverables

### Primary: The Poster

`poster/layout.pptx` (or `.tex`). Renders to a printed 36"×48" poster. Built from `output/poster_figures.py` exports.

### Secondary: Supporting Excel handout

`output/marchand_index_2026.xlsx`:

| Sheet | Contents |
|---|---|
| `Players` | All ~700 NHLers: bio + CES + BDS + engagement_raw + peer-group + **OAQ_observed (± CI)** + **OAQ_portable (± CI)** + Marchand Index (± CI) + favorability + polarization + theme shares + flags + match_quality |
| `Peer_Groups` | Per player: K=10 peer set + skill distances + OAQ deltas |
| `Themes` | Per-player theme decomposition + theme-level classifier F1 |
| `Classifier_Validation` | Hand-label table + confusion matrix + per-theme F1 |
| `Market_Baselines` | Per team: market baseline value + roster count + how this enters portable OAQ |
| `Validations` | Three validation ρ values + signing event-study summary + scatter screenshots |
| `Prereg` | H1–H4 results |
| `CaseStudies` | Featured 8 with full breakdown |
| `Acquisition_Recs` | Demo support |
| `Trade_Examples` | Demo support |

### Tertiary: Live demo CLI

```powershell
python -m trade_eval --send "Brad Marchand" --receive "Toronto Maple Leafs"
python -m acquisition_recommender --team "Chicago Blackhawks"
python -m fa_pipeline --team "Anaheim Ducks"
```

Booth setup: laptop pre-loaded, results pre-cached, demo response <2 sec.

## Build order (~14 weeks)

| Wk | Layer | Deliverable |
|---|---|---|
| 1 | Scrape infra A | Reddit (PRAW), Wikipedia, Google Trends → SQLite mirrors. Establish polite scrape patterns. |
| 2 | Scrape infra B | Instagram, PuckPedia, HockeyDB, EliteProspects (shared w/ draft model), attendance, Forbes, All-Star vote totals (2022/2023/2024). |
| 3 | **Pre-registration committed** + Signal aggregation | `docs/preregistration.md` committed. OpenRouter sentiment classifier. **CES (volume-only) + BDS computed.** Favorability and polarization stored as separate outputs. |
| 4 | LLM theme classification (Pass 2) | Batch theme classifier across all ~700 players. Output `player_themes.csv`. |
| 5 | **LLM theme classifier validation** | Stratified hand-label 300 comments. Compute F1 per theme + macro-F1 + Cohen's kappa. Iterate prompt / model if F1 < 0.60. **Hard gate: don't proceed to scoring until macro-F1 ≥ floor.** |
| 6 | Peer matching + OAQ + market baseline | K=10 NN peer matching. Compute team_market_baseline. Compute OAQ_observed + OAQ_portable. Match-quality diagnostics. |
| 7 | Marchand Index + Validations 1 & 2 | Marchand Index = OAQ_portable / cap. Jersey list ρ. All-Star vote ρ (available seasons). **Mid-build gate: ρ floors met?** |
| 8 | Validation 3 + Pre-reg tests | Event-study DID. H1–H4 with bootstrap CIs. |
| 9 | Bootstrap CI + confidence formalization | Per-player bootstrap CI on OAQ_portable and Marchand Index. Match-quality flags. Confidence column shipped. |
| 10 | Demo layer | Team classifier, acquisition recommender, trade-return CLI, FA pipeline. Pre-cache demo examples. |
| 11 | Case study cards | Render 8 featured players with both OAQ flavors, error bars, theme breakdowns, named K=1 peer. Pull photos. |
| 12 | Poster figures | All figures rendered via `output/poster_figures.py`. Three validation plots, theme stacked bars, peer-matching example diagram, case study grid. |
| 13 | Poster layout + Excel + writeup | `layout.pptx` assembled. Supporting Excel exported. `methodology.md` + `classifier_validation.md` + `case_studies.md` finalized. |
| 14 | Polish + demo rehearsal | Poster print proof. Demo dry run (<2 sec). Final spell-check + numerical sanity. **Ship gate: all model + classifier + poster floors met.** |

**Mid-build gates:**
- End Wk 5: macro-F1 ≥ 0.60 on theme classifier. If not, no theme decomposition appears on poster.
- End Wk 7: Validations 1 + 2 pass the floor. If not, halt and revisit composite weights / peer matching.
- End Wk 8: Pre-reg test outputs known → drives headline finding.
- End Wk 12: All figures rendered. Lock content; only formatting changes after.

**Conference timing flexibility:** If the conference is sooner than 14 weeks out, cut in this order — Week 10 (demo) first, then trim Week 11 case studies from 8 to 5, then condense Week 9 confidence formalization. **Never cut Weeks 5 (classifier validation), 6 (peer matching + market control), or 7–8 (validations + pre-reg). Those are the rigor backbone.**

## Validation summary (three independent proofs + classifier audit)

1. **Composite-is-real gate (Validation 1):** Spearman ρ between OAQ_portable top-50 and NHL annual jersey list. Aim ρ ≥ 0.50, floor ρ ≥ 0.40.
2. **Fan-preference gate (Validation 2):** Spearman ρ between OAQ_portable and All-Star fan vote share, available seasons. Aim ρ ≥ 0.55, floor ρ ≥ 0.45.
3. **Premise-is-real gate (Validation 3):** Historical signing event study. Avg 60-day follower delta for top-50 FA signings since 2020 positive, p < 0.05 (aim) or directionally positive (floor).
4. **Classifier-is-real gate (Theme audit):** Macro-F1 ≥ 0.70 (aim) / ≥ 0.60 (floor), κ ≥ 0.65 (aim) / ≥ 0.55 (floor).

Failing any single gate: identify cause, iterate, re-validate. Failing two or more: do not ship.

## Critical files / external resources

- Vault defaults: `C:\Local Only\Ai projects\CLAUDE.md`
- OpenRouter URL: `https://openrouter.ai/api` (NO `/v1`).
- Reddit PRAW: register a script-app at reddit.com/prefs/apps.
- Wikipedia pageviews: `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/`.
- Google Trends via pytrends.
- PuckPedia: scrape only.
- NHL All-Star vote totals: NHL.com / archived season-summary pages (2022/2023/2024 only).
- Player photos: Wikimedia Commons (CC), NHL press images (cite), team-account official posts.
- EliteProspects SQLite mirror: **shared with NHL Draft Model**.

## Verification (end-to-end)

```powershell
python scripts/build_engagement_set.py
python scripts/run_theme_classification.py
python scripts/validate_theme_classifier.py       # macro-F1 + kappa
python scripts/compute_market_baseline.py
python scripts/compute_peer_groups.py             # K=10 NN
python scripts/compute_oaq.py                     # observed + portable
python scripts/compute_confidence.py              # bootstrap CIs
python scripts/compute_marchand_index.py
python scripts/run_validations.py
python scripts/run_prereg_tests.py
python scripts/render_poster_figures.py
python scripts/export_workbook.py
pytest tests/ -q

# Demo dry run
python -m trade_eval --send "Brad Marchand" --receive "Toronto Maple Leafs"
python -m acquisition_recommender --team "Chicago Blackhawks"
python -m fa_pipeline --team "Anaheim Ducks"
```

Manual sanity checks before printing:

- **Peer-matching sanity** — Marchand's K=10 peer set: plausible same-skill set of LWs at similar age/role/production? Distance distribution healthy?
- **OAQ_observed vs. OAQ_portable** — Marner: OAQ_observed should be noticeably higher than OAQ_portable (market amplification visible). Reaves: both should be high (he's not in a top market, so his attention is largely portable).
- **Marchand Index ranking** — Marchand, Reaves, Hughes top decile? Crosby modest (high cap absorbs his real attention)?
- **All-Star ρ ≥ 0.45?** If not, halt.
- **Theme classifier F1** — macro ≥ 0.60? Worst-performing theme identified and acknowledged in limitations?
- **Theme decomposition sanity** — Reaves dominant in `fight` + `personality`? Hughes dominant in `skill` + `relationship_viral`?
- **Pre-reg findings** — at least 2 of 4 hypotheses returned a clear verdict (not all inconclusive)?
- **Headline finding** — one quotable number computed and defensible?
- **Match-quality coverage** — ≥ 80% of NHLers have OAQ with `match_quality ∈ {high, medium}`?

## Open questions / known limitations (poster footer + Section 7)

- **Attention ≠ revenue.** Jersey list ρ + signing-impact event study are our best proxies; the dollar number is not ours to assert.
- **Market control is approximated, not perfect.** Team baseline captures team-average attention but doesn't separate "this team has stars" from "this team has a big market." Imperfect but transparent.
- **Peer-matching quality is uneven.** Stars have few good peers (small N at the top); goalies are categorically different. Match-quality reported per player; low-confidence cases flagged.
- **All-Star validation is data-availability-limited.** 2024-25 ASG was skipped for 4 Nations Face-Off — we have 2022/2023/2024 only. Stated transparently.
- **Twitter/X engagement is dark.** Free tier dead, paid out of budget. Documented gap.
- **LLM classifier accuracy is bounded.** We report macro-F1 and κ explicitly; worst-performing theme is acknowledged as higher-uncertainty.
- **Causal inference limits.** Event-study correlation between high-OAQ signings and follower deltas is suggestive, not causal — confounders partially controlled via DID + FE.
- **Coach / GM / dev staff retention is downstream of org health.** Surfaced as context, not modeled.
- **Reddit cross-sub mentions** can have name collisions. Disambiguated with team + position + recent-context filter.
- **Prospect OAQ is shaky.** Pre-NHL engagement volumes are inherently lower. Top-100 only; high-uncertainty cases flagged.
- **Goalies excluded from the main analysis.** Goalie skill features differ enough that peer-matching is unreliable; goalies are in the supplementary Excel only, with the static caveat that team-need-driven drafting and small sample make goalie attention modeling its own future-work problem.

## What we explicitly chose NOT to add (and why)

- **Twitter/X engagement scrape** — free tier dead.
- **Endorsement deal tracking** — private data, scraping fragile + ToS-grey.
- **Per-game ticket prices / secondary market** — too noisy.
- **Rebuild-archetype classifier** — defer to v1.1.
- **Podcast / streaming guest tracking** — too manual.
- **Coach-tenure as predictive model** — sample too thin.
- **Web dashboard / Streamlit** — Excel + CLI + poster is enough for v1.
- **Network analysis of teammate attention spillover** — interesting future direction; dilutes the peer-matching focus.
- **Goalie OAQ in headline analysis** — peer-matching breaks down for goalies; supplementary sheet only.

## Dependencies (requirements.txt seed)

```
requests
requests-cache
beautifulsoup4
lxml
praw                  # Reddit
pytrends              # Google Trends
instaloader           # Instagram
pandas
numpy
scikit-learn
lightgbm
scipy                 # Mahalanobis, statistical tests
statsmodels           # DID regression for event study
openpyxl
python-dotenv
pytest
anthropic             # OpenRouter via Anthropic-compatible client
tqdm
click                 # CLI
matplotlib            # poster figures
seaborn               # poster figures
Pillow                # case study cards
nltk                  # tokenization for stratified label sampling
```

## Why this is a 9.5/10 poster

- **Methodologically defensible against expert attack:**
  - K=10 peer matching (not brittle single twin)
  - Market control via team baseline (both observed + portable reported)
  - Volume separated from sentiment (no punishment of polarizing players)
  - LLM classifier validated against hand labels (macro-F1 + κ)
  - Bootstrap CIs and match-quality flags per player
- **Three independent validation proofs:** jersey list, All-Star vote, event study. Triangulated.
- **Pre-registered hypotheses:** rigor signal at publication-quality bar.
- **Novel analytical contribution:** validated LLM theme decomposition into 8 themes. Nobody in the public hockey-analytics community has shipped this.
- **Memorable cases:** 8 named players with photos, theme breakdowns, both OAQ flavors, error bars.
- **Sticky brand:** *The Marchand Index*. Eponymous + intuitive + accurate framing of namesake.
- **Honest limit-of-claim:** ROI → Fan Demand reframe survives any finance-judge attack.
- **Live demo:** acquisition recommender + trade CLI + FA planner running on a laptop.

What would push to 10/10:
- Direct team partnership giving access to internal ticket / merch revenue (eliminates the proxy concern entirely). Out of reach for v1.
- Multi-season historical re-run showing Marchand Index predicts future signing announcements / contract premia. Deferred to v1.5.
- Cross-validation against external SaaS attention products (e.g., Nielsen / SponsorUnited) for an independent ground truth. Costs money, out of scope.
