"""Unit tests for the A12 re-locked composite + wiki_intl sentinel renorm."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


# --- Task 7: re-locked weights ---

def test_weights_are_a12_vector_summing_to_one():
    assert co.WEIGHTS == {
        "wiki_12mo": 0.29,
        "wiki_intl_12mo": 0.11,
        "reddit_mentions_12mo": 0.27,
        "reddit_upvotes_12mo": 0.17,
        "trends_12mo": 0.16,
    }
    assert abs(sum(co.WEIGHTS.values()) - 1.0) < 1e-9


def test_instagram_dropped_from_composite():
    assert "instagram_followers" not in co.WEIGHTS
    assert "instagram_followers" not in co.COMPONENTS


def test_wiki_intl_is_a_component():
    assert "wiki_intl_12mo" in co.COMPONENTS


# --- Task 8: load_inputs merge + renorm ---

def test_engagement_renorm_drops_null_wiki_intl():
    import pandas as pd
    df = pd.DataFrame({
        "wiki_12mo": [10.0, 20.0, 30.0],
        "wiki_intl_12mo": [5.0, np.nan, 15.0],
        "reddit_mentions_12mo": [1.0, 2.0, 3.0],
        "reddit_upvotes_12mo": [4.0, 5.0, 6.0],
        "trends_12mo": [7.0, 8.0, 9.0],
    })
    er, dropped = co.compute_engagement_raw(df)
    assert dropped[1] == "wiki_intl_12mo"
    assert np.isfinite(er[1])
    assert dropped[0] == "" and dropped[2] == ""


def test_load_inputs_has_wiki_intl_column():
    import pandas as pd
    try:
        df = co.load_inputs()
    except FileNotFoundError:
        import pytest
        pytest.skip("raw inputs not materialized")
    assert "wiki_intl_12mo" in df.columns
    assert pd.api.types.is_numeric_dtype(df["wiki_intl_12mo"])


# --- Task 9: bootstrap component dict + intl daily loader ---

def test_bootstrap_component_dict_has_no_instagram():
    import inspect
    src = inspect.getsource(co.bootstrap_player_cis)
    assert "instagram_followers" not in src
    assert "wiki_intl_12mo" in src


def test_load_wiki_intl_daily_summed_concats_pool(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "wiki_intl_daily.csv").write_text(
        "player_id,edition,n_days,daily_views\n"
        "1,cs,2,50|50\n"
        "1,sv,1,40\n"
        "2,ru,3,1|2|3\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(co, "RAW_DIR", raw)
    out = co.load_wiki_intl_daily_summed()
    assert set(out.keys()) == {1, 2}
    assert sorted(out[1].tolist()) == [40.0, 50.0, 50.0]  # pooled cs+sv days
    assert out[2].tolist() == [1.0, 2.0, 3.0]


# --- Task 10: no residual instagram in results writer ---

def test_no_instagram_column_reference_in_results_writer():
    import inspect
    src = inspect.getsource(co.write_results_md)
    assert "instagram_followers" not in src
