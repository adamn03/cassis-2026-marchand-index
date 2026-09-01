# Session Handoff
Date: 2026-08-27
Active: NHL_Marchand_Index

LAST: **Scope changed — CASSIS is off.** Owner made the Mann Cup (lacrosse) and can no
longer attend the Sept 12 2026 symposium. The project is no longer a conference
submission. New and final deliverable: a clean, self-explanatory **GitHub-facing writeup**
of the MI / `OAQ_portable` ranking, the interesting movers, and a small number of findings
— built to read well as a portfolio / resume artifact.

STATUS: working — no code blockers left. The old blocker dissolved (see below).

NEXT: Task 1 below — exclude Johnny Gaudreau from the pool and reconcile the 771 vs 774
row count. Do not build the writeup until tasks 1–3 are done; it renders numbers.

---

## The deliverable

A repo a stranger can land on and understand in three minutes, and that a hiring manager
reads as evidence of judgment. Not a poster, not a paper.

| # | Section | Content |
|---|---|---|
| 1 | What this is | 2–3 plain-language paragraphs. No jargon before it is defined. The Marchand framing: *a high-skill player whose public salience and polarizing identity exceed what production-matched peers produce* — never "mid-skill" |
| 2 | **The ranking** | Top ~25 by `marchand_index` and by `OAQ_portable`, each with bootstrap CI and `match_quality_flag`. Full table linked, not inlined |
| 3 | **Interesting movers** | The handful of players whose attention is furthest from what their production predicts, each with 1–2 sentences on *why* that player is interesting. This is the part people actually read. **HARD CONSTRAINT: only the tails.** Peer-stack v2 showed mid-pack ranks are not defensible — Pastrnak moved 664→81 and Eichel 164→689 under a reasonable alternative peer vector, while the metric itself held at Pearson 0.955. Feature the extremes, never a mid-pack ordering, and never say "ranked Nth" for anyone outside the tails |
| 4 | **Findings** | Headline: **the NHL does not pay extra for attention.** −0.4% per +1 SD Wikipedia on veteran re-signings, CI [−6.5%, +6.5%], against +43.8% for +1 SD of TOI. Frame as *cost, not value* — a club acquires the attention without paying a premium for it. Optional second finding: the Wikipedia/Reddit sign flip |
| 5 | Method | Short. K=10 Mahalanobis position-locked peers, the composite, the market strip, bootstrap. Link `marchand_index/preregistration.md` rather than restating it |
| 6 | **Limits + what we killed** | The honest section. Pull from `value_propositions.md` Part 1. Eleven dead ends including a retracted finding of our own is a *rigor* signal on a resume, not an embarrassment — say so plainly |

Constraints: charts readable at a glance, no unexplained acronyms, every headline number
carries a CI. Format TBD — root `README.md` + a `results/` figure folder is the default;
a single self-contained HTML page is the alternative.

## The old blocker is gone — do not re-litigate it

`compute_oaq.py` assumes **one row per player**. That was a blocker only because the
per-season panels (A52) would have triple-counted, and how to combine three seasons was
left deliberately unsettled. **The new deliverable needs one ranking, which means
window-level OAQ — exactly what `compute_oaq.py` was built for.** Run it on the
window-level inputs as designed and do not feed it `attention_by_season.csv`. The
per-season panel stays in the repo for the event studies; it is not on the critical path.

## Task order

1. **Exclude Johnny Gaudreau + reconcile the pool count.** He died Aug 2024 and is still in
   the roster pool; his 2026-02-22 memorial spike (**2,130,333 views in one day**) is the
   largest single observation in the dataset. Real traffic, wrong pool — he cannot appear
   in a published ranking. Also reconcile `oaq_pilot.csv` 771 rows vs A10's locked 774.
2. **Make the test suite run.** `test_build_mover_list_a38.py` and
   `test_expected_cap_a24.py` fail at *collection*
   (`ImportError: cannot import name 'find_2025_26_caphit' from 'fetch_cap_hits'`), which
   aborts the whole suite. A repo where `pytest` dies on import is a bad look on a resume.
   Roughly 14 further failures were seen in a partial run before it was killed; get a real
   tally once collection is fixed.
3. **Re-run `compute_oaq.py`** window-level on the refreshed inputs → fresh
   `oaq_pilot.csv` + `results.json`. Both are stale (2026-08-06, pre-A52).
