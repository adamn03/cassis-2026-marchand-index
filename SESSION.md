# Session Handoff
Date: 2026-05-16

## LAST SESSION
- **Built:** Full design + implementation plan for the NHL draft prospect model. Plan saved to `C:\Users\adamn\.claude\plans\build-an-nhl-draft-rosy-puzzle.md` and embedded below for portability.
- **Status:** Planning complete. No code written yet. The full plan was iterated through ~10 rounds of pushback / refinement. Spec is locked.
- **Next:** Start Week 1 of the build order — build `ingest/eliteprospects/` SQLite mirror + CLI (printingpress.dev ideology in Python), bulk-sync EliteProspects pre-draft seasons for 2010-2024 drafts × CHL/NCAA/USNTDP/USHL plus team-level scoring context, set up NHL API mirror for outcome data, build `historical_player_seasons.csv` from SQLite joins. This is the riskiest unknown — confirm scrape resilience and data quality before moving on.

## Quickstart for a fresh session
1. Read this whole file.
2. Project root: `C:\Local Only\Ai projects\NHL draft model\` (this folder).
3. Stack: Python (vault default). OpenRouter for free-tier LLM. CSV/SQLite local files. Atomic `.tmp` → rename writes.
4. Vault context: see `C:\Local Only\Ai projects\CLAUDE.md`.
5. OpenRouter URL gotcha: `https://openrouter.ai/api` (NO `/v1` suffix — Anthropic SDK appends `/v1/messages` itself).
6. Goal: Excel-ranked 2026 NHL draft prospect list before the late-June 2026 draft. Hybrid timeline — ship rough v1, then keep building.

---

# Full Plan

## Context
Data-driven NHL draft scouting assistant. Cross-league/age/body/context comparison. Output = ranked list with score, risk band, comparables, archetype, scouting-context notes. Replaces neither scouts nor public rankings — provides a normalized analytical foundation.

**Guiding philosophy:**
- Measurable stats drive the score.
- Subjective signal (consensus rank + keyword tags + LLM note) capped at ~10-15% of model score; surfaced as text for human judgment.
- Find undervalued prospects via large `model_rank − consensus_rank` deltas + historical comparables.

**Timeline:** ~8 weeks. Hybrid ship — get NA leagues + base model running first, layer Euro leagues in last 1-2 weeks. If a Euro source proves brittle, those prospects fall back to consensus-rank.

## Goals / Non-goals

**Goals:**
- Ranked Excel/CSV of 2026 eligibles with score, risk band, archetype, top-3 + ceiling + floor historical comparables, templated note.
- Beat consensus-rank baseline on 2010-2020 → 2021-2023 backtest.
- Find undervalued prospects.
- Reusable data + feature pipeline for v1.5+ growth.

**Non-goals v1 (deferred):**
- Detailed goalie projection model — goalies ARE in v1 but with a **simplified model**: KMeans clustering on goalie-specific features → predicted draft *range* (min/max of K nearest neighbors' actual draft positions), not a single rank. Rationale: goalies develop wildly differently, are heavily drafted on team-need (which we don't model), even 1st-round goalies bust ~30%+ of the time. See "Goalie model (v1, simplified)" below.
- 5v5-isolated / TOI / WOWY / deployment (paid microdata).
- Game-level primary-assist scrape (deferred to v1.5; ~1 week extra; v1 uses cheaper play-driving proxies).
- Full free-text NLP / sentiment on scouting reports (low ROI vs. consensus-rank approach).
- Team-fit overlay (v2).
- NHL Combine data (patchy, invitees only).
- Streamlit / web UI (v1.5).

## Scope

| | v1 | v1.5+ |
|---|---|---|
| Leagues | CHL (WHL/OHL/QMJHL), NCAA, USNTDP, USHL, SHL, Liiga, KHL | Czech, DEL, Allsvenskan, Mestis, Slovak, USPHL, BCHL/AJHL, more IIHF |
| Positions | Skaters (F+D) full model + Goalies simplified KMeans draft-range model | Full goalie projection with NHL-outcome labels |
| Output | Excel + templated note (LLM 1-2 sentence summary) | Streamlit dashboard, team-fit overlay |
| Features | NHLe, age-cohort z, trajectory, body, RAE, consensus, scouting tags, play-driving proxies, schedule strength, IIHF + cross-context elevation | Game-level primary assists, opponent-quality per-game, 5v5 splits, deployment, true WOWY |

