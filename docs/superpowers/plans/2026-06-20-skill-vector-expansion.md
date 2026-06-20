# Skill-Vector Expansion (A13) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Expand The Marchand Index peer-matching skill vector from the 3 box-score features `(age, ppg, toi_per_game)` to a 6-feature vector adding three MoneyPuck 5v5 on-ice play-driving / deployment metrics — `cf_pct`, `xgf_pct`, `ozs_pct` — so the "skill-controlled" residual claim is honest against a stats-literate audience, all under Amendment A13. The `expected_cap` (A4) market-price regression is deliberately left unchanged.

**Architecture:** A new network fetcher (`fetch_moneypuck.py`) downloads MoneyPuck's free season-summary skater CSV once (cached in `raw/`), filters to `situation == '5on5'`, derives the three features (with `ozs_pct` computed from raw zone-start counts), collapses traded players (one 5v5 row per team, no aggregate row) by icetime-weighted mean for the two rate features and summed-count ratio for `ozs_pct`, applies a 150-minute 5v5 thin floor (NULL the features + `onice_status=thin`), left-joins onto the 774-player pool on `nhl_player_id` == MoneyPuck `playerId`, and writes `raw/nhl_onice.csv`. `compute_oaq.py` then gains the three columns in `SKILL_COLS`, one merge in `load_inputs`, and relies on the existing `_standardize_skill` group-mean NULL imputation to fill thin/missing players to position-group neutral before standardizing. The K=10 within-group Mahalanobis distance (inverse covariance) is unchanged; only the column list grows 3->6. `compute_expected_cap` is untouched.

**Tech Stack:** Python 3, `requests_cache`, `numpy`, `pandas`, `pytest`. Local Windows + SQLite cache. No new dependencies.

**Pending migration note (NOT part of this plan):** the directory rename `pilot2/` -> `Marchand Index/` is a SEPARATE pending migration. This plan builds entirely into the existing `pilot2/` tree where `_common.py` and `compute_oaq.py` live. Do not rename anything here.

**Co-modification warning (shared-file sequencing):** A sibling ingestion amendment (**A12**, already written to `docs/superpowers/plans/2026-06-20-ingestion-expansion.md`) also edits `pilot2/compute_oaq.py` and `pilot2/preregistration.md`, and **A12 commits its shared-file edits BEFORE A13 starts.** Before executing A13, `git pull`/rebase onto the committed A12 edits. The two amendments touch DIFFERENT regions of `compute_oaq.py`:
> - **A12 owns:** the `WEIGHTS` composite dict + `engagement_from_components`/`bootstrap_player_cis` component dict + the instagram->wiki_intl swap + the `wiki_intl` merge in `load_inputs` + `OUT_COLS` (composite region).
> - **A13 owns:** the `SKILL_COLS` list, `_standardize_skill` (no change needed — it iterates `SKILL_COLS`), the `nhl_onice.csv` merge in `load_inputs`, and the skill columns in `OUT_COLS` (peer region).
>
> They collide only at (a) the `load_inputs` merge block and (b) `OUT_COLS`. After rebasing on A12, the A13 merge is inserted near the OTHER skill merge (`df.merge(skill[...])`), and the three skill columns are added next to `age, ppg, toi_per_game` in `OUT_COLS` — both distinct from A12's wiki_intl region. Keep every A13 edit localized to the peer region.

## Global Constraints

- $0 budget, free public data only.
- Local Windows + Python + SQLite.
- Atomic `.tmp`->rename writes via `_common.atomic_write_csv`.
- MoneyPuck credited on poster (non-commercial license).
- Situation locked = 5v5.
- Thin floor = 150 min 5v5.
- Join key = nhl_player_id.
- Trade aggregation = icetime-weighted mean (rates) + summed-count ratio (ozs).
- 774-skater non-exclusionary pool (never drop a player — NULL+impute).
- Anti-tuning (features/situation/floor fixed before any re-compute, original 3-feature vector retained, not chosen by effect on any rank).
- UTF-8 forced (Windows cp1252 console).

---

## File Structure

| File | Create/Modify | Responsibility |
|---|---|---|
| `pilot2/tests/__init__.py` | Create (if absent) | Marks `tests` a package. NOTE: created by sibling A12 plan Task 1; if A13 rebases AFTER A12, this file already exists — skip creation, do not overwrite. |
| `pilot2/fetch_moneypuck.py` | Create | Download MoneyPuck season-summary skaters CSV (cached in `raw/`); filter 5v5; derive cf_pct/xgf_pct/ozs_pct; icetime-weighted trade aggregation; 150-min thin floor; left-join onto 774 pool on nhl_player_id; write `raw/nhl_onice.csv`. |
| `pilot2/raw/moneypuck_skaters_2025.csv` | Output (cache) | Raw MoneyPuck download cached in `raw/` (re-runs free). |
| `pilot2/raw/nhl_onice.csv` | Output | Per-player 5v5 on-ice features + onice_status (spec §5 schema). |
| `pilot2/compute_oaq.py` | Modify (peer region) | Add cf_pct/xgf_pct/ozs_pct to `SKILL_COLS`; merge `raw/nhl_onice.csv` in `load_inputs`; add the three columns to `OUT_COLS`. `_standardize_skill`/`compute_peers`/`compute_expected_cap` unchanged in body. |
| `pilot2/preregistration.md` | Modify (append only) | Append the verbatim A13 amendment text (spec §9) after the A12 block. |
| `pilot2/tests/test_fetch_moneypuck.py` | Create | Unit tests for fetcher pure logic (5v5 filter, ozs formula, trade aggregation, thin floor, join), mocked download. |
| `pilot2/tests/test_compute_oaq_skill.py` | Create | Unit tests for SKILL_COLS expansion, standardization-with-NULL-imputation over 6 dims, expected_cap unchanged, prereg A13 text. |

**Test location convention:** the project has NO existing `pytest.ini`/`pyproject.toml` and `pilot2/tests/` does not exist in the pre-A12 tree. The sibling A12 plan creates `pilot2/tests/__init__.py`. Because A13 rebases on A12, that file should already be present; Task 1 below creates it ONLY if absent (idempotent). Tests run with the repo root as CWD; each test file does `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` to import `fetch_moneypuck` / `compute_oaq` directly (mirroring how `compute_oaq.py`, `fetch_nhl_api.py`, and the A12 test files do `sys.path.insert`).

---

## Task 1: Scaffold test package + MoneyPuck fetcher constants

**Files:**
- Create (if absent): `pilot2/tests/__init__.py` (empty)
- Create: `pilot2/fetch_moneypuck.py` (constants + header only this task)
- Test: `pilot2/tests/test_fetch_moneypuck.py`

**Interfaces:**
- Consumes: nothing (constants only).
- Produces (in `fetch_moneypuck.py`):
  - `MP_URL: str` == `"https://moneypuck.com/moneypuck/playerData/seasonSummary/2025/regular/skaters.csv"`
  - `START_YEAR: str` == `"2025"`
  - `LOCKED_SITUATION: str` == `"5on5"`
  - `ONICE_MIN_ICETIME_5V5: int` == `150` (minutes 5v5; locked before any re-run)
  - `CACHE_CSV: pathlib.Path` == `RAW_DIR / "moneypuck_skaters_2025.csv"`
  - `OUT_CSV: pathlib.Path` == `RAW_DIR / "nhl_onice.csv"`
  - `OUT_FIELDS: list[str]` == the spec §5 schema (exact list below)

Steps:

- [ ] (1) Write the failing test. Create `pilot2/tests/__init__.py` if it does not already exist (it is created by the sibling A12 plan; do NOT overwrite if present). Then create `pilot2/tests/test_fetch_moneypuck.py`:

```python
"""Unit tests for fetch_moneypuck pure logic (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pilot2/
import fetch_moneypuck as fmp  # noqa: E402


def test_url_and_locked_constants():
    assert fmp.MP_URL == (
        "https://moneypuck.com/moneypuck/playerData/seasonSummary/"
        "2025/regular/skaters.csv"
    )
    assert fmp.START_YEAR == "2025"
    assert fmp.LOCKED_SITUATION == "5on5"
    assert fmp.ONICE_MIN_ICETIME_5V5 == 150


def test_out_fields_match_spec_schema():
    assert fmp.OUT_FIELDS == [
        "player_id", "nhl_player_id", "full_name", "team_code", "situation",
        "cf_pct", "xgf_pct", "ozs_pct", "mp_icetime_5v5",
        "mp_games_played_5v5", "n_team_rows", "onice_status", "fetch_date",
    ]
```

