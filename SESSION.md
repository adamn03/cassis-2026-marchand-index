# Session Handoff
Date: 2026-06-18
Active: NHL_Marchand_Index — WHOLE-LEAGUE (774 skaters). Abstract ACCEPTED for CASSIS poster
(2026-09-12). Pool LOCKED & FINAL. All no-blocker scrapes DONE & verified. Remaining work is the
Reddit fetch + final compute (blocked on OAuth) and a trends re-fetch retry.

LAST (this session):
- **DECISION 1 IS FINAL → pool = 774. Owner veto CLOSED 2026-06-18.** Rule = `career_nhl_gp >= 1`
  (keeps Barkov + 6 other zero-GP-this-season NHLers; drops 14 never-played org-depth prospects).
  Owner confirmed the gate is the justification (a player with 0 NHL games has no production to
  peer-match → OAQ undefined, not just small-sample). Full 788 audit preserved in `pool_gp_audit.csv`;
  the 14 dropped names are in the A10 pre-reg. STOP re-raising the veto — it is settled.
- **Step 2 done:** purged stale 788-keyed `raw/reddit_counts.csv` + `raw/reddit_detail.csv` (deleted).
- **Step 4 done:** rebuilt `external_outcomes.csv` → 774 rows. **V1 jersey overlap n=11 (>=10 → no
  longer underpowered; was the binding weakness on the 160-set).** V2 ASG-2024 n=9 (still <10).
- **Step 3 ran** — no-blocker scrape chain, background sequential, 20:10–21:08 UTC (`raw/_chain.log`).
  Verified row counts (all 774 ✓ except trends):
  - `raw/nhl_skill.csv` ✓ 774 (773 with PPG, 0 missing NHL id) — carries `games_played` → small_sample
  - `raw/wiki_pageviews.csv` ✓ 774 (764 pageviews, 0 weak-match, 10 unresolved) + `raw/wiki_daily.csv` ✓ 774
  - `raw/cap_hits.csv` ✓ 774 (653 ok, 121 low/missing — within expected, flagged downstream)
  - `raw/instagram_followers.csv` ✓ 774 (0 follower counts — Meta 403, pre-declared NULL, sentinel renorm)
  - **`raw/trends.csv` FAILED (rc=1):** DNS `getaddrinfo failed` resolving `trends.google.com` at
    `TrendReq()` construction (fetch_trends.py:43) — that call is OUTSIDE the per-player try/except, so
    the script died before writing anything. The on-disk file was the STALE 160-old-ID copy
    (fetch_date 2026-05-28, player_id 1 = "Cutter Gauthier" under old IDs) → a mis-join landmine.
    **DELETED it** so it can't poison the compute join. Trends worked fine on 2026-05-28, so today's
    failure is transient/host-specific DNS, not a permanent block.

STATUS: blocked

