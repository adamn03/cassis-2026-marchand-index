# Session Handoff
Date: 2026-08-02
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: Designed + measured the **Defect 1** fix instead of building it. Probe
`diagnostics/probe_firstname_guard_options.py` (committed `3a96f8e`) compares
four options on the live corpus. Owner selected **C'**. No pipeline code
touched.

STATUS: working — pipeline unchanged, suite still **302, all green**.

NEXT: implement **C'** in `fetch_reddit.py` (4 edit sites), then tests, re-run,
diff, prereg **A48**. **~2.5-3.5 h and it REQUIRES a `fetch_reddit.py` re-run** —
that is why it was deferred. Full spec below.

**FIX ORDER — do them in this order, one at a time:**

| order | defect | why here | cost |
|---|---|---|---|
| 1st | **Defect 1 + Defect 5 TOGETHER** | both edit `fetch_reddit.py` and share ONE re-run; splitting them costs a second full re-run for no benefit | 3-4 h + one re-run |
| 2nd | **Defect 2** — own-vs-rival split | opening 31 more subs first would multiply Defect 1's collision | ~1 h |
| 3rd | **Defect 4** — wiki_intl stale QID | independent, no code, self-corrects on re-run | ~10 min |

All four are fully spec'd — edit sites, conditions and tests are written down.
No design work left; next session is execution.

**There is NO "Defect 0".** The Phase A plan calls the Defect 1 fix `Task 0`
purely because it runs before that plan's Task 1. Same fix, same work, nothing
extra. **Defect 6** is a known limit, not scheduled work — do not block on it.

---

# DEFECT 1 — decided, spec'd, NOT built

**The bug.** 13 pool surnames are also another pool player's FIRST name, and
those surnames are unique in the pool, so `attribute()` (`fetch_reddit.py:437`,
*"Single-member groups always win"*) hands every hit over with no evidence
check. Every "Quinn Hughes" mention credits **Jack Quinn**; every "Cole
Caufield" credits **Ian Cole**.

The 13: `beck blake cole colton connor frank james joshua paul quinn reilly
shea thomas`. Only `connor`/`james`/`paul` guarded today.

**Original SESSION plan (P3 blanket) was measured and REJECTED** — see option A
below. It destroys 63% of these players' Reddit signal.

## The rule — C'

Per submission containing collision surname `sn` (owner = the player carrying
it as a surname), classify into one state:

| state | condition | verdict |
|---|---|---|
| S1 | EVERY occurrence of `sn` is immediately followed by the surname of a pool player whose FIRST name is `sn` | proven first-name usage -> owner ineligible |
| S2 | >=1 standalone occurrence AND owner's A15 checker fires | owner eligible |
| S3 | >=1 standalone occurrence, no first-name evidence | UNKNOWN -> see below |

S3 resolution: **eligible if the submission is in the owner's own team sub;
otherwise ambiguous** (disclosed, counted for nobody). r/hockey never resolves
S3 — that is where the contamination lives.

**S1 takes precedence over S2.** Verified correct: 14 r/hockey posts have every
`connor` followed by a pool surname *and* the checker firing, e.g.
`"Instagram story posted by Lauren Kyle (Connor McDavid's wife)"`. Kyle Connor
is credited for those today.

## The two scoping rules — do not drop either