Skater coverage ~85-90% of 2026 NHL draftees once Euro lands.

## Architecture (folder layout)

```
NHL draft model/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example                     # OpenRouter key for LLM notes
├── ingest/                          # printingpress.dev-ideology data layer
│   ├── eliteprospects/              # SQLite mirror + CLI (primary source)
│   │   ├── __main__.py              # python -m ingest.eliteprospects cohort|player|season|team
│   │   ├── scrape.py                # polite, cached, rate-limited HTML fetchers
│   │   ├── parse.py                 # HTML → typed rows
│   │   └── db.py                    # data/eliteprospects.sqlite schema + sync
│   ├── nhl_api/                     # local mirror of NHL career outcomes
│   ├── hockeydb/                    # cross-check + fallback outcomes
│   ├── iihf/                        # U18 WJC, U20 WJC, Hlinka, U17 WHC
│   ├── chl_top_prospects/           # annual CHL Top Prospects Game (cross-context)
│   ├── leagues/                     # league sites (only where EP coverage is gappy)
│   │   ├── chl.py / ncaa.py / ushl.py / shl.py / liiga.py / khl.py
│   └── rankings/                    # public ranker scrapes
│       ├── nhl_css.py / daily_faceoff.py / tsn.py (McKenzie+Button) /
│       ├── smaht.py / future_considerations.py / ep_preview.py
├── data/
│   ├── eliteprospects.sqlite        # primary source-of-truth
│   ├── nhl_outcomes.sqlite
│   ├── iihf.sqlite
│   ├── raw/                         # CSVs for rankings / sources without SQLite mirror
│   ├── processed/                   # joined player-season + outcome tables (Parquet/CSV)
│   └── cache/                       # requests-cache backend
├── features/
│   ├── nhle.py                      # league-strength multipliers + refit, position-specific
│   ├── age_cohort.py                # z-scores within (league, position, draft cohort)
│   ├── trajectory.py                # D-1/D/D+1 deltas
│   ├── body.py                      # ht/wt/BMI, position-z-scored
│   ├── consensus.py                 # public rank aggregation + variance
│   ├── play_driving.py              # team-relative PPG, goal share
│   ├── schedule_strength.py         # opponent win% per team-season
│   ├── international.py             # IIHF tournament z-scores + tournament elevation
│   ├── cross_context.py             # production OUT of usual linemate context
│   ├── goalie_stats.py              # SV%/GAA league-adjusted, team save environment, tournament SV%
│   └── scouting_tags.py             # fixed-vocab keyword tags from blurbs
├── model/
│   ├── nearest_neighbor.py          # pGPS-style cohort comparables (K=20)
│   ├── gbm.py                       # LightGBM multi-target regression
│   ├── explain.py                   # SHAP-based per-prospect top-3 feature drivers
│   ├── ensemble.py                  # weighted NN + GBM + consensus
│   ├── archetypes.py                # HDBSCAN clustering on NHL skater graduates
│   ├── goalies.py                   # KMeans clustering + draft-position-range output (v1 simplified)
│   └── notes.py                     # LLM-generated 1-2 sentence note
├── output/
│   ├── excel_export.py
│   └── templates.py
├── scripts/
│   ├── build_training_set.py        # historical ingest + label join
│   ├── refit_nhle.py
│   ├── train_models.py
│   ├── backtest.py
│   └── score_2026.py
├── autoresearch/                    # v1.5+ self-improvement loop
│   ├── program.md                   # research strategy doc
│   ├── config_space.yaml            # Optuna search space
│   ├── run_optuna.py                # free path
│   ├── run_agent.py                 # v2 paid agent path
│   ├── eval.py                      # backtest → composite metric
│   └── log.jsonl
├── tests/
└── SESSION.md                       # this file
```

