# Session Handoff
Date: 2026-08-01
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

LAST: Audited every name-based collector for the Defect-1 collision class. Found 3 NEW defects; fixed the worst one end-to-end (**A47, committed `a8deaa4`**). Suite **269 -> 302, all green.**

STATUS: working — nothing broken, nothing half-applied. 4 known defects remain, all diagnosed.

NEXT: **Defect 1** — P3 guard prong in `fetch_reddit.py:313-318` (4 lines + tests + re-run + before/after diff + prereg **A48**, ~1.5 h). Full spec below.

---

# DONE THIS SESSION — A47 (committed)

Google Trends had no entity guard. Fixed in `fetch_trends.py` + `compute_oaq.py`:

- **Raw-string fallback retired.** It queried a bare name whenever no suggestion qualified OR the call was throttled (429s dominate every run log). Result: Will Smith = **9.664671, rank 1/771** (the actor); Garrett Wilson = NFL WR; Ben Jones = NFL C; Taylor Ward = MLB OF. Hockey-only names were *under*counted (a string query loses what a topic MID aggregates).
- **Position tie-break.** First-qualifying-suggestion gave both Elias Petterssons one MID; the D carried the C's volume at **78x**.
- **Punctuation folding** on the A44 franchise test — `"St. Louis Blues defenseman"` never matched the `st-louis-blues` slug, falsely refusing Parayko/Holloway/Suter.
- **A25 Trends `no_entity_exists` branch retired.** It inferred "no Google entity" from a blank `query_mid`, which post-A47 covers every refusal — a 429 would have scored as zero search interest. All NULL trends now renormalize (≡ imputing the player's weight-averaged z over the components that resolved; test asserts equality to 1e-12). **Wiki keeps raw-0** — a missing article does mean no salience.

Result: 25 of 771 rows re-fetched, **746 bit-identical**. Ovechkin 0.377 -> 1.963. Top-8 now Crosby, McDavid, Ovechkin, J. Hughes, Celebrini, Bedard, Marchand, Matthews (was led by a film actor). 12 rows sit at `no_hockey_topic` -> NULL -> renormalized; Will Smith is one of them and is scored on his other 4 components (0.84 of the composite).

**Do not re-propose the `"<name> hockey"` query scale.** Tested and rejected (recorded in A47): it ranked Will Smith **2.3x above McDavid** and returned exactly 0 for 5 of 7 probed players. It measures how often a name needs disambiguating, not salience.

---

# AUDIT RESULT — every other name-based collector

Clean, verified against the real files: `fetch_rosters_league`, `filter_pool_played`, `fetch_nhl_api`, `fetch_cap_hits` (id-validated), `fetch_market_proxy` (team-level), `fetch_external_outcomes` (id decides; already handles Pettersson + Sebastian Aho), `build_mover_list`/`research_mover_dates` (full name + both team nicknames + direction; conflicts -> `needs_date`), `augment_wiki_redirects` (inherits canonical), `fetch_instagram`, `fetch_wikipedia` (en).

Pool facts: **1 duplicate full name** (Elias Pettersson C/D, both VAN), **0 blank `nhl_player_id`** — so `fetch_moneypuck`'s name-fallback is dead code today (latent only).

`fetch_wikipedia` (en) is the **reference implementation** — its `nhl_id` match tier (8 rows) is the pattern the other fixes copy.

---

# DEFECT 1 (NEXT — urgent, corrupts live CES data)

**13 pool surnames are also another pool player's FIRST name.** `attribute()` (`fetch_reddit.py:437`) says *"Single-member groups always win"* — every "Quinn Hughes" mention is credited to **Jack Quinn**, every "Cole Caufield" to **Ian Cole**, unguarded.

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

**10 of 13 unguarded.** Only 9 players guarded league-wide.

**Root cause — a threshold artifact, not a design flaw.** Prong **P2a in `guard_set_a43` already implements the right rule** (*"≥share of occurrences followed by a pool surname"*). It never runs because `fetch_reddit.py:317` gates all of P2 behind `GUARD_DF_THRESHOLD = 0.01`: `quinn` DF 0.00931 misses by **0.0007**; `cole` 0.00865; `thomas` 0.00518.

**Fix — 4 lines.** First-name collision is deterministic from the roster: no corpus statistics, no threshold. Add prong **P3 before the DF gate** in `guard_set_a43` (`fetch_reddit.py:313-318`):

```python
if sn in pool_first_names:
    guarded[sn] = "P3 surname-is-pool-first-name"
    continue
```

`pool_first_names` is **already a parameter**. Routes all 13 into the same `make_evidence_check(..., force=True)` path that already protects Will Smith and the existing 9.

**Steps:** (1) P3 + tests — fires for all 13; existing 9 stay guarded; `mcdavid` NOT guarded (P2b exemption must survive). (2) re-run `python fetch_reddit.py` (minutes; landing JSONs cached). (3) `git diff` `raw/reddit_counts.csv` + `raw/reddit_detail.csv` — **expect movement, that is the point**; produce a before/after table. (4) prereg **A48**. **Show the owner the impact table before proceeding.**

**Expected:** Ian Cole ~589 -> ~150 mentions; likely **closes open item #2's Ian Cole half**. **Logan Stanley unaffected** (already guarded, wiki-driven) — his half stays open.

---

# DEFECT 2 (after Defect 1) — A22 sub-scope, ~1 h

`raw/reddit_detail.csv` cannot support an own-vs-rival split. A22 searched only r/hockey, r/nhl, r/fantasyhockey + own-team subs. Phase A gave own 59.6% / other **3.1%** / neutral 37.3% — the 3.1% is trade history (max `rival_reach` = **3**).

Signal exists and is large: `scan_corpus` already streams all 36 subs and stores winners in `allsubs_ids` (`fetch_reddit.py:540`); `reddit_counts.csv` already carries **68,396 off-sub mentions**, 756/771 players, **median rival_reach 20** (`diagnostics/probe_rival_reach.py`). Just never written out.

**Fix:** (1) `allsubs_ids` set -> dict `{post_id: (sub, score)}` (~3 lines, `fetch_reddit.py:488,540`). (2) emit `raw/reddit_detail_allsubs.csv` (~8 lines near 633). (3) point `compute_affiliation.py` at it. (4) flip `PUBLISH_DELIVERABLE = True`. (5) prereg **A45**.

**DO THIS AFTER DEFECT 1** — rival subs would otherwise multiply the collision across 31 more subreddits.

---

# DEFECT 4 (~10 min, no code) — wiki_intl stale QID

`fetch_wikipedia_intl` reuses `wikidata_qid` from `wiki_pageviews.csv`. Exactly **1 row disagrees**: pid 695 Elias Pettersson (D) carries `Q28057083` (the **center**) instead of `Q114003684`, so he gets the C's 36,948 intl views (rank 94/764). `wiki_pageviews` fixed this via its `nhl_id` tier; intl was never regenerated. Weight 0.11. **Self-corrects on re-run** — no code change.

# DEFECT 5 (low, folds into A48) — reddit null-vs-zero

Both Petterssons: `reddit_mentions_12mo=0`, `reddit_upvotes_12mo=0`, `unique_authors=0`, **`reddit_status="ok"`**, 433 `ambiguous_mentions` discarded. No-cross-credit is the right call, but an $11.6M franchise center scoring a true zero on 44% of CES weight while flagged "ok" reads as measured. Should be NULL -> renorm, not 0. (Same principle A47 just settled for Trends.)

# Non-defect, cosmetic

`wiki_pageviews`, `wiki_intl`, `instagram_followers`, `cap_hits`, `nhl_onice` carry 3 orphan rows (pids 368/500/637, pre-A41 duplicates of Colton/Benoit/Andrae). Survivors have correct rows under current pids and `compute_oaq` left-joins from `players.csv`, so orphans drop.

---

# PLANS

- `docs/superpowers/plans/2026-07-31-phase-a-attention-affiliation.md` — Tasks 1-5 done, 6-7 skipped. **Owner said delete when done.** Keep until Defect 2 is fixed (Tasks 3-5 are the template for the corrected re-run), then delete.
- `docs/superpowers/plans/2026-07-31-market-z-activity-sensitivity.md` (**A46**) — NOT executed, still fully valid, independent of every defect. ~2 h. Do not delete.

# STILL OPEN

- **#2** — `OAQ_portable` low tail. Ian Cole half likely resolved by Defect 1; **Logan Stanley half unaffected, still open**.
- **#3A** — missing-skill star via imputation (Barkov #15 on NaN skill).
- **#3B** — MON floods top-100. Evidence: Spearman(subscribers, in-window submissions) = **0.299** across 32 teams. MON 101,589 subs / **14,510 submissions** (1st) vs TOR 359,680 / 9,603. UTA is a data hole (rename split the sub) and its bad subscriber figure is **already inside the A30 primary**. A46 turns this into a sensitivity analysis; activity stays a reporting lens only (endogenous).
- **#4** — degenerate peer set for thin rows with extreme rate features (Kevin Rooney).
- **Owner data request** — 32-team IG + X follower counts, hand-collected. IG is an exogenous *stock* fixing reddit's English/US skew — different job from the activity *flow*, not a replacement.

# Design decisions not yet pre-registered

1. **Cap adjustment demoted** to an audit column; headline becomes plain `OAQ_portable`.
2. **Build negative-first.** Headline `hostility_gap = neg_other_rate − neg_own_rate` — identical under 3-way sentiment and under a neg/non-neg fallback, so a κ-gate failure degrades the poster instead of breaking it.
3. **If the sentiment gate fails, collapse to neg/non-neg — NEVER pos/non-pos.** r/hockey is 37% news/game threads; pos/non-pos sweeps that into "negative" and re-derives raw volume.
4. **Four-way split is a companion panel**, not a CES component (~63% of one of four CES inputs).
5. **Phase B costs ~$13-20** (Sonnet 5, Batch API, ~35k items). `claude -p` headless loop is the genuine $0 path.
6. **Normalize by submissions, never subscribers.** r/BostonBruins has more subscribers than r/Habs (119,306 vs 101,589) but ~1/5 the submissions (3,070 vs 14,510).

---

CARRY-FORWARD: **302 tests**; pool 771; window [2025-04-18, 2026-04-17]; corpus 250,004 submissions / 36 subs; A12 weights unchanged (wiki .29, wiki_intl .11, reddit_mentions .27, reddit_upvotes .17, trends .16); impl seed 20260526 / spec seed 20260522 (never harmonize); `cache/reddit_corpus/` GITIGNORED LOCAL SOURCE OF RECORD; `english_top1000.txt` pinned (never edit). Amendments: **A45 = affiliation/rival split** (claimed by `test_affiliation_a45.py` + 5 commits), **A46 = market_z activity lens** (plan written), **A47 = Trends entity guard (DONE, committed)**, **A48 = P3 guard fix**. Next free: **A49**. `attention_affiliation.csv` stays untracked on purpose (invalid `other_*` columns). Still NO production `compute_oaq` run (gated: Phase-1 hygiene + Gate-4).

Deadline: poster 2026-09-12 (~6.0 wk).
