# Design Spec — Skill-Vector Expansion (Amendment A13)

**Project:** The Marchand Index (NHL off-ice fan-attention model)
**Date:** 2026-06-20
**Status:** Approved design, pre-implementation
**Pre-registration:** continues the chain in `preregistration.md` (A1–A11, with A12 = ingestion committing first). This is **A13 (peer/skill vector)**.
**Target home:** the real project tree `Marchand Index/` (method ported from `pilot2/`).

---

## 1. Purpose

The locked peer-matching vector is three box-score stats — `(age, PPG, TOI/G)`. None measures on-ice play-driving, so "OAQ is skill-controlled" actually controls only for *deployment and scoring*, not for *how the team plays with the player on the ice*. Against a stats-literate audience that overstates the control. This amendment adds the three most-cited public on-ice metrics so the residual is matched against a defensible skill profile, making the "skill-controlled" claim honest (criterion 1 + criterion 6).

## 2. Locked decisions

| Decision | Value |
|---|---|
| New features | `cf_pct`, `xgf_pct`, `ozs_pct` — added to `(age, PPG, TOI/G)` → 6-dim vector |
| Source | MoneyPuck free public season-summary skater CSV |
| Situation | **5v5** (even-strength play-driving; `all` re-imports special-teams confound) |
| QoC | **Skipped** — no MoneyPuck column; within-NHL opponent spread is small vs college/junior; `ozs_pct` is the deployment partial-control; gap disclosed on poster |
| `expected_cap` (A4) | **Unchanged** — cap market prices points+TOI, not Corsi; keeps changes orthogonal |
| Thin-sample | `< 150 min` 5v5 ice → NULL the three on-ice features, impute to peer-group neutral; **never drop the player** |
| V3 re-roll | **Accepted** — re-rolling skill re-rolls every gate; V3 (0.391 on latest set) may stay/fall below 0.40, reported honestly |
| Credit | MoneyPuck credited on poster (its non-commercial terms) |

## 3. Source (verified live 2026-06-20)

| Item | Value |
|---|---|
| URL pattern | `https://moneypuck.com/moneypuck/playerData/seasonSummary/{START_YEAR}/regular/skaters.csv` |
| This season | `START_YEAR = 2025` (2025-26 regular season) |
| Player id | `playerId` = **NHL playerId** (verified: Larkin = 8477946) → clean join, no name-matching |
| Situation split | rows stratified by `situation ∈ {all, 5on5, 5on4, 4on5, other}` — must filter |
| Corsi share | `onIce_corsiPercentage` (on-ice shot-attempt share, 0–1) |
| xG share | `onIce_xGoalsPercentage` (on-ice expected-goals share, 0–1) |
| Zone starts | raw counts `I_F_oZoneShiftStarts`, `I_F_dZoneShiftStarts`, `I_F_neutralZoneShiftStarts` — **no pre-computed OZS%; derive** |
| QoC | **none** (no opponent-quality column exists) |
| License | free non-commercial, credit required |

## 4. Features

New 6-dim peer vector: `(age, PPG, TOI/G, cf_pct, xgf_pct, ozs_pct)`, all from the **5v5** row:

