"""A39: concentration statistics (no I/O)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from diagnostics.attention_concentration import (  # noqa: E402
    gini, top_share, between_team_r2)


def test_gini_known_value():
    # [0,0,10]: sum|diff| over ordered pairs = 40; mean=10/3
    # G = 40 / (2*9*10/3) = 0.6667
    assert gini([0, 0, 10]) == pytest.approx(2 / 3)


def test_gini_equality_is_zero():
    assert gini([5, 5, 5, 5]) == pytest.approx(0.0)


def test_top_share():
    assert top_share([1, 1, 1, 7], 1) == pytest.approx(0.7)


def test_between_team_r2_extremes():
    # identical within teams, different across -> R2 = 1
    assert between_team_r2([1, 1, 9, 9], ["A", "A", "B", "B"]) == pytest.approx(1.0)
    # identical everywhere -> ss_total = 0 -> 0.0 guard
    assert between_team_r2([3, 3, 3, 3], ["A", "A", "B", "B"]) == 0.0