State files: atomic `.tmp` → rename per vault convention.

## Data pipeline

### Historical training set (drafts 2010-2024, 15 years)

Expanded from original 10-year scope. Pre-2010 data quality drops (EP coverage thinner, no consensus archives, IIHF spottier, era effects). v1.5 expansion to 2005-2024 with era adjustment (era-specific NHLe per bucket: 2005-2009, 2010-2014, 2015-2019, 2020+; era as soft NN feature). v2 maybe 2000-2024 only if build-and-measure shows signal.

Per draft class × per prospect on v1 league:
1. **Bio** — name, DOB, ht/wt, position, shoots, draft year/team/overall pick (EP + NHL.com).
2. **Pre-draft seasons** — D−2, D−1, D (and D+1, D+2 follow-on) from EP scrape (cross-check HockeyDB). Includes team-level scoring context (team goals, GF/G, top-9 F PPG, top-4 D PPG) for play-driving + schedule-strength features.
3. **Cross-context events** — IIHF (U18 WJC, U20 WJC, Hlinka-Gretzky, U17 WHC) + CHL Top Prospects Game (Team Cherry vs. Orr split). **Why:** separates drivers from passengers on stacked top lines — canonical MacKinnon/Drouin Halifax 2012-13 case.
4. **Outcome labels** (from NHL API + HockeyReference):
   - `nhl_gp_by_age_24` (int)
   - `made_nhl_tier` (0=bust, 1=AHL/depth, 2=regular, 3=top-6/top-pair, 4=star) — **position-specific thresholds** (D P/GP thresholds shifted lower so top-pair D ≈ top-6 F at same tier)
   - `ppg_age_22_28` (continuous, NaN if insufficient GP)
5. **Public rankings at the time** (NHL CSS, McKenzie, FC where archived) — backtest baseline only.

Stored: `data/processed/historical_player_seasons.csv` + `historical_outcomes.csv`.

### Current 2026 prospects

1. Eligibility list: first-time (born 2007-09-16 → 2008-09-15) + repeat-eligibles, from EP + league sites.
2. Current-season stats from each v1 league site (incl. team-level scoring).
3. 2026 cross-context: Hlinka 2025, U18 WJC 2026, U20 WJC 2026, CHL Top Prospects 2026.
4. Consensus rank: scrape 6-8 free rankings → `consensus_rank` (mean) + `rank_variance` (std).
5. Scouting blurbs: 2-3 free sources per prospect → keyword tagger.

Stored: `data/processed/2026_prospects.csv`.

### LLM note generation

OpenRouter free-tier (e.g., `meta-llama/llama-3.3-70b-instruct:free`). One call per prospect (~250-400 prospects). Structured prompt: stats + tags + comparables → 1-2 sentence note. Always show underlying stats alongside; notes are advisory.

## Feature engineering

### Position handling (applies to every feature)

All comparisons are **position-locked**:
- z-scores within `(league, position, draft_year_cohort)`
- NN distance: position is a hard filter
- NHLe multipliers per-`(league, position)` (D multipliers lower)
- Body z-scored within position
- `made_nhl_tier` thresholds position-specific

### Features table

