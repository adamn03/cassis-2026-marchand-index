# Session Handoff
Date: 2026-08-03
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build` (pushed to GitHub).

LAST: **Execution session — entire defect queue cleared.** Defect 1 (C') +
Defect 5 (unmeasurable) + Defect 2 (allsubs) + Defect 4 (wiki_intl QID) all
implemented, verified, committed, pushed. A46 sensitivity plan also executed
in full. Prereg amendments A45, A46, A48 appended. Both plan files fully
reconciled (all checkboxes ticked, statuses updated).

STATUS: working — suite **351, all green**. No half-applied anything.

NEXT: owner reviews the **A49 draft** (4 design decisions: headline = plain
OAQ_portable with cap variants demoted to audit; hostility_gap negative-first
headline; κ-gate degradation path fixed to neg/non-neg-or-nothing; four-way
split companion-panel only — full draft was in session scratchpad, regenerable
from the "Design decisions" section below). Lock it into
`marchand_index/preregistration.md` as A49 BEFORE any Phase B classifier run.
After that: Phase B sentiment build or Phase-1 hygiene toward the gated
production `compute_oaq` run.

## What landed this session (all verified, all pushed)

| fix | result | commits |
|---|---|---|
| Defect 1 (A48, option C') | Pipeline == probe oracle **13/13 exact**. Ian Cole 589→53, Kyle Connor 294→364 (recall fix). 771-row diff moved ONLY the 13 + 2 Pettersson status flips. detail.csv 163,937→161,947 (−1,990 = probe −1,970 + known drift). New column `reddit_firstname_collision`. | `0b66fa8` `f006ad3` `e060924` |
| Defect 5 (A48) | `reddit_status="unmeasurable"` third state; both Elias Petterssons (433 ambiguous each); disclosure columns stay populated; `compute_oaq.reddit_null_mask` NULLs → renormalize (A47 path). Marcus P. correctly stays ok. | same |
| Defect 2 (A45) | `raw/reddit_detail_allsubs.csv` (224,510 rows, venue+score). Counts CSV verified bit-identical on re-run #2. `attention_affiliation.csv` now VALID + tracked + published to `final_dataset/affiliation/`: own 43.6% / other 24.7% / neutral 31.7% (rival was 3.1% trade-history artifact). 47 low_n. Task 6 report built. | `46679ed` `700a143` |
| Defect 4 | pid 695 Elias Pettersson (D): `Q28057083`→`Q114003684`, 36,948→**2,113** intl views. Median rel delta all other rows **0.0000%**. | `cd3fd45` |
| A46 (executed) | `market_activity.csv` (32 rows, UTA only `low`, ρ=0.299 exact). Lenses `market_z_activity` + `market_z_social_blend`; A30 primary bit-identical (tested). Report written. | `399b817` `5ef1c03` `7b8e4aa` |

## Collection hardening (Defect 4 side-discoveries, all committed in `cd3fd45`)

1. Wikimedia pageviews 404s are transient under load → retry before believing
   (fetch: 3 attempts; augment: 404 confirmed by 2, only 429/5xx get the full
   ladder).
2. Articles renamed post-window 404 their new canonical in-window → augment
   iterates `editions_available` and redirect summation recovers them (39
   players were affected; all values restored to pre-fix levels).
3. api.php replies `Vary: Cookie` + set cookies → responses NEVER cache-hit →
   cookie jars now cleared before api.php calls. This was why re-runs could
   not finish.
4. Live MediaWiki calls go through a global 2 req/s pacer (per-worker sleeps
   let 6 workers draw 429 storms); politeness sleeps skip cache-served
   responses. `augment_wiki_redirects.py` gained `--en-only` / `--intl-only`.

**Ops note:** background task kills leave ORPHANED python processes holding
the sqlite HTTP-cache lock — everything crawls until they're killed
(`Get-Process python*` → `Stop-Process`). This burned ~2 hours.

## STILL OPEN

- **#2** — `OAQ_portable` low tail: Ian Cole half RESOLVED by Defect 1
  (589→53). **Logan Stanley half still open** (P1 guard, unaffected).
- **#3A** — missing-skill star via imputation (Barkov #15 on NaN skill).
- **#3B** — now has TWO measured answers that point OPPOSITE ways:
  A45 affiliation: MON median own_share 0.738, rank 7/32 — leans (b) genuine
  over-indexing. A46 sensitivity: MON delta **+1.628, league-largest**
  (market_z 0.359→1.987 under activity; TOR mirror −1.615); player-level
  Spearman(A30, activity) 0.839 — leans (a) strip under-corrects. NET: both
  partially true; specification dependence goes to poster limits-of-claim per
  the A46 pre-registered decision rule (never switch specs).
  Reports: `diagnostics/market_sensitivity_report.md`, `python -m
  diagnostics.affiliation_report`.
- **#4** — degenerate peer set for thin rows (Kevin Rooney).
- **X/Twitter data** — owner added `team_social.csv` X follower counts
  (`8f6913d`) + has untracked WIP: `collect_player_social.py`,
  `ig_scraper.py`, `raw/player_social.csv`. Owner's lane, do not touch.
- **Phase A plan file** — complete + delete-eligible; owner pre-authorized
  deletion, automated `git rm` was permission-blocked. Owner deletes.

## Design decisions not yet pre-registered (→ A49 draft, owner to lock)

1. Cap adjustment demoted to audit columns; headline = plain `OAQ_portable`.
2. Negative-first: headline `hostility_gap = neg_other_rate − neg_own_rate`
   (identical under 3-way and neg/non-neg — κ-gate failure degrades, not
   breaks).
3. Gate failure collapses to neg/non-neg, NEVER pos/non-pos (r/hockey ~37%
   news/game threads → pos/non-pos re-derives volume). Neither passes → no
   sentiment on poster.
4. Four-way split is a companion panel, never a CES input.
5. (operational, not prereg) Phase B ~$13–20 Sonnet Batch; `claude -p` loop is
   the $0 path.
6. (already locked in A45/A46) normalize by submissions, never subscribers.

---

CARRY-FORWARD: **351 tests**; pool 771; window [2025-04-18, 2026-04-17];
corpus 250,004 submissions / 36 subs; A12 weights unchanged (wiki .29,
wiki_intl .11, reddit_mentions .27, reddit_upvotes .17, trends .16); impl seed
20260526 / spec seed 20260522 (never harmonize); `cache/reddit_corpus/`
GITIGNORED LOCAL SOURCE OF RECORD; `english_top1000.txt` pinned (never edit).
Amendments RECORDED: A45 (affiliation split + allsubs), A46 (market_z activity
lens), A47 (Trends entity guard), A48 (C' collision guard + unmeasurable).
Next free: **A49** (draft exists, owner to lock). `reddit_status` values: ok |
partial | null | unmeasurable. `attention_affiliation.csv` now TRACKED and
published (final_dataset/affiliation/). `reddit_detail_allsubs.csv` is the
affiliation input (36 subs); `reddit_detail.csv` stays the §10 bootstrap
input (counting subs). Still NO production `compute_oaq` run (gated: Phase-1
hygiene + Gate-4). HTTP cache `cache/http_cache.sqlite` ~640MB — safe to keep.

Deadline: poster 2026-09-12 (~5.7 wk).