- [ ] (2) Run it (expected FAIL — module does not exist):

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py::test_url_and_locked_constants -v
```

Expected: `ModuleNotFoundError: No module named 'fetch_moneypuck'` (collection error / FAIL).

- [ ] (3) Minimal implementation. Create `pilot2/fetch_moneypuck.py`:

```python
"""Fetch MoneyPuck 5v5 on-ice play-driving features for the 774 pool (A13).

Adds three on-ice features to the §6 peer (skill) vector:
  cf_pct  = onIce_corsiPercentage   (5v5 territorial play-driving share, 0-1)
  xgf_pct = onIce_xGoalsPercentage  (5v5 shot-quality-weighted share, 0-1)
  ozs_pct = I_F_oZoneShiftStarts / (I_F_oZoneShiftStarts + I_F_dZoneShiftStarts)
            (offensive-zone-start share; neutral starts excluded, standard
            convention)

Source: MoneyPuck free season-summary skater CSV (2025-26 regular season),
downloaded once and cached in raw/. The CSV is stratified by `situation` in
{all, 5on5, 5on4, 4on5, other}; A13 LOCKS situation == '5on5' (even-strength;
all-situations re-imports the special-teams confound). Join key is
`nhl_player_id` (players.csv) == MoneyPuck `playerId` (identical NHL id space);
name-fallback only where nhl_player_id is blank.

Traded players have ONE 5v5 row per team and NO aggregate row, so rows are
collapsed per playerId by icetime-weighted mean (cf_pct, xgf_pct) and
summed-count ratio (ozs_pct). Skaters below ONICE_MIN_ICETIME_5V5 = 150 min
5v5 have the three features NULLed (onice_status=thin); compute_oaq.py's
existing group-mean imputation fills them to position-group neutral before
standardizing. No player is ever dropped (A10 774-pool preserved). MoneyPuck
credited on the poster per its non-commercial terms.

Writes:
  pilot2/raw/moneypuck_skaters_2025.csv   raw download cache
  pilot2/raw/nhl_onice.csv                774 rows, schema = OUT_FIELDS
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONTACT_UA, RAW_DIR, atomic_write_csv, load_players, session  # noqa: E402

START_YEAR = "2025"  # pre-reg locks the 2025-26 regular season
MP_URL = (
    "https://moneypuck.com/moneypuck/playerData/seasonSummary/"
    f"{START_YEAR}/regular/skaters.csv"
)
LOCKED_SITUATION = "5on5"            # A13 locked situation (NOT a default)
ONICE_MIN_ICETIME_5V5 = 150         # minutes 5v5 thin floor (locked, A13)

CACHE_CSV = RAW_DIR / "moneypuck_skaters_2025.csv"
OUT_CSV = RAW_DIR / "nhl_onice.csv"

OUT_FIELDS = [
    "player_id", "nhl_player_id", "full_name", "team_code", "situation",
    "cf_pct", "xgf_pct", "ozs_pct", "mp_icetime_5v5",
    "mp_games_played_5v5", "n_team_rows", "onice_status", "fetch_date",
]
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py -v
```

Expected: 2 passed.

- [ ] (5) Commit:

```
git add pilot2/tests/__init__.py pilot2/tests/test_fetch_moneypuck.py pilot2/fetch_moneypuck.py
git commit -m "pilot2: A13 scaffold moneypuck fetcher (locked constants + 5v5 + 150-min floor) + spec schema"
```

---

## Task 2: 5v5 filter + ozs_pct formula on a single row

**Files:**
- Modify: `pilot2/fetch_moneypuck.py`
- Test: `pilot2/tests/test_fetch_moneypuck.py`

**Interfaces:**
- Consumes: a raw MoneyPuck DataFrame with columns `playerId`, `name`, `team`, `situation`, `icetime`, `games_played`, `onIce_corsiPercentage`, `onIce_xGoalsPercentage`, `I_F_oZoneShiftStarts`, `I_F_dZoneShiftStarts`.
- Produces:
  - `filter_5v5(raw: pd.DataFrame) -> pd.DataFrame` — returns ONLY `situation == '5on5'` rows, coercing the six numeric columns with `pd.to_numeric(errors="coerce")`. Keeps `playerId`, `name`, `team`, `icetime`, `games_played`, `cf_pct` (= `onIce_corsiPercentage`), `xgf_pct` (= `onIce_xGoalsPercentage`), `ozs_raw` (= `I_F_oZoneShiftStarts`), `dzs_raw` (= `I_F_dZoneShiftStarts`).
  - `ozs_pct(ozs: float, dzs: float) -> float` — `ozs / (ozs + dzs)`; returns `float("nan")` when `ozs + dzs == 0` or either is NaN.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_fetch_moneypuck.py`:

```python
import numpy as np
import pandas as pd


def _raw_row(pid, sit, ct=0.0, xt=0.0, ozs=0.0, dzs=0.0, ice=1000.0, gp=10,
             name="X", team="BOS"):
    return {
        "playerId": pid, "name": name, "team": team, "situation": sit,
        "icetime": ice, "games_played": gp,
        "onIce_corsiPercentage": ct, "onIce_xGoalsPercentage": xt,
        "I_F_oZoneShiftStarts": ozs, "I_F_dZoneShiftStarts": dzs,
    }


def test_filter_5v5_keeps_only_5on5_and_renames():
    raw = pd.DataFrame([
        _raw_row(1, "all", ct=0.9),
        _raw_row(1, "5on5", ct=0.55, xt=0.52, ozs=120, dzs=80),
        _raw_row(1, "5on4", ct=0.99),
        _raw_row(2, "5on5", ct=0.48),
    ])
    out = fmp.filter_5v5(raw)
    assert set(out["situation"]) == {"5on5"}
    assert len(out) == 2
    r = out[out["playerId"] == 1].iloc[0]
    assert r["cf_pct"] == 0.55 and r["xgf_pct"] == 0.52
    assert r["ozs_raw"] == 120 and r["dzs_raw"] == 80


def test_ozs_pct_formula():
    assert fmp.ozs_pct(120.0, 80.0) == 0.6
    assert fmp.ozs_pct(0.0, 0.0) != fmp.ozs_pct(0.0, 0.0)  # NaN != NaN
    assert np.isnan(fmp.ozs_pct(np.nan, 5.0))
```

- [ ] (2) Run it (expected FAIL — functions undefined):

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py::test_filter_5v5_keeps_only_5on5_and_renames -v
```

Expected: `AttributeError: module 'fetch_moneypuck' has no attribute 'filter_5v5'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_moneypuck.py`:

```python
import numpy as np


def ozs_pct(ozs: float, dzs: float) -> float:
    """Offensive-zone-start share (neutral starts excluded). NaN if no starts."""
    if not (np.isfinite(ozs) and np.isfinite(dzs)):
        return float("nan")
    denom = ozs + dzs
    if denom == 0:
        return float("nan")
    return ozs / denom


def filter_5v5(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep only situation == '5on5'; coerce numerics; rename to feature cols.

    A13 LOCKED situation. The MoneyPuck CSV stratifies every player by
    situation; the aggregate 'all' row re-imports the special-teams confound,
    so it is dropped here before any aggregation.
    """
    df = raw[raw["situation"].astype(str) == LOCKED_SITUATION].copy()
    for src in ("icetime", "onIce_corsiPercentage", "onIce_xGoalsPercentage",
                "I_F_oZoneShiftStarts", "I_F_dZoneShiftStarts", "games_played"):
        df[src] = pd.to_numeric(df[src], errors="coerce")
    df = df.rename(columns={
        "onIce_corsiPercentage": "cf_pct",
        "onIce_xGoalsPercentage": "xgf_pct",
        "I_F_oZoneShiftStarts": "ozs_raw",
        "I_F_dZoneShiftStarts": "dzs_raw",
    })
    return df[["playerId", "name", "team", "situation", "icetime",
               "games_played", "cf_pct", "xgf_pct", "ozs_raw", "dzs_raw"]]
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py -v
```

Expected: 4 passed.

- [ ] (5) Commit:

```
git add pilot2/fetch_moneypuck.py pilot2/tests/test_fetch_moneypuck.py
git commit -m "pilot2: A13 5v5 filter + ozs_pct formula (neutral starts excluded)"
```

---

## Task 3: Icetime-weighted trade aggregation (collapse per playerId)

**Files:**
- Modify: `pilot2/fetch_moneypuck.py`
- Test: `pilot2/tests/test_fetch_moneypuck.py`

**Interfaces:**
- Consumes: a 5v5-filtered DataFrame (output of `filter_5v5`) that may contain >1 row per `playerId` (traded players: one row per team, no aggregate row — spec risk #1).
- Produces:
  - `aggregate_traded(df5v5: pd.DataFrame) -> pd.DataFrame` — collapses to ONE row per `playerId`. For each playerId:
    - `cf_pct`, `xgf_pct` -> icetime-weighted mean across team-rows (weight = row `icetime`; a simple mean would over-weight a 3-game stint). If total icetime is 0 / all-NaN, fall back to simple `np.nanmean`.
    - `ozs_pct` -> recompute from SUMMED `ozs_raw` and `dzs_raw` (sum counts, then divide — correct for a ratio), via `ozs_pct(sum_ozs, sum_dzs)`.
    - `mp_icetime_5v5` -> sum of `icetime`; `mp_games_played_5v5` -> sum of `games_played`.
    - `n_team_rows` -> count of input rows for that playerId (>=2 ⇒ trade-aggregated).
    - `name`, `team` -> from the max-`icetime` row (the player's primary team this season). The fetcher MUST branch on `groupby(['playerId','situation']).size()` empirically (spec risk #1) before trusting the one-row-per-team assumption; this function takes the already-empirically-grouped frame.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_fetch_moneypuck.py`:

