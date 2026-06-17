# Session Handoff
Date: 2026-06-17
Active: NHL_Marchand_Index — **WHOLE-LEAGUE PIVOT**. Abstract ACCEPTED for a CASSIS poster (Sept 12, 2026). Building the full-league run; the prior 160-skater Tier-1 set (A7) is superseded.

LAST:
- Brainstormed + owner-APPROVED the whole-league pool design. Full spec:
  **`docs/superpowers/specs/2026-06-17-whole-league-pool-design.md`** (read first).
- **CAPTURED + LOCKED the roster snapshot** (perishable — beat the July 1 free-agency window).
  New script **`fetch_rosters_league.py`** pulled `/roster/{team}/current` for all 32 teams, all
  forwards+defensemen, goalies excluded. **`players.csv` overwritten: 788 skaters (506 F / 282 D)**,
  schema unchanged + new `roster_snapshot_date=2026-06-17`. Verified: 0 goalies, group f1/d1 correct.
- **OPEN DATA-QUALITY ISSUE (must resolve before A10 + scraping):** 788 is high and per-team counts
  swing **18 → 33** (NSH 18, DET 19 … MIN/OTT/UTA 30, VEG 31, PHI 32, BUF 33). A real end-of-season
  active roster is ~22-23 skaters. So `/current` in mid-June is NOT a clean end-of-season snapshot:
  high-count teams include signed reserves/prospects (some with **0 NHL games** in 2025-26 = AHL/junior
  org depth); low-count teams have already shed expired-UFA regulars. Never-played prospects have no PPG
  → can't be production-matched → pure noise. (This is NOT the valuable-low-GP NHLer we want to keep —
  e.g. Buium-type — those played games.)

STATUS: blocked on TWO owner decisions + the long-standing Reddit creds blocker.

## DECISION 1 (one-glance, next session): final pool definition
GP diagnostic run over the 788 (`_pool_gp_diag.py`, read-only, 0 fetch-fails). 2025-26 NHL reg-season GP:
- **GP = 0 (never played 2025-26): 21**
- GP 1-19: 82  ·  GP 20-40: 80  ·  GP 41+: 605
- **Played ≥1 NHL game: 767 (97%)**

So `/current` is cleaner than feared — only 21 reserves, not ~100. BUT the 21 GP=0 are a MIX:
- Mostly never-played junior/AHL prospects (drop): Nico Myatovic, Stian Solberg, Noah Warren, Anton
  Wahlberg, Radim Mrtka, Riley Fiddler-Schultz, Vsevolod Komarov, Tyler Boucher, Graeme Clarke,
  Helge Grans, Trevor Connelly, etc. (20 shown in the diagnostic; re-run `_pool_gp_diag.py` for the full 21).
- **At least one injured franchise player: Aleksander Barkov (FLA).** VERIFIED — no 2025-26 row at all,
  prior 8 seasons 50-82 GP. A naive "≥1 GP this year" filter would WRONGLY drop him. This is exactly the
  valuable-player-who-missed-the-year case you flagged.

RECOMMENDATION (revised by the Barkov finding): refine to **"≥1 NHL GP in 2025-26 OR career regular"**.
Only 21 names are ambiguous, so just **hand-classify those 21** (keep career NHLers like Barkov, drop
never-played prospects). Net pool ≈ 767 + a few injured vets ≈ **~770**. Options:
1. **≥1 GP OR career-regular, hand-classifying the 21** (RECOMMENDED) — keeps injured stars, drops prospects.
2. **Strict ≥1 NHL GP in 2025-26** → exactly 767; simplest but drops injured vets like Barkov (slightly wrong).
3. **Keep all 788** — maximal; the 21 never-played prospects sit at the bottom with no production (NaN/noise).
To apply: post-filter `players.csv` to the kept `nhl_player_id`s (or add a season-totals GP+career
intersection to `fetch_rosters_league.py`), then re-lock players.csv (player_ids re-sequence — fine,
nothing depends on them yet).

## DECISION 2 / BLOCKER: Reddit OAuth creds (still empty)
`pilot2/.env` keys exist but all 4 VALUES are blank. Register a free *script* app at
https://www.reddit.com/prefs/apps (redirect `http://localhost:8080`); fill `REDDIT_CLIENT_ID` +
`REDDIT_CLIENT_SECRET`. Reddit = 0.417 of the attention signal (mentions+upvotes); essential.