1. **P1-strict (this is the `'` in C').** A surname already guarded by A43
   prong **P1** (common English word) gets **NO own-sub allowance**. Own-sub
   context resolves a *rival player* confuser; it cannot resolve an *ordinary
   word* confuser, which appears in every sub equally. Verified: of the 13,
   exactly **`james` and `paul` are in `english_top1000.txt`**; the other 11
   are not. Without this rule, bare "stanley" in r/winnipegjets counts for
   **Logan Stanley** and reopens open item #2.
2. **Own-sub allowance applies ONLY to collision surnames**, never to P1/P2b
   guards generally. So the other 6 guarded players are untouched and the 13
   below are the **complete blast radius** — no unmeasured spillover.

## Measured results (probe, live corpus, 250,004 submissions)

State split, counting subs only:

| token | owner | hits | S1 | S2 | S3 | S3 own-sub | S3 r/hockey |
|---|---|---|---|---|---|---|---|
| connor | Kyle Connor | 1539 | 55% | 18% | 27% | 84 | 325 |
| quinn | Jack Quinn | 735 | 44% | 35% | 21% | 95 | 56 |
| cole | Ian Cole | 589 | **75%** | 9% | 17% | 1 | 97 |
| thomas | Robert Thomas | 495 | 27% | 36% | 38% | 71 | 116 |
| paul | Nick Paul | 421 | 10% | 22% | **68%** | 49 | 239 |
| blake | Jackson Blake | 404 | 21% | 43% | 36% | 103 | 43 |
| frank | Ethen Frank | 355 | 31% | 23% | 47% | 27 | 139 |
| reilly | Mike Reilly | 286 | 16% | 15% | **69%** | 22 | 174 |
| james | Dominic James | 240 | 13% | 24% | 62% | 52 | 98 |
| colton | Ross Colton | 219 | 53% | 32% | 16% | 23 | 12 |
| beck | Owen Beck | 215 | 20% | 40% | 40% | 79 | 6 |
| joshua | Dakota Joshua | 212 | 4% | 48% | 48% | 78 | 24 |
| shea | Ryan Shea | 212 | 31% | 35% | 34% | 54 | 19 |

Totals across the 13:

| option | mentions | delta | -> ambiguous |
|---|---|---|---|
| today | 4152 | — | |
| **A** P3 blanket (old plan) | 1545 | **-2607 (-63%)** | 0 |
| **B** bigram only | 3631 | -521 | 0 |
| **C** bigram + own-sub | 2283 | -1869 | 1348 |
| **C' SELECTED** | **2182** | **-1970** | 1449 |

Expected headline movements: **Ian Cole 589 -> 53** (should close the Ian Cole
half of open item #2). **Kyle Connor 280 -> 364 (+84)** — C' is also a RECALL
fix; the existing A42 guard has been silently deleting real mentions for the 9
guarded players. `paul` and `james` stay flat under P1-strict.

Bigram rule is **not knife-edge**: tight (next token = surname of a player
whose first name is `sn`) vs loose (next token = any pool surname) differ by
<=26 posts per name, and by **1** for `cole`. Use tight.

## The probe is the verification oracle

`python diagnostics/probe_firstname_guard_options.py` from inside
`marchand_index/`. Read-only, no network, ~1 corpus pass. It imports folding /
tokenizing / counting-subs / checker from `fetch_reddit` rather than
reimplementing them, and reads counting subs from `reddit_subs_searched` so it
needs no NHL API calls.

**Self-check today: 11 of 13 owners reproduce `reddit_mentions_12mo` EXACTLY.**
The 2 that drift (`connor` -14, `paul` -6) are the probe being *more* correct
than the pipeline — root-caused to the Lauren Kyle posts above.

**After implementing, assert pipeline `reddit_mentions_12mo` == probe C' column
for all 13.** Turns the before/after step from eyeballing a diff into pass/fail.

## Implementation — 4 edit sites in `fetch_reddit.py`

1. **~line 564** — build the collision set (surname unique in pool AND in
   `pool_first_names`) plus, per surname, `fn_surnames` = surnames of players
   whose first name is that token.
2. **`build_groups` (~400)** — carry `collision`, `fn_surnames`, `p1` onto each
   member dict.
3. **`scan_corpus` (~512, 521)** — `tokens` is currently a SET
   (`match_tokens`); the bigram test needs ORDER. Restructure to
   `toks = match_fold(...).split()` then `tokens = set(toks)` (same work, no
   extra cost). Then the 3-state eligibility block replacing lines 521-524.
4. **counts output (~626)** — disclosure column(s).

**Read new member fields via `m.get(...)`, not `m[...]`** — that keeps
`test_fetch_reddit_a42.py`'s `_member` helper and all 43 existing reddit tests
passing untouched, with no signature change to `scan_corpus`/`build_groups`.

Confirmed: **no non-test code reads the guard columns** (`affiliation.py` only
says "guard" in prose). Downstream is `reddit_counts.csv` + `reddit_detail.csv`
consumers only, and there is still no production `compute_oaq` run, so nothing
cascades.

## Two open implementation risks

1. **Bucket split.** S1 ("proven not him") and S3-league ("unknown") are
   different disclosures — `guard_filtered` vs `ambiguous`. A third column may
   be needed to keep them clean (+20 min).
2. **Movement outside the 13.** The positional-token switch should change no
   other player's count. If the 771-row diff shows movement elsewhere, explain
   it before proceeding.

## A48 prereg scope — BIGGER than previously written

A48 must document, not bury: the 3-state rule; P1-strict scoping; that it
**overrides A42 rule 2** (*"team context never suffices for guarded
surnames"*); that it **overrides P2** for collision surnames (`connor` is
P2-guarded today and C' is strictly more permissive for it — defensible because
per-post bigram evidence beats a token-level aggregate, but it is a real
prereg change); and the tight-vs-loose bigram sensitivity.

## Owner decision on file (2026-08-02) — record on the poster's limits section

Owner **declined** the ~20-30 min hand-label validation of S3-in-own-sub:
*"surname and/or team name mention is enough to make it accurate enough most of
the time."* So the own-sub allowance (**605 mentions**) rests on a base-rate
judgment, not on labelled data. Accepted deliberately for time. This is an
honest-limits (criterion 6) item, not a hidden one. Re-offer if the schedule
loosens.

# DEFECT 6 (new, low, do NOT block on it) — A15 checker false positives

The A15 evidence checker fires on the first name appearing ANYWHERE in the
post, so "Lauren Kyle" credits Kyle Connor. Under C' these land in **S2**, the
keep-bucket, so every option carries a small residual over-count. C' is less
wrong, not right. Quantified only for `connor` (14 posts in r/hockey). Not
worth fixing before the poster; note it in limits.

---

# DEFECT 2 (after Defect 1) — A22 sub-scope, ~1 h

`raw/reddit_detail.csv` cannot support an own-vs-rival split. A22 searched only
r/hockey, r/nhl, r/fantasyhockey + own-team subs. Phase A gave own 59.6% /
other **3.1%** / neutral 37.3% — the 3.1% is trade history (max `rival_reach`
= **3**).

Signal exists and is large: `scan_corpus` already streams all 36 subs and
stores winners in `allsubs_ids` (`fetch_reddit.py:540`); `reddit_counts.csv`
already carries **68,396 off-sub mentions**, 756/771 players, **median
rival_reach 20** (`diagnostics/probe_rival_reach.py`). Just never written out.

**Fix:** (1) `allsubs_ids` set -> dict `{post_id: (sub, score)}` (~3 lines,
`fetch_reddit.py:488,540`). (2) emit `raw/reddit_detail_allsubs.csv` (~8 lines
near 633). (3) point `compute_affiliation.py` at it. (4) flip
`PUBLISH_DELIVERABLE = True`. (5) prereg **A45**.

**DO THIS AFTER DEFECT 1** — rival subs would otherwise multiply the collision
across 31 more subreddits.

# DEFECT 4 (~10 min, no code) — wiki_intl stale QID

`fetch_wikipedia_intl` reuses `wikidata_qid` from `wiki_pageviews.csv`. Exactly
**1 row disagrees**: pid 695 Elias Pettersson (D) carries `Q28057083` (the
**center**) instead of `Q114003684`, so he gets the C's 36,948 intl views (rank
94/764). `wiki_pageviews` fixed this via its `nhl_id` tier; intl was never
regenerated. Weight 0.11. **Self-corrects on re-run** — no code change.

# DEFECT 5 — reddit null-vs-zero. SPEC'D 2026-08-02. ~30 min. DO IT WITH DEFECT 1.

Both Petterssons: `reddit_mentions_12mo=0`, `reddit_upvotes_12mo=0`,
`unique_authors=0`, **`reddit_status="ok"`**, 433 `ambiguous_mentions`
discarded. No-cross-credit is the right call, but an $11.6M franchise center
scoring a true zero on 44% of CES weight while flagged "ok" reads as measured.
Should be NULL -> renorm, not 0. (Same principle A47 settled for Trends.)

**Do this in the SAME edit pass as Defect 1** — both touch `fetch_reddit.py`
and both need the same re-run. Done together it costs **zero extra re-runs**;
done separately it costs a second full one.

## The rule

A zero is *measured* only if we looked and found nothing. If the surname
appeared in the corpus but every occurrence was discarded, we did not measure
zero — **we failed to measure.** Those are different and must not share a
status value.

New `reddit_status` value **`unmeasurable`**, set when all three hold:

```
status would otherwise be "ok" or "partial"
AND reddit_mentions_12mo == 0
AND (ambiguous_mentions > 0 OR guard_filtered_mentions > 0)
```

A player with 0 mentions, 0 ambiguous and 0 guard-filtered is a **genuine**
zero and stays `ok`. That distinction is the whole point of the defect.

## Measured blast radius (from the current CSV, no re-run needed)

| bucket | rows |
|---|---|
| status != null with 0 mentions | 12 |
| -> `unmeasurable` via `ambiguous > 0` | **2** (both Elias Petterssons, 433 each) |
| -> `unmeasurable` via `guard_filtered` only | 0 |
| -> TRUE zero, stays `ok` | 10 |

**The rule is defined by the condition, not by that list.** Defect 1's C' fix
changes `ambiguous_mentions` and `guard_filtered_mentions` for the 13 collision
players, so re-check the counts after the re-run — the set can grow.

## Edit sites — 2 files

1. **`fetch_reddit.py:605-612`** — the status ladder. Add the `unmeasurable`
   branch after `ok`/`partial` are decided (it needs `a["ambiguous"]` and
   `a["guard_filtered"]`, which are already in `acc`).
   **Keep every disclosure column populated** for `unmeasurable` rows — unlike
   `"null"`, which blanks them at lines 621-629. The evidence for why the row
   is NULL must stay visible in the CSV.
2. **`compute_oaq.py:280`** — extend `null_mask`:

```python
null_mask = (status.isna() | (status == "null") | (status == "")
             | (status == "unmeasurable"))
```

Line 281 then NULLs both reddit columns, and renormalization is already the
post-A47 default — same path Trends NULLs take. **No renormalization code to
write.**

**`detail_rows` (line 632) needs no change**: an `unmeasurable` row has
`mentions == 0`, so `a["scores"]` is empty and it contributes no detail rows
either way.

## Tests

- `unmeasurable` fires: 0 mentions + ambiguous > 0.
- `unmeasurable` fires: 0 mentions + guard_filtered > 0, ambiguous == 0.
- Stays `ok`: 0 mentions, 0 ambiguous, 0 guard_filtered (the 10 true zeros).
- Stays `ok`: mentions > 0 with ambiguous > 0 (ambiguity alone must NOT trigger).
- `"null"` still wins when no corpus file is present.
- `compute_oaq` NULLs both reddit columns on `unmeasurable` and the weights
  renormalize (assert to 1e-12, as `test_trends_null_taxonomy_a47.py` does).
- Disclosure columns remain populated on an `unmeasurable` row.

## Prereg

Folds into **A48**. Record that `unmeasurable` is a *third* state distinct from
both `ok` and `null`: `null` = the source was unavailable, `unmeasurable` = the
source was read but the player could not be separated within it. Cite the
A47 Trends precedent for NULL -> renormalize, and note the **Wiki raw-0
exception still stands** (a missing article does mean no salience).

# Non-defect, cosmetic

`wiki_pageviews`, `wiki_intl`, `instagram_followers`, `cap_hits`, `nhl_onice`
carry 3 orphan rows (pids 368/500/637, pre-A41 duplicates of
Colton/Benoit/Andrae). Survivors have correct rows under current pids and
`compute_oaq` left-joins from `players.csv`, so orphans drop.

---

# REFERENCE — A47 (done, committed `a8deaa4`) + collector audit

Google Trends entity guard. Raw-string fallback retired; position tie-break;
punctuation folding on the A44 franchise test; A25 Trends `no_entity_exists`
branch retired (NULL -> renormalize; **Wiki keeps raw-0**). 25 of 771 rows
re-fetched, **746 bit-identical**. Ovechkin 0.377 -> 1.963.

**Do not re-propose the `"<name> hockey"` query scale.** Tested and rejected:
ranked Will Smith **2.3x above McDavid**, returned exactly 0 for 5 of 7 probed
players. Measures how often a name needs disambiguating, not salience.

Audit of every other name-based collector — **clean**, verified against the
real files: `fetch_rosters_league`, `filter_pool_played`, `fetch_nhl_api`,
`fetch_cap_hits` (id-validated), `fetch_market_proxy` (team-level),
`fetch_external_outcomes` (id decides), `build_mover_list` /
`research_mover_dates`, `augment_wiki_redirects`, `fetch_instagram`,
`fetch_wikipedia` (en). Pool facts: **1 duplicate full name** (Elias Pettersson
C/D, both VAN), **0 blank `nhl_player_id`** — `fetch_moneypuck`'s name-fallback
is dead code today. `fetch_wikipedia` (en) is the **reference implementation**.

# PLANS

- `docs/superpowers/plans/2026-07-31-phase-a-attention-affiliation.md` — Tasks
  1-5 done, 6-7 skipped. **Now also holds the Defect 1 C' fix as a blocking
  `Task 0`** (added 2026-08-02) — full spec, evidence tables, 5 checkbox steps,
  known limits. That is the executable version; the Defect 1 section above is
  the summary. **Owner said delete when done.** Keep until BOTH Defect 1
  (Task 0) and Defect 2 are fixed, then delete.
- `docs/superpowers/plans/2026-07-31-market-z-activity-sensitivity.md`
  (**A46**) — NOT executed, still fully valid, independent of every defect.
  ~2 h. Do not delete.

# STILL OPEN

- **#2** — `OAQ_portable` low tail. Ian Cole half expected to resolve on the
  Defect 1 re-run (589 -> 53); **Logan Stanley half unaffected, still open**.
- **#3A** — missing-skill star via imputation (Barkov #15 on NaN skill).
- **#3B** — MON floods top-100. Spearman(subscribers, in-window submissions) =
  **0.299** across 32 teams. MON 101,589 subs / **14,510 submissions** (1st) vs
  TOR 359,680 / 9,603. UTA is a data hole (rename split the sub) and its bad
  subscriber figure is **already inside the A30 primary**. A46 turns this into
  a sensitivity analysis; activity stays a reporting lens only (endogenous).
- **#4** — degenerate peer set for thin rows with extreme rate features
  (Kevin Rooney).
- **Owner data request** — 32-team IG + X follower counts, hand-collected. IG
  is an exogenous *stock* fixing reddit's English/US skew — different job from
  the activity *flow*, not a replacement.

# Design decisions not yet pre-registered

1. **Cap adjustment demoted** to an audit column; headline becomes plain
   `OAQ_portable`.
2. **Build negative-first.** Headline `hostility_gap = neg_other_rate -
   neg_own_rate` — identical under 3-way sentiment and under a neg/non-neg
   fallback, so a κ-gate failure degrades the poster instead of breaking it.
3. **If the sentiment gate fails, collapse to neg/non-neg — NEVER pos/non-pos.**
   r/hockey is 37% news/game threads; pos/non-pos sweeps that into "negative"
   and re-derives raw volume.
4. **Four-way split is a companion panel**, not a CES component (~63% of one of
   four CES inputs).
5. **Phase B costs ~$13-20** (Sonnet 5, Batch API, ~35k items). `claude -p`
   headless loop is the genuine $0 path.
6. **Normalize by submissions, never subscribers.** r/BostonBruins has more
   subscribers than r/Habs (119,306 vs 101,589) but ~1/5 the submissions
   (3,070 vs 14,510).

---

CARRY-FORWARD: **302 tests**; pool 771; window [2025-04-18, 2026-04-17]; corpus
250,004 submissions / 36 subs; A12 weights unchanged (wiki .29, wiki_intl .11,
reddit_mentions .27, reddit_upvotes .17, trends .16); impl seed 20260526 / spec
seed 20260522 (never harmonize); `cache/reddit_corpus/` GITIGNORED LOCAL SOURCE
OF RECORD; `english_top1000.txt` pinned (never edit). Amendments: **A45 =
affiliation/rival split** (claimed by `test_affiliation_a45.py` + 5 commits),
**A46 = market_z activity lens** (plan written), **A47 = Trends entity guard
(DONE, committed)**, **A48 = Defect 1 C' guard + Defect 5 null rule**. Next
free: **A49**. UNTRACKED ON PURPOSE: `attention_affiliation.csv` (invalid
`other_*` columns) and `diagnostics/probe_firstname_guard_options.py` (new this
session, not yet committed). Still NO production `compute_oaq` run (gated:
Phase-1 hygiene + Gate-4).

Deadline: poster 2026-09-12 (~5.9 wk).
