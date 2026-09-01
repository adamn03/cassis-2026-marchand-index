"""Unit tests for the A16 anchored-Trends pure logic (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_trends as ft  # noqa: E402


def test_timeframe_is_the_widened_collection_window():
    """A51/A52 widened collection. Trends is the one component that could NOT be
    sliced back to the A11 window afterwards -- it stores a normalised mean, and
    the weekly series was averaged away at fetch time. Recorded in
    V-A11-Window and disclosed in the published methods."""
    assert ft.TIMEFRAME == "2023-10-10 2026-04-17"


def test_anchor_is_locked_a16_value():
    assert ft.ANCHOR_NAME == "Brad Marchand"


def test_ratio_basic():
    assert ft.ratio_from_means(10.0, 40.0) == 0.25


def test_ratio_zero_player_is_true_zero():
    assert ft.ratio_from_means(0.0, 40.0) == 0.0


def test_ratio_none_when_anchor_missing_or_zero():
    # A16: a zero/absent anchor is a throttle artifact, not a valid scale.
    assert ft.ratio_from_means(10.0, 0.0) is None
    assert ft.ratio_from_means(10.0, None) is None
    assert ft.ratio_from_means(None, 40.0) is None


def test_output_fields_carry_a16_audit_columns():
    for col in ("query_mid", "trends_method", "player_mean_scaled",
                "anchor_mean_scaled"):
        assert col in ft.FIELDS