4. **Build the writeup.**

## Publication mechanics — checked 2026-08-27, all still to do

Four things stand between "analysis done" and "link someone can click". None are hard;
all are invisible until you hit them.

| # | Gap | Note |
|---|---|---|
| 1 | **There is no root `README.md`.** | GitHub renders the root README as the landing page — so the root README *is* the deliverable. Right now the repo root holds only `CLAUDE.md`, `SESSION.md`, `Full Project Files/`, `Pilot Files/`. `Full Project Files/README.md` is an internal index, not a landing page; do not repurpose it |
| 2 | **Repo is named `cassis-2026-marchand-index`** | Remote: `https://github.com/adamn03/cassis-2026-marchand-index.git`. The name advertises a conference that is not happening. Owner's call — GitHub 301-redirects the old URL after a rename, so nothing breaks. Suggested: `nhl-marchand-index` |
| 3 | **All the work is on `position-locked-peers-rawcap-mi`, not `main`** | GitHub shows `main` by default. Whatever gets written lands nowhere useful until it is merged. Merging to main is the last step, not the first |
| 4 | **Stale branches are publicly visible** | `agents/ai-agents-mode-claude-pro-query`, `whole-league-774-scrapes`. Clutter on a repo meant to look considered. Delete or leave — owner's call |

Also: folder names `Full Project Files/` and `Pilot Files/` contain spaces and read as
working notes rather than a project. Renaming touches every path in every doc and the
`_common.py` path constants — real work, and cosmetic. **Do not do it** unless the owner
asks; the root README can simply explain the layout in one line.

## λ = 0.5 — decision needed at task 3, not before

`OAQ_portable` strips home-market size with a one-sided damped subtraction at λ=0.5 (A5).
That term has now **failed in three independent designs** (latest: dated trades, Δlog metro
pop b=−0.021 t=−0.37, Δlog team subreddit b=+0.080 t=+1.09, n=60).

Recommendation: **keep λ=0.5 as the headline.** It is pre-registered, and keeping a
pre-registered value needs no amendment — changing it after seeing results is what the
prereg exists to prevent. Add a λ=0 column as robustness (also no amendment) and disclose
the three failures in the limits section. That converts an awkward result into a
credibility signal. Owner may overrule, but overruling requires a numbered amendment.

## Still live, do not rebuild

Full detail in `Full Project Files/marchand_index/value_propositions.md` Part 1 — the idea
ledger, WORKS/KINDA/DEAD/UNTESTED, 26 ideas. Short version:

- **WORKS:** the Wiki/Reddit sign flip during international tournaments; attention is
  unpriced (bounded null); event spike ranking; Reddit daily panel recovery.
- **KINDA:** peer-stack v2 (robustness only — claim the tails, not the ordering);
  attention concentration.
- **DEAD (11):** the ratchet (**retracted 2026-08-26** — was Olympics contamination), the
  Rosen/Adler "identity compounds" framing (sign reversed), the endogenous spike-≥2x
  treatment rule, λ's market term, Google Trends commercial intent (instrument floor),
  the eBay API (licence — four disqualifying clauses), and five others.

## Repo state

- Branch `position-locked-peers-rawcap-mi`, **nothing committed** from the last two
  sessions. 58 files changed, ~1,700 diff lines after the housekeeping pass.
- Housekeeping done 2026-08-26: `.gitattributes` (`*.csv -diff`) collapsed a 1,014,065-line
  diff to ~1,700; `final_dataset/` is now generated by `export_final_dataset.py` and
  gitignored; backup dir + crashed `.tmp` writes moved to `../_marchand_quarantine/`;
  49 run logs moved to `marchand_index/logs/`. Rules recorded in `CLAUDE.md` §Git hygiene.
- Commit convention now: `feat:`/`fix:` touch only `.py`/`.md`, `data:` only CSVs, never mixed.

## Open question for the owner

The CASSIS artifacts — `Pilot Files/submission/` (accepted abstract + methods guide) and
the CASSIS-specific scaffolding in `CLAUDE.md` — are now superseded but **not deleted**,
per the project's own "ask before deleting" rule. They are also the record of an accepted
submission, which is itself a resume-worthy fact. Ask before removing anything.
