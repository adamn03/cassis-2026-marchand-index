# Application Plan — Poster-Day Artifact + Post-Conference Applications

**Date:** 2026-07-11
**Status:** DESIGN ONLY. Nothing here is built until (a) the production compute lands and (b) the pre-registered gates resolve per the A31 shipping matrix. This plan exists so execution can start the moment gates pass.
**Inputs:** `marchand_index/value_propositions.md` (#1–#7), `NHL_Marchand_Index.md` (live spec + status banner), `Pilot Files/submission/abstract_v1.md` (accepted abstract), `docs/airtight_execution_plan.md` §A31/§E/§F (what "proven" means).
**Hard constraints inherited:** $0, local-only Windows/Python/SQLite, no revenue claims (attention is a proxy — every deliverable carries the caveat), no causal claims, headline = `OAQ_portable`, K=10 never single-twin, bootstrap CIs + `match_quality_flag` on every published OAQ, A34 leaderboard exclusion rule, themes only if the F1/κ gate passes.

---

## Horizon 1 — Poster-day artifact (CASSIS criterion 7, 2026-09-12)

### Decision: single-file offline HTML explorer — `marchand_explorer.html`

One self-contained HTML file (inline JSON + CSS + vanilla JS, zero network calls, opens from `file://` in any browser) exposing the full 774-player OAQ table with per-player case cards and CIs. Runs on the booth laptop; a spare copy on a USB stick is the disaster-recovery plan. Not hosted anywhere — this is a local artifact, not a web dashboard (the v1 "web dashboard" rejection stands: no server, no deploy, no URL).

### Why this option

| Option | Verdict | Reason |
|---|---|---|
| **Single-file HTML explorer** | **PICK** | Zero-dependency (any browser), survives no-wifi venue, judge drives it hands-on in seconds, shows CIs + match-quality natively, degrades gracefully per gate outcomes, buildable in ≤2 days because every input already exists as a `compute_oaq.py` emit. |
| Static interactive notebook | Reject | Requires a live Jupyter kernel at the booth (fragile), judges face code cells before content, restart-on-crash mid-conversation, and "static export" loses the interactivity that makes it criterion-7-grade. |
| Printed case-card deck | Reject as primary | Static print is not a *working* artifact — a judge can't interrogate it, sort it, or look up their own team's players. Weakest criterion-7 option. The poster's 2×4 printed card grid already covers this ground; a deck adds nothing. |

The spec's booth CLI (`trade_eval` / `acquisition_recommender` / `fa_pipeline`) is unchanged and remains the operator-driven second demo. The explorer is the *judge-touch* artifact: judges won't type CLI commands, they will click a table. Explorer complements, does not replace — criterion 7 gets stronger, nothing else weakens.

### Inputs (all already emitted or pre-registered emits — no new data)

| Input | Source | Used for |
|---|---|---|
| `player_scores.csv` (774 rows) | `compute_oaq.py` Phase-2 emit | OAQ_observed ± CI, OAQ_portable ± CI, hybrid MI + lens panel, `match_quality_flag`, `small_sample`, GP |
| `peer_groups.csv` | same run | K=10 peer set + named K=1 peer per card |
| Validation verdicts (small JSON, hand-assembled from `results.md`) | A31 shipping-matrix outcome | Header headline tier + validation strip |
| `player_themes.csv` + classifier F1/κ | only if gate passed | Theme stacked bar per card |
| 8 featured-player photos (Wikimedia CC, base64-embedded) | Phase-1 task 1.7 card list | Featured cards only; all other cards photo-free |

Generator: one new script `output/build_explorer.py` (pandas + stdlib) → writes `marchand_explorer.html` atomically (`.tmp` → rename). No JS framework, no CDN, no fonts fetched.

### Screens (single page, three zones)

1. **Header strip.** The A31 headline sentence — auto-selected from the verdicts JSON, so the artifact *cannot* overclaim relative to the shipping matrix (rows 1–8 map to fixed header text; row 8 renders the "exploratory descriptive instrument" wording). Directly under it, permanently visible, the limit-of-claim line: *"We measure public attention as a proxy for fan demand. No revenue claims. No causal claims."* Plus a compact validation strip: each gate's point estimate + 95% CI + verdict label, including inconclusive/failed ones.
2. **Table zone.** Sortable/filterable 774-row table: name, team, position, OAQ_observed, OAQ_portable, hybrid MI, match-quality badge. Search box; team/position/match-quality filters; column-click sort. **A34 enforced:** `small_sample=true` or null-GP rows are excluded from every ranked view by default; a "show excluded (n=X)" toggle reveals them flagged and unranked. An observed↔portable sort toggle is the method demo: watch big-market names drop when the market is stripped.
3. **Card zone.** Click a row → case card: OAQ_observed and OAQ_portable as side-by-side CI bars (never a bare point), hybrid MI with the descriptive per-dollar panel (per A31.5 MI is a panel, not a headline), K=10 peer list with the named K=1 peer flagged "story, not the estimator," match-quality badge, mention-sample size, theme stacked bar (rendered only if the classifier gate passed; otherwise the slot shows "theme decomposition did not clear its pre-registered validation gate and is not shown"), and a fixed footer on **every** card: *"Attention surplus vs. K=10 production-matched peers. Not revenue. Not causation."*

### What a judge does in 90 seconds

- **0–15s:** types a player they know → card with both OAQ flavors + CIs. Immediate personal hook.
- **15–45s:** sorts by OAQ_portable → sees the Reaves-archetype depth names surface; flips the observed↔portable toggle → Toronto/NY names visibly drop. The market control is *demonstrated*, not asserted.
- **45–75s:** opens the Marner card (or the traded-player reframe per Phase-1 task 1.7) → the observed-vs-portable gap is the worked example from poster §2, now interactive.
- **75–90s:** glances at the validation strip → sees gate verdicts with CIs, including anything inconclusive. The honesty tiering is the closing impression.

### Build budget (≤2 days, post-gates only)

| Slot | Work |
|---|---|
| Day 1 AM | `build_explorer.py`: load emits, assemble inline JSON, A34 filter, headline-tier switch |
| Day 1 PM | Table zone: render, sort, search, filters, toggles |
| Day 2 AM | Card zone: CI bars (inline SVG), peer list, theme conditional, claim footers |
| Day 2 PM | Featured-photo embed, offline smoke test (`file://`, wifi off, both light/dark), booth laptop + USB copy |

### Criteria check (1–7)

- **1 Novelty:** unaffected (presentation layer only).
- **2 ≥3 pathways:** unaffected; validation strip *displays* all pathways.
- **3 Prereg:** untouched — no prereg edits; the explorer reads verdicts, never computes them.
- **4 Per-claim uncertainty:** strengthened — CI bars on every card, no point estimate rendered without its interval.
- **5 Quotable finding:** header carries the A31 headline sentence verbatim.
- **6 Honest limits:** strengthened — limit-of-claim in header + every card footer; failed/inconclusive gates displayed, not hidden.
- **7 Working artifact:** this is it. CLI demo retained as backup depth.

Risk note: only failure mode is scope creep (animations, charts beyond CI bars, a hosted copy). The mitigation is this spec — anything not listed above is out.

---

## Horizon 2 — Post-conference applications (backlog #1–#7)

### Ranking: value × credibility-once-gates-pass ÷ effort

Scores 1–10; effort 1–5 (higher = costlier). Credibility = how hard a hostile professional statistician finds the *application* to dismiss, **given** the index itself has cleared its gates (V1b + secondaries + Gate-4, and the theme classifier where relevant).

| Rank | Idea | Value | Credibility | Effort | Score (V×C/E) | One-line rationale |
|---|---|---|---|---|---|---|
| **1** | **#2 Superstar Whistle** | 7 | 9 | 1.5 | **42.0** | GREEN data, huge N, falsifier (drawn/taken asymmetry) baked in — near-certain clean result at the lowest cost on the board. |
| **2** | **#6 Sticky Minutes** | 9 | 9 | 2.5 | **32.4** | Highest team-decision value; FE stack defeats both mechanical rebuttals; data-doability 9/10, fully in-pipeline. |
| 3 | #3 Road Tax | 6 | 8.5 | 2 | 25.5 | Textbook-defensible (Hausman–Leonard precedent) but the user is league policy, not a single decision-maker who acts. |
| 4 | #7 Generous Ledger | 8.5 | 8.5 | 3 | 24.1 | Strongest novelty + concrete trade-diligence decision, but the team×home fix and the xG/taxonomy build put it a tier costlier than #6. |
| 5 | #4 Contracts | 9 | 5.5 | 3 | 16.5 | Highest narrative value; credibility permanently shadowed by salary-in-denominator circularity even with the contracts-out variant. Keep as the *narrative* closer, not an application anchor. |
| 6 | #1 Sentencing Gap | 7 | 8 | 5 | 11.2 | Most quotable, cleanest residual design — but HARD (gated LLM rubric-coder, AMBER prose, ~250–350 rulings) and no buyer beyond media splash. |
| 7 | #5 DFS Price-vs-Crowd | 5 | 4 (expected) | 4 | 5.0 | Cleanest identification *if* free actual-ownership data exists; it probably doesn't at scale. Data-gated → expected credibility collapses. |

Sequencing note: #2 then #6 is also the right *dependency* order — #2 needs no LLM at all; #6's load-bearing theme placebo requires the classifier gate, which by the "gates passed" premise has already resolved. #7 is the designated third build if both land, reusing #6's panel infrastructure.

### Application 1 — #2 Superstar Whistle (officiating asymmetry audit)

- **User.** Primary: sports media analytics desks (The Athletic / Sportsnet-class) and NHL Hockey Ops officiating-integrity review. Secondary: team analytics staff setting expected penalty differentials for game-planning and discipline coaching.
- **Decision informed.** Officiating consistency review: which referee crews show the largest salience-linked drawn/taken asymmetry, and how large is the league-wide effect. For teams: how much penalty-differential expectation to attach to a high-OAQ opponent (or their own star) when projecting special-teams minutes.
- **Deliverable.** A reproducible local report (Python/SQLite, seed-deterministic like the main pipeline): (i) league-wide penalties-drawn/60 and penalties-taken/60 regressions within K=10 production-matched cells with referee fixed effects, lagged OAQ_portable; (ii) the asymmetry test as the headline table (drawn UP + taken DOWN = salience signature; both UP = agitator, published as the null); (iii) per-crew star-effect estimates with bootstrap CIs; (iv) one-page methods note. Data: NHL PBP penalties + ESPN officials feed, both GREEN-verified.
- **Honest limit-of-claim (must appear verbatim-class on every output).** *"We report a salience-associated asymmetry in penalty calls. We do not claim any referee consciously or deliberately favors any player; association is not intent and not causation. OAQ measures public attention — a proxy — not player value or revenue. Lagged attention windows limit, but cannot fully eliminate, reverse-causality from recent on-ice events. If drawn and taken rates move together, the salience mechanism is refuted and we publish that."*
- **Kill condition (inherited):** poor penalty↔referee join coverage or cells too sparse after FE; same-direction movement = published null, not a build failure.

### Application 2 — #6 Sticky Minutes (deployment-rigidity audit)

- **User.** Primary: team front office / analytics department auditing whether coach deployment is win-maximizing or name-protected ("are we playing the player or the brand?"). Secondary: player agents, since deployment manufactures the counting stats that price the next contract.
- **Decision informed.** A same-day in-house lever: whether a slumping high-salience player's ice time is responding to form the way an equally cold low-salience teammate's does. Output feeds the coach-deployment conversation and lineup/TOI reallocation — marginal wins reclaimed at zero acquisition cost.
- **Deliverable.** Per-team deployment-rigidity audit pack (local notebook + CSV, one per team, generated from one league-wide player-game panel): (i) within-player TOI-elasticity to rolling form (demeaned 5–10-game points/60 or on-ice xG) with player + opponent + game-state + season FE; (ii) the form_dev × OAQ_portable interaction with the downside-asymmetry test as the headline; (iii) block-bootstrap CIs clustered by player; (iv) the off-ice-theme placebo panel (glamour-theme OAQ must read live, skill-theme must wash out — the load-bearing answer to "the coach sees hidden two-way value"), which is permitted because the classifier gate has passed by premise; (v) placebo columns: team-market baseline (must be null), net-sentiment (must be null), and the OAQ_observed-vs-portable headline-metric check.
- **Honest limit-of-claim (must appear on every audit pack).** *"We report an association between public salience and the rigidity of deployment under negative form. We do not claim coaches consciously favor famous players, and we do not claim that reallocating minutes causes wins. Coaches observe information our rolling-form measure does not. Bottom-six ice time is floor-compressed, so depth-player elasticities are attenuated and noisier. OAQ measures public attention as a proxy — never revenue."*
- **Kill condition (inherited):** interaction CI includes 0 with player FE + cap control, or the effect survives only for OAQ_observed and not OAQ_portable.

### Guardrails common to all post-conference work

- Every deliverable ships the attention-is-a-proxy caveat, association-only framing, bootstrap CIs, and its pre-declared kill condition. New hypotheses get their own prereg entries before any production run — same discipline as H1–H4.
- Nothing in this horizon starts before the A31 shipping-matrix verdict is written. If the index lands in matrix rows 2–8 (downgraded/failed), Horizon 2 is re-scoped: credibility scores above assume row 1; a downgraded index caps every application at "exploratory" framing and the ranking must be re-run before committing effort.
- #4 Contracts stays in the portfolio as the narrative economic closer (owner's rule) but is never resourced ahead of #2/#6.
