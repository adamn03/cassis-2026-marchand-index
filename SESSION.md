# Session Handoff
Date: 2026-07-31
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: Set out to add a four-way attention split (pos/neg × own/rival fanbase) replacing the cap adjustment. Split it into Phase A (affiliation, no LLM) and Phase B (sentiment). **Built Phase A end-to-end — 269 tests pass — but the run uncovered TWO data defects, one of which corrupts live CES inputs today.** Neither is fixed. Both are diagnosed precisely with the fix located.

STATUS: blocked

BLOCKER: Two defects, fix #1 FIRST — see below. Total ~2.5 hours.

---

# DEFECT 1 (URGENT — corrupts live data) — surname/first-name collisions

**13 pool surnames are also another pool player's FIRST name.** `attribute()` (`fetch_reddit.py:437`) says *"Single-member groups always win"* — so every "Quinn Hughes" mention is credited to **Jack Quinn**, every "Cole Caufield" mention to **Ian Cole**, unguarded and uncontested.

Contamination = share of token hits that ALSO name the first-name player (strong evidence, not proof):

| token | credited to | hits | contaminated | guarded? |
|---|---|---|---|---|
| `cole` | Ian Cole | 2,150 | **77%** | NO |
| `connor` | Kyle Connor | 3,763 | 67% | yes |
| `quinn` | Jack Quinn | 2,313 | **64%** | NO |
| `colton` | Ross Colton | 597 | **63%** | NO |
| `shea` | Ryan Shea | 446 | **53%** | NO |
| `beck` | Owen Beck | 395 | **50%** | NO |
| `frank` | Ethen Frank | 825 | **46%** | NO |
| `reilly` | Mike Reilly | 926 | **38%** | NO |
| `james` | Dominic James | 667 | 35% | yes (P1) |
| `thomas` | Robert Thomas | 1,289 | **34%** | NO |
| `blake` | Jackson Blake | 859 | **27%** | NO |
| `paul` | Nick Paul | 1,199 | 14% | yes (P1) |
| `joshua` | Dakota Joshua | 369 | 5% | NO |

**10 of 13 unguarded.** Only 9 players are guarded league-wide.

## Root cause — a threshold artifact, not a design flaw

Prong **P2a in `guard_set_a43` already implements the right rule**: *"≥share of occurrences followed by a pool surname (first-name usage)"*. It never runs for these names because `fetch_reddit.py:317` gates all of P2 behind `GUARD_DF_THRESHOLD = 0.01`:

| surname | DF | gate | result |
|---|---|---|---|
| power | 0.02174 | passes | guarded |
| stanley | 0.01778 | passes | guarded |
| connor | 0.01516 | passes | guarded |
| **quinn** | **0.00931** | **misses by 0.0007** | unguarded |
| **cole** | **0.00865** | misses | unguarded |
| thomas | 0.00518 | misses | unguarded |

Jack Quinn is unguarded purely because "quinn" appears in 0.93% of posts instead of 1.0%.

## The fix — 4 lines, same mechanism as the Will Smith case

First-name collision is deterministic from the roster: no corpus statistics, no threshold. Add prong **P3 before the DF gate** in `guard_set_a43` (`fetch_reddit.py:313-318`):

```python
if sn in pool_first_names:
    guarded[sn] = "P3 surname-is-pool-first-name"
    continue
```

`pool_first_names` is **already a parameter** of that function. This routes all 13 into the identical `make_evidence_check(..., force=True)` path that already protects Will Smith (4 Smiths in pool → `surname_shared=True` → first-name evidence required) and the existing 9 guarded players. A42 rule 2 then applies: team context never suffices for a guarded surname.

## Steps

1. Add P3 + tests: fires for all 13; existing 9 stay guarded; `mcdavid` NOT guarded (its only dominant neighbour is its own first name — the existing P2b exemption must survive).
2. Re-run `python fetch_reddit.py` (runtime minutes; landing JSONs cached).
3. `git diff` `raw/reddit_counts.csv` + `raw/reddit_detail.csv` vs HEAD. **Expect them to move — that is the point.** Produce a before/after table of which players shift and by how much.
4. Write prereg amendment **A48** — "P3: surname-is-pool-first-name" — documenting that the DF gate created an arbitrary cutoff.