```python
def test_aggregate_single_team_passthrough():
    df = fmp.filter_5v5(pd.DataFrame([
        _raw_row(1, "5on5", ct=0.55, xt=0.52, ozs=120, dzs=80, ice=1000, gp=20),
    ]))
    agg = fmp.aggregate_traded(df)
    assert len(agg) == 1
    r = agg.iloc[0]
    assert r["n_team_rows"] == 1
    assert r["cf_pct"] == 0.55 and r["xgf_pct"] == 0.52
    assert r["ozs_pct"] == 0.6
    assert r["mp_icetime_5v5"] == 1000 and r["mp_games_played_5v5"] == 20


def test_aggregate_traded_two_team_rows_icetime_weighted():
    # Player 7 traded: 900 min @ cf 0.60 on team A, 100 min @ cf 0.40 on team B.
    # icetime-weighted cf = (0.60*900 + 0.40*100)/1000 = 0.58 (NOT simple 0.50).
    # ozs from summed counts: (180+20)/((180+20)+(120+80)) = 200/400 = 0.5.
    df = fmp.filter_5v5(pd.DataFrame([
        _raw_row(7, "5on5", ct=0.60, xt=0.62, ozs=180, dzs=120, ice=900, gp=45,
                 team="TOR", name="Traded Guy"),
        _raw_row(7, "5on5", ct=0.40, xt=0.42, ozs=20, dzs=80, ice=100, gp=5,
                 team="CGY", name="Traded Guy"),
    ]))
    agg = fmp.aggregate_traded(df)
    assert len(agg) == 1
    r = agg.iloc[0]
    assert r["n_team_rows"] == 2
    assert abs(r["cf_pct"] - 0.58) < 1e-9
    assert abs(r["xgf_pct"] - 0.60) < 1e-9   # (0.62*900+0.42*100)/1000
    assert abs(r["ozs_pct"] - 0.5) < 1e-9    # summed-count ratio, NOT averaged
    assert r["mp_icetime_5v5"] == 1000 and r["mp_games_played_5v5"] == 50
    assert r["team"] == "TOR"   # max-icetime (primary) team


def test_aggregate_one_row_per_player():
    df = fmp.filter_5v5(pd.DataFrame([
        _raw_row(1, "5on5", ice=500), _raw_row(1, "5on5", ice=400),
        _raw_row(2, "5on5", ice=900),
    ]))
    agg = fmp.aggregate_traded(df)
    assert sorted(agg["playerId"].tolist()) == [1, 2]
    assert agg["playerId"].is_unique
```

- [ ] (2) Run it (expected FAIL — `aggregate_traded` undefined):

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py::test_aggregate_traded_two_team_rows_icetime_weighted -v
```

Expected: `AttributeError: module 'fetch_moneypuck' has no attribute 'aggregate_traded'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_moneypuck.py`:

```python
def _wmean(vals: np.ndarray, weights: np.ndarray) -> float:
    """Icetime-weighted mean; falls back to simple nanmean if all weight is 0."""
    m = np.isfinite(vals) & np.isfinite(weights)
    if not m.any():
        return float("nan")
    v, w = vals[m], weights[m]
    if w.sum() <= 0:
        return float(np.nanmean(v))
    return float((v * w).sum() / w.sum())


def aggregate_traded(df5v5: pd.DataFrame) -> pd.DataFrame:
    """Collapse 5v5 rows to one row per playerId (trade aggregation).

    cf_pct/xgf_pct -> icetime-weighted mean across the player's team-rows;
    ozs_pct -> recomputed from SUMMED zone-start counts (sum then divide);
    icetime/games summed; n_team_rows records the team-row count (>=2 = traded).
    """
    out_rows = []
    for pid, grp in df5v5.groupby("playerId", sort=True):
        ice = grp["icetime"].to_numpy(dtype=float)
        cf = _wmean(grp["cf_pct"].to_numpy(dtype=float), ice)
        xgf = _wmean(grp["xgf_pct"].to_numpy(dtype=float), ice)
        sum_ozs = np.nansum(grp["ozs_raw"].to_numpy(dtype=float))
        sum_dzs = np.nansum(grp["dzs_raw"].to_numpy(dtype=float))
        primary = grp.sort_values("icetime", ascending=False).iloc[0]
        out_rows.append({
            "playerId": int(pid),
            "name": primary["name"],
            "team": primary["team"],
            "cf_pct": cf,
            "xgf_pct": xgf,
            "ozs_pct": ozs_pct(sum_ozs, sum_dzs),
            "mp_icetime_5v5": float(np.nansum(ice)),
            "mp_games_played_5v5": float(
                np.nansum(grp["games_played"].to_numpy(dtype=float))),
            "n_team_rows": int(len(grp)),
        })
    return pd.DataFrame(out_rows)
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py -v
```

Expected: 7 passed.

- [ ] (5) Commit:

```
git add pilot2/fetch_moneypuck.py pilot2/tests/test_fetch_moneypuck.py
git commit -m "pilot2: A13 icetime-weighted trade aggregation (rates) + summed-count ozs ratio"
```

---

## Task 4: Thin-floor NULLing + onice_status assignment

**Files:**
- Modify: `pilot2/fetch_moneypuck.py`
- Test: `pilot2/tests/test_fetch_moneypuck.py`

**Interfaces:**
- Consumes: one aggregated row's `mp_icetime_5v5` (and the row's feature values).
- Produces:
  - `apply_thin_floor(row: dict) -> dict` — mutates/returns a copy: if `mp_icetime_5v5 < ONICE_MIN_ICETIME_5V5` (or icetime NaN), set `cf_pct = xgf_pct = ozs_pct = float("nan")` and `onice_status = "thin"`; else `onice_status = "ok"`. (The `"missing"` status is assigned at JOIN time, Task 5, for players with NO MoneyPuck row — handled there, not here.)

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_fetch_moneypuck.py`:

