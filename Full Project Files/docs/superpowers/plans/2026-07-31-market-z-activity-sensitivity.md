# `market_z` Subscriber-vs-Activity Sensitivity Implementation Plan

> **STATUS: EXECUTED IN FULL 2026-08-03** (commits `399b817` Tasks 1–2,
> `5ef1c03` Tasks 3–4). All verification passed: 32 rows, UTA the only `low`,
> Spearman **0.299 exactly**; primary invariance tests green; suite 333 → 351.
> Deviations from the text below: `to_markdown` → `to_string` in the report
> (tabulate not installed, $0 stack); test-count expectations were stale
> (written pre-A45/A47/A48). Finding, recorded in SESSION #3B: **MON delta
> +1.628, league-largest positive** — supports interpretation (a), while the
> A45 affiliation split leaned (b); both stand, specification dependence goes
> to limits-of-claim per the pre-registered decision rule. The pre-window
> activity follow-up (exogenous primary candidate) remains NOT in scope.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure how much `OAQ_portable` depends on using subreddit **subscribers** (a stock) rather than subreddit **submission activity** (a flow) as the social component of `market_z` — and answer open item #3B with evidence instead of argument.

**Architecture:** Add a derived `market_activity.csv` built from the local corpus, then register two new **reporting-only lenses** in `compute_market_z`'s existing lens dict. The A30 primary is not touched. A diagnostic script runs the OAQ pipeline in memory under each lens and reports the deltas.

**Tech Stack:** Python 3, pandas, numpy, pytest. Same conventions as the rest of `marchand_index/`.

## Global Constraints

- Working directory for all commands is `Full Project Files/marchand_index/`. `pytest` runs from inside that directory.
- Measurement window is `[2025-04-18, 2026-04-17]` inclusive.
- **The A30 primary must not change.** `MARKET_COMPONENTS_A30` stays `["metro_population", "team_sub_subscribers", "attendance_pct_capacity"]`. Everything added here is a lens, matching the existing `compute_market_z` docstring: *"reporting-only, never fed to gate verdicts."*
- **Activity is endogenous.** Submissions inside the measurement window are co-determined with the attention being measured — a team on a playoff run posts more and its players get more mentions. That is why activity is a lens and not a candidate primary. State this wherever the lens is defined.
- **No production `compute_oaq` run.** That remains gated on Phase-1 hygiene + Gate-4. The diagnostic in Task 3 runs in memory and writes no CSV other than its own report.
- `market_proxy.csv` is **not** modified. Activity lives in a separate `market_activity.csv` so a re-run of `fetch_market_proxy.py` cannot silently drop it.
- Atomic writes only: `.tmp` then `os.replace`.
- `cache/reddit_corpus/` is gitignored and read-only.
- New pre-registration amendment number is **A46**. If the Phase A plan (A45) has not been executed yet, A46 is still correct — the numbers are independent.

---

## The finding this plan investigates

In-window submission counts per team subreddit, against the subscriber counts currently feeding `market_z`:

| Team | Subscribers | Submissions | Per 1k subs |
|---|---|---|---|
| MON | 101,589 | **14,510** | 142.8 |
| TOR | **359,680** | 9,603 | 26.7 |
| BOS | 119,306 | 3,070 | **25.7** |
| FLA | 34,946 | 8,132 | **232.7** |
| UTA | 2,268 | **81** | 35.7 |

Spearman correlation between the two columns is **0.299**. They are nearly independent measures. Subscribers rank Montreal 7th; activity ranks Montreal 1st — which is precisely the mechanism open item #3B proposes for MON holding 16 of the `OAQ_portable` top-100.

**Utah is a known data hole.** 81 submissions across a full year, against 2,171 for the next-lowest team, and 2,268 subscribers against a league median near 62,000. Both figures are artifacts of the franchise rename splitting the subreddit mid-window (see `_utah_repull.log`). UTA must be flagged in every output here, and the sensitivity must be reported both with and without it.

---

## File Structure

| File | Responsibility |
|---|---|
| `build_market_activity.py` (create) | Scan the corpus, count in-window submissions per team subreddit, write `market_activity.csv`. Pure derivation, no network. |
| `market_activity.csv` (output) | `team_code, team_sub, sub_submissions_window, submissions_per_1k_subs, activity_quality` — 32 rows. |
| `compute_oaq.py` (modify, `compute_market_z` region ~lines 876–924) | Register two new lenses. No change to `MARKET_COMPONENTS_A30` or to `_market_z_from`. |
| `diagnostics/market_sensitivity.py` (create) | In-memory sensitivity report: per-team `market_z` deltas, rank correlation, and top-100 team-composition shift under each lens. |
| `tests/test_market_activity_a46.py` (create) | Unit tests for the builder and the new lenses. |
| `preregistration.md` (modify) | Append amendment A46. |