**Est. 1.5 hours.**

## Expected consequences

- Ian Cole ~589 → ~150 mentions. Propagates to `engagement_raw` → OAQ for him and his K=10 peers.
- **Likely CLOSES open item #2's Ian Cole anomaly** ("Cole's buzz is reddit/trends-driven, not wiki" — because most of it was Cole Caufield).
- **Logan Stanley is NOT affected** — already guarded (1,292 filtered, DF 0.01778). His high OAQ is wiki-driven (63,868 vs peer-median 36,325). Open item #2 stays open for him.

---

# DEFECT 2 (blocks Phase A) — A22 sub-scope

`raw/reddit_detail.csv` cannot support an own-vs-rival split. `fetch_reddit.py` rule A22 searched each player **only** in r/hockey, r/nhl, r/fantasyhockey, and their own window-roster team subs. Rival subs were never written out for that player.

Phase A run gave own 59.6% / other **3.1%** / neutral 37.3%. The 3.1% is trade history, not rival attention:

| check | result |
|---|---|
| players with any rival mention | 220 / 771 |
| `rival_reach == 0` | 551 |
| max `rival_reach` | **3** (it can only count former team subs) |
| mean `other_mentions`, traded / not | 22.4 / 1.9 |

**Valid today:** `own_mentions`, `own_intensity`, `neutral_mentions`, `neutral_intensity`.

## The signal is real and large

`scan_corpus` **already** streams all 36 subs, attributes every hit, and stores winners in `allsubs_ids` (`fetch_reddit.py:540`). `counting` gates only `scores`/`authors`. `reddit_counts.csv` already carries `reddit_mentions_allsubs`: **68,396 off-sub mentions**, 756/771 players.

Unguarded ceiling probe (`diagnostics/probe_rival_reach.py`): own 85,103 / **RIVAL 59,777** / neutral 69,497, **median rival_reach = 20 subreddits**. Guarded estimate ~53-58k after removing r/nhl + r/fantasyhockey. Guards do not eat the signal.

## The fix

1. `allsubs_ids` set → dict `{post_id: (sub, score)}` (~3 lines, `fetch_reddit.py:488,540`).
2. Emit `raw/reddit_detail_allsubs.csv` — player_id, submission_id, subreddit, score (~8 lines near line 633).
3. Point `compute_affiliation.py` at it; take `subreddit` from the file instead of joining the corpus index.
4. Flip `compute_affiliation.py:PUBLISH_DELIVERABLE` to `True`.
5. Prereg **A45** for the rival split (the test file already bears that number).

**Est. 1 hour. DO THIS SECOND** — rival subs would otherwise multiply Defect 1 across 31 more subreddits (Cole Caufield is discussed everywhere).

---

# What landed this session (6 commits, all green)

- `affiliation.py` — venue map, nickname→code map, trade-aware team timeline, mention labeling, volume-normalized aggregation. Pure functions.
- `compute_affiliation.py` — corpus scan + driver. **`PUBLISH_DELIVERABLE = False`** blocks publishing to `final_dataset/` until Defect 2 is fixed. Runs in 6s.
- `tests/test_affiliation_a45.py` — 29 tests. Suite **240 → 269**.
- `diagnostics/probe_rival_reach.py`, `diagnostics/probe_surname_collision.py` — the evidence above, re-runnable, results in their headers.
- `attention_affiliation.csv` — 771 rows. **Untracked and unpublished on purpose** (invalid `other_*` columns).

Phase A plan Tasks 6-7 (diagnostics, prereg) **deliberately skipped** — pre-registering a metric known to be broken would be wrong. **A45 stays reserved for the affiliation/rival split** — `tests/test_affiliation_a45.py` and 5 commits already claim it.

**Keep this design decision:** normalize by **submissions**, never subscribers. r/BostonBruins has more subscribers than r/Habs (119,306 vs 101,589) but ~1/5 the submissions (3,070 vs 14,510).

---

# PLANS

