"""A38: event-window mechanics + lambda mapping (no I/O)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from diagnostics.lambda_portability import (  # noqa: E402
    event_windows, delta_log_attention, lambda_emp)


def test_event_windows_interior():
    pre, post = event_windows(100)
    assert (min(pre), max(pre)) == (37, 92)      # t-63 .. t-8
    assert (min(post), max(post)) == (108, 163)  # t+8 .. t+63


def test_event_windows_clip_at_window_end():
    # Clipping is relative to the series length passed in, not to a global --
    # a 365-day vector must clip at 364 even though collection now runs 921.
    pre, post = event_windows(340, 365)          # deadline-class mover
    assert max(post) == 364 and len(post) == 17  # truncated


def test_delta_log_attention_min_days_guard():
    daily = [10] * 365
    assert delta_log_attention(daily, 340) is None          # post too short
    assert delta_log_attention(daily, 100) == 0.0           # flat series


def test_lambda_emp_mapping():
    assert lambda_emp(0.0, 0.4) == 0.0        # fully portable
    assert lambda_emp(0.2, 0.4) == 0.5        # midpoint
    assert lambda_emp(0.9, 0.4) == 1.0        # clipped
    assert lambda_emp(0.2, 0.0) is None       # undefined gradient
