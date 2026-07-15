# Idea-Maximization Review — red-team + ranked upgrades (2026-07-11)

**Status:** §4 ACCEPTED — owner approved U3 (A40 descriptive batch) 2026-07-13 with the U-slate (prereg §14, commit 91ab66b). §4's draft text is to be committed as A40 at its Phase-0 slot (after A39, before compute) — not yet written to prereg. Rest of this doc remains advisory red-team context. Next free impl amendment number: **A40** (A41 = pool dedup, claimed).
**Read before writing this:** live spec, airtight plan v1.1 (§A–§I), free-data supplement (A36/A37 + pre-chews), cross-domain supplement (A38/A39 + citation kit), spec prereg (H1–H4 + Gate-4 §5–§8), impl prereg (A1–A20 + verification log), accepted abstract (`Pilot Files/submission/abstract_v1.md`).
**Constraint honored throughout:** ~9-week runway with heavy execution debt (Reddit 0/774, Trends 331/774, Phase 0 uncommitted). Every proposal ≤1 day; most are hours.

---

## 1. Red-team: what A21–A39 still leave open

The A21–A39 program is unusually complete on *statistical* attack surface (identity, censoring, boundary bias, multiplicity, market confound, forking paths). The remaining exposure is concentrated in four places:

| # | Open attack / gap | Who fires it | Currently covered? |
|---|---|---|---|
| R1 | **Gate-4 coverage is load-bearing and untested against reality.** The ≥3-pathway criterion stands or falls on a floor (≥75 outside-star players × ≥3 primary events) that no one has probed. If the allow-list channels yield thin depth-player coverage, you find out ~8 fetch-days into a 9-week runway. | Execution reality, then J3 | No. Task-6 manifest covers *quota*, not *yield*. |
| R2 | **"Your confirmatory test can't distinguish anything at n=12 positives"** — and its twin, "you compared AUCs without a paired test." A31 fixes interpretation rules but never states the minimum detectable effect, and reports baseline AUCs beside OAQ's without a paired ΔAUC CI. | J1-class hostile statistician | Partially (A31.1/A31.3 interpretation only). |
| R3 | **"Is the composite even reliable measurement?"** No internal-consistency or split-half stability number exists anywhere. A psychometrically literate judge asks this in the first two minutes: a residual (OAQ) of an unreliable composite is mostly noise, and no bootstrap CI answers *trait stability*. | Measurement methodologist | No. `diagnostics/source_correlation.py` shows inter-source correlation, not reliability of the composite score. |
| R4 | **"Show me the pipeline recovers null."** No negative-control / permutation-calibration panel. The permutation machinery already exists for A31's p-values; the *visible* calibration figure does not. | Any validation methodologist | No (machinery yes, panel no). |
| R5 | **Criterion 7 has no concrete plan.** The airtight plan ends at poster copy; the spec's demo layer (recommenders, trade CLI) silently fell out of scope. "Working artifact" is currently a claim, not a deliverable with a task. | Judging rubric itself | No. |
| R6 | **Criterion 3 is the project's best asset and is presented as a footnote.** 39+ pre-data amendments with git timestamps is a rigor artifact no other CASSIS poster will have; current poster plan cites the prereg doc in one line. | Nobody attacks it — that's the problem; it's un-monetized | Under-used. |
| R7 | **Pool survivorship line missing from §G:** the 2026-06-17 roster snapshot excludes skaters who played most of 2025-26 but exited the NHL before June (buyouts, Europe, retirement). Their attention was real and in-window; they are absent from the pool. One sentence fixes it. | Detail-oriented judge | No. |
| R8 | **Quotable-finding insurance is thinner than it looks.** A39 is good but gated out of the headline except in shipping rows 6–8; the row-1 headline sentence is AUC-speak, correct but not what a judge repeats a week later. | Best-in-show bar | Partially (A39). |

---

## 2. Ranked upgrades

Scoring: criterion strengthened (of the 7), effort (h), risk, prereg amendment needed. Ordered by leverage-per-hour against the judge pool.