- `docs/superpowers/plans/2026-07-31-phase-a-attention-affiliation.md` — Tasks 1-5 executed, 6-7 skipped. **Owner said delete when done.** Keep until Defect 2 is fixed (Tasks 3-5 are the template for the corrected re-run), then delete.
- `docs/superpowers/plans/2026-07-31-market-z-activity-sensitivity.md` — **NOT executed, still fully valid**, unaffected by either defect. ~2 hours. Do not delete.

---

# NEW FINDING — subscribers vs activity (feeds open item #3B)

**Spearman(`team_sub_subscribers`, in-window submissions) = 0.299** across 32 teams — nearly independent measures.

| team | subscribers | submissions | per 1k subs |
|---|---|---|---|
| MON | 101,589 | **14,510** | 142.8 |
| TOR | **359,680** | 9,603 | 26.7 |
| BOS | 119,306 | 3,070 | **25.7** |
| FLA | 34,946 | 8,132 | **232.7** |
| UTA | 2,268 | **81** | 35.7 |

Subscribers rank MON 7th; activity ranks MON 1st — exactly the mechanism #3B proposes for MON holding 16 of the OAQ top-100. **UTA is a data hole** (rename split the sub); note its bad subscriber figure is already inside the **A30 primary**, not just the proposed lens. Plan A46 turns this into a sensitivity analysis, with activity permanently locked as a reporting lens (it is endogenous — a winning team's sub posts more).

---

# Design decisions this session (not yet pre-registered)

1. **Cap adjustment demoted** to an audit column; headline becomes plain `OAQ_portable`. Spec separately from the split.
2. **Build negative-first.** Headline `hostility_gap = neg_other_rate − neg_own_rate` — purely negative-label-driven, so identical under 3-way sentiment and under a neg/non-neg fallback. A κ-gate failure then degrades the poster instead of breaking it.
3. **If the sentiment gate fails, collapse to neg/non-neg — NEVER pos/non-pos.** r/hockey is 37% news and game threads; pos/non-pos sweeps that neutral volume into "negative" and re-derives raw volume.
4. **Four-way split is a companion panel**, not a CES component — it covers ~63% of one of four CES inputs.
5. **Phase B costs ~$13-20** (Sonnet 5, Batch API, ~35k items after dedup + top-N-by-score). Cheap enough that $0 is a preference, not a limit. `claude -p` headless loop is the genuine $0 path with equivalent consistency (fresh context per call).

---

# STILL OPEN

- **#2** — `OAQ_portable` low tail. **Ian Cole half likely resolved by Defect 1 fix; Logan Stanley half unaffected and still open.**
- **#3A** — missing-skill star via imputation (Barkov #15 on NaN skill).
- **#3B** — MON floods top-100. **New evidence above.**
- **#4** — degenerate peer set for thin rows with extreme rate features (Kevin Rooney).
- **Owner data request** — 32-team IG + X follower counts, hand-collected. Still worth doing: IG is an exogenous *stock* fixing reddit's English/US skew — a different job from the activity *flow* above, not a replacement.

---

NEXT: Fix Defect 1 (P3 guard prong, `fetch_reddit.py:313-318`, 4 lines + tests + re-run + before/after diff + prereg A48, ~1.5 h). Show the owner the impact table before proceeding. Then Defect 2 (rival detail emission, ~1 h). Then Phase A republishes and Phase B becomes viable. Plan A46 (market_z sensitivity, ~2 h) is independent of both and can run any time.

CARRY-FORWARD: 269 tests; pool 771; window [2025-04-18, 2026-04-17]; corpus 250,004 submissions / 36 subs; A12 weights unchanged; impl seed 20260526 / spec seed 20260522 (never harmonize); `cache/reddit_corpus/` GITIGNORED LOCAL SOURCE OF RECORD; `english_top1000.txt` pinned (never edit). Amendment numbers: **A45 = affiliation/rival split** (claimed by `test_affiliation_a45.py` + commits), **A46 = market_z activity lens** (plan written), **A48 = P3 guard fix**. A47 unused. Next free: A49. Still NO production `compute_oaq` run (gated: Phase-1 hygiene + Gate-4).

Deadline: poster 2026-09-12 (~6.0 wk).
