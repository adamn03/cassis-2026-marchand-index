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
GP diagnostic was run over the 788 (`_pool_gp_diag.py`, read-only). Results:

> **GP DIAGNOSTIC RESULT: in progress (background task bqoqo4imc) — numbers patched in on completion.**

Options (nothing scraped yet, so refining now is free):
1. **Refine to ≥1 NHL game in 2025-26** (RECOMMENDED) — clean "played in the NHL this season" pool;
   keeps every real NHLer incl. low-GP, drops never-played reserves. Not the GP gate you objected to.
2. **Keep all 788 as-is** — maximal; carries never-played reserves; `small_sample` flag can't catch GP=0.
3. **Light floor: ≥1 NHL GP OR on the active 23-man roster** — also re-includes shed UFAs.
To apply opt 1/3: add a season-totals GP intersection to `fetch_rosters_league.py` (or post-filter
`players.csv`), then re-lock players.csv (player_ids re-sequence — fine, nothing depends on them yet).

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
