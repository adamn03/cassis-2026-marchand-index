# Session Handoff
Date: 2026-05-27
Active: NHL_Marchand_Index — **pilot2** (160-skater Tier-1 pilot) for the CASSIS abstract.

LAST: Phase 3 compute is DONE and ran clean on full data. Reddit re-fetched with a hardened, resumable fetcher → 160/160 (155 ok, 5 partial, 0 null). Roster validation passed (159/160, 0 real mismatches; Benning the expected blank). Built `pilot2/compute_oaq.py` (faithful to locked §4/6/7/8/9/10/11; patched in the §8 `match_quality` flag). Ran it: **PC confirmed** (8 of top-10 by engagement_raw displaced under MI), externals **underpowered as expected** (V1a n=4, V1b 8/160, V2 4/160). THEN discovered + diagnosed a real artifact and designed the fix (see ROOKIE FIX).

STATUS: working. Data + compute complete; ONE locked-method amendment (A4) decided + logged, NOT yet implemented.

BLOCKER: none. Decision is made; next session implements A4, re-runs, then Phase 4.

NEXT (in order):
1. **Implement amendment A4 (expected-cap denominator)** in `pilot2/compute_oaq.py`. Spec below. Re-run `python pilot2/compute_oaq.py`, re-verify PC still confirmed, sanity-check the new MI top-10 (should be an age mix, not 9/10 ELC).
2. **Settle two OPEN reporting decisions** (owner, see OPEN DECISIONS) — needed before writing the abstract.
3. **Build Phase 4**: `pilot2/render_figure.py` (Panel A only — Panel B omitted, externals underpowered), rewrite `abstract_v1.md` §2/§3/§4, reconcile `methods.md`, re-render `abstract_final.pdf`.

---

## ROOKIE FIX — the headline issue this session (amendment A4, logged, not yet built)

**Problem:** `marchand_index = OAQ_portable / cap_hit_M` (locked §8) is dominated by entry-level contracts. MI top-10 was **9/10 ELC, median age 21** (Celebrini, Will Smith, Fantilli, Parekh...). Cause: ELC cap is a **CBA-imposed constant (~$0.95M), not a market price**, so `1/cap` explodes for anyone cheap. Peer matching does NOT fix this — it controls skill on the *attention* (OAQ) side, never touches the cap denominator. Owner confirmed this was an a-priori-obvious construction oversight.

**Fix (DECIDED): replace actual cap with skill-EXPECTED (market-rate) cap in the denominator.**
- `expected_cap(P)` = predicted market cap from a **`cap ~ production` regression**, fit **within position** (F and D separately), predictors **PPG + TOI per game** (age **excluded** — including it re-imports the rookie-scale via young/cheap peers), prediction **floored at league min $0.775M**.
- `marchand_index` (new headline) = `OAQ_portable / expected_cap`.
- **Retain** the original raw-cap value as `marchand_index_rawcap` (the §8-original) for audit + as the secondary "current-season bargain" lens.
- Does NOT alter §4 weights, §6 peers / OAQ, §7 market proxy, or §9 floors.

