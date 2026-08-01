# Session Handoff
Date: 2026-07-31
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: Decided to demote the cap/contract adjustment and add a four-way attention split (pos/neg × own/other fanbase). Split into Phase A (affiliation only, no LLM) and Phase B (sentiment). **Built Phase A end-to-end — code is correct and tested (269 pass, +29), but the run exposed a BLOCKING data-scope defect that makes the headline metric uncomputable from existing data.** Two implementation plans written. Phase B not started.

STATUS: blocked

BLOCKER: `raw/reddit_detail.csv` cannot support an own-vs-rival split. See below.

---

## BLOCKER — A22 sub-scope makes `other` structurally empty

**Symptom.** `compute_affiliation.py` ran clean: 163,276 in-window mention pairs, own 59.6% / other **3.1%** / neutral 37.3%. The neutral share matched prediction exactly (37.3% vs ~37% expected), so the venue map is complete — but `other` at 3.1% is an artifact, not a measurement.

**Root cause.** `fetch_reddit.py` header lines 6-7 and 41 (rule A22): each player was searched **only** in `r/hockey`, `r/nhl`, `r/fantasyhockey`, and the team subreddit(s) they were rostered on inside the window. **Rival subreddits were never scanned for that player.**

**Evidence.**
| Check | Result |
|---|---|
| Players with any rival mention | 220 of 771 |
| Players with `rival_reach == 0` | 551 |
| Max `rival_reach` observed | 3 (of 31 possible rivals) |
| Mean `other_mentions`, traded players | 22.4 |
| Mean `other_mentions`, non-traded | 1.9 |

`rival_reach` maxes at 3 because it can only count a player's own FORMER team subs. The `other_*`, `own_share`, `rival_reach`, and `top_rival` columns measure **trade history**, not rival-fanbase attention.

**What IS valid:** `own_mentions`, `own_intensity`, `neutral_mentions`, `neutral_intensity`. Own subs and all three neutral subs were searched for every player, so the own-vs-neutral split is real.

**Fix.** Re-match all 771 players against all 36 corpus subreddits. The corpus already holds every submission needed (**250,004** across 36 subs in `cache/reddit_corpus/`) — only the *matching* was scoped, so **no new collection is required**. Cost is a re-run of the A21/A23/A42/A43 identity-disambiguation machinery at ~12x current matching volume. Non-trivial risk: those guards were tuned in an own-sub context, where a surname ambiguous league-wide may be unique within one team's sub. Expect the common-word / shared-surname guards to need re-validation.

**Guard in place.** `compute_affiliation.py:PUBLISH_DELIVERABLE = False` blocks the copy to `final_dataset/`. The misleading copy was created once and has been removed. Flip to `True` only after the re-scan.

---

## Phase A — what landed

Committed (4 commits, all tests green):
- `affiliation.py` — venue map, nickname→code map, player team-timeline from trades, mention labeling, volume-normalized aggregation. Pure functions, no I/O.
- `compute_affiliation.py` — corpus scan + driver, deliverable copy gated.
- `tests/test_affiliation_a45.py` — 29 tests. Suite 240 → **269**.
- `attention_affiliation.csv` — 771 rows, 104 `low_n`. **Not committed, not published** (invalid columns).

NOT done, deliberately: Task 6 (diagnostics) and Task 7 (prereg A45). Pre-registering a metric known to be broken would be wrong, and the diagnostics would report meaningless rival numbers.

**Design decision worth keeping.** Normalize by **submissions**, never subscribers. r/BostonBruins has *more* subscribers than r/Habs (119,306 vs 101,589) but ~1/5 the submissions (3,070 vs 14,510). Subscribers are the wrong denominator for attention.

---

## PLANS — DELETE AFTER USE (owner asked)

- `Full Project Files/docs/superpowers/plans/2026-07-31-phase-a-attention-affiliation.md` — **Tasks 1-5 executed; 6-7 intentionally skipped.** Delete once the re-scan decision is made, or keep as the template for the corrected re-run. Owner's call.
- `Full Project Files/docs/superpowers/plans/2026-07-31-market-z-activity-sensitivity.md` — **NOT executed.** Still live and still valid; the blocker above does not affect it. Do not delete.

---

