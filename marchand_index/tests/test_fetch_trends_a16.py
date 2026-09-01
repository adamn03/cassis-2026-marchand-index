"""Unit tests for the A16 anchored-Trends pure logic (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_trends as ft  # noqa: E402


def test_timeframe_is_the_locked_composite_window():
    """Trends must be measured over the SAME window as every other component.

    It briefly was not: A51/A52 widened `WINDOW_START_DATE` for the three-season
    panel and this fetcher inherited it, putting the component on 921 days while
    the rest sat on 365 (V-A11-Window). It could not be sliced back afterwards
    -- the weekly series is averaged away at fetch time -- so it was re-fetched
    on the correct window (V-Trends-Refetch). This asserts the composite window,
    not the collection window, which is the distinction that was missed."""
    import _common as c
    assert ft.TIMEFRAME == "2025-04-18 2026-04-17"
    assert ft.TIMEFRAME == (f"{c.COMPOSITE_WINDOW_START_DATE.isoformat()} "
                            f"{c.WINDOW_END_DATE.isoformat()}")
    assert c.COMPOSITE_WINDOW_DAYS == 365


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