```python
def test_apply_thin_floor_nulls_below_150():
    row = {"cf_pct": 0.65, "xgf_pct": 0.60, "ozs_pct": 0.7,
           "mp_icetime_5v5": 120.0}
    out = fmp.apply_thin_floor(row)
    assert out["onice_status"] == "thin"
    assert np.isnan(out["cf_pct"]) and np.isnan(out["xgf_pct"])
    assert np.isnan(out["ozs_pct"])


def test_apply_thin_floor_keeps_above_floor():
    row = {"cf_pct": 0.55, "xgf_pct": 0.52, "ozs_pct": 0.6,
           "mp_icetime_5v5": 800.0}
    out = fmp.apply_thin_floor(row)
    assert out["onice_status"] == "ok"
    assert out["cf_pct"] == 0.55 and out["ozs_pct"] == 0.6


def test_apply_thin_floor_nan_icetime_is_thin():
    out = fmp.apply_thin_floor(
        {"cf_pct": 0.5, "xgf_pct": 0.5, "ozs_pct": 0.5,
         "mp_icetime_5v5": float("nan")})
    assert out["onice_status"] == "thin"
    assert np.isnan(out["cf_pct"])
```

- [ ] (2) Run it (expected FAIL — `apply_thin_floor` undefined):

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py::test_apply_thin_floor_nulls_below_150 -v
```

Expected: `AttributeError: module 'fetch_moneypuck' has no attribute 'apply_thin_floor'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_moneypuck.py`:

```python
def apply_thin_floor(row: dict) -> dict:
    """NULL the three on-ice features below ONICE_MIN_ICETIME_5V5 (thin sample).

    Rate stats are unstable at low ice (a 5-game callup can post 65% CF% on
    noise). Below the floor the features are NULLed and onice_status='thin';
    compute_oaq.py's existing group-mean imputation then fills them to
    position-group neutral before standardizing, so the player is matched on
    his stable box-score stats. The player is NEVER dropped (A10 pool).
    """
    out = dict(row)
    ice = out.get("mp_icetime_5v5")
    if ice is None or not np.isfinite(ice) or ice < ONICE_MIN_ICETIME_5V5:
        out["cf_pct"] = float("nan")
        out["xgf_pct"] = float("nan")
        out["ozs_pct"] = float("nan")
        out["onice_status"] = "thin"
    else:
        out["onice_status"] = "ok"
    return out
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py -v
```

Expected: 10 passed.

- [ ] (5) Commit:

```
git add pilot2/fetch_moneypuck.py pilot2/tests/test_fetch_moneypuck.py
git commit -m "pilot2: A13 thin-floor NULLing (<150 min 5v5 -> onice_status=thin)"
```

---

## Task 5: Left-join onto the 774 pool (id + name fallback, onice_status=missing)

**Files:**
- Modify: `pilot2/fetch_moneypuck.py`
- Test: `pilot2/tests/test_fetch_moneypuck.py`

**Interfaces:**
- Consumes: the 774-player roster (list of dicts from `_common.load_players`, each with `player_id`, `full_name`, `team_code`, `nhl_player_id`) and the aggregated+floored MoneyPuck rows (DataFrame, one row per `playerId`).
- Produces:
  - `_norm_name(name: str) -> str` — lowercase, strip, collapse internal whitespace (for the name fallback only).
  - `join_pool(players: list[dict], mp: pd.DataFrame, fetch_date: str) -> list[dict]` — returns exactly `len(players)` rows (NEVER drops a player). For each player:
    - Primary join: `int(nhl_player_id) == mp.playerId`.
    - Name fallback ONLY where the player's `nhl_player_id` is blank/non-digit: match on `_norm_name(full_name) == _norm_name(mp.name)`.
    - No MoneyPuck match -> `cf_pct/xgf_pct/ozs_pct = "" (NULL)`, `mp_icetime_5v5/mp_games_played_5v5 = ""`, `n_team_rows = 0`, `onice_status = "missing"`.
    - Output `team_code` is the POOL's `team_code` (players.csv authoritative), not MoneyPuck's `team`. `situation` is always `"5on5"`. `nhl_player_id` echoes the pool value. NaN feature values are written as `""`.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_fetch_moneypuck.py`:

```python
def _agg_df(rows):
    # rows already aggregated/floored; supply the post-aggregate columns.
    return pd.DataFrame(rows)


def test_join_pool_id_match_and_status():
    players = [
        {"player_id": "1", "full_name": "Leo Carlsson", "team_code": "ANA",
         "nhl_player_id": "8484153"},
        {"player_id": "2", "full_name": "No Match Guy", "team_code": "BOS",
         "nhl_player_id": "9999999"},
    ]
    mp = _agg_df([
        {"playerId": 8484153, "name": "Leo Carlsson", "team": "ANA",
         "cf_pct": 0.55, "xgf_pct": 0.52, "ozs_pct": 0.6,
         "mp_icetime_5v5": 800.0, "mp_games_played_5v5": 40.0,
         "n_team_rows": 1, "onice_status": "ok"},
    ])
    out = fmp.join_pool(players, mp, "2026-06-20")
    assert len(out) == 2
    leo = next(r for r in out if r["player_id"] == "1")
    assert leo["cf_pct"] == 0.55 and leo["onice_status"] == "ok"
    assert leo["team_code"] == "ANA" and leo["situation"] == "5on5"
    miss = next(r for r in out if r["player_id"] == "2")
    assert miss["onice_status"] == "missing"
    assert miss["cf_pct"] == "" and miss["n_team_rows"] == 0


def test_join_pool_name_fallback_only_when_id_blank():
    players = [
        {"player_id": "3", "full_name": "Michael Benning", "team_code": "FLA",
         "nhl_player_id": ""},  # blank id -> name fallback allowed
    ]
    mp = _agg_df([
        {"playerId": 8480000, "name": "michael  benning", "team": "FLA",
         "cf_pct": 0.50, "xgf_pct": 0.49, "ozs_pct": 0.45,
         "mp_icetime_5v5": 600.0, "mp_games_played_5v5": 30.0,
         "n_team_rows": 1, "onice_status": "ok"},
    ])
    out = fmp.join_pool(players, mp, "2026-06-20")
    assert out[0]["cf_pct"] == 0.50  # matched by normalized name


def test_join_pool_never_drops_player():
    players = [{"player_id": str(i), "full_name": f"P{i}", "team_code": "BOS",
                "nhl_player_id": str(8000000 + i)} for i in range(5)]
    out = fmp.join_pool(players, _agg_df([]), "2026-06-20")
    assert len(out) == 5
    assert all(r["onice_status"] == "missing" for r in out)
```

- [ ] (2) Run it (expected FAIL — `join_pool` undefined):

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py::test_join_pool_id_match_and_status -v
```

Expected: `AttributeError: module 'fetch_moneypuck' has no attribute 'join_pool'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_moneypuck.py`:

```python
import re


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _blank(s) -> str:
    return "" if (s is None or (isinstance(s, float) and not np.isfinite(s))) else s