NEXT (in order — needs no clarifying questions once Decision 1 is made):
1. **Resolve Decision 1** using the GP diagnostic numbers above; if refining, re-run the (edited)
   roster build → re-lock `players.csv`.
2. **Log pre-reg amendment A10** in `methods.md` (after A9) + `docs/preregistration.md`: pool = final
   end-of-2025-26 roster definition + locked count + snapshot date 2026-06-17. BEFORE any compute.
3. **Add `small_sample` flag (GP<20), non-exclusionary**, where `match_quality` is set in `compute_oaq.py`.
4. **No-blocker scrapes (no creds needed):** `fetch_nhl_api.py` (~6m) → `fetch_wikipedia.py` (~12m)
   → `fetch_cap_hits.py` (~35m). Then `fetch_trends.py` best-effort (resume+backoff, partial OK, 13.9% wt).
5. **Reddit (when creds land):** purge `raw/reddit_counts.csv` + `raw/reddit_detail.csv`, then
   `python fetch_reddit.py` (~45-90m over OAuth, resume-safe).
6. `python compute_oaq.py` → results.{md,json} + oaq_pilot.csv on full-league data.
7. Re-run/confirm V1/V2/V3 on new pool (report honestly). Refresh abstract/methods numbers + re-render
   `abstract_final.pdf` + `methods_final.pdf` for the POSTER.
8. (Process) Invoke `writing-plans` to formalize steps 1–7 into a tracked implementation plan.
9. Cleanup: delete `_pool_gp_diag.py`, `_reddit_reuse.py`.

## Working-tree state (uncommitted — on `main`, branch before any commit)
- NEW, uncommitted: `fetch_rosters_league.py`, `docs/superpowers/specs/2026-06-17-whole-league-pool-design.md`,
  `_pool_gp_diag.py` (temp), this `SESSION.md`.
- **`players.csv` OVERWRITTEN to the 788 league set (perishable — was the committed A7 160-set).**
  Not committed. If you want this snapshot safe in git, commit it (and `fetch_rosters_league.py`) first thing.
- Stale-provisional from the May 30 session (will be overwritten by the league run — ignore):
  `pilot2/results.{md,json}`, `oaq_pilot.csv`, `raw/*`, `external_outcomes.csv`; A8 edits in
  `compute_oaq.py`/`methods.md`/`roster_validation.md`; untracked `_reddit_reuse.py`.

## Technical carry-forward (still valid)
- **Reddit:** anonymous is IP-blocked at Fastly (sticky 403 HTML). OAuth via `oauth.reddit.com` + bearer
  token is the only path. `fetch_reddit.py` validates creds up-front (ZERO contact without creds).
- **Resume pitfall:** `load_resume` keys on set-relative `player_id` + drops null rows. ALWAYS purge
  reddit_counts.csv + reddit_detail.csv when the set changes (it IS changing: 160 → ~788/refined).
- **Monitor pitfall:** never `open()` reddit_counts.csv while `fetch_reddit.py` runs (races atomic
  `os.replace` → PermissionError WinError 5). Watch the task `.output` file, not the CSV.
- **players.csv schema:** `group` MUST stay `f1`(F)/`d1`(D) — compute_oaq peer-split key. `position` = NHL code.
  Adding columns is safe (consumers use `load_players()`/`pd.read_csv`; `roster_source`/`line_slot` are write-only).
- compute_oaq deterministic (seed 20260526, 1000 bootstrap draws). `_common.py` forces UTF-8; Windows console
  cp1252 (no non-ASCII in ad-hoc `python -c`). Background network fetches need `dangerouslyDisableSandbox: true`.
- Render toolchain: pandoc 3.9.0.1 + Chrome `C:\Program Files\Google\Chrome\Application\chrome.exe`
  (`--no-sandbox` print-to-pdf to $TEMP then mv).
- NHL roster endpoint quirk: `/current` in offseason ≠ end-of-season active roster (see Decision 1).

## Deadline
Abstract DONE (accepted for poster). Next real date: **poster session Sept 12, 2026** — ample runway.
No live perishability remaining (roster snapshot already captured 2026-06-17).