| Feature | How |
|---|---|
| NHLe | Per-(league, position) multiplier. Start Vollman/Bacon, refit separately for F and D. |
| Age-cohort z-score | Within (league, position, cohort), z of NHLe-adjusted PPG. |
| Trajectory | (PPG_D − PPG_D−1) and (PPG_D+1 − PPG_D when avail). |
| Body | Ht (in), Wt (lb), BMI; age-adjusted to cohort distribution. |
| Underage flag | Played higher-tier league pre-draft-eligibility year. |
| Relative age effect (RAE) | `days_younger_than_cohort_median` — late birthdays are systematically underrated. Strong "diamond in the rough" signal. |
| Consensus rank | Mean of available public ranker positions (sentinels for missing). |
| Rank variance | Std of available ranker positions. |
| Scouting tags | Fixed vocab (skating, hands, IQ, compete, defensive, leadership, shot, frame, motor) → 0/1/2 from blurbs. Low weight. |
| Schedule strength | `schedule_strength_pct` per team-season = avg opponent win% weighted by GP-vs-each-opponent. Addresses within-league schedule variance. NHLe handles between-league. |
| Team-relative PPG | Player PPG ÷ team-avg top-9 F PPG (or top-4 D PPG). Play-driving proxy #1 — teammate quality. |
| Goal share | G / (G+A). Play-driving proxy #2 — goal scorers less linemate-dependent. |
| ~~Weak-team amplification~~ | **DROPPED.** Couldn't control for opponent strength without per-game data → deferred to v1.5. |
| Tournament production | Per-event PPG at U18 WJC, U20 WJC, Hlinka, U17 WHC, CHL Top Prospects; z-scored within (event, position, age). Weighted 1.5-2.0× league stats. |
| Tournament elevation | (Tournament PPG z) − (regular-season PPG z). Captures "rises in big moments". |
| Cross-context elevation | Mean PPG z across events without primary linemates − league PPG z. **The MacKinnon/Drouin separator.** Weight 1.5×. |
| Cross-context sample size | Number of cross-context events. Low N → high uncertainty, flagged in note column, never used to downgrade. |

Features modules are pure functions: `(player_season_row) → feature_row`.

## Modeling

### Primary: cohort nearest-neighbor (pGPS-style)

For each prospect:
1. Feature vector: position, league-tier, NHLe-band, age-relative-to-cohort, height-band, weight-band, trajectory, cross-context elevation, tournament production.
2. K=20 nearest neighbors among 2010-2020 graduates.
3. Score = inverse-distance-weighted mean of neighbors' `made_nhl_tier` + `ppg_age_22_28`.
4. Risk band = std dev of neighbors' outcomes.
5. **Displayed comparables (5 named players):**
   - Top 3 closest by feature distance
   - **Ceiling** = K=20 neighbor with BEST NHL outcome (made_nhl_tier desc, ppg_age_22_28 desc)
   - **Floor** = K=20 neighbor with WORST NHL outcome

### Secondary: LightGBM multi-output

Predicts `made_nhl_tier` + `ppg_age_22_28` jointly. Strict time-series CV.

### Ensemble

`final_score = 0.5 × NN_score + 0.4 × GBM_score + 0.10 × consensus_rank_score`

**Methodological discipline — consensus_rank usage.** Used ONLY at scoring time (10% ensemble cap) and as backtest baseline. **NOT** an input feature to GBM or NN distance. Otherwise the model would partly reproduce the public consensus instead of improving on it.

**Position-specific risk band widening.** D have higher historical outcome variance than F. Same model_score → wider band for a D than an F.

**Feature-group weighting (NN distance + GBM input scaling):**
- League regular-season production: 1.0×
- IIHF tournament production: 1.5-2.0× (per user "top-level comp at that age" requirement)
- Cross-context elevation: 1.5× (the MacKinnon/Drouin separator)
- Play-driving proxies: 1.25×
- Scouting tags: 0.4× (low — advisory)
- Body / physical: 1.0×

### Archetype clustering

HDBSCAN on feature embedding of NHL graduates (2010-2020, `made_nhl_tier ≥ 2`). Manual cluster labels (playmaking winger, two-way C, puck-mover D, shutdown D, power forward, high-skill undersized). Prospect inherits dominant cluster of K=20 neighbors.

### Goalie model (v1, simplified)

Deliberately different from skater model. Goalie projection is unreliable, NHL teams draft goalies on need (not modeled), even 1st-round goalies bust ~30%+. **Outputting a single rank = falsely precise. Outputting a range = honest.**

