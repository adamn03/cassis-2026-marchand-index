# Session Handoff
Date: 2026-07-07
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

STATUS: working — no production results (Reddit 0/774). Trends STALLED at 331/774 (4 null); resume with `python fetch_trends.py` (resumable, ~443 left at ~9s/player).

THIS SESSION (2026-07-07 pm, Fable final day) — NO code/prereg changes; wrote two executable supplement plans for weaker models (Opus/GPT). Both supplement `docs/airtight_execution_plan.md` v1.1, overlap nothing in it, claim amendment numbers A36–A39:

1. `Full Project Files/docs/superpowers/plans/2026-07-07-free-data-improvements.md`
   - **A36** player-wiki redirect-title pageview summation, en+intl (code-confirmed gap: `fetch_wikipedia.py` fetches canonical title only; A29 gave teams redirect summation, players never got it; A1 measured Ovechkin redirect at 7,059 dropped views). Full amendment text + augmenter script spec + tests.
   - **A37** V1b union-completion sweep: pre-declared all-or-none retrieval of ALL official jersey lists in the locked 3-season class → more positives for the sole confirmatory primary (n=12 now). Fixed search manifest + 5-clause qualification.
   - Pre-chews: **A31 shipping-matrix rows 3–7 written verbatim** (airtight plan left them "fill in amendment" — do NOT let a weaker model invent them), BH permutation mechanics pins, Gate-4 quota manifest spec, Wayback archival of outcome-source URLs, abstract→poster conformance crosswalk (incl. reconciling abstract's "hybrid MI = headline metric" with A31's validation-finding headline).
2. `Full Project Files/docs/superpowers/plans/2026-07-07-cross-domain-improvements.md`
   - **A38** empirical λ anchor: event study on in-window team-changers vs their K=10 peers (λ=0.5 is "unanchored" per §G — weakest assumption on poster). Descriptive diagnostic only; primary λ untouched under every outcome. Estimator fully pinned (λ̂=clip(β̂/γ̂,0,1), windows, exclusions, bootstrap seed 20260526).
   - **A39** attention-concentration descriptive panel (Gini, top-1%/10% shares, payroll contrast, between-team ANOVA R²; Rosen/Adler superstar-econ framing) — criterion-5 quotable-number insurance, pre-registered.
   - 12-citation framing kit (`docs/poster_related_work.md` content) with mandatory verification protocol — weaker model must verify, never generate citations. Rejected-ideas tables in both plans.
   - Consistency patch to plan 1: A36 rewrites `wiki_daily.csv` as zero-filled 365-day date-indexed vectors (A26 block bootstrap already assumes 365-day rings; A38 requires the date index).

NEXT (exact order):
1. OWNER: 3 §D decisions in `docs/airtight_execution_plan.md` (Gate-4 GO — panel says mandatory; A30 market-proxy rebuild yes/no — recommend yes; A31 headline sign-off). Record in prereg.
2. Execute airtight Phase 0 (A21–A35 + G4-A1..A3) exactly as written, then supplement Phase-0 tail (A36 → A37 → A38 → A39; amendment text committed BEFORE code; ALL while Reddit is 0/774). When writing A31, paste the pre-chewed content from supplement plan 1 Task 5.
3. Phase 1 in parallel: resume trends 331→774 FIRST (longest pole besides Reddit), cap_quality triage (OWNER-ASSISTED), duplicate-vector + MID-dupe scans, MoneyPuck audit, case-card roster verify, Reddit dry-run readiness, V3 re-fetch after A29, A38 mover-date lookups (supplement plan 2 Task 2), Wayback archival (plan 1 Task 7).
4. Reddit creds (USER ACTION) → Phase 2 one-shot compute → §E diagnostics, now also `diagnostics/lambda_portability.py` + `diagnostics/attention_concentration.py` (register in §E/§H/§I per plan 2 sequencing note).
5. Gate-4 fetch right after G4 amendments (~8 fetch-days; use plan 1 Task 6 quota manifest).

CARRY-FORWARD: 774 locked pool (497F/277D, snapshot 2026-06-17); fixed window [2025-04-18, 2026-04-17]; A12 weights (wiki_en .29 / wiki_intl .11 / r_mentions .27 / r_upvotes .17 / trends .16); seed 20260526; tests 102 passing; MoneyPuck cached; UTF-8 forced in _common. Source-of-truth stack for open work: `airtight_execution_plan.md` v1.1 + the two 2026-07-07 supplement plans (this order). A36–A39 numbering is claimed — any new amendment starts at A40.

Deadline: poster session 2026-09-12 (~9.5 wk runway).
