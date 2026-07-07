# Session Handoff
Date: 2026-07-07
Active: NHL_Marchand_Index — FULL BUILD. Branch: `marchand-index-full-build`.

STATUS: working — no production results yet (Reddit 0/774, blocked on creds). Trends re-fetch STALLED at 331/774 (4 null); background job from 07-03 is dead, resume needed.

THIS SESSION (2026-07-07) — design audit + airtight execution plan, NO code/prereg changes made:

1. **Full logic audit of the model** (spec + prereg A1–A20 + code spot-checks) → internal findings E1–E9. Code-confirmed bugs: Reddit A15 filter double-attributes identical-name pairs (two Elias Petterssons both VAN, two Sebastian Ahos — `fetch_reddit.py:140-179`); expected_cap OLS fit includes ELC rows (`compute_oaq.py:491`, biases rookie MI up); V3 team-outcome window is RUN-ANCHORED (`fetch_team_outcomes.py:89` — playoff contamination, same class A14 fixed); V1b (only powered validation) has NO pre-registered AUC floor.
2. **3-judge CASSIS panel (subagents: hostile statistician, NHL club practitioner, validation methodologist) + panel-chair review** → consolidated, APPROVED plan. Three headline attacks closed: (a) poster headline (MI hybrid) was never touched by any validation gate; (b) honest independent-pathway count = 1 (jersey family) — Gate-4 now load-bearing + V2 powered via ASG 2022+2023+2024 union + V3 relabeled consistency-check; (c) Reddit 0.44 weight measures "plays for Canadian team" — market proxy rebuild w/ team-sub subscribers via OAuth.
3. **DELIVERABLE: `Full Project Files/docs/airtight_execution_plan.md` v1.1** — amendments A21–A35 + G4-A1–A3 fully specified (mechanical rules, file targets, tests, acceptance criteria), Phase 0 (amendments) → Phase 1 (data hygiene) → Phase 2 (one-shot compute) → Phase 3 (Gate-4). Written to be executable by a weaker model. §G = complete poster-limitations list; §H = forking-paths labeling rule; A31 shipping matrix skeleton.

NEXT (exact order):
1. **OWNER: make the 3 §D decisions in the plan** — (1) Gate-4 GO (panel: mandatory), (2) A30 market-proxy rebuild yes/no (recommend yes), (3) headline structure sign-off. Record in prereg.
2. **Execute plan Phase 0**: amendments A21–A35 + G4-A1–A3 in order per `docs/airtight_execution_plan.md` §B — amendment text committed BEFORE code, convention `marchand_index: A<N> <summary>`. A30 only after decision #2. Everything must land while Reddit is 0/774.
3. **Phase 1 in parallel**: resume trends (`python fetch_trends.py`, 331→774), cap_quality triage (121 low, OWNER-ASSISTED), duplicate-vector scan (Jones/Walker), MID-duplicate check, MoneyPuck audit, case-card roster verify (Marner/Reaves), Reddit dry-run readiness, V3 re-fetch after A29.
4. **Reddit creds (USER ACTION)** → Phase 2 one-shot compute per plan §E.
5. **Gate-4 fetch launches right after G4 amendments** (~8 fetch-days, long-lead, independent of Reddit).

CARRY-FORWARD: 774 locked pool (497F/277D, snapshot 2026-06-17); fixed window [2025-04-18, 2026-04-17]; A12 weights (wiki_en .29 / wiki_intl .11 / r_mentions .27 / r_upvotes .17 / trends .16); seed 20260526; tests 102 passing; MoneyPuck cached; UTF-8 forced in _common. Prior open MEDIUMs (bootstrap understatement, reddit cap censoring, star-boundary diagnostic, cap_quality triage) are ALL absorbed into the plan (A26, A23, A27, Phase 1.2) — the plan supersedes the old carry-forward list as the source of truth for open work.

Deadline: poster session 2026-09-12 (~9.5 wk runway).
