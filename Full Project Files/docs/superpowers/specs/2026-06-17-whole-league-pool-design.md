# Design: Whole-League Pool (pilot2 → "league" run)

Date: 2026-06-17
Status: APPROVED (owner, 2026-06-17). Execution DEFERRED — blocked on Reddit OAuth creds.
Project: NHL_Marchand_Index (CASSIS poster — abstract accepted; this is poster/talk prep)

## Context

The CASSIS abstract was submitted and **accepted for a poster** (session Sept 12, 2026).
Owner direction: expand from the curated 160-skater Tier-1 set (A7) to the **whole league**.
This redefines the player pool only — the Marchand Index method is unchanged.

## 1. Player pool (locked snapshot)

- **Pool = every rostered skater (F + D) on each of the 32 teams' end-of-2025-26 roster.**
- Source: NHL API `/roster/{team}/current`, captured NOW (before July 1 free agency).
- **No GP gate, no career override.** Roster membership IS the qualification. Players sent down
  to the AHL are not on the end-of-season NHL roster, so the snapshot filters them naturally —
  no arbitrary threshold, and no risk of cutting valuable low-GP young players (e.g. a Buium-type
  who played few games but is a real, rostered NHLer).
- **Goalies excluded entirely** (hard rule: K=10 peer matching breaks for ~60 goalies; production
  not comparable to skaters).
- Scale: ~22.3 skaters/team (calibrated live: VAN 23 / EDM 23 / TOR 21) → **~715 skaters**.
- **Lock it:** capture once, write `players.csv`, stamp `roster_snapshot_date`, treat as the
  pre-registered pool. Do NOT re-derive later (July 1 moves would corrupt it).

### New script: `fetch_rosters_league.py`
- Replaces the TOI-selection logic in `fetch_rosters_toi.py` (which picked top-5/team).
- For each team: pull roster, take ALL `forwards` + `defensemen` entries (drop `goalies`).
- Emit the SAME `players.csv` schema as today so every downstream scraper + `compute_oaq.py`
  work unchanged:
  - `group` = `f1` for all forwards / `d1` for all D (peer-split key; position-lock).
  - `position` = NHL code (L/C/R/D), descriptive only.
  - `nhl_player_id` straight from roster endpoint; `wikipedia_slug`/`capwages_slug` as today.
  - add `roster_snapshot_date`.

## 2. Pre-registration amendment A10 (BEFORE any production compute — criterion 3)

Log in `methods.md` (after A9) and `docs/preregistration.md`:
- Pool redefined: 160-skater TOI-selected set (A7) → full end-of-2025-26 roster snapshot
  (~715 skaters), no GP filter, locked on capture date.
- Rationale: whole-league coverage; roster membership as qualification; avoids excluding
  legitimate low-GP NHLers.
- This is the honesty gate. Log it before the production run touches data.

## 3. Method unchanged — only the pool grows

Carry over verbatim:
- A8 hybrid headline (`marchand_index_hybrid`: rookie-deal → expected_cap; others → cap_hit_M).
- `OAQ_portable` headline; `OAQ_observed` also reported.
- λ=0.5 one-sided damped market correction (A5).
- K=10 peer matching, position-locked (F vs D never mixed via `group`).
- Per-player sentinel renormalization of engagement components.
- Engagement weights: wiki 0.306, reddit_mentions 0.250, reddit_upvotes 0.167, trends 0.139,
  instagram 0.139.
- Bootstrap: 1000 draws, seed 20260526.

Peer pools grow 96F/64D → ~450F/~265D, so K=10 matching becomes MORE robust.

## 4. Scrape plan — clean uniform re-pull (no cache reuse)

The set changes, so `player_id` is set-relative. Reusing old cached rows risks ID mismatches and
mixed fetch windows. For pre-reg cleanliness, do a **fresh uniform pull keyed to new IDs**, and
**purge `raw/reddit_counts.csv` + `raw/reddit_detail.csv`** first (the documented resume pitfall:
`load_resume` keys on `player_id`).

Order + rough cost ($0, resume-safe, mostly unattended):

| Source | Blocker | Est. time (~715) | Notes |
|---|---|---|---|
| NHL skill (PPG/TOI/GP) | none | ~6 min | `fetch_nhl_api.py` |
| Wikipedia pageviews | none | ~10 min | `fetch_wikipedia.py` |
| Cap hits | none | ~30 min | `fetch_cap_hits.py` (polite rate) |
| Google Trends | best-effort | hours, partial OK | 13.9% wt, renormalizes; resume + backoff |
| Reddit | **OAuth creds** | ~45-90 min | 0.417 wt, ESSENTIAL; runs when creds land |

No-blocker sources (NHL/wiki/cap) can run the moment the pool is locked. Trends best-effort.
Reddit is the one hard prerequisite.

## 5. Data-honesty safeguard (criterion 6)

Add a **descriptive, non-exclusionary** `small_sample` flag on low-GP players (GP < 20) so the
headline is never quoted on a ~3-GP call-up. Players stay in the pool and in all computations;
bootstrap CIs already widen for thin signal. Flag surfaces alongside `match_quality_flag` in
`oaq_pilot.csv` / `results.md`.

## 6. Validation + outputs

- Re-run V1/V2/V3 on the new pool. V3 team-level triangulation gets more robust (more players/team).
- Refresh `results.{md,json}`, `oaq_pilot.csv`.
- Refresh abstract/methods numbers + re-render `abstract_final.pdf` + `methods_final.pdf`
  (pandoc 3.9 → HTML → headless Chrome print-to-pdf). Target is the POSTER, not a submission.

## 7. Risks / prerequisites

- **Reddit OAuth creds (HARD BLOCKER).** `pilot2/.env` keys exist but values are empty. Register a
  free *script* app at https://www.reddit.com/prefs/apps (redirect `http://localhost:8080`); fill
  `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET`. Without it, no Reddit = 0.417 of attention signal lost.
- **July 1 free agency (PERISHABLE).** Capture + lock the roster pool before June 30 or the
  end-of-season snapshot is unrecoverable. This step needs no creds.

## 8. Open items (resolved)

- Eligibility: all rostered skaters, no GP gate — RESOLVED.
- Goalies: excluded — RESOLVED.
- Cache reuse: clean re-pull, purge Reddit CSVs — RESOLVED.
- small_sample flag: add it (non-exclusionary) — RESOLVED.

## Next (implementation)

When resuming: invoke `writing-plans` to turn this into a step-by-step implementation plan,
starting with A10 pre-reg log → roster capture → no-blocker scrapes → Reddit (on creds) → compute → render.