### U1 — Gate-4 fail-fast dry-run (10-player coverage probe) — DO FIRST
- **Fixes:** R1. **Criterion:** 2 (protects load-bearing pathway #3). **Effort:** 3–5 h once the YouTube API key exists. **Risk:** low. **Amendment:** NONE — this is execution QA producing no reported numbers; the §6.2.2 escalation rule already pre-registers what happens on shortfall, so probing yield early is not selection.
- Run the §6.3 query + §7.2 relevance filter (as amended by G4-A1) for 10 players — 5 depth-band, 3 regular, 2 star — against the primary allow-list only. Record events-per-player after relevance + dedup + ≥500-view floor. Extrapolate to the coverage floor (75×3). Costs ~1,000–1,500 quota units (well inside one day's 10,000).
- Payoff: if depth-band yield is thin you learn it in July with time to invoke the *pre-registered* escalation path calmly, instead of discovering it in the last fetch-week. This is the single cheapest insurance on the ≥3-pathway criterion.

### U2 — V1b power statement + paired ΔAUC companion (fold into A31 at write time)
- **Fixes:** R2. **Criteria:** 4, 6. **Effort:** 2–3 h. **Risk:** none. **Amendment:** NONE if folded into A31's text *before it is committed* (Phase 0 is still uncommitted — this window is free); otherwise one A40 clause.
- Two additions to the A31 amendment text:
  1. **Pre-computed precision statement** (Hanley–McNeil, n=12 vs 762, post-A37 n if larger): state in advance the expected CI half-width at plausible AUCs and the minimum AUC resolvable from 0.50. Registers "we knew the test's resolution before running it" — kills the "you designed a test you can't fail/pass" attack and makes shipping-matrix row 2 look planned rather than excused.
  2. **Paired ΔAUC:** the A31.3 baseline panel reports AUC(OAQ_portable), AUC(engagement_raw), AUC(PPG) side by side. Add the *paired* bootstrap ΔAUC with 95% CI (same 1,000 stratified draws, same seed — compute both AUCs per draw, difference the draws). Interpretation stays exactly A31.3's (baseline ≥ OAQ is expected); the pairing just makes the comparison statistically literate. A judge who sees unpaired AUCs compared will ding it; this is a two-line code change inside work already scheduled.

### U3 — A40 descriptive-measurement batch (one amendment, five clauses) — DRAFT BELOW
- **Fixes:** R3, R4, R7, R8 (partially), plus a cheap CI-honesty upgrade. **Criteria:** 4, 5, 6 (+2-adjacent credibility). **Effort:** ~1 day total across five small pieces, all post-compute analysis on data already scheduled. **Risk:** low — every piece is descriptive, floor-free, confined to designated panels under the §H rule. **Amendment:** YES — one A35-style batch. Draft text in §4 below.
- Clauses:
  1. **Split-half reliability of the composite.** Odd/even-day split of the wiki_en and wiki_intl daily vectors; odd/even-index split of the Reddit submission pool; trends and market held fixed (no sub-window resolution). Recompute engagement_raw on each half, Spearman-correlate halves across the 774, Spearman–Brown correct. One number ("split-half reliability r = 0.9x") answers the "is this noise?" question no bootstrap CI can, and it is nearly free — every input is already fetched for the primary compute.
  2. **Permutation-null calibration panel.** Shuffle engagement_raw across players (whole-pool permutation, 1,000 draws, seed 20260526), recompute OAQ and V1b AUC per draw, show the null distribution beside the observed value. Proves the pipeline is not mechanically rigged by pool construction or the peer/market structure. The permutation machinery is already mandated for A31's p-values — this adds a *figure*, not a method.
  3. **Market-attribution share on case cards.** For each case-study player: `λ·max(0, market_z) / engagement_raw` — "the share of this player's measured attention attributable to his market under the locked correction." Pure arithmetic on already-registered quantities. This is the Marner quotable ("X% of Marner's attention is Toronto") that survives every gate outcome — cards are illustration (A31.5), the stat is descriptive, and it makes the observed-vs-portable distinction concrete for a lay-hostile judge.
  4. **Drop-one-peer whisker on case cards.** For the 8 cards only: recompute OAQ_portable K times leaving out one peer each; show the min–max range as a thin secondary whisker beside the bootstrap CI. Directly pre-empts "your CIs ignore matching uncertainty" (the A26 disclosure table admits peer sets are not propagated — this shows, descriptively, how much that matters for the players actually on the poster).
  5. **§G survivorship line** (poster limitations): "The pool is the 2026-06-17 roster snapshot; skaters who exited the NHL before the snapshot are absent even where their in-window attention was real."

### U4 — Amendment-timeline "audit trail" figure (poster panel)
- **Fixes:** R6. **Criterion:** 3 (visibly showcased), 6. **Effort:** 3–4 h — generated from `git log` timestamps. **Risk:** none. **Amendment:** none (presentation only).
- One horizontal timeline: every amendment (A1–A40, G4-A1..3) plotted by commit date, with vertical markers for "first production Reddit byte" and "one-shot compute." Every design decision visibly predates the data. Caption: "Every rule on this poster was committed to git before the data it governs was fetched." No other poster in the room will have this figure; for an overclaim-hostile judge pool it is the single most memorable *rigor* visual available, and it converts the project's genuinely unusual discipline from a footnote into a headline asset. Costs nothing statistically.

### U5 — Criterion-7 artifact package: repo snapshot + one-command reproduce + booth lookup CLI
- **Fixes:** R5. **Criterion:** 7. **Effort:** ~1 day. **Risk:** low (see data-publication caveat). **Amendment:** none.
- Three pieces, replacing the spec's heavier demo suite (recommenders / trade CLI / FA planner = scope debt; cut them formally):
  1. Public GitHub snapshot of `marchand_index/` (code + prereg + derived CSVs; **exclude** `reddit_detail` text — publish derived counts only, ToS-clean).
  2. `reproduce.ps1` / `make reproduce`: one command → byte-identical `oaq_pilot.csv` + `results.md` at seed 20260526 (the abstract already promises diff-verified determinism — make it a stranger-runnable fact).
  3. Booth CLI: `python lookup.py "Player Name"` → card render (OAQ_observed ± CI, OAQ_portable ± CI, MI panel value, K=10 peers with distances, flags). All data is in CSVs already; this is an afternoon of formatting, runs offline, <2 s, and gives the booth a live artifact for any of 774 players a judge names.
- The poster footer already promises a repo URL; right now nothing in any plan produces it.

### U6 — Booth attack-FAQ card
- **Fixes:** presentation under fire. **Criteria:** 6 (and the oral-standing meta-goal). **Effort:** 2–3 h at poster phase. **Risk:** none. **Amendment:** none.
- One laminated page: the 10 most likely hostile questions, each answered in two sentences with a pointer to the amendment that already handles it ("Isn't this just a fame detector?" → Gate-4 + A31.3 baseline rule; "Reddit measures playing in Canada" → A30; "n=12 positives?" → U2 power statement; "λ=0.5 is made up" → A38 anchor + ladder; "matching bias at the star boundary" → A27; "post-hoc tuning?" → U4 timeline). The panel review generated this list already — §A of the airtight plan *is* the FAQ source. Composure at the poster is scored implicitly; this makes it mechanical.

### U7 — Elevate the A38 λ̂ portability estimate to second-billed finding (layout, not stats)
- **Fixes:** R8. **Criterion:** 5 (quotable insurance independent of gate outcomes), 1 (it is the poster's most *novel empirical* number). **Effort:** ~2 h at poster phase. **Risk:** none — labels and the A38 interpretation rule are untouched; this is real-estate allocation.
- "We measured how much fame travels when a player changes teams — an empirical portability estimate from n=N in-window movers" is a genuinely new number in hockey analytics (nobody has published a fame-portability coefficient), it is quotable in one sentence, and it exists regardless of how V1b/Gate-4 land. Currently A38 is destined for a diagnostics panel at footnote scale. Give it a titled sub-panel with the event-study picture (pre/post attention paths, movers vs peer counterfactual). Descriptive label stays verbatim.

### U8 — Merchandise/usage outcome sweep (pathway insurance) — OPTIONAL, ranked last deliberately
- **Fixes:** partial insurance if Gate-4 fails (shipping rows 3/7 cap pathway count at 2). **Criterion:** 2. **Effort:** 3–4 h search + small code (A37-pattern). **Risk:** moderate-honest: likely null result, and **J3's family logic would probably classify trading-card lists as the same purchase-behavior family as jerseys** — only a *usage*-class outcome (e.g., an official EA NHL "most-used players" release, if one exists for the window) would plausibly count as a distinct pathway. **Amendment:** YES (A41-class, A37-style all-or-none qualification rules) — do not run the search before the rule is committed.
- Recommendation: only spend the hours if the U1 dry-run comes back worrying. If Gate-4 looks healthy, skip — this is exactly the marginal-gain scope the pushback policy exists to catch.

### Explicitly considered and NOT proposed (so no future session re-derives)
| Idea | Why not |
|---|---|
| Zenodo/DOI archival of data + prereg | Tension with the local-only constraint's spirit; GitHub snapshot (U5) covers criterion 7; flag to owner only if they want citability. |
| Reddit comments via archive services | Already rejected (sibling plan) — construct change + ToS. |
| Any new composite component, weight, window, λ, K change | Locked; violates governing rule. |
| Additional Wikipedia-side outcomes (watchers, edits, talk pages) | Shared-platform with 0.40 of composite weight — same class as V3, would not count as independent. |
| Web dashboard for the booth | Rejected list; U5's CLI is the compliant 80% substitute. |
| H1–H4 / theme-classifier resurrection for the poster | Deferred by A10 scope note; reopening is the largest possible scope violation at 9 weeks. |

---

## 3. Sequencing against the existing plans

| Upgrade | When | Blocking? |
|---|---|---|
| U2 (fold into A31) | During Phase 0, at A31 write time — the free window closes when A31 commits | Yes — do not commit A31 without deciding this |
| U3 (A40 batch) | Phase-0 tail, after A39, before Phase-2 compute (same governing rule: Reddit 0/774) | Yes — amendment must precede compute |
| U1 (Gate-4 dry-run) | Immediately after G4-A1..3 commit + API key; before the full Gate-4 launch | Yes for Gate-4 launch |
| U8 (if taken) | Phase-0 tail, A37-style | Before compute |
| U4, U5, U6, U7 | Poster phase (post-Phase-2); U5's repo scaffolding can start any idle moment | No |

Total new pre-compute load: U1 + U2 + U3 ≈ 2 working days. Everything else lands in the poster phase where the current plans are thinnest.

---

## 4. DRAFT A40 text (NOT committed — owner decides; adjust number if A40 is taken)

```markdown
**A40 (YYYY-MM-DD) — Descriptive measurement-quality batch (five clauses). Logged
BEFORE the Phase-2 compute; Reddit remains 0/774. DESCRIPTIVE — no floor, no gate,
not a validation pathway; nothing here can alter the headline under any outcome.**

1. **Split-half reliability of the engagement composite.** The wiki_en and
   wiki_intl daily vectors (post-A36, zero-filled 365-day, date-indexed) are split
   odd/even by day index; the Reddit submission pool is split odd/even by
   submission index after the A15/A21 attribution filter; trends and all non-flow
   quantities are held at their full-window values in both halves (no sub-window
   resolution exists; disclosed). engagement_raw is recomputed per half under the
   unchanged §4/A12 weights and sentinel rules; the Spearman correlation of the
   two half-composites across the pool is reported with its Spearman–Brown
   correction and a 1,000-draw player-level bootstrap CI (seed 20260526).
2. **Permutation-null calibration.** 1,000 whole-pool permutations of
   engagement_raw across the 774 (seed 20260526); OAQ_observed, OAQ_portable, and
   the V1b AUC recomputed per draw; the null distribution is displayed beside the
   observed values in one designated calibration figure. Interpretation fixed now:
   this panel demonstrates pipeline calibration (a null input yields chance-level
   validation statistics); it is not a hypothesis test and carries no verdict.
3. **Market-attribution share (case cards only).** Each case-study card reports
   share_market = λ·max(0, market_z) / engagement_raw (0 when engagement_raw ≤ 0;
   flagged), labeled "share of measured attention attributable to team market
   under the locked λ = 0.5 correction." Arithmetic on already-registered
   quantities; illustration per A31.5, never evidence.
4. **Drop-one-peer sensitivity (case cards only).** For each case-study player,
   OAQ_portable is recomputed K times omitting one of the K=10 peers; the min–max
   range is shown as a secondary whisker beside the §10 bootstrap CI, labeled
   "peer-set sensitivity (not propagated in the primary CI — see A26 table)."
5. **Pool-survivorship limitation (poster §G addition, verbatim):** "The pool is
   the 2026-06-17 roster snapshot; skaters who exited the NHL before the snapshot
   are absent even where their in-window attention was real."

**Presentation rule (fixed now):** clauses 1–4 appear only in designated
descriptive panels per the airtight plan §H forking-paths rule, which is extended
to name them; none is eligible to become the headline under any outcome; no
number from this amendment is quoted standalone in the abstract-conformance copy.

**Anti-tuning compliance (§13):** logged before the Phase-2 compute while Reddit
is 0/774, so no composite, OAQ, or validation result could have influenced the
design; splits, permutation scheme, and card statistics are mechanical and fixed
in advance; weights (§4/A12), peer features (§6/A13), λ (A5), denominators
(A4/A8), pool (§2/A10), window (A11/A14), seed, and all validation floors (§9,
A6/V3, A31) are unchanged.
```

---

## 5. Most likely reason this loses best-in-show — and the counter

**Verdict.** The most likely loss mode is not a methodological kill-shot — the A21–A39 program has pre-answered essentially every statistical attack — it is *rigor without a memorable discovery*. The honest architecture deliberately narrows the headline to "OAQ_portable separated 12 jersey-list players from 762 skaters with AUC = X.XX," while simultaneously (and correctly, per A31.3) reporting that raw fame does roughly the same; every striking claim the project was named for — polarization, themes, the Reaves archetype, H1–H4 — is deferred or contingent on a load-bearing Gate-4 whose depth band is pre-disclosed as statistically thin. A judge panel of pro statisticians will respect the discipline, score it safely into the upper tier, and then hand best-in-show to a poster that taught them one new thing about hockey. The week-later memory of this poster is currently "impeccably pre-registered" — a compliment, not a win.

**Single highest-leverage counter.** Guarantee one novel, defensible, gate-independent empirical sentence and bill it prominently: elevate the A38 mover event-study to a titled second finding — *the first empirical estimate of how much NHL fan attention travels with a player who changes teams* (λ̂ with CI, movers-vs-peer-counterfactual picture). It is already pre-registered, already costed, uses data already in hand, cannot be sunk by any validation outcome, and is the one number in the entire build that no one in the room has seen before. Pair it with U4's audit-trail timeline so the poster's two memorable images are "fame is X% portable" and "every rule predated the data" — a discovery plus a discipline, which is what best-in-show looks like to this judge pool.

---

## 6. Seven-criteria conformance check of this review's proposals

| Criterion | Effect of U1–U8 |
|---|---|
| 1 Novelty | U7 surfaces the most novel empirical estimate (fame portability) instead of burying it. No method changes. |
| 2 ≥3 pathways | U1 protects the load-bearing pathway; U8 optional insurance. No pathway weakened. |
| 3 Prereg | U3 adds one pre-compute batch amendment in the established pattern; U2 lands inside A31 before commit; U4 showcases the discipline. Nothing post-hoc. |
| 4 Uncertainty | U2 (power + paired ΔAUC), U3.1 (reliability CI), U3.4 (peer-set whisker) all extend per-claim honesty. |
| 5 Quotable | U3.3 (Marner market share), U7 (λ̂), A39 (existing) — three gate-independent quotables. |
| 6 Limit-of-claim | U3.5 closes the survivorship gap; U6 operationalizes limits under live fire. All new stats carry fixed descriptive labels. |
| 7 Artifact | U5 turns the promised repo/demo from a claim into a scheduled deliverable. |

No proposal touches: weights, window, λ, K, seed, pool, floors, headline definition, or anything in `Pilot Files/`. No proposal exceeds one day of effort.