- `cf_pct = onIce_corsiPercentage` — territorial play-driving.
- `xgf_pct = onIce_xGoalsPercentage` — shot-quality-weighted play-driving (corrects Corsi's volume bias).
- `ozs_pct = oZoneShiftStarts / (oZoneShiftStarts + dZoneShiftStarts)` — offensive-zone-start share (neutral starts excluded, standard convention). Deployment/usage context: lets Mahalanobis distinguish a sheltered 55% CF% from a tough-minutes 55%, and is the cheap partial substitute for the skipped QoC.

**5v5 is the locked situation** (not a default): `all`-situations on-ice shares are contaminated by special-teams deployment (a PP specialist posts inflated on-ice xGF% reflecting the power play, not the player). Even-strength is the apples-to-apples standard.

**Not added (anti-scope-creep):** per-60 rates, danger tiers, rebound xG, score/flurry-adjusted variants, `gameScore` — collinear with the chosen three, bloat the distance space, invite a cherry-pick attack. Three is the honest minimum that fixes the claim.

## 5. Join

**Key:** `nhl_player_id` (players.csv) ↔ MoneyPuck `playerId` (identical NHL id space). Normalized-name fallback only where `nhl_player_id` is blank (`match_quality=low` players), logged.

**Order — filter then aggregate (locked):**
1. Load `skaters.csv`, **filter `situation == '5on5'`** first.
2. **Trade aggregation** — a traded player has one 5v5 row per team and no aggregate row; collapse to one row per `playerId`:
   - `cf_pct`, `xgf_pct` → **icetime-weighted mean** across the player's team-rows (weight = row `icetime`; a simple mean would over-weight a 3-game stint).
   - `ozs_pct` → recompute from **summed** `oZoneShiftStarts` and `dZoneShiftStarts` (sum counts, then divide — correct for a ratio).
3. **Left-join** onto the 774 `players.csv` on `nhl_player_id`. No MoneyPuck row → NULL features → existing group-mean imputation; flag `onice_status=missing`.
4. Assert one row per `playerId` after aggregation; on a surviving duplicate keep max-`icetime` row and log.

**Output — `raw/nhl_onice.csv`:** `player_id, nhl_player_id, full_name, team_code, situation (='5on5'), cf_pct, xgf_pct, ozs_pct, mp_icetime_5v5, mp_games_played_5v5, n_team_rows (≥2 ⇒ trade-aggregated), onice_status (ok|thin|missing), fetch_date`. Atomic write.

**Fetcher — `fetch_moneypuck.py`:** one cached HTTP GET of the season CSV; filter/aggregate/join; write. `compute_oaq.py` `load_inputs()` gains one merge; `SKILL_COLS` gains the three names.

## 6. Thin-sample handling

Rate stats are unstable at low ice (a 5-game callup can post 65% CF% on noise). The existing `small_sample` (<20 GP, A10) flag is row-level/display; this needs a feature-level handler:

- `ONICE_MIN_ICETIME_5V5 = 150` minutes 5v5 (locked here, before any re-run).
- Below the floor → `cf_pct/xgf_pct/ozs_pct = NULL`, `onice_status=thin`. The existing group-mean imputation in `_standardize_skill` then fills them with the position-group mean **before** standardizing, so the player is matched on his stable box-score stats and the on-ice axes contribute nothing for him.
- Never drop the player (preserves the A10 non-exclusionary 774 pool). `small_sample` GP flag unchanged (complementary, not redundant).

Rationale: keeping a raw thin rate would feed noise into the Mahalanobis distance and corrupt the peer set (opposite of the goal); NULL-the-player would violate the pool lock. NULL-feature + impute-neutral is the only option consistent with both.

## 7. Mahalanobis implications

- **Collinearity** (CF% ↔ xGF% ~0.7–0.8, both ↔ PPG): handled automatically by the within-group **inverse-covariance** weighting — the original reason §6 chose Mahalanobis over Euclidean. Adding correlated features is *safe*; they don't double-count as skill distance. No PCA/de-correlation needed.
- **Dimensionality:** 6 features, K=10, pools 497 F / 277 D. Covariance estimation needs n ≫ p; 277 ≫ 6 (rule-of-thumb floor ~60) is comfortable — strictly better than the A7 160-set this method already ran on. `np.linalg.pinv` already guards singularity.
- **Standardization:** unchanged — within position group, ddof=1, group-mean imputation for NULLs before standardizing. 0–1 scale vs PPG/TOI is irrelevant post-z-score.

## 8. `expected_cap` (A4) — unchanged

The new features are **not** added to the §8/A4 `cap_hit_M ~ PPG + TOI/G` regression. That is a market-price proxy (the cap market prices points and ice-time; GMs do not pay a direct premium for CF%); adding on-ice features would add noise and weaken a deliberately parsimonious proxy. Keeping the two amendments orthogonal (A12 touches composite, A13 touches only §6 peer features) preserves attribution. Age stays excluded from `expected_cap` per A4.

## 9. Amendment A13 text (to commit before any re-compute)

> **A13 (2026-06-XX) — §6 peer (skill) vector: add MoneyPuck 5v5 on-ice play-driving + deployment features (CF%, xGF%, O-zone-start%) to `(age, PPG, TOI/G)`. Logged BEFORE any re-compute on the augmented vector.**
>
> Motivation: §6's peer vector measured only deployment and scoring, so the "skill-controlled" claim controlled nothing about on-ice play-driving. The three most-cited public on-ice control metrics are added so the OAQ residual is matched against a defensible skill profile.
>
> New peer vector (all 774): `(age, PPG, TOI/G, cf_pct, xgf_pct, ozs_pct)` from MoneyPuck's free season-summary skater CSV (2025-26 regular), filtered `situation=='5on5'`: `cf_pct=onIce_corsiPercentage`, `xgf_pct=onIce_xGoalsPercentage`, `ozs_pct=oZoneShiftStarts/(oZoneShiftStarts+dZoneShiftStarts)`. **5v5 is the locked situation** (even-strength; all-situations re-imports special-teams confound). **QoC deliberately excluded:** MoneyPuck exposes no QoC column, within-NHL opponent spread is small versus junior/college, and `ozs_pct` provides the deployment partial-control; the QoC gap is disclosed on the poster.
>
> Source/join: key `nhl_player_id` ↔ MoneyPuck `playerId` (identical NHL id space); name-fallback only where the id is blank. Traded players (one 5v5 row per team, no aggregate row) collapsed by icetime-weighted mean (cf_pct, xgf_pct) and summed-count ratio (ozs_pct). Written to `raw/nhl_onice.csv`. MoneyPuck credited per its non-commercial terms.
>
> Thin-sample: skaters below `ONICE_MIN_ICETIME_5V5 = 150` min 5v5 have the three on-ice features NULLed (`onice_status=thin`); existing §6 group-mean imputation fills them to position-group neutral before standardizing, so they are matched on stable box-score stats. No player dropped (A10 pool preserved). The descriptive `small_sample` (<20 GP) flag is unchanged.
>
> Distance unchanged: K=10, within-group standardization (ddof=1), within-group inverse-covariance (Mahalanobis); only the column list grows 3→6. Collinearity among PPG/CF%/xGF% is handled by inverse-covariance weighting; covariance is stable at 497 F / 277 D ≫ 6 dims.
>
> `expected_cap` (A4) unchanged — on-ice features deliberately NOT added to the `cap_hit_M ~ PPG + TOI/G` market-price regression; age remains excluded.
>
> **Re-confirmation obligation (disclosed in advance):** the peer vector enters OAQ_observed, OAQ_portable, all Marchand Index lenses, and every validation gate. Re-rolling the peer features re-rolls every validation pathway — V1a/V1b, V2, V3/PD are all re-reported regardless of direction against the unchanged §9/A6 floors; any fall below floor is an honest disconfirmation, not a quiet drop. PC recomputed off the new peer sets. Pre-amendment 3-feature vector and downstream numbers retained in git history (§13).
>
> **Anti-tuning (§13):** decided on construct-validity grounds, logged before any re-compute; features, situation (5v5), OZS% formula, and the 150-min floor are mechanical and fixed in advance, not chosen by effect on any player's rank; composite weights (§4/A12), market-proxy (§7), λ (A5), denominators (A4/A8), OAuth (A9), the A10 pool, and all validation floors (§9, A6) unchanged.

## 10. Risks

1. **Trade-row structure (highest):** if the real 2025-26 file deviates from one-row-per-team, the join mis-aggregates. Fetcher must branch on `groupby(['playerId','situation']).size()` empirically, not trust assumptions.
2. **Coverage gaps:** deep callups / no-id players → NULL features → impute; report the count (`onice_status=missing`) in `results.md`.
3. **V3/PD re-roll (real):** richer skill matching changes the residual and could move V3 below 0.40. Accepted and reported as a sensitivity finding, not hidden.
4. **MoneyPuck availability/format drift:** single external dependency. Cache the CSV in `raw/`, pin column names in the amendment, fail loud if a required column is absent.
5. **xG opacity:** xGF% is MoneyPuck's proprietary model. Credit + one-line poster disclosure that it is model-derived.
6. **Scale/parse traps:** percentages are 0–1 (no double-z, no ×100); OZS% for traded players must use summed counts, not averaged ratios. Pinned in the amendment.