def join_pool(players: list[dict], mp: pd.DataFrame, fetch_date: str) -> list[dict]:
    """Left-join MoneyPuck rows onto the 774 pool on nhl_player_id (name-fallback
    only where the id is blank). NEVER drops a player; no match -> onice_status
    =missing with NULL features."""
    by_id = {int(r["playerId"]): r for _, r in mp.iterrows()} if len(mp) else {}
    by_name = ({_norm_name(r["name"]): r for _, r in mp.iterrows()}
               if len(mp) else {})
    out: list[dict] = []
    for p in players:
        pid = (p.get("nhl_player_id") or "").strip()
        rec = None
        if pid.isdigit() and int(pid) in by_id:
            rec = by_id[int(pid)]
        elif not pid.isdigit():
            rec = by_name.get(_norm_name(p["full_name"]))
        if rec is None:
            out.append({
                "player_id": p["player_id"],
                "nhl_player_id": pid,
                "full_name": p["full_name"],
                "team_code": p["team_code"],
                "situation": LOCKED_SITUATION,
                "cf_pct": "", "xgf_pct": "", "ozs_pct": "",
                "mp_icetime_5v5": "", "mp_games_played_5v5": "",
                "n_team_rows": 0, "onice_status": "missing",
                "fetch_date": fetch_date,
            })
            continue
        out.append({
            "player_id": p["player_id"],
            "nhl_player_id": pid,
            "full_name": p["full_name"],
            "team_code": p["team_code"],
            "situation": LOCKED_SITUATION,
            "cf_pct": _blank(rec["cf_pct"]),
            "xgf_pct": _blank(rec["xgf_pct"]),
            "ozs_pct": _blank(rec["ozs_pct"]),
            "mp_icetime_5v5": _blank(rec["mp_icetime_5v5"]),
            "mp_games_played_5v5": _blank(rec["mp_games_played_5v5"]),
            "n_team_rows": int(rec["n_team_rows"]),
            "onice_status": rec["onice_status"],
            "fetch_date": fetch_date,
        })
    return out
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py -v
```

Expected: 13 passed.

- [ ] (5) Commit:

```
git add pilot2/fetch_moneypuck.py pilot2/tests/test_fetch_moneypuck.py
git commit -m "pilot2: A13 left-join onto 774 pool (id + name-fallback, onice_status=missing)"
```

---

## Task 6: Download/cache + `main()` wiring + INTEGRATION fetch

**Files:**
- Modify: `pilot2/fetch_moneypuck.py`
- Test: `pilot2/tests/test_fetch_moneypuck.py`

**Interfaces:**
- Consumes: `_common.session`, `_common.CONTACT_UA`, `_common.atomic_write_csv`, `_common.load_players`, `RAW_DIR`.
- Produces:
  - `load_raw(s) -> pd.DataFrame` — if `CACHE_CSV` exists, read it; else GET `MP_URL` (User-Agent `CONTACT_UA`, timeout 60), write the response bytes to `CACHE_CSV` via a `.tmp`->`os.replace` atomic write, then read. Returns the raw skater DataFrame.
  - `empirical_group_report(df5v5: pd.DataFrame) -> dict[int, int]` — `groupby(['playerId','situation']).size()` collapsed to `playerId -> n_5v5_rows` (spec risk #1: branch empirically, do not trust one-row-per-team). Used to print how many players have `n_5v5_rows >= 2` (in-season trades).
  - `main() -> None` — load raw, `filter_5v5`, assert/print the empirical group report, `aggregate_traded`, `apply_thin_floor` per row, `join_pool`, `atomic_write_csv(OUT_CSV, rows, OUT_FIELDS)`; print ok/thin/missing counts and `n_team_rows>=2` count.

Steps:

- [ ] (1) Write the failing test (download logic via a fake session; main() exercised by the integration step). Append to `pilot2/tests/test_fetch_moneypuck.py`:

```python
def test_load_raw_uses_cache_when_present(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "moneypuck_skaters_2025.csv").write_text(
        "playerId,name,team,situation,icetime,games_played,"
        "onIce_corsiPercentage,onIce_xGoalsPercentage,"
        "I_F_oZoneShiftStarts,I_F_dZoneShiftStarts\n"
        "8484153,Leo Carlsson,ANA,5on5,800,40,0.55,0.52,120,80\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(fmp, "RAW_DIR", raw)
    monkeypatch.setattr(fmp, "CACHE_CSV", raw / "moneypuck_skaters_2025.csv")

    class _NoNet:
        def get(self, *a, **k):
            raise AssertionError("network hit despite cache present")

    df = fmp.load_raw(_NoNet())
    assert int(df.iloc[0]["playerId"]) == 8484153
    assert df.iloc[0]["situation"] == "5on5"


def test_empirical_group_report_flags_traded():
    df = fmp.filter_5v5(pd.DataFrame([
        _raw_row(7, "5on5", ice=900), _raw_row(7, "5on5", ice=100),
        _raw_row(9, "5on5", ice=800),
    ]))
    rep = fmp.empirical_group_report(df)
    assert rep[7] == 2 and rep[9] == 1
```

- [ ] (2) Run it (expected FAIL — `load_raw`/`empirical_group_report` undefined):

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py::test_empirical_group_report_flags_traded -v
```

Expected: `AttributeError: module 'fetch_moneypuck' has no attribute 'empirical_group_report'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_moneypuck.py`:

```python
import os


def load_raw(s) -> pd.DataFrame:
    """Read the cached MoneyPuck CSV, downloading once if absent (atomic write)."""
    if not CACHE_CSV.exists():
        r = s.get(MP_URL, headers={"User-Agent": CONTACT_UA}, timeout=60)
        r.raise_for_status()
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_CSV.with_suffix(CACHE_CSV.suffix + ".tmp")
        tmp.write_bytes(r.content)
        os.replace(tmp, CACHE_CSV)
    return pd.read_csv(CACHE_CSV)


def empirical_group_report(df5v5: pd.DataFrame) -> dict[int, int]:
    """playerId -> count of 5v5 rows (spec risk #1: branch on the real file,
    do not trust one-row-per-team). >=2 ⇒ in-season trade -> aggregation."""
    sizes = df5v5.groupby(["playerId", "situation"]).size()
    out: dict[int, int] = {}
    for (pid, _sit), cnt in sizes.items():
        out[int(pid)] = out.get(int(pid), 0) + int(cnt)
    return out


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    s = session(expire_hours=24)
    raw = load_raw(s)
    df5v5 = filter_5v5(raw)

    report = empirical_group_report(df5v5)
    n_traded = sum(1 for n in report.values() if n >= 2)
    print(f"5v5 rows: {len(df5v5)}; unique playerIds: {len(report)}; "
          f"playerIds with >=2 5v5 rows (in-season trades): {n_traded}")

    agg = aggregate_traded(df5v5)
    floored = [apply_thin_floor(r) for r in agg.to_dict("records")]
    floored_df = pd.DataFrame(floored)

    players = load_players()
    rows = join_pool(players, floored_df, fetch_date)
    atomic_write_csv(OUT_CSV, rows, OUT_FIELDS)

    counts = {"ok": 0, "thin": 0, "missing": 0}
    for r in rows:
        counts[r["onice_status"]] = counts.get(r["onice_status"], 0) + 1
    n_agg_traded = sum(1 for r in rows if r["n_team_rows"] >= 2)
    print(f"Wrote {OUT_CSV}: {len(rows)} rows "
          f"(ok={counts['ok']}, thin={counts['thin']}, "
          f"missing={counts['missing']}; trade-aggregated={n_agg_traded})")


if __name__ == "__main__":
    main()
```

- [ ] (4) Run pass (unit):

```
python -m pytest pilot2/tests/test_fetch_moneypuck.py -v
```

Expected: 15 passed.

- [ ] (4b) INTEGRATION (real network — run once; requires `pilot2/players.csv` for the 774 pool):

```
python pilot2/fetch_moneypuck.py
```

Expected output:
- Downloads + caches `pilot2/raw/moneypuck_skaters_2025.csv` (first run; re-runs read the cache, no network).
- Prints the empirical group report with `playerIds with >=2 5v5 rows (in-season trades): N` where **N >= 2** (in-season-traded players exist in a full 2025-26 season — spec risk #1 confirmed empirically).
- Writes `pilot2/raw/nhl_onice.csv` with **774 rows** (one per pool player; never dropped).
- Prints `ok=/thin=/missing=` counts. Spot-check: a regular top-line skater (e.g. Leo Carlsson, nhl_player_id 8484153) is `onice_status=ok` with `cf_pct`/`xgf_pct` in [0,1] and `mp_icetime_5v5 >= 150`; deep callups / no-id players show `onice_status=missing` or `thin`. Report the ok/thin/missing split (goes to `results.md` per spec risk #2 at the next compute).

- [ ] (5) Commit:

```
git add pilot2/fetch_moneypuck.py pilot2/tests/test_fetch_moneypuck.py
git commit -m "pilot2: A13 wire moneypuck main() + download/cache + empirical trade branch + integration fetch"
```

---

## Task 7: Add the three features to `SKILL_COLS` in `compute_oaq.py`

**Files:**
- Modify: `pilot2/compute_oaq.py` (the `SKILL_COLS` constant only)
- Test: `pilot2/tests/test_compute_oaq_skill.py`

**Interfaces:**
- Consumes: nothing (constant edit).
- Produces (in `compute_oaq.py`): `SKILL_COLS == ["age", "ppg", "toi_per_game", "cf_pct", "xgf_pct", "ozs_pct"]`. `_standardize_skill` and `compute_peers` read `SKILL_COLS` and need NO body change. `EXPECTED_CAP_PREDICTORS` is NOT touched.

**Rebase note:** this task assumes the A12 edits are already committed (rebase first). The `SKILL_COLS` line is in the peer region, distinct from A12's `WEIGHTS` region.

Steps:

- [ ] (1) Write the failing test. Create `pilot2/tests/test_compute_oaq_skill.py`:

```python
"""Unit tests for the A13 6-feature peer (skill) vector."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pilot2/
import compute_oaq as co  # noqa: E402


def test_skill_cols_are_the_six_feature_vector():
    assert co.SKILL_COLS == [
        "age", "ppg", "toi_per_game", "cf_pct", "xgf_pct", "ozs_pct",
    ]


def test_expected_cap_predictors_unchanged_ppg_toi_only():
    # A13 must NOT add on-ice features to the A4 market-price regression.
    assert co.EXPECTED_CAP_PREDICTORS == ["ppg", "toi_per_game"]
    assert "cf_pct" not in co.EXPECTED_CAP_PREDICTORS
    assert "xgf_pct" not in co.EXPECTED_CAP_PREDICTORS
    assert "ozs_pct" not in co.EXPECTED_CAP_PREDICTORS
```

- [ ] (2) Run it (expected FAIL — `SKILL_COLS` still 3 features):

```
python -m pytest pilot2/tests/test_compute_oaq_skill.py::test_skill_cols_are_the_six_feature_vector -v
```

Expected: `AssertionError` (SKILL_COLS is still `["age", "ppg", "toi_per_game"]`) FAIL.

- [ ] (3) Minimal implementation. In `pilot2/compute_oaq.py`, replace the `SKILL_COLS` line:

```python
# A13 (2026-06-XX) — peer (skill) vector expanded 3->6 with MoneyPuck 5v5
# on-ice play-driving + deployment features (cf_pct, xgf_pct, ozs_pct), so the
# "skill-controlled" residual is matched against a defensible skill profile.
# Distance unchanged (K=10, within-group Mahalanobis); _standardize_skill's
# group-mean NULL imputation fills thin/missing on-ice features to position-
# group neutral before standardizing. expected_cap (A4) is NOT touched.
SKILL_COLS = ["age", "ppg", "toi_per_game", "cf_pct", "xgf_pct", "ozs_pct"]
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_compute_oaq_skill.py -v
```

Expected: 2 passed.

- [ ] (5) Commit:

```
git add pilot2/compute_oaq.py pilot2/tests/test_compute_oaq_skill.py
git commit -m "pilot2: A13 expand SKILL_COLS 3->6 (cf_pct, xgf_pct, ozs_pct); expected_cap untouched"
```

---

## Task 8: Standardization-with-NULL-imputation over the 6-dim vector

**Files:**
- Test only: `pilot2/tests/test_compute_oaq_skill.py` (no production change — `_standardize_skill` already iterates `SKILL_COLS` and imputes group-mean for NULLs; this task LOCKS that behavior over 6 dims, including the on-ice NULLs from thin/missing players).

**Interfaces:**
- Consumes: `co._standardize_skill(df)` and `co.compute_peers(df)` with `df` carrying the 6 `SKILL_COLS` columns (some on-ice NULL).
- Produces: a `(n, 6)` standardized matrix where NULL on-ice features are imputed to the position-group mean BEFORE standardizing (so a thin/missing player contributes 0 on the on-ice axes after z-scoring and is matched on his box-score stats); per-column standard deviation is 1 (ddof=1, within the function's all-rows standardize).

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_compute_oaq_skill.py`:

```python
def _skill_df():
    # 6 forwards (group f1) + 6 defense (group d1). Player idx 2 (a forward)
    # and idx 8 (a defenseman) have NULL on-ice features (thin/missing) and
    # must be imputed to their group mean before standardizing.
    n_each = 6
    rows = []
    for g, base in (("f1", 0.50), ("d1", 0.48)):
        for k in range(n_each):
            cf = base + 0.01 * k
            rows.append({
                "group": g,
                "age": 24 + k, "ppg": 0.5 + 0.1 * k,
                "toi_per_game": 15 + k,
                "cf_pct": cf, "xgf_pct": cf - 0.02, "ozs_pct": 0.45 + 0.01 * k,
            })
    df = pd.DataFrame(rows)
    df.loc[2, ["cf_pct", "xgf_pct", "ozs_pct"]] = np.nan   # thin forward
    df.loc[8, ["cf_pct", "xgf_pct", "ozs_pct"]] = np.nan   # thin defenseman
    df["player_id"] = range(1, len(df) + 1)
    return df


def test_standardize_skill_is_six_dim_and_imputes_nulls():
    df = _skill_df()
    Z = co._standardize_skill(df)
    assert Z.shape == (12, 6)              # 6 features now, not 3
    assert np.isfinite(Z).all()           # NULL on-ice features were imputed
    # Each column standardized: ddof=1 sd == 1 (within the all-rows standardize).
    sds = Z.std(axis=0, ddof=1)
    assert np.allclose(sds, 1.0, atol=1e-6)


def test_imputed_player_sits_at_group_mean_on_onice_axes():
    # The thin forward (idx 2) imputed to the f1 group mean on cf/xgf/ozs:
    # after standardizing it equals the standardized group-mean on those axes.
    df = _skill_df()
    Z = co._standardize_skill(df)
    f1_mask = (df["group"] == "f1").to_numpy()
    cf_col = Z[:, 3]                       # cf_pct is index 3 in SKILL_COLS
    # idx 2's standardized cf equals the mean of the OTHER f1 members' raw-mean
    # imputation -> close to the f1 standardized centroid on that axis.
    f1_cf_mean = cf_col[f1_mask].mean()
    assert abs(cf_col[2] - f1_cf_mean) < 0.30  # near group centroid, not extreme


def test_compute_peers_runs_with_six_features():
    df = _skill_df()
    peers = co.compute_peers(df)
    assert len(peers) == 12
    # K capped by group size-1 (6 per group -> at most 5 peers each here).
    assert all(len(pl) <= 5 for pl in peers)
    # Hard position split: a forward's peers are all forwards.
    groups = df["group"].to_numpy()
    for i, pl in enumerate(peers):
        assert all(groups[j] == groups[i] for j in pl)
```

- [ ] (2) Run it (expected: FAIL if Task 7 not applied; PASS once `SKILL_COLS` has 6 entries):

```
python -m pytest pilot2/tests/test_compute_oaq_skill.py::test_standardize_skill_is_six_dim_and_imputes_nulls -v
```

Expected BEFORE Task 7: `AssertionError: Z.shape == (12, 3)` FAIL. AFTER Task 7 (already committed): these tests PASS with no production change — confirming `_standardize_skill`/`compute_peers` need no body edit for the 6-dim vector.

- [ ] (3) Minimal implementation: NONE. `_standardize_skill` reads `df[SKILL_COLS]` and imputes group-mean (then overall mean) per column before standardizing; `compute_peers` reads the same. The 6-dim behavior is already correct once `SKILL_COLS` grew in Task 7. If any test fails, the cause is a Task 7 error — fix `SKILL_COLS`, do not change `_standardize_skill`.

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_compute_oaq_skill.py -v
```

Expected: 6 passed (2 from Task 7 + 4 here).

- [ ] (5) Commit:

```
git add pilot2/tests/test_compute_oaq_skill.py
git commit -m "pilot2: A13 lock 6-dim standardization + group-mean NULL imputation behavior (test-only)"
```

---

## Task 9: Merge `raw/nhl_onice.csv` in `load_inputs` + add to `OUT_COLS`

**Files:**
- Modify: `pilot2/compute_oaq.py` (`load_inputs` merge block + `_to_num` list + `OUT_COLS`)
- Test: `pilot2/tests/test_compute_oaq_skill.py`

**Interfaces:**
- Consumes: `raw/nhl_onice.csv` (columns `player_id`, `cf_pct`, `xgf_pct`, `ozs_pct`, `onice_status`).
- Produces: `load_inputs()` returns a DataFrame with numeric `cf_pct`, `xgf_pct`, `ozs_pct` columns (NaN where onice_status=thin/missing or player absent from the file) and a string `onice_status` column. Since `_standardize_skill`/`compute_peers` iterate `SKILL_COLS`, the new columns flow into peer matching automatically with the existing group-mean imputation handling the NULLs.

**Co-modification note:** the merge block and `OUT_COLS` are the two collision points with A12. After rebasing on A12: insert the `nhl_onice` merge directly after the existing SKILL merge (`df = df.merge(skill[["player_id", "age", "ppg", "toi_per_game", "games_played"]], ...)`), NOT near A12's `wiki_intl` merge. Add the three feature names to `_to_num`'s skill list (they ride along with `SKILL_COLS` since `_to_num(df, SKILL_COLS + [...])` already covers them — verify they are included via `SKILL_COLS`). In `OUT_COLS`, add `"cf_pct", "xgf_pct", "ozs_pct", "onice_status"` next to `toi_per_game`, distinct from A12's wiki_intl insertion.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_compute_oaq_skill.py`:

```python
def test_load_inputs_has_onice_columns(monkeypatch):
    # Smoke: real load_inputs reads raw/nhl_onice.csv if present; skip if the
    # raw inputs are not materialized in this checkout.
    try:
        df = co.load_inputs()
    except FileNotFoundError:
        import pytest
        pytest.skip("raw inputs not materialized")
    for c in ("cf_pct", "xgf_pct", "ozs_pct"):
        assert c in df.columns
        assert pd.api.types.is_numeric_dtype(df[c])
    assert "onice_status" in df.columns


def test_out_cols_include_onice_features():
    for c in ("cf_pct", "xgf_pct", "ozs_pct", "onice_status"):
        assert c in co.OUT_COLS
```

- [ ] (2) Run it (expected FAIL — `OUT_COLS` lacks the on-ice columns; `load_inputs` does not merge them):

```
python -m pytest pilot2/tests/test_compute_oaq_skill.py::test_out_cols_include_onice_features -v
```

Expected: `AssertionError` (cf_pct not in OUT_COLS) FAIL.

- [ ] (3) Minimal implementation. In `pilot2/compute_oaq.py` `load_inputs()`, after the existing skill read line
`skill = pd.read_csv(RAW_DIR / "nhl_skill.csv", dtype={"player_id": int})`
add the on-ice read:

```python
    onice = pd.read_csv(RAW_DIR / "nhl_onice.csv", dtype={"player_id": int})
```

Immediately after the existing SKILL merge line
`df = df.merge(skill[["player_id", "age", "ppg", "toi_per_game", "games_played"]], on="player_id", how="left")`
add the on-ice merge:

```python
    df = df.merge(
        onice[["player_id", "cf_pct", "xgf_pct", "ozs_pct", "onice_status"]],
        on="player_id", how="left",
    )
```

The existing `_to_num(df, SKILL_COLS + [...])` call already coerces `cf_pct`/`xgf_pct`/`ozs_pct` because they are now in `SKILL_COLS` (Task 7) — no edit needed there; if a defensive maintainer prefers explicitness, leave it, the duplication is harmless. Add a default for `onice_status` in case the file lacks a row for a player (left-join NaN):

```python
    df["onice_status"] = df["onice_status"].astype("string").fillna("missing")
```

Place this line near the existing `df["cap_quality"] = df["cap_quality"].astype("string").fillna("low")` line.

In `OUT_COLS`, add the four columns next to `toi_per_game` (peer region — keep distinct from A12's wiki_intl insertion):

```python
    "age", "ppg", "toi_per_game", "cf_pct", "xgf_pct", "ozs_pct",
    "onice_status", "games_played", "small_sample",
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_compute_oaq_skill.py -v
```

Expected: `test_out_cols_include_onice_features` PASS; `test_load_inputs_has_onice_columns` PASS or SKIP (skips only if raw inputs absent). Re-run the full `test_compute_oaq_skill.py` — 8 passed (or 7 passed + 1 skipped).

- [ ] (5) Commit:

```
git add pilot2/compute_oaq.py pilot2/tests/test_compute_oaq_skill.py
git commit -m "pilot2: A13 merge nhl_onice.csv in load_inputs; add cf/xgf/ozs + onice_status to OUT_COLS"
```

---

## Task 10: Append the A13 amendment text to `preregistration.md`

**Files:**
- Modify: `pilot2/preregistration.md` (append only, after the A12 block)
- Test: `pilot2/tests/test_compute_oaq_skill.py` (text-presence assertion)

**Interfaces:**
- Consumes: spec §9 verbatim amendment text.
- Produces: the A13 block appended to `pilot2/preregistration.md`, after A12.

**Co-modification note:** this is the second shared file with A12. A12 appends its block first (committed before A13 starts). A13 appends ITS block AFTER A12's (per spec §9 / the A12 "Letter reconciliation: A13" line). Append only — do not edit A1–A12.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_compute_oaq_skill.py`:

```python
def test_a13_amendment_appended_after_a12():
    txt = (Path(__file__).resolve().parents[1] / "preregistration.md").read_text(
        encoding="utf-8")
    assert "A13 (2026-06-" in txt
    assert "MoneyPuck 5v5 on-ice play-driving" in txt
    assert "ONICE_MIN_ICETIME_5V5 = 150" in txt
    assert "expected_cap (A4) unchanged" in txt
    # A13 must come AFTER A12 in the file (append order).
    assert txt.index("A12 (2026-06-") < txt.index("A13 (2026-06-")
```

- [ ] (2) Run it (expected FAIL — A13 text absent):

```
python -m pytest pilot2/tests/test_compute_oaq_skill.py::test_a13_amendment_appended_after_a12 -v
```

Expected: `AssertionError` (no "A13 (2026-06-" in file) FAIL.

- [ ] (3) Implementation. Append to the END of `pilot2/preregistration.md` (after the A12 block), the verbatim A13 text from spec §9. Render each spec blockquote line as a Markdown blockquote (`> ...`), exactly as the spec shows. The spec's date placeholder `2026-06-XX` is set to the commit date `2026-06-20`:

```markdown

**A13 (2026-06-20) — §6 peer (skill) vector: add MoneyPuck 5v5 on-ice play-driving + deployment features (CF%, xGF%, O-zone-start%) to `(age, PPG, TOI/G)`. Logged BEFORE any re-compute on the augmented vector.**

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
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_compute_oaq_skill.py::test_a13_amendment_appended_after_a12 -v
```

Expected: PASS.

- [ ] (5) Commit:

```
git add pilot2/preregistration.md pilot2/tests/test_compute_oaq_skill.py
git commit -m "pilot2: log A13 amendment in preregistration (before any re-compute on 6-feature vector)"
```

---

## Task 11: Full-suite green + end-to-end verification

**Files:**
- Test: all of `pilot2/tests/`

**Interfaces:** none (verification task).

Steps:

- [ ] (1) Run the full unit suite (A12 + A13 tests together — confirms no shared-file regression):

```
python -m pytest pilot2/tests/ -v
```

Expected: ALL tests pass (A13 contributes `test_fetch_moneypuck.py` 15 + `test_compute_oaq_skill.py` 8 — counts approximate; zero failures). The A12 test files (`test_fetch_wikipedia_intl.py`, `test_compute_oaq_weights.py`, `test_diagnostics.py`) still pass — A13 touched DIFFERENT regions.

- [ ] (2) Run the fetcher then the full pipeline end-to-end (requires the 774 raw inputs; `nhl_onice.csv` from Task 6, and the A12 raw outputs already materialized):

```
python pilot2/fetch_moneypuck.py
python pilot2/compute_oaq.py
```

Expected:
- `fetch_moneypuck.py` writes `pilot2/raw/nhl_onice.csv` with 774 rows; prints `ok/thin/missing` counts and `trade-aggregated >= 2`.
- `compute_oaq.py` runs end-to-end, prints `Wrote .../oaq_pilot.csv`, and `oaq_pilot.csv` now contains `cf_pct`, `xgf_pct`, `ozs_pct`, `onice_status` columns. The `results.md` "Configuration" peer-vector line and Mahalanobis description reflect the 6-feature vector once those strings are regenerated (no plan edit forces the prose change; verify the CSV columns are present and finite/imputed for all 774 — no NaN survives `_standardize_skill`, so `compute_peers` produces a full peer set for every player).
- Spot-check `oaq_pilot.csv`: a thin/missing player has empty `cf_pct` in the raw `nhl_onice.csv` but is still peer-matched (non-empty `peer_player_ids`) because the imputation runs inside `_standardize_skill`, not in the CSV.

- [ ] (3) (no code) Confirm the spec self-review checklist (below) is fully covered.

- [ ] (4) Commit any final fixups:

```
git add -A
git commit -m "pilot2: A13 full-suite green + end-to-end verification (6-feature peer vector)"
```

---

## Self-review against the spec

**Spec-section -> task coverage:**

| Spec section | Covered by |
|---|---|
| §1 Purpose (add on-ice play-driving to peer vector; honest "skill-controlled") | Tasks 1–10 collectively |
| §2 Locked: new features cf_pct/xgf_pct/ozs_pct -> 6-dim | Tasks 2, 7 |
| §2 Locked: source = MoneyPuck free season-summary CSV | Task 1 (`MP_URL`), Task 6 (`load_raw`) |
| §2 Locked: situation = 5v5 | Task 1 (`LOCKED_SITUATION`), Task 2 (`filter_5v5`) |
| §2 Locked: QoC skipped | No code (correctly nothing to build); disclosed in amendment (Task 10) + poster |
| §2 / §8 Locked: expected_cap (A4) UNCHANGED | Task 7 (`EXPECTED_CAP_PREDICTORS` assertion), Task 10 (amendment), no body change to `compute_expected_cap` |
| §2 Locked: thin-sample <150 min -> NULL + impute, never drop | Task 4 (`apply_thin_floor`), Task 8 (imputation lock), Task 5 (missing handling) |
| §2 V3 re-roll accepted/reported | Task 10 (amendment re-confirmation obligation); existing `external_validation`/`evaluate_patterns` re-run automatically (no new code) |
| §2 Credit MoneyPuck | Task 1 docstring + Task 10 amendment; poster (out of scope here) |
| §3 Source: URL pattern + START_YEAR=2025 | Task 1 |
| §3 Source: playerId == NHL id | Task 5 (`join_pool` id match) |
| §3 Source: situation split must filter | Task 2 |
| §3 Source: derive OZS% from raw counts (no precomputed) | Task 2 (`ozs_pct`), Task 3 (summed-count ratio) |
| §3 Source: QoC none | No code |
| §4 Features: cf_pct/xgf_pct/ozs_pct from 5v5 row; neutral starts excluded | Tasks 2, 3 |
| §4 5v5 locked rationale | Task 2 docstring + Task 10 |
| §4 Not-added (per-60, danger, gameScore) | No code (correctly nothing built) |
| §5 Join key + name-fallback | Task 5 (`join_pool`, `_norm_name`) |
| §5 Order: filter THEN aggregate | Tasks 2 -> 3 (enforced in `main()`, Task 6) |
| §5 Trade aggregation: icetime-weighted mean (rates) + summed counts (ozs) | Task 3 (`aggregate_traded`, `_wmean`) |
| §5 Left-join onto 774; missing -> NULL + onice_status=missing | Task 5 |
| §5 Assert one row per playerId; max-icetime on duplicate | Task 3 (`is_unique` test + max-icetime primary row) |
| §5 Output schema `raw/nhl_onice.csv` (13 cols) | Task 1 (`OUT_FIELDS`), Task 5 (`join_pool` row), Task 6 (`atomic_write_csv`) |
| §5 Fetcher: cached GET; load_inputs gains one merge; SKILL_COLS gains three | Task 6 (`load_raw`), Task 9 (merge), Task 7 (`SKILL_COLS`) |
| §6 Thin-sample: ONICE_MIN_ICETIME_5V5=150; NULL+impute; small_sample unchanged | Tasks 1, 4, 8 |
| §7 Mahalanobis: collinearity via inverse-cov; K=10; n>>p; standardization unchanged | Task 8 (6-dim standardize + compute_peers; no body change) |
| §8 expected_cap NOT extended; age excluded | Task 7 (assertion), Task 10 (amendment) |
| §9 Amendment text appended verbatim | Task 10 |
| §10 risk #1 (trade-row structure — branch on groupby size empirically) | Task 6 (`empirical_group_report` + integration assertion N>=2) |
| §10 risk #2 (coverage gaps -> impute; report count) | Task 5 (missing), Task 6 (ok/thin/missing print), surfaced to `results.md` at compute |
| §10 risk #3 (V3/PD re-roll reported) | Task 10 amendment; existing validation path (no new code) |
| §10 risk #4 (cache CSV, pin columns, fail loud on missing column) | Task 6 (cache in raw/); column names pinned in `filter_5v5`/`aggregate_traded` (KeyError if absent = fail loud) |
| §10 risk #5 (xG opacity — credit + poster disclosure) | Task 1 docstring + Task 10 amendment; poster (out of scope) |
| §10 risk #6 (0–1 scale, no ×100, no double-z; ozs from summed counts) | Tasks 2, 3 (formula tests assert summed-count ratio; standardization is post-z only) |

**Placeholder scan:** no "TODO", "add error handling", "similar to Task N", or undefined-function references. Every function used in a later task is defined in an earlier task (`ozs_pct`, `filter_5v5`, `_wmean`, `aggregate_traded`, `apply_thin_floor`, `_norm_name`, `_blank`, `join_pool`, `load_raw`, `empirical_group_report`, `main`). Reused codebase symbols (`atomic_write_csv`, `RAW_DIR`, `CONTACT_UA`, `session`, `load_players`, `SKILL_COLS`, `EXPECTED_CAP_PREDICTORS`, `_standardize_skill`, `compute_peers`, `compute_expected_cap`, `load_inputs`, `OUT_COLS`) match real signatures verified in `_common.py`, `fetch_nhl_api.py`, and `compute_oaq.py`.

**Type/name consistency:** MoneyPuck source columns are referenced by their verified names (`playerId`, `name`, `team`, `situation`, `icetime`, `games_played`, `onIce_corsiPercentage`, `onIce_xGoalsPercentage`, `I_F_oZoneShiftStarts`, `I_F_dZoneShiftStarts`). Internal feature columns are `cf_pct`/`xgf_pct`/`ozs_pct` everywhere. `onice_status` is `"ok"|"thin"|"missing"`. CSV NULLs are `""`; DataFrame NULLs are NaN. `nhl_player_id`/`playerId` are the same NHL id space (int compare after `.isdigit()` guard). The `compute_oaq.py` edits stay in the peer region (`SKILL_COLS`, the skill merge in `load_inputs`, the skill columns in `OUT_COLS`), distinct from A12's composite region; A13 rebases on A12.

**Known gaps / could-not-map (surfaced to caller):**
1. **§7/§10 risk-3 "V3/PD re-roll re-rolls every gate"** requires no new code — `external_validation`/`evaluate_patterns` in `compute_oaq.py` already run on the new peer sets automatically. No task builds it; Task 11's end-to-end run exercises it. Flagged so the caller knows it is deliberately not a separate task.
2. **`results.md` prose** (the "K peers ... standardized (age, ppg, toi_per_game)" config line at `compute_oaq.py` ~line 1020) still names the 3 OLD features in a hardcoded f-string. The plan does NOT edit that prose string because it is descriptive text, not a method input, and editing it risks colliding with A12's results-writer edits. RECOMMENDATION to the caller: a one-line cosmetic update of that f-string to list all 6 features is desirable for poster honesty but is intentionally left out of the locked task set to keep edits localized; do it as a trivial follow-up after A12+A13 both land.
3. **QoC, poster credit, xG opacity disclosure** (§2/§10 risk-5) are poster/disclosure items, not code — captured in the amendment text (Task 10) and out of scope for this build plan.
4. **`ozs_pct` denominator edge case** (a player with 0 total zone-start counts at 5v5) yields NaN by design (`ozs_pct` returns NaN); that NaN is then imputed by `_standardize_skill` exactly like a thin/missing feature — consistent with the non-exclusionary pool. Noted in case the caller expected 0.5 instead of impute.