**Why it works (verified empirically this session):**
- A `±5-year age band` was tested and REJECTED — it *lowers* a rookie's expected_cap and *re-inflates* MI (Celebrini 0.76 → 0.96). The age-blind regression is correct.
- Regression de-skews: Celebrini MI 4.54 → 0.48 (expected_cap $9.24M), Crosby 0.43 → 0.53 (now correctly ABOVE marginal rookies), Fantilli 0.72 → 0.12.
- For players already on market deals, raw ≈ expected (McDavid 0.14→0.16, Crosby 0.43→0.53) so MI barely moves; divergence is concentrated in ELCs. **So expected-cap MI ≈ what a rookie's raw-cap MI BECOMES post-extension** — it pre-prices the next contract instead of rewarding the temporary CBA discount. This is the strong defensible line for the abstract.
- Bonus: under the regression the all-rookie wall breaks (top-10 becomes an age mix incl. Crosby 38, Orlov 34, DeMelo 33) and what remains at the top is genuine attention-surplus incl. depth players — which is the ORIGINAL Reaves/Marchand thesis ("engagement out of proportion to skill"), not a bug.
- Residual (disclose, don't fix): low-PRODUCTION players also get small expected_cap, so a depth guy with modest surplus can rank high. That's efficiency / on-thesis, a deliberate choice.

**Anti-tuning note:** A4 is logged in `preregistration.md` §14 BEFORE the re-run, motivated by a known structural artifact (not a specific player's rank), originals retained. Compliant with §13.

---

## OPEN DECISIONS (owner — settle before writing the abstract)
1. **Pilot headline framing.** Options surfaced (not yet chosen): (a) PC reordering "adjustment displaces 8/10" as the mechanism demo + honest limits [matches locked plan]; (b) embrace "cheapest attention" angle; (c) lead with OAQ_portable. Leaning (a). With A4, the reordering story is cleaner.
2. **Dual-lens reporting.** Report BOTH MI lenses? raw-cap = "current-season bargain" (rookies legitimately win), expected-cap = "intrinsic / timing-independent efficiency" (headline). Mirrors the existing OAQ_observed/OAQ_portable dual lens. Leaning yes.
3. **Market-clustering disclosure.** OAQ_portable top ranks cluster small-market (5 SJS, 4 WPG) — the standardized `market_z` subtraction is a strong effect. Plan: disclose as an honest-limit (criterion 6), keep locked method, no re-run. (Owner has not objected.)

---

## Phase 3 results as they stand NOW (pre-A4) — pilot2/results.md, oaq_pilot.csv, results.json
- N=160 (96 F / 64 D). Market components used: metro_population + arena_attendance (team IG dropped, 403). Reddit 160/160 non-NULL. Dropped components: instagram_followers ×160 (all), trends ×11. match_quality=low ×1, cap_quality=low ×1 (both Benning).
- **PC: confirmed** — displaced from top-10 by MI: Crosby, McDavid, Q.Hughes, Ovechkin, M.Tkachuk, Suzuki, Bedard, Draisaitl.
- **PA: inconclusive (underpowered)** — V1a Spearman rho=0.80, n=4. **PB: inconclusive (underpowered)** — V2 AUC=0.53 (membership-only, 4). **V1b** AUC=0.66, 8/160, underpowered.
- These numbers will CHANGE for MI/leaderboards after A4 (OAQ_portable + externals are unaffected; only the cap denominator changes).

## What's on disk (pilot2/)
- `compute_oaq.py` DONE (faithful; needs A4 edit). `oaq_pilot.csv`, `results.md`, `results.json` (pre-A4). `roster_validation.md` (159/160 ok).
- `raw/`: reddit_counts.csv + reddit_detail.csv (50,496 detail rows) NOW COMPLETE; wiki_pageviews/wiki_daily/trends/instagram/cap_hits/nhl_skill all done. `market_proxy.csv` (32, attendance not live-verified — see prior note), `external_outcomes.csv` (160, underpowered).
- v1 `pilot/` untouched/preserved. Abstract can still ship with the v1 figure if pilot2 stalls.

## Technical carry-forward
- Reddit fetcher is now **resumable** (snapshots both CSVs per player; re-fetches only null/missing on restart) with escalating 429 backoff. This fixed the prior detached-`&`/throttle failure.
- Bash tool = Git Bash. `_common.py` forces UTF-8. Background `&` detaches (no notification) — use run_in_background=true alone.
- requests_cache sqlite in `pilot2/cache/` (gitignored). reddit = plain session (no cache).
- compute bootstrap: 1000 draws, seed 20260526, resamples wiki_daily + reddit_detail; ~couple min runtime.
- PDF re-render: pandoc → HTML → headless Chrome print-to-pdf (Chrome at `/c/Program Files/Google/Chrome/Application/chrome.exe`, --no-sandbox, render to $TEMP then mv).

## Deadline
**May 31, 2026** (4 days). Owner-only: email `abstract_final.pdf` to `cascadia-sports@sfu.ca`.