## NEW FINDING — subscribers vs activity (feeds open item #3B)

Independent evidence that `market_z`'s social component mis-measures fanbase intensity:

**Spearman(`team_sub_subscribers`, in-window submissions) = 0.299** across 32 teams — nearly independent measures.

| Team | Subscribers | Submissions | Per 1k subs |
|---|---|---|---|
| MON | 101,589 | **14,510** | 142.8 |
| TOR | **359,680** | 9,603 | 26.7 |
| BOS | 119,306 | 3,070 | **25.7** |
| FLA | 34,946 | 8,132 | **232.7** |
| UTA | 2,268 | **81** | 35.7 |

Subscribers rank MON 7th; activity ranks MON 1st. That is exactly the mechanism open item #3B proposes for MON holding 16 of the OAQ_portable top-100.

**UTA is a data hole:** 81 in-window submissions vs 2,171 for the next-lowest team, and 2,268 subscribers vs a ~62k league median — both artifacts of the franchise rename splitting the subreddit. Note the bad subscriber figure is already inside the **A30 primary**, not just the proposed lens.

Plan `2026-07-31-market-z-activity-sensitivity.md` (A46) turns this into a sensitivity analysis. Key constraint pre-locked in that plan: **activity is endogenous** (a winning team's sub posts more), so it can only ever be a reporting lens, never a `market_z` primary.

---

## Design decisions made this session (not yet pre-registered)

1. **Cap adjustment demoted.** Headline becomes plain `OAQ_portable`; cap becomes an audit column. Separate decision from the split — spec them apart.
2. **Build negative-first.** Headline metric is `hostility_gap = neg_other_rate − neg_own_rate`. Purely negative-label-driven, so it is identical under 3-way sentiment and under a neg/non-neg fallback. A κ-gate failure then degrades the poster instead of breaking it.
3. **If the sentiment gate fails, collapse to neg/non-neg — never pos/non-pos.** r/hockey is 37% news and game threads; pos/non-pos sweeps all that neutral volume into "negative" and re-derives raw volume.
4. **Four-way split is a companion panel**, not a CES component. It covers ~63% of one of four CES inputs and cannot rescale OAQ.
5. **Phase B costs ~$13-20** (Sonnet 5 on Batch API, ~35k items) — cheap enough that the $0 constraint is a preference, not a limit. `claude -p` headless loop is the genuine $0 path with equivalent consistency.

---

## STILL OPEN (unchanged from prior session)

- **#2** — `OAQ_portable` low-tail behaviour (Logan Stanley class); decisions 1-4.
- **#3A** — missing-skill star gets headline OAQ via imputation (Barkov #15 on NaN skill).
- **#3B** — MON floods top-100 (16/26 Habs). **Now has new evidence — see above.**
- **#4** — degenerate peer set for thin/small-sample rows with extreme rate features (Kevin Rooney).
- **Owner data request** — 32-team IG + X follower counts, hand-collected. Still worth doing: IG is an exogenous *stock* that fixes reddit's English/US skew. Distinct job from the activity *flow* above; one does not replace the other.

---

NEXT: Decide the Phase A blocker. Three options, in order of my recommendation:
**(a)** Re-scan the corpus unscoped — re-match 771 players × 36 subs, re-validating the A42/A43 surname guards at league-wide scope. Unblocks the whole four-way split. Est. 1-2 days.
**(b)** Ship Phase A own-vs-neutral only — drop every `other_*` column. Valid today, but loses the polarizing signal the index is named for.
**(c)** Execute the A46 market_z plan first (unaffected by this blocker, ~2 hours) while deciding on (a).

CARRY-FORWARD: 269 tests; pool 771; window [2025-04-18, 2026-04-17]; corpus 250,004 submissions / 36 subs; A12 weights unchanged; impl seed 20260526 / spec seed 20260522 (never harmonize); `cache/reddit_corpus/` GITIGNORED LOCAL SOURCE OF RECORD; english_top1000.txt pinned. Next free amendment number: **A45** (unused — Phase A prereg deliberately not written; A46 reserved by the market_z plan). Still NO production `compute_oaq` run (gated: Phase-1 hygiene + Gate-4).

Deadline: poster 2026-09-12 (~6.0 wk).