BLOCKER:
1. **Reddit OAuth** — `pilot2/.env` keys still BLANK (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`).
   Reddit = 0.417 of engagement weight (mentions 0.250 + upvotes 0.167); required for a real headline.
   Register a free *script* app at https://www.reddit.com/prefs/apps (redirect `http://localhost:8080`),
   fill the two id/secret keys (`client_credentials` app-only grant needs just those).
2. **trends.csv missing** (stale copy deleted). Must exist as a 774-keyed file before compute. Only
   13.9% weight and sentinel-renorms if NULL, so low priority — but cannot be the stale 160 file.

NEXT (exact order; steps 2-4 need OAuth, step 1 does not):
1. **Re-fetch trends:** `python pilot2/fetch_trends.py` (background, `dangerouslyDisableSandbox: true`,
   ~26 min). If DNS resolves it writes 774 rows (mostly NULL is fine). If it crashes at construction
   again (rc=1, no file written), generate a 774-row NULL placeholder instead: load_players() +
   atomic_write_csv with `trends_12mo=""`, `n_weeks=0`, `query=full_name`, today's fetch_date, schema
   `[player_id, full_name, query, trends_12mo, n_weeks, fetch_date]`. Verify 774 rows + 2026-06-xx date.
2. (When creds land) fill `.env`, confirm reddit CSVs still purged, `python pilot2/fetch_reddit.py`
   (~45-90 min OAuth, resume-safe, snapshot-writes per player).
3. `python pilot2/compute_oaq.py` → `oaq_pilot.csv` + `results.{md,json}` on full-league data.
4. **Re-confirm V1/V2/V3 on the 774 pool** vs unchanged §9/A6 floors (A10 re-confirmation obligation —
   re-rolling the set re-rolls every gate; report any direction honestly).
5. Refresh abstract/methods numbers (160→774) + re-render `abstract_final.pdf` + `methods_final.pdf`
   (pandoc 3.9 → HTML → headless Chrome `--no-sandbox` print-to-pdf to $TEMP then mv).
6. **Cleanup:** delete `pilot2/_pool_gp_diag.py` + `pilot2/_reddit_reuse.py` (obsolete temp). KEEP
   `filter_pool_played.py` (reproducible A10 transform) and `pool_gp_audit.csv` (788 audit trail).

Working-tree state (uncommitted — on `main`; branch before any commit):
- `players.csv` = 774 (was committed 788 @ HEAD e79b7ce).
- Fresh 774-keyed (regenerated this session): `raw/nhl_skill.csv`, `raw/wiki_pageviews.csv`,
  `raw/wiki_daily.csv`, `raw/cap_hits.csv`, `raw/instagram_followers.csv`, `external_outcomes.csv`.
- DELETED: `raw/trends.csv` (stale 160), `raw/reddit_counts.csv` + `raw/reddit_detail.csv` (purged).
- Edited earlier (still uncommitted): `compute_oaq.py` (small_sample), `pilot2/preregistration.md`,
  `methods.md`, `docs/preregistration.md` (all A10).
- New (keep): `filter_pool_played.py`, `pool_gp_audit.csv`. Temp to delete at step 6: `_pool_gp_diag.py`,
  `_reddit_reuse.py`. Logs: `raw/_chain.log`, `raw/_reddit*.log`.
- `team_outcomes.csv` + `market_proxy.csv` present, TEAM-keyed (stable, no rebuild).

Technical carry-forward (still valid):
- players.csv schema: `group` MUST stay f1=F / d1=D (compute_oaq peer-split key); `player_id` 1..774 contiguous.
- **Reddit:** anonymous is IP-blocked at Fastly (sticky 403); OAuth via `oauth.reddit.com` + bearer is
  the ONLY path. `fetch_reddit.py` validates creds up front (zero contact without creds). ALWAYS purge
  reddit_counts/detail when the set changes (already purged for 774).
- **Monitor pitfall:** never `open()` reddit_counts.csv while `fetch_reddit.py` runs (races atomic
  `os.replace` → PermissionError WinError 5). Watch the task `.output`, not the CSV.
- **Background buffering:** python stdout redirected to a file is block-buffered → per-player lines lag.
  Don't read an empty log as a stall; check the END markers / rc in `raw/_chain.log`.
- Scrapes share one sqlite `cache/http_cache`; ran them SEQUENTIALLY to avoid lock contention. Network
  background fetches need `dangerouslyDisableSandbox: true`.
- compute_oaq deterministic (seed 20260526, 1000 bootstrap draws). `_common.py` forces UTF-8; Windows
  console is cp1252 (NO non-ASCII in ad-hoc `python -c`). `fetch_*.py` all read load_players() fresh and
  full-overwrite via atomic_write_csv (no resume state) → safe to re-run after a re-lock.
- Render toolchain: pandoc 3.9.0.1 + Chrome `C:\Program Files\Google\Chrome\Application\chrome.exe`.

Deadline: abstract DONE (accepted for poster). Next real date: **poster session 2026-09-12** — ample
runway. Roster snapshot locked 2026-06-17; no remaining live perishability.
