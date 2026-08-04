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