- **Algorithm:** KMeans (k≈5-7, silhouette-tuned) on historical goalies 2010-2024, then K=15 NN within cluster.
- **Features (goalie-only, no skater features):** league-adjusted SV%, league-adjusted GAA, starter-share GP, age, ht/wt position-adjusted, team save environment, tournament SV%/GAA (U18/U20/Hlinka), D−1 → D SV% trajectory.
- **Outcome label:** actual NHL draft overall pick number. Predicting *where this profile gets drafted*, not their NHL career.
- **Output per goalie:** cluster label, `(draft_range_min, draft_range_max)` = (min, max) of K=15 neighbors' actual draft positions, median predicted position (for sort), top 5 comparable goalies + their draft pick + brief NHL outcome.
- **Output format:** separate `Goalies` sheet in Excel, sorted by median predicted position.
- **Validation:** for 2021-2023 historical goalies, ≥70% of actual draft positions must fall within predicted range.
- **Static caveat note on every goalie row:** "goalie projection is an open problem in hockey analytics; team-need drives goalie picks heavily and is not modeled here. Range is informational only."

### Note generation

`model/notes.py` → OpenRouter free-tier. Prompt: stats + archetype + consensus + top comp + tags → 1-2 sentence summary. Templated. Always show underlying stats.

## Output (v1)

`output/draft_2026_ranked.xlsx`, sorted by `model_score` desc. Conditional formatting on `model_minus_consensus`.

```
rank | name | pos | shoots | team | league | ht | wt | age |
model_score | risk_band | archetype |
nhle | age_z | traj_slope | underage_flag |
schedule_strength_pct | team_rel_ppg | goal_share | play_driver_score |
intl_tourn_ppg_z | tourn_elevation | tourn_events_played |
cross_context_elevation | cross_context_events_n |
consensus_rank | rank_variance | model_minus_consensus | top_3_drivers |
comp_1 | comp_1_outcome | comp_2 | comp_2_outcome | comp_3 | comp_3_outcome |
ceiling_comp | ceiling_outcome | floor_comp | floor_outcome |
scouting_tags | note_llm
```

`top_3_drivers` = SHAP-derived "top 3 features pushing this prospect's score" (LightGBM `pred_contrib=True`). Critical for scout adoption.

## Validation

