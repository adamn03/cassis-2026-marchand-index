"""Unit tests for the A13 6-feature peer (skill) vector."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
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