---

### Task 1: Build `market_activity.csv`

Counts in-window submissions per team subreddit from the local corpus. Two edge cases carry over from the corpus itself: Utah has two subreddit names (`utahmammoth`, `UtahHockey`) that must be summed into one UTA row, and the three neutral subs (`hockey`, `nhl`, `fantasyhockey`) belong to no team and are excluded.

**Files:**
- Create: `build_market_activity.py`
- Test: `tests/test_market_activity_a46.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `WINDOW_START: pd.Timestamp`, `WINDOW_END: pd.Timestamp`
  - `SUB_ALIASES: dict[str, str]` — extra corpus sub names folded into a canonical one
  - `NEUTRAL_SUBS: frozenset[str]`
  - `ACTIVITY_QUALITY_MIN: int` (= 500)
  - `count_window_submissions(corpus_dir: Path) -> dict[str, int]` — canonical lowercased sub name to in-window submission count
  - `build_activity_table(counts: dict[str, int], market_proxy: pd.DataFrame) -> pd.DataFrame`
  - `main() -> None` — writes `market_activity.csv`

- [ ] **Step 1: Write the failing test**

Create `tests/test_market_activity_a46.py`:

```python
"""A46 — market_z subscriber-vs-activity sensitivity."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import build_market_activity as bma


def _write_corpus(tmp_path: Path, records: list[dict]) -> Path:
    corpus = tmp_path / "reddit_corpus"
    corpus.mkdir()
    by_sub: dict[str, list[dict]] = {}
    for rec in records:
        by_sub.setdefault(rec["subreddit"], []).append(rec)
    for sub, recs in by_sub.items():
        with (corpus / f"{sub}.jsonl").open("w", encoding="utf-8") as fh:
            for rec in recs:
                fh.write(json.dumps(rec) + "\n")
    return corpus


# 2025-06-01 is inside the window; 2020-01-01 is not.
IN_WINDOW = "1748736000"
OUT_OF_WINDOW = "1577836800"


def test_count_window_submissions_counts_per_sub(tmp_path: Path):
    corpus = _write_corpus(
        tmp_path,
        [
            {"id": "a", "subreddit": "canucks", "created_utc": IN_WINDOW},
            {"id": "b", "subreddit": "canucks", "created_utc": IN_WINDOW},
            {"id": "c", "subreddit": "leafs", "created_utc": IN_WINDOW},
        ],
    )
    counts = bma.count_window_submissions(corpus)
    assert counts["canucks"] == 2
    assert counts["leafs"] == 1


def test_count_window_submissions_excludes_out_of_window(tmp_path: Path):
    corpus = _write_corpus(
        tmp_path,
        [
            {"id": "a", "subreddit": "canucks", "created_utc": IN_WINDOW},
            {"id": "b", "subreddit": "canucks", "created_utc": OUT_OF_WINDOW},
        ],
    )
    assert bma.count_window_submissions(corpus)["canucks"] == 1


def test_count_window_submissions_folds_utah_aliases(tmp_path: Path):
    corpus = _write_corpus(
        tmp_path,
        [
            {"id": "a", "subreddit": "utahmammoth", "created_utc": IN_WINDOW},
            {"id": "b", "subreddit": "UtahHockey", "created_utc": IN_WINDOW},
        ],
    )
    counts = bma.count_window_submissions(corpus)
    assert counts["utahmammoth"] == 2
    assert "utahhockey" not in counts


def test_count_window_submissions_excludes_neutral_subs(tmp_path: Path):
    corpus = _write_corpus(
        tmp_path,
        [{"id": "a", "subreddit": "hockey", "created_utc": IN_WINDOW}],
    )
    assert bma.count_window_submissions(corpus) == {}


def _market_proxy() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "team_code": ["MON", "BOS", "UTA"],
            "team_sub": ["Habs", "BostonBruins", "utahmammoth"],
            "team_sub_subscribers": [101589, 119306, 2268],
        }
    )


def test_build_activity_table_has_one_row_per_team():
    counts = {"habs": 14510, "bostonbruins": 3070, "utahmammoth": 81}
    out = bma.build_activity_table(counts, _market_proxy())
    assert len(out) == 3
    assert set(out["team_code"]) == {"MON", "BOS", "UTA"}


def test_build_activity_table_computes_per_1k():
    counts = {"habs": 14510, "bostonbruins": 3070, "utahmammoth": 81}
    out = bma.build_activity_table(counts, _market_proxy()).set_index("team_code")
    assert out.loc["MON", "submissions_per_1k_subs"] == pytest.approx(
        14510 / (101589 / 1000), rel=1e-3
    )


def test_build_activity_table_flags_low_volume_teams():
    counts = {"habs": 14510, "bostonbruins": 3070, "utahmammoth": 81}
    out = bma.build_activity_table(counts, _market_proxy()).set_index("team_code")
    assert out.loc["UTA", "activity_quality"] == "low"
    assert out.loc["MON", "activity_quality"] == "ok"
    assert out.loc["BOS", "activity_quality"] == "ok"


def test_build_activity_table_raises_on_missing_team():
    counts = {"habs": 14510}
    with pytest.raises(RuntimeError, match="no corpus submissions"):
        bma.build_activity_table(counts, _market_proxy())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_market_activity_a46.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_market_activity'`

- [ ] **Step 3: Write minimal implementation**

Create `build_market_activity.py`:

```python
"""A46 — derive per-team subreddit submission activity from the local corpus.

