# Sports Analytics Conference Projects — Instructions

## Conference target

**CASSIS — Cascadia Symposium on Statistics in Sports** (https://www.cascadiasports.com/)

| Field | Value |
|---|---|
| Date | September 12, 2026 |
| Location | SFU Harbour Centre, Vancouver |
| Format | Oral talks + poster session + panel. Oral is preferred; poster is the fallback for non-oral selections. |
| Audience | Pro statisticians + analysts from sports teams, sports media, universities. Stat-literate, hostile to overclaim. NOT undergrad — judge floor is high. |
| Abstract submission | 2-page PDF to `cascadia-sports@sfu.ca` |
| Submission deadline | **May 31, 2026** |
| Review completion | June 15, 2026 |

**Goal:** push for **best-in-show idea quality**, not just "accepted." Aim for an oral slot; design every decision to maximize the work's standing in a roomful of pro statisticians.

## The 7 criteria — checked on every plan, every change

These are the floor for a 9.5/10 idea. Push back on any proposal that weakens any one.

| # | Criterion | What "passes" looks like |
|---|---|---|
| 1 | Methodologically novel | New method or new framing — not just a known method on new data |
| 2 | ≥3 independent validation pathways | Triangulation, not single proof |
| 3 | Pre-registered hypotheses | Locked in `Full Project Files/docs/preregistration.md` BEFORE the production model runs |
| 4 | Per-claim uncertainty | Bootstrap CIs or posteriors on every headline number |
| 5 | ≥1 striking, quotable finding | The retweetable number a judge remembers a week later |
| 6 | Honest limit-of-claim | Explicit "what we don't claim" on the poster, not in a footnote |
| 7 | Working artifact | Demo, code repo, or interactive notebook — not slides alone |

**Workflow hook:** when proposing or evaluating any change in this folder, explicitly check it against criteria 1–7. If it weakens any, flag the impact and offer a cheaper way to preserve that criterion. Failing one criterion drops the work to 9.0; failing two = below ship floor for CASSIS.

## Selected project + folder structure

**SELECTED: NHL Marchand Index.** It is the active full build (the `NHL_Draft_Model` candidate lost selection and is archived). Reorganized 2026-06-28 into two top-level folders:

```
<root>/
├── CLAUDE.md, SESSION.md, .gitignore     # project infra — stay at root (harness auto-loads)
├── Full Project Files/                   # the active Marchand Index build (everything in use)
│   ├── README.md                         # index of this folder
│   ├── NHL_Marchand_Index.md             # the live spec
│   ├── marchand_index/                   # the codebase (self-contained; run pytest from inside)
│   │   └── preregistration.md            # CANONICAL impl prereg (A1–A14) — code/tests read it
│   └── docs/
│       ├── preregistration.md            # H1–H4 + gate-rule prereg (spec-level)
│       └── superpowers/{specs,plans}/    # design history
└── Pilot Files/                          # decided / non-active artifacts
    ├── README.md                         # index of this folder
    ├── pilot/                            # the N=160 pilot codebase + data (archived)
    ├── submission/                       # accepted CASSIS abstract + methods (pilot-derived)
    └── archive/NHL_Draft_Model.md        # rejected candidate idea
```

When asked to work on "the project," it is the Marchand Index under `Full Project Files/`. Vault Python defaults, atomic-write convention, and OpenRouter LLM access apply.

## Hard Constraints (all projects)

- **$0 budget.** Free APIs / public scraping only — polite + rate-limited + cached.
- **Local-only:** Windows + Python + SQLite. No cloud, no paid services.
- **OpenRouter URL:** `https://openrouter.ai/api` (NO `/v1` suffix — Anthropic SDK appends `/v1/messages` itself).
- **Atomic file writes:** `.tmp` → rename. Never overwrite mid-write.
- **No causal claims** we can't back with the data on hand.
- **No revenue claims** for the Marchand Index — attention is explicitly a proxy.
- **Pre-registration discipline:** hypotheses lock before any production run.
- **LLM-derived features must be validated** (F1 + κ vs. hand labels) before appearing on the poster.

## Communication style (this project)

- **Terse.** Bullets and tables over prose. State decisions; don't narrate deliberation.
- **Code-first updates.** WHY in one line, then diff. Don't recap what the code says.
- **No emoji** unless explicitly requested.
- **Push back.** Owner explicitly wants critique on weak ideas — see Pushback Policy.

## Pushback Policy

Challenge any idea that:
- Weakens any of the 7 criteria above
- Is high-effort for marginal gain
- Reinvents proven public work (pGPS, NHLe, Corsi, GSAA — use, don't replicate)
- Is scope-creep displacing higher-ROI work
- Has a data-leakage risk (outcome-correlated feature feeding training)
- Overclaims precision the data can't support

**Format when pushing back:** (a) what to skip and why, (b) cheaper proxy that captures ~80% of the value, (c) cost in time/risk if the owner insists anyway.

## SESSION.md format (token-efficient)

Read SESSION.md at the start of every session. Overwrite it when the owner says "update session" / "wrap up." Format — keep this tight:

```
# Session Handoff
Date: YYYY-MM-DD
Active: <NHL_Draft_Model | NHL_Marchand_Index | other>
LAST: <what was built/decided in 1-2 lines>
STATUS: working | broken | blocked
BLOCKER: <only if status ≠ working>
NEXT: <one specific actionable task, no clarifying questions needed>
```

Be specific in every field. "Next" must be actionable enough that a fresh session can resume immediately.

## Per-project hard rules (apply ONLY to whichever idea gets selected)

The rules below are pre-locked design constraints for each candidate. They activate the moment the owner picks that idea to build. Until then they are reference, not commitments.

### NHL_Draft_Model
- Position-locked comparisons. F / D / G never mixed.
- Consensus rank: scoring-time only, ≤10% of final score. **Never** a training feature.
- 2021–2023 holdout is sacred. Touching it for tuning invalidates metrics.
- Two-tier success: aim ρ ≥ 0.50, top-31 hit ≥ 65%, lift ≥ +10 pp. Ship gate ρ ≥ 0.40, top-31 ≥ 55%, lift ≥ +5 pp.
- Honest output: every goalie row carries the team-need caveat.

### NHL_Marchand_Index
- K=10 peer matching, **never** single twin.
- Both `OAQ_observed` (market-included) and `OAQ_portable` (market-stripped) reported. Headline = `OAQ_portable`.
- `net_sentiment` is **never** in CES weights. Volume separated from sentiment.
- LLM theme classifier must pass macro-F1 ≥ 0.60 AND Cohen's κ ≥ 0.55 before themes appear on the poster.
- H1–H4 pre-registered in `Full Project Files/docs/preregistration.md` BEFORE the model runs on production data.
- Bootstrap CIs + `match_quality_flag` on every published OAQ.
- Marchand framing: "high-skill player whose public salience and polarizing identity exceed what production-matched peers produce" — never "mid-skill."

## What NOT to re-propose without strong reason

**Draft Model:** game-level scrape (v1.5), full NLP on scouting reports, shots/G or +/- as features, Memorial Cup data, weak-team amplification, full goalie projection model (v1 is range-bracket only).

**Marchand Index:** Twitter/X engagement (free tier dead), endorsement-deal scrape (private + ToS-grey), per-game ticket prices (too noisy), web dashboard (v1.5), coach-tenure as predictive model (sample too thin), goalies in headline analysis (peer matching breaks down).

## References

- Vault defaults: `C:\Local Only\Ai projects\CLAUDE.md`
- Conference: https://www.cascadiasports.com/
- NHL outcomes API: `https://api-web.nhle.com/`
- OpenRouter: `https://openrouter.ai/api` (no `/v1`)
- Live spec: `Full Project Files/NHL_Marchand_Index.md` · archived candidate: `Pilot Files/archive/NHL_Draft_Model.md`
- Downstream value-prop backlog: `Full Project Files/marchand_index/value_propositions.md`