`scripts/backtest.py`:
- **Train:** 2010-2020 (11 classes with age-24+ outcomes)
- **Holdout:** 2021-2023
- **Two-tier targets** (see CLAUDE.md for full table):
  - **Aim:** top-31 hit rate ≥65%, lift vs consensus ≥+10pp, Spearman ρ ≥0.50, stacked-line ≥70%, goalie range ≥70%.
  - **Ship gate (below = don't ship):** top-31 ≥55%, lift ≥+5pp, ρ ≥0.40, stacked-line ≥60%, goalie range ≥60%.
- **Hard rule:** if model fails to beat consensus baseline by ≥+5pp, do not ship — model adds no value.
- **Metrics computed:**
  - Top-31 hit rate (% reaching `made_nhl_tier ≥ 2` by age 24)
  - Spearman ρ (rank vs `made_nhl_tier`)
  - MAE (`final_score` vs `ppg_age_22_28`)
  - Lift vs consensus baseline
  - Calibration plot (binned predicted-tier vs actual, should be ~monotonic)
- **Stacked-line separability test (gate):** for same-team prospect pairs with `|made_nhl_tier_a − made_nhl_tier_b| ≥ 2`, model must rank the eventual stronger NHLer higher in ≥70% (aim) / ≥60% (floor) of pairs. Canonical: MacKinnon vs Drouin (Halifax 2012-13), Eichel vs BU 2014-15 teammates, others discovered by scan.

Fail-to-beat-baseline or fail-separability-test → iterate on features (esp. cross-context elevation weight) / NHLe refit / NN distance metric *before* shipping.

## Build order (~8 weeks, tight against June 2026 draft)

1. **Week 1** — Build `ingest/eliteprospects/` SQLite mirror + CLI (printingpress.dev ideology, Python). Bulk-sync EP pre-draft seasons 2010-2024 × CHL/NCAA/USNTDP/USHL incl. team-level scoring. NHL API mirror for outcomes. Build `historical_player_seasons.csv`. **Riskiest unknown.**
2. **Week 2** — Feature engineering on 15-year training set: NHLe refit (position-specific), age-cohort z-scores, trajectory, body, play-driving proxies, schedule-strength, RAE. Unit tests.
3. **Week 3** — Cross-context historical scrape (IIHF + CHL Top Prospects 2010-2024) into SQLite mirrors. Tournament + cross-context elevation features. NN model with top-3 + ceiling + floor comparables. First backtest. Archetype clustering.
4. **Week 4** — LightGBM training, ensemble, SHAP per-prospect drivers, refined backtest. Tune feature-group weights. **Mid-build gates: beat consensus baseline? Pass MacKinnon/Drouin separability test?**
5. **Week 5** — 2026 current-season ingest: NA league scrapers + public ranking scrapes. Build `2026_prospects.csv` (NA only).
6. **Week 6** — Add SHL + Liiga + KHL, current-cycle cross-context (Hlinka 2025, U18 2026, CHL TP 2026), scouting tag extractor, LLM note generation. Re-score 2026 skater pool. **Build goalie pipeline:** `features/goalie_stats.py` + `model/goalies.py` (KMeans + draft-range output). Backtest goalie range coverage on 2021-2023.
7. **Week 7** — Excel export (skater main sheet + Goalies sheet with predicted-draft-range columns), manual sanity review, weight retuning. Re-verify separability test + goalie range coverage ≥70%.
8. **Week 8 (buffer)** — Slippage / polish. Brittle Euro source → those prospects fall back to consensus-rank with a flag note.

**v1.5+:** Czech/DEL/Allsvenskan/junior-tier leagues; Streamlit dashboard; archetype refinement; goalie model design; team-fit research; self-improvement loop (below); historical expansion to 2005-2024 with era adjustment.

## Self-improvement loop (v1.5+, Karpathy autoresearch-style)

Runs *after* v1 ships. Each iteration mutates config, runs backtest, keeps change if composite metric improves.

**Free path (v1.5): Optuna Bayesian sweep.** Defines hyperparameter space (ensemble weights, NN K, feature weights, GBM hyperparams, NHLe knobs). No API costs. Hundreds of overnight experiments. **Start here.**

**Agent path (v2, needs API budget):** Claude Code agent with autonomous-loop skill iteratively edits `model/*.py`. Wider search (new features, restructure). Costs tokens per iter.

**Pick-range binary success metrics:**

Forwards:
| Pick range | By age 24 | By age 28 |
|---|---|---|
| 1-3 | 200+ GP, top-9 team TOI/G ≥1 season, 0.60+ PPG | top-3 team TOI/G ≥3 seasons, 0.75+ PPG, All-Star or top-50 league scoring season |
| 4-10 | 200+ GP, 0.50+ PPG or top-9 team TOI/G ≥1 season | top-9 team TOI/G ≥3 seasons, 0.60+ career PPG |
| 11-31 | 150+ GP by 24, 0.40+ PPG | 400+ career GP, top-12 team TOI/G ≥3 seasons |
| 32-62 | 100+ GP by 24 | 250+ career GP |
| 63-93 | 50+ GP or AHL top-scorer | 150+ career GP |
| 94+ | 25+ GP or AHL scorer | 75+ career GP |

Defensemen (lower P/GP, higher TOI weight):
| Pick range | By age 24 | By age 28 |
|---|---|---|
| 1-3 | 200+ GP, top-4 team TOI/G ≥1 season, 0.40+ PPG | top-3 team TOI/G ≥3 seasons, Norris ballot or All-Star or 0.50+ career PPG |
| 4-10 | 200+ GP, top-6 team TOI/G | top-4 team TOI/G ≥3 seasons, 0.35+ career PPG |
| 11-31 | 150+ GP by 24 | 400+ career GP, top-6 team TOI/G ≥3 seasons |
| 32-62 | 100+ GP by 24 | 250+ career GP |
| 63-93 | 50+ GP | 150+ career GP |
| 94+ | 25+ GP or AHL D | 75+ career GP |

**Composite metric:** `overall_score = Σ_r weight_r × hit_rate_r`. Suggested weights: top-3=4×, 4-10=3×, 11-31=2×, 32-62=1.5×, 63-93=1×, 94+=0.7×.

**Holdout discipline (critical):** Optuna only sees 2010-2020. 2021-2023 stays sacred. Rolling-window train/val splits within 2010-2020 for loop iterations. 2021-2023 = once-per-week sanity check on the loop's best config. Without this, the loop overfits the holdout.

## Critical files / external resources

- Vault stack: `C:\Local Only\Ai projects\CLAUDE.md` (Python, OpenRouter, CSV atomic writes).
- OpenRouter base URL: `https://openrouter.ai/api` (no `/v1`).
- NHLe refs: Patrick Bacon (Hockey Abstract), Rob Vollman.
- pGPS methodology: Pick224, Jeremy Davis (replicate approach, not code).
- NHL API: `https://api-web.nhle.com/` (free, no key).
- Polite scraping: `requests-cache` everywhere.

## Verification (end-to-end)

```powershell
python scripts/build_training_set.py
python scripts/refit_nhle.py
python scripts/train_models.py
python scripts/backtest.py
python scripts/score_2026.py
pytest tests/ -q
```

Manual sanity checks before trusting v1:
- Top 31 in output Excel — plausible vs. consensus? Disagreements defensible?
- Pick 3 known 2021 backtest graduates (star, regular, bust). Predicted scores in right ballpark?
- `model_minus_consensus` outliers — sane statistical story (NHLe, trajectory, age z)?
- Model top-31 hit rate beats consensus top-31 hit rate in `backtest_report.csv`. **Must win** or README flags v1 as informational only.

## Open questions / known limitations

- **NHLe refit data sufficiency** for sparse Euro leagues — fallback to published Vollman/Bacon values; refit only CHL/NCAA at scale.
- **EP scraping resilience** — fallback to HockeyDB + league sites if rate-limited.
- **2026 ranker coverage** — use mean of whatever has published by June.
- **Stacked top-line weakness** — team-relative PPG can't fully separate driver from rider when ≥2 NHL prospects share a top line. Cross-context features help; game-level primary-assist data (v1.5) is the real fix. Note column flags affected prospects.
- **Opponent-quality** — 3 layers: (1) between-league handled by NHLe ✓, (2) within-league schedule by `schedule_strength_pct` ✓, (3) per-game opponent variance deferred to v1.5 (needs game-level scrape). IIHF + cross-context features partly compensate for #3. ~80% coverage on free data.
- **IIHF sample sizes are tiny** (5-7 games/event) — a hot streak dominates the z-score. Always present GP/PPG alongside.
- **Tournament invite selection bias** — only best players get U18/U20 invites; "no tournament" handled as missing, not zero.
- **Goalie model is intentionally limited in v1** — outputs a draft range, not a single rank. v1.5+ can add NHL-outcome labels (career SV% vs peers, NHL GP as starter) and a full projection model once basic clustering is trusted and post-2026-draft data is available.

## What we explicitly chose NOT to add (and why)

- **Shots-per-game / shooting%** — inconsistent across 7 leagues, limited signal at this scope.
- **Team-development-quality score** ("London Knights produce well") — can't disentangle "team develops" from "better players go there".
- **Memorial Cup data** — happening May 2026 but rosters mostly already-drafted older players; limited new signal for first-time eligibles.
- **Plus/minus** — too noisy at low weight to be worth wiring.
- **Weak-team amplification** — couldn't control for opponent strength → would reward stat-padding.
- **Full free-text NLP / sentiment on scouting reports** — low ROI vs. consensus-rank approach.

## Dependencies (requirements.txt seed)

```
requests
requests-cache
beautifulsoup4
lxml
pandas
numpy
scikit-learn
lightgbm
hdbscan
openpyxl
python-dotenv
pytest
anthropic         # for OpenRouter via OpenAI-compatible / for Claude API if used
tqdm
click             # for CLI entrypoints
optuna            # v1.5 self-improvement loop
```
