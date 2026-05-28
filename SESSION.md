# Session Handoff
Date: 2026-05-28
Active: NHL_Marchand_Index — **pilot2** (160-skater Tier-1 pilot) for the CASSIS abstract.

LAST: A5 + A6 shipped on top of A4. A6 = new validation gate V3 (team-level triangulation, n=32 teams) → **PD confirmed: ρ = 0.418, 95% CI [0.073, 0.682], outcome = team Wikipedia 12-mo pageviews** (Reddit /about.json blanket-403, graceful-degradation logged in pre-reg before fetch). Reddit subscriber 0/32, Wiki 32/32 powered. Mechanical baseline (sum of engagement_raw) ρ=0.410 — peer-skill control adds essentially no team-aggregate signal, disclosed openly. Abstract + methods rewritten end-to-end around A4/A5/A6 reality (dropped stale v1 14-player numbers; lead with V3 confirmation; IG-NULL weight-transfer + A5 peer-asymmetry both disclosed in prose). Four-perspective review (presenter/fan/judge/professional) converged on **poster, not oral**; professional confirmed they take A4 expected_cap denominator back to their NHL team's bargain-rate dashboard this week.

STATUS: working. All commits pushed (or about to be — see this commit). Deterministic at seed 20260526, diff-verified across runs.

NEXT (in order, ~70 min to ship-ready):
1. **λ sensitivity vs V3 ρ table** in `results.md` — recompute V3 ρ under λ ∈ {0, 0.25, 0.5, 0.75, 1.0} on `OAQ_observed` aggregates. Removes the professional's #1 clarification ("is λ=0.5 grid-search-in-disguise or a flat surface?"). ~20 min.
2. **Karlsson peer-baseline sensitivity** — recompute Lens 5 top-10 if peer baseline is `mean(engagement_raw across peers)` instead of `mean(A5-adjusted across peers)`. Tests whether Karlsson #1 is the A5 asymmetric-peer-mean artifact the judge flagged. ~30 min.
3. **Render `abstract_final.pdf`** — pandoc → HTML → headless Chrome print-to-pdf at `/c/Program Files/Google/Chrome/Application/chrome.exe --no-sandbox`; render to $TEMP then mv. ~15 min.
4. **Email submission** — owner-only, `abstract_final.pdf` → `cascadia-sports@sfu.ca`, deadline 2026-05-31.

Post-submission (Phase 5, oral upgrade path): leaguewide rerun (~700 active skaters) + LLM theme classifier validation (κ ≥ 0.55) — converts "poster with one validation gate" into a powered, leaguewide test. Required for oral if abstract accepted with upgrade option.

## Pilot2 state — numbers that matter

- **N=160** (96 F / 64 D), Reddit 160/160 non-NULL, IG 0/160 (disclosed weight-transfer to wiki 0.355 / reddit-m 0.290 / reddit-u 0.194 / trends 0.161).
- **PA** inconclusive (V1a n=4); **PB** inconclusive (V2 4/160 ASG, V1b 8/160 jersey); **PC** confirmed (4 displaced: McDavid/Suzuki/Bedard/Draisaitl); **PD** confirmed (V3 ρ=0.418 n=32).
- Headline **Lens 5 top 5** (A4 expected_cap, A5 λ=0.5): Linus Karlsson (26, VAN), Crosby (38, PIT), Ovechkin (40, WSH), Q.Hughes (26, VAN), Will Smith (21, SJS).
- 5 leaderboard lenses + λ sensitivity ladder all in `pilot2/results.md`.

## Files on disk (pilot2/)

- `compute_oaq.py` — A4 + A5 + A6 implemented; deterministic; 5 lenses + V3 + λ ladder.
- `fetch_team_outcomes.py` — new in this session (A6 outcome fetcher).
- `team_outcomes.csv` — 32 rows; wiki_12mo populated for all 32, subreddit_subscribers NULL for all 32 (Reddit 403 graceful-degraded).
- `preregistration.md` — A1–A6 amendment trail, all timestamped before each re-run.
- `oaq_pilot.csv`, `results.md`, `results.json` — all refreshed under A6 run.
- v1 `pilot/` untouched.

## Reviewer reports (this session — for next-session context)

Run inside `Sports Analytics Conference Projeccts/` from the Agent tool, parallel:
- **Presenter:** "Not oral-ready; borderline poster-ready; rewrite abstract around method+disconfirmation."
- **Fan:** "Cool idea, but right now it's mostly finding bargains, not Marchands."
- **Judge:** "(b) Accept-for-poster as-is; amendment trail more disciplined than 80% of NESSIS."
- **Professional:** "Methods piece, not a model we can use yet. Worth lifting one technique: A4 expected_cap. Sam wires it in this week."

Consensus: **submit as poster**, not oral. Oral path = leaguewide rerun + V1b/V2 power recovery.

## Technical carry-forward

- Bash tool = Git Bash; `_common.py` forces UTF-8.
- Bootstrap: 1000 draws, seed 20260526; deterministic, diff-verified.
- requests_cache sqlite in `pilot2/cache/` (gitignored); reddit = plain session.
- atomic_write_csv signature is `(path, rows, fieldnames)` — NOT (path, fieldnames, rows).
- PDF re-render path: pandoc → HTML → Chrome print-to-pdf, render to $TEMP, then mv.

## Deadline

**May 31, 2026** (3 days). Owner-only: email `abstract_final.pdf` to `cascadia-sports@sfu.ca`.