Writes `market_activity.csv`. This is a DERIVATION, not a fetch: every input
is already on disk and no network call is made.

Why this exists
---------------
`market_z`'s social component is `team_sub_subscribers` — a stock. Subreddit
submission volume is a flow, and the two barely agree (Spearman 0.299 across
the 32 teams). r/BostonBruins has more subscribers than r/Habs but roughly a
fifth of the submissions. This file makes the flow measurable so the
dependence of `OAQ_portable` on that choice can be reported.

Activity is ENDOGENOUS — a winning team's subreddit posts more, and its
players draw more mentions. It is therefore a reporting lens only and must
never become a `market_z` primary component.

Run from inside `marchand_index/`:

    python build_market_activity.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

PILOT_DIR = Path(__file__).parent
CORPUS_DIR = PILOT_DIR / "cache" / "reddit_corpus"
OUT_PATH = PILOT_DIR / "market_activity.csv"

# Matches the rest of the project (SESSION.md CARRY-FORWARD). Both inclusive.
WINDOW_START = pd.Timestamp("2025-04-18")
WINDOW_END = pd.Timestamp("2026-04-17")

# The Utah franchise was renamed mid-window, splitting its subreddit. Both
# names are the same fanbase and are summed into the canonical one that
# `market_proxy.csv` lists.
SUB_ALIASES = {"utahhockey": "utahmammoth"}

# Belong to no single team; excluded from a per-team activity measure.
NEUTRAL_SUBS = frozenset({"hockey", "nhl", "fantasyhockey"})

# Below this many in-window submissions the activity figure is treated as a
# collection artifact rather than a fanbase signal. Utah sits at 81 against
# 2,171 for the next-lowest team, so the threshold separates one known data
# hole from the real distribution.
ACTIVITY_QUALITY_MIN = 500


