# Session Handoff
Date: 2026-06-20
Active: NHL_Marchand_Index — **FULL BUILD** (no longer a "pilot"). Branch: `marchand-index-full-build`.

LAST (this session): **Pivoted pilot2 -> the actual full comprehensive model. Brainstormed + LOCKED two design specs + wrote both implementation plans.**

DECISIONS LOCKED (all via brainstorming, owner-approved):
- **This is the real project**, not a pilot. New home = `Marchand Index/` tree; code still lives in `pilot2/` for now — a `pilot2/` -> `Marchand Index/` rename is a PENDING separate mechanical migration (not yet done).
- **A12 (ingestion):** ADD multi-language Wikipedia (`wiki_intl_12mo`; whitelist sv,fi,cs,ru,de,sk,fr; reuse the A1 Wikidata QID; A11 fixed window). DROP Instagram/X (noisy lifetime stock, fights the window) AND GDELT (3-month API window can't honor A11 — not worth it). New composite weights (sum 1.00): `wiki_en 0.29, wiki_intl 0.11, reddit_mentions 0.27, reddit_upvotes 0.17, trends 0.16` (IG removed; Reddit family 0.44, down from 0.484). ADD two diagnostics: source-correlation matrix + Reddit-downweight robustness.
- **A13 (skill vector):** ADD MoneyPuck 5v5 `cf_pct, xgf_pct, ozs_pct` to the peer vector (age, PPG, TOI/G -> 6 dims). Skip QoC (no MoneyPuck column; OZS% is the partial sub + poster disclosure). expected_cap (A4) UNCHANGED. Thin floor = 150 min 5v5 -> NULL features + impute neutral (never drop a player). Join key `nhl_player_id == MoneyPuck playerId` — columns VERIFIED live (playerId, name, team, situation, games_played, icetime, onIce_corsiPercentage, onIce_xGoalsPercentage, I_F_oZoneShiftStarts/dZoneShiftStarts). Accept the V3 re-roll risk.
- **YouTube = Gate-4 validation ONLY, never a composite input** (anti-circularity; it's the only free depth-covering held-out signal). If Gate 4 fails -> pre-registered §8 scope-down (depth claim -> exploratory), headline survives on V1/V2/V3; NO retroactive swap.
- **Held the V3 0.40 floor** (no tuning). **Kept Reddit at 0.44** + rely on the pre-registered robustness response (if rho(full,no-Reddit)<0.7 -> disclose Reddit-dependence + co-equal downweighted leaderboard).
- Abstract framing fixed (Path A): lead with the ONE pre-registered headline (Lens 4 hybrid, lambda=0.5); panel demoted to robustness. (`abstract_v1.md` edits — committed; the submitted PDF unchanged.)

ARTIFACTS:
- Specs (committed 683eec0): `docs/superpowers/specs/2026-06-20-ingestion-expansion-design.md` (A12), `...skill-vector-expansion-design.md` (A13).
- Plans (this commit): `docs/superpowers/plans/2026-06-20-ingestion-expansion.md` (14 TDD tasks), `...skill-vector-expansion.md` (11 TDD tasks). Both grounded in real `pilot2/` signatures, self-reviewed with spec->task coverage matrices.
- `pilot2/fetch_trends.py` re-pointed to the A11 FIXED window (`timeframe="2025-04-18 2026-04-17"`) — was run-time-anchored ("today 12-m"), which leaked the 2026 playoffs (same confound A11 fixed for Reddit).

STATUS: blocked (for the FINAL compute) / ready-to-build (everything else)

BLOCKER:
1. **Reddit OAuth creds STILL BLANK** in `pilot2/.env` — hard prereq ONLY for the final end-to-end `compute_oaq` (Reddit = ~0.44 of engagement weight). Building/unit-testing A12+A13 fetchers does NOT need it.
2. **Trends A11 re-run did NOT finish this session** — `pilot2/raw/trends.csv` is still the OLD run-time-window file (mtime 11:58), NOT committed. The A11 re-run (`python pilot2/fetch_trends.py`) must be re-run + verified (774 rows; magnitudes weekly n_weeks=53; it's now A11-windowed by the code change).

NEXT (exact order):
1. **Execute the A12 plan FIRST** (commits before A13 per shared-file sequencing — both touch `compute_oaq.py` + `preregistration.md`). Reddit-free. Use subagent-driven-development or executing-plans. Build `fetch_wikipedia_intl.py`, the weight update, the 2 diagnostics, append A12 amendment.
2. **Execute the A13 plan** (rebase on A12 edits). Build `fetch_moneypuck.py`, expand SKILL_COLS, append A13 amendment.
3. **Re-run + verify Trends** on the A11 window (774 rows). (Fallback: 774-row NULL placeholder.)
4. **(When Reddit OAuth lands)** run `fetch_reddit.py` -> `fetch_wikipedia_intl.py` (if not yet) -> `fetch_moneypuck.py` -> `compute_oaq.py` -> re-confirm V1/V2/V3 on the 774 set vs unchanged floors (report regardless of direction).
5. Do the `pilot2/` -> `Marchand Index/` rename migration (mechanical; update import paths) once the new code works.
6. Build the remaining full-build subsystems (Gate 4 YouTube stratified, Gate 5 theme classifier, H1-H4) — specced as future sub-projects.

Technical carry-forward (still valid):
- 774 locked pool (497 F / 277 D, snapshot 2026-06-17). `players.csv` schema: `group` f1=F/d1=D; `player_id` 1..774 contiguous; `nhl_player_id` per player.
- Reddit: anonymous IP-blocked at Fastly; OAuth via `oauth.reddit.com` + bearer is the ONLY path. A11 FIXED window WINDOW_END=2026-04-17 baked into fetch_reddit.py. ALWAYS purge reddit_counts/detail when the set changes.
- MoneyPuck CSV: `https://moneypuck.com/moneypuck/playerData/seasonSummary/2025/regular/skaters.csv` (filter situation=='5on5'; traded players = one row per team, no aggregate -> icetime-weighted mean for rates, summed-count ratio for OZS).
- compute_oaq deterministic (seed 20260526, 1000 bootstrap). `_common.py` forces UTF-8; Windows console cp1252 (no non-ASCII in ad-hoc python -c). Scrapes share one sqlite `cache/http_cache` -> run SEQUENTIALLY. Network bg fetches need `dangerouslyDisableSandbox: true`.
- Composite weight code key `wiki_12mo` == the spec's `wiki_en_12mo`.

Deadline: abstract accepted for poster. Poster session **2026-09-12** (~12 wk runway). Roster snapshot locked; no live perishability.