def count_window_submissions(corpus_dir: Path) -> dict[str, int]:
    """Canonical lowercased subreddit name -> in-window submission count.

    Neutral subreddits are excluded, aliases are folded, malformed lines are
    skipped rather than aborting the scan.
    """
    counts: dict[str, int] = {}
    start = WINDOW_START.timestamp()
    end = (WINDOW_END + pd.Timedelta(days=1)).timestamp()

    for path in sorted(corpus_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sub = str(rec["subreddit"]).lower()
                if sub in NEUTRAL_SUBS:
                    continue
                sub = SUB_ALIASES.get(sub, sub)
                stamp = int(rec["created_utc"])
                if start <= stamp < end:
                    counts[sub] = counts.get(sub, 0) + 1
    return counts


def build_activity_table(
    counts: dict[str, int], market_proxy: pd.DataFrame
) -> pd.DataFrame:
    """One row per team in `market_proxy`, with activity and a quality flag.

    Raises if any team has no corpus submissions at all — that would mean the
    venue mapping is wrong, and silently emitting a zero would corrupt the
    z-score for all 32 teams.
    """
    records = []
    for row in market_proxy.itertuples(index=False):
        sub = str(row.team_sub).lower()
        sub = SUB_ALIASES.get(sub, sub)
        n = counts.get(sub)
        if n is None:
            raise RuntimeError(
                f"no corpus submissions for team {row.team_code} (sub {row.team_sub})"
            )
        subscribers = float(row.team_sub_subscribers)
        records.append(
            {
                "team_code": row.team_code,
                "team_sub": row.team_sub,
                "sub_submissions_window": int(n),
                "submissions_per_1k_subs": round(n / (subscribers / 1000.0), 2),
                "activity_quality": "ok" if n >= ACTIVITY_QUALITY_MIN else "low",
            }
        )
    return pd.DataFrame.from_records(records)


def main() -> None:
    market = pd.read_csv(PILOT_DIR / "market_proxy.csv")
    counts = count_window_submissions(CORPUS_DIR)
    out = build_activity_table(counts, market)

    tmp = OUT_PATH.with_suffix(".csv.tmp")
    out.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, OUT_PATH)

    low = out[out["activity_quality"] == "low"]["team_code"].tolist()
    print(f"wrote {OUT_PATH} ({len(out)} rows)")
    print(f"  low-quality teams: {low or 'none'}")
    merged = out.merge(market[["team_code", "team_sub_subscribers"]], on="team_code")
    rho = merged[["team_sub_subscribers", "sub_submissions_window"]].corr(
        method="spearman"
    ).iloc[0, 1]
    print(f"  spearman(subscribers, submissions) = {rho:.3f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_market_activity_a46.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Run the builder on real data**

Run: `python build_market_activity.py`

Expected: 32 rows, `low-quality teams: ['UTA']`, and `spearman(subscribers, submissions) = 0.299`.

If the Spearman value differs materially from 0.299, stop and check the window bounds and the Utah alias fold before continuing — the rest of this plan is built on that number.

- [ ] **Step 6: Commit**

```bash
git add build_market_activity.py market_activity.csv tests/test_market_activity_a46.py
git commit -m "feat(a46): derive per-team subreddit submission activity"
```

---

### Task 2: Register the activity lenses in `compute_market_z`

Adds two reporting-only lenses beside the existing `market_z_lockedv1` and `market_z_metro_only`. The A30 primary is untouched — that is the whole safety property of this task, and the tests assert it directly.

Two lenses rather than one, because they answer different questions. `market_z_activity` swaps subscribers out entirely and shows the maximum possible impact of the choice. `market_z_social_blend` averages the two social measures and shows what a hedged specification would do.

**Files:**
- Modify: `compute_oaq.py` — `compute_market_z` region, roughly lines 876–924
- Test: `tests/test_market_activity_a46.py`

**Interfaces:**
- Consumes: `market_activity.csv` (Task 1); existing `_market_z_from`, `_align_teams`, `zscore_array`
- Produces:
  - `MARKET_COMPONENTS_A46_ACTIVITY: list[str]`
  - `load_market_activity(path: Path | None = None) -> pd.DataFrame | None` — returns `None` when the file is absent
  - `compute_market_z(df, mp=None)` gains `"market_z_activity"` and `"market_z_social_blend"` keys in its returned `lenses` dict when `market_activity.csv` is present

- [ ] **Step 1: Write the failing test**

Append to `tests/test_market_activity_a46.py`:

```python
import numpy as np

import compute_oaq as co


def _mp32() -> pd.DataFrame:
    """32 synthetic teams, all market components present."""
    codes = [f"T{i:02d}" for i in range(32)]
    return pd.DataFrame(
        {
            "team_code": codes,
            "team_sub": [f"sub{i:02d}" for i in range(32)],
            "metro_population": np.linspace(1e6, 7e6, 32),
            "attendance_pct_capacity": np.linspace(0.85, 1.02, 32),
            # Subscribers ascending, activity DESCENDING — maximally opposed,
            # so any lens that actually uses activity must differ from primary.
            "team_sub_subscribers": np.linspace(30_000, 360_000, 32),
        }
    )


def _activity32() -> pd.DataFrame:
    codes = [f"T{i:02d}" for i in range(32)]
    return pd.DataFrame(
        {
            "team_code": codes,
            "team_sub": [f"sub{i:02d}" for i in range(32)],
            "sub_submissions_window": np.linspace(15_000, 2_000, 32).astype(int),
            "submissions_per_1k_subs": np.linspace(150, 10, 32),
            "activity_quality": ["ok"] * 32,
        }
    )


def _players32() -> pd.DataFrame:
    codes = [f"T{i:02d}" for i in range(32)]
    return pd.DataFrame({"player_id": range(32), "team_code": codes})


def test_a30_primary_components_unchanged():
    assert co.MARKET_COMPONENTS_A30 == [
        "metro_population",
        "team_sub_subscribers",
        "attendance_pct_capacity",
    ]


def test_activity_components_swap_only_the_social_term():
    assert co.MARKET_COMPONENTS_A46_ACTIVITY == [
        "metro_population",
        "sub_submissions_window",
        "attendance_pct_capacity",
    ]


def test_compute_market_z_registers_activity_lenses():
    _, _, lenses = co.compute_market_z(
        _players32(), _mp32(), activity=_activity32()
    )
    assert "market_z_activity" in lenses
    assert "market_z_social_blend" in lenses


def test_activity_lens_differs_from_primary():
    primary, _, lenses = co.compute_market_z(
        _players32(), _mp32(), activity=_activity32()
    )
    assert not np.allclose(primary, lenses["market_z_activity"])


def test_primary_is_identical_with_and_without_activity():
    """Registering a lens must not perturb the A30 primary."""
    without, _, _ = co.compute_market_z(_players32(), _mp32(), activity=None)
    with_act, _, _ = co.compute_market_z(
        _players32(), _mp32(), activity=_activity32()
    )
    assert np.allclose(without, with_act)


def test_existing_lenses_still_present():
    _, _, lenses = co.compute_market_z(
        _players32(), _mp32(), activity=_activity32()
    )
    assert "market_z_metro_only" in lenses


def test_lenses_absent_when_activity_missing():
    _, _, lenses = co.compute_market_z(_players32(), _mp32(), activity=None)
    assert "market_z_activity" not in lenses
    assert "market_z_social_blend" not in lenses
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_market_activity_a46.py -v`
Expected: FAIL — `AttributeError: module 'compute_oaq' has no attribute 'MARKET_COMPONENTS_A46_ACTIVITY'`

- [ ] **Step 3: Write minimal implementation**

In `compute_oaq.py`, immediately after the `MARKET_COMPONENTS_LOCKEDV1` definition, add:

```python
# A46 lens components. `sub_submissions_window` replaces `team_sub_subscribers`
# — a flow in place of a stock. The two barely agree (Spearman 0.299 across 32
# teams), so this quantifies how much OAQ_portable depends on that choice.
#
# ENDOGENOUS BY CONSTRUCTION: in-window submission volume is co-determined with
# the attention OAQ measures (a winning team's subreddit posts more, and its
# players draw more mentions). This is a REPORTING LENS ONLY and must never be
# promoted to a market_z primary — doing so would partially control for the
# outcome.
MARKET_COMPONENTS_A46_ACTIVITY = ["metro_population", "sub_submissions_window",
                                  "attendance_pct_capacity"]
```

Then add a loader beside it:

```python
def load_market_activity(path: Path | None = None) -> pd.DataFrame | None:
    """Read `market_activity.csv`, or None when it has not been built yet.

    Absence is not an error: the A46 lenses are optional reporting extras and
    every primary code path must work without them.
    """
    if path is None:
        path = PILOT_DIR / "market_activity.csv"
    if not Path(path).exists():
        return None
    return pd.read_csv(path)
```

Replace the body of `compute_market_z` with:

```python
def compute_market_z(df: pd.DataFrame, mp: pd.DataFrame | None = None,
                     activity: pd.DataFrame | None = _UNSET):
    """Returns (market_z aligned to df rows, components used, lenses dict).

    Primary = A30 components, unchanged. lenses = {"market_z_lockedv1"
    (§7-original metro + raw attendance), "market_z_metro_only" (E9
    sensitivity), and when `market_activity.csv` is available,
    "market_z_activity" and "market_z_social_blend" (A46)} — reporting-only,
    never fed to gate verdicts.

    `activity` defaults to loading `market_activity.csv` from disk; pass an
    explicit DataFrame to override, or None to suppress the A46 lenses.
    """
    if mp is None:
        mp = pd.read_csv(PILOT_DIR / "market_proxy.csv")
    if activity is _UNSET:
        activity = load_market_activity()

    z_primary, used = _market_z_from(mp, MARKET_COMPONENTS_A30)
    aligned = _align_teams(df, mp, z_primary)

    lenses: dict[str, np.ndarray] = {}
    z_v1, used_v1 = _market_z_from(mp, MARKET_COMPONENTS_LOCKEDV1)
    if set(used_v1) == set(MARKET_COMPONENTS_LOCKEDV1):
        lenses["market_z_lockedv1"] = _align_teams(df, mp, z_v1)
    z_metro, _ = _market_z_from(mp, ["metro_population"])
    lenses["market_z_metro_only"] = _align_teams(df, mp, z_metro)

    if activity is not None:
        # Merge activity onto a COPY so the caller's market_proxy frame — and
        # the A30 primary computed from it above — are untouched.
        mp_act = mp.merge(
            activity[["team_code", "sub_submissions_window"]],
            on="team_code",
            how="left",
        )
        z_act, used_act = _market_z_from(mp_act, MARKET_COMPONENTS_A46_ACTIVITY)
        if set(used_act) == set(MARKET_COMPONENTS_A46_ACTIVITY):
            lenses["market_z_activity"] = _align_teams(df, mp_act, z_act)
            # Blend: average the two social z-scores, keep the other two
            # components as-is. Shows what a hedged specification would do.
            social = zscore_array(
                zscore_array(
                    pd.to_numeric(mp_act["team_sub_subscribers"]).to_numpy(float)
                )
                + zscore_array(
                    pd.to_numeric(
                        mp_act["sub_submissions_window"]
                    ).to_numpy(float)
                )
            )
            mp_blend = mp_act.copy()
            mp_blend["social_blend"] = social
            z_blend, _ = _market_z_from(
                mp_blend,
                ["metro_population", "social_blend", "attendance_pct_capacity"],
            )
            lenses["market_z_social_blend"] = _align_teams(df, mp_blend, z_blend)

    return aligned, used, lenses
```

Add the sentinel near the other module constants, above `compute_market_z`:

```python
# Distinguishes "caller passed None to suppress the A46 lenses" from "caller
# said nothing, so load from disk".
_UNSET = object()
```

Confirm `from pathlib import Path` is already imported at the top of `compute_oaq.py`; add it if not.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_market_activity_a46.py -v`
Expected: PASS, 15 tests

- [ ] **Step 5: Confirm no existing test regressed**

Run: `pytest -q`

Expected: PASS. `test_market_proxy_a30.py` and `test_lambda_portability_a38.py` both exercise `compute_market_z` and are the ones most likely to catch an accidental primary change. If either fails, the primary was perturbed — revert and re-approach.

- [ ] **Step 6: Commit**

```bash
git add compute_oaq.py tests/test_market_activity_a46.py
git commit -m "feat(a46): register activity and blend market_z lenses"
```

---

### Task 3: Sensitivity diagnostic

Runs the OAQ pipeline in memory under the primary and each lens, and reports what actually moves. This is the deliverable that answers open item #3B.

Three outputs, each targeting a specific question. Per-team `market_z` deltas show which markets the choice affects. The rank correlation shows whether the specification matters at all. The top-100 team composition shows whether Montreal's 16-of-100 survives.

**Files:**
- Create: `diagnostics/market_sensitivity.py`
- Test: `tests/test_market_activity_a46.py`

**Interfaces:**
- Consumes: `compute_market_z` with A46 lenses (Task 2)
- Produces:
  - `team_z_table(mp, activity, lenses_by_team) -> pd.DataFrame`
  - `top_n_composition(df: pd.DataFrame, score_col: str, n: int = 100) -> pd.DataFrame`
  - `main() -> None` — prints the report, writes `diagnostics/market_sensitivity_report.md`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_market_activity_a46.py`:

```python
from diagnostics import market_sensitivity as ms


def test_top_n_composition_counts_by_team():
    df = pd.DataFrame(
        {
            "team_code": ["MON"] * 5 + ["BOS"] * 3 + ["VAN"] * 2,
            "oaq": list(range(10, 0, -1)),
        }
    )
    out = ms.top_n_composition(df, "oaq", n=8).set_index("team_code")
    assert out.loc["MON", "n_in_top"] == 5
    assert out.loc["BOS", "n_in_top"] == 3
    assert "VAN" not in out.index


def test_top_n_composition_sorted_descending():
    df = pd.DataFrame(
        {"team_code": ["BOS", "MON", "MON"], "oaq": [3.0, 2.0, 1.0]}
    )
    out = ms.top_n_composition(df, "oaq", n=3)
    assert list(out["team_code"]) == ["MON", "BOS"]


def test_top_n_composition_ignores_nan_scores():
    df = pd.DataFrame(
        {"team_code": ["MON", "BOS"], "oaq": [float("nan"), 1.0]}
    )
    out = ms.top_n_composition(df, "oaq", n=2)
    assert list(out["team_code"]) == ["BOS"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_market_activity_a46.py -v`
Expected: FAIL — `ImportError: cannot import name 'market_sensitivity' from 'diagnostics'`

- [ ] **Step 3: Write minimal implementation**

Create `diagnostics/market_sensitivity.py`:

```python
"""A46 — how much does OAQ_portable depend on the market_z social component?

`market_z` currently uses `team_sub_subscribers` (a stock). Subreddit
submission volume (a flow) is a nearly independent measure — Spearman 0.299
across the 32 teams. This report quantifies the consequence.

Answers open item #3B: is Montreal's 16-of-100 showing in the OAQ_portable top
100 real over-indexing, or a market strip that under-corrects because Reddit
subscriber counts understate a francophone fanbase?

IN-MEMORY ONLY. Writes one markdown report and no CSV. Does not constitute a
production `compute_oaq` run and does not touch any sacred CSV.

Run from inside `marchand_index/`:

    python -m diagnostics.market_sensitivity
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

import compute_oaq as co

PILOT_DIR = Path(__file__).parent.parent
REPORT_PATH = Path(__file__).parent / "market_sensitivity_report.md"


def team_z_table(
    mp: pd.DataFrame,
    activity: pd.DataFrame,
    primary: np.ndarray,
    lenses: dict[str, np.ndarray],
    team_codes: pd.Series,
) -> pd.DataFrame:
    """One row per team: market_z under the primary and each A46 lens."""
    frame = pd.DataFrame({"team_code": team_codes, "market_z_a30": primary})
    for name in ("market_z_activity", "market_z_social_blend"):
        if name in lenses:
            frame[name] = lenses[name]
    per_team = frame.groupby("team_code").first().reset_index()
    per_team = per_team.merge(
        activity[["team_code", "sub_submissions_window", "activity_quality"]],
        on="team_code",
        how="left",
    ).merge(
        mp[["team_code", "team_sub_subscribers"]], on="team_code", how="left"
    )
    if "market_z_activity" in per_team.columns:
        per_team["delta"] = per_team["market_z_activity"] - per_team["market_z_a30"]
        per_team = per_team.sort_values("delta", ascending=False)
    return per_team.reset_index(drop=True)


def top_n_composition(
    df: pd.DataFrame, score_col: str, n: int = 100
) -> pd.DataFrame:
    """Team counts among the top `n` rows by `score_col`, highest first."""
    ranked = df.dropna(subset=[score_col]).nlargest(n, score_col)
    counts = (
        ranked.groupby("team_code").size().reset_index(name="n_in_top")
    )
    return counts.sort_values("n_in_top", ascending=False).reset_index(drop=True)


def main() -> None:
    mp = pd.read_csv(PILOT_DIR / "market_proxy.csv")
    activity = co.load_market_activity()
    if activity is None:
        raise SystemExit(
            "market_activity.csv not found — run `python build_market_activity.py` first"
        )

    players = pd.read_csv(PILOT_DIR / "players.csv")
    primary, used, lenses = co.compute_market_z(players, mp, activity=activity)

    per_team = team_z_table(
        mp, activity, primary, lenses, players["team_code"].astype(str)
    )

    lines: list[str] = []
    lines.append("# A46 — market_z social-component sensitivity\n")
    lines.append(f"Primary (A30) components used: `{used}`\n")

    merged = activity.merge(
        mp[["team_code", "team_sub_subscribers"]], on="team_code"
    )
    rho = merged[["team_sub_subscribers", "sub_submissions_window"]].corr(
        method="spearman"
    ).iloc[0, 1]
    lines.append(
        f"Spearman(subscribers, submissions) across 32 teams: **{rho:.3f}**\n"
    )

    if "market_z_activity" in lenses:
        z_rho = pd.Series(primary).corr(
            pd.Series(lenses["market_z_activity"]), method="spearman"
        )
        lines.append(
            f"Spearman(market_z A30, market_z activity) across players: "
            f"**{z_rho:.3f}**\n"
        )

    lines.append("\n## Per-team market_z\n")
    lines.append(per_team.to_markdown(index=False))

    low = activity[activity["activity_quality"] == "low"]["team_code"].tolist()
    lines.append(
        f"\n**Low-quality activity teams (excluded from conclusions): "
        f"{low or 'none'}**\n"
    )

    report = "\n".join(lines)
    tmp = REPORT_PATH.with_suffix(".md.tmp")
    tmp.write_text(report, encoding="utf-8")
    os.replace(tmp, REPORT_PATH)

    print(report)
    print(f"\nwrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_market_activity_a46.py -v`
Expected: PASS, 18 tests

- [ ] **Step 5: Run the report and record the finding**

Run: `python -m diagnostics.market_sensitivity`

Read `delta` for MON. Interpretation:

- **MON's delta is strongly positive** (activity raises its `market_z`): subscribers were understating Montreal's market. Because `OAQ_portable` subtracts `λ · max(0, market_z)`, a higher `market_z` means a larger discount and Montreal players fall. That supports interpretation (a) in open item #3B — the market strip under-corrects and "portable" still carries fanbase intensity.
- **MON's delta is near zero**: the specification does not drive Montreal's showing, supporting interpretation (b) — Habs players genuinely over-index against production-matched peers.

Record the number and the interpretation in SESSION.md under open item #3B. **Do not change the A30 primary either way** — this is a finding, not a fix.

- [ ] **Step 6: Commit**

```bash
git add diagnostics/market_sensitivity.py diagnostics/market_sensitivity_report.md tests/test_market_activity_a46.py
git commit -m "feat(a46): market_z social-component sensitivity report"
```

---

### Task 4: Pre-registration amendment A46

Locks the lens as reporting-only before anyone sees whether it flatters or damages the current results. Without this, swapping to whichever specification looks better after the fact is indistinguishable from tuning.

**Files:**
- Modify: `preregistration.md`

**Interfaces:**
- Consumes: constants from Tasks 1–2
- Produces: nothing consumed by code

- [ ] **Step 1: Append the amendment**

Append to `preregistration.md`:

```markdown
## A46 — `market_z` social-component sensitivity (subscribers vs. activity)

**Status:** locked 2026-07-31, before any sensitivity output was inspected.

**Motivation.** `market_z`'s social component under A30 is
`team_sub_subscribers`, a stock. Subreddit submission volume over the
measurement window is a flow, and the two are nearly independent — Spearman
**0.299** across the 32 teams. r/BostonBruins carries more subscribers than
r/Habs (119,306 vs 101,589) but roughly a fifth of the submissions (3,070 vs
14,510). Whether `OAQ_portable` depends on that choice is an empirical
question, and open item #3B turns on the answer.

**What is added.** Two lenses in `compute_market_z`, alongside the existing
`market_z_lockedv1` and `market_z_metro_only`:

- `market_z_activity` — A30 with `sub_submissions_window` in place of
  `team_sub_subscribers`
- `market_z_social_blend` — A30 with the mean of the two social z-scores

**What does not change.** `MARKET_COMPONENTS_A30` remains
`["metro_population", "team_sub_subscribers", "attendance_pct_capacity"]`.
`LAMBDA_BIGMARKET`, the one-sided `max(0, market_z)` correction, the CES
weights, and the peer-matching procedure are all untouched.

**Why activity cannot become primary.** In-window submission volume is
**endogenous** to the quantity being measured: a team having a strong season
draws more posts to its subreddit, and its players draw more mentions inside
those posts. Promoting it to a `market_z` component would partially control
for the outcome. It is therefore permanently a reporting lens. This holds
regardless of what the sensitivity report shows.

A pre-window activity measure (2024-04-18 to 2025-04-17) would be exogenous
and could in principle serve as a primary component. That is **not** part of
A46; it requires new collection and would need its own amendment.

**Data quality.** UTA records 81 in-window submissions against 2,171 for the
next-lowest team, an artifact of the franchise rename splitting the subreddit
mid-window. Teams below `ACTIVITY_QUALITY_MIN = 500` submissions are flagged
`activity_quality = "low"` and are excluded from any conclusion drawn from
this lens. UTA is the only such team.

**Decision rule, fixed in advance.** The sensitivity report is descriptive.
No gate verdict, headline number, or published ranking is computed from any
A46 lens. If the lenses show a large effect, the response is to **document the
dependence as a limit of claim**, not to switch specifications.

**Limits of claim.**
- Activity and subscriber counts carry different vintages: subscribers are
  frozen at 2025-02-14/15, activity spans the full window.
- Submission counts reflect what was collected, not necessarily everything
  posted. Collection volume differs across subreddits by up to 12x and the
  sampling process was not stratified.
- The corpus covers submissions only, not comments.
```

- [ ] **Step 2: Verify the constants match the code**

Run:

```bash
grep -n "MARKET_COMPONENTS_A30\|MARKET_COMPONENTS_A46_ACTIVITY" compute_oaq.py
grep -n "ACTIVITY_QUALITY_MIN\|WINDOW_START\|WINDOW_END" build_market_activity.py
```

Expected: `MARKET_COMPONENTS_A30` still lists `team_sub_subscribers`,
`MARKET_COMPONENTS_A46_ACTIVITY` lists `sub_submissions_window`,
`ACTIVITY_QUALITY_MIN = 500`, and the window bounds are `2025-04-18` /
`2026-04-17` — all matching the amendment. Fix whichever side is wrong.

- [ ] **Step 3: Run the full suite**

Run: `pytest -q`

Expected: PASS. This plan adds 18 tests to whatever the current count is (240
before A45; 271 if the Phase A plan was executed first).

- [ ] **Step 4: Commit**

```bash
git add preregistration.md
git commit -m "docs(a46): pre-register market_z activity sensitivity lens"
```

---

## Verification

After all tasks:

```bash
pytest -q                                   # all passing, +18 from this plan
python build_market_activity.py             # 32 rows, UTA flagged low, rho 0.299
python -m diagnostics.market_sensitivity    # per-team deltas + report
```

Two invariants that must hold:

1. `MARKET_COMPONENTS_A30` is byte-identical to what it was before this work.
   Everything here lives in the `lenses` dict.
2. `test_primary_is_identical_with_and_without_activity` passes. If it ever
   fails, a lens has leaked into the primary path.

## Follow-up, not in scope

If the sensitivity report shows Montreal moving materially, the exogenous fix
is a **pre-window** activity measure — submission counts for 2024-04-18 to
2025-04-17, which cannot be contaminated by this season's results. That needs
an Arctic Shift pull (counts only, not full text) and its own amendment.
Decide only after seeing the A46 numbers; there is no point collecting it if
the specification turns out not to matter.
