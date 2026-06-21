"""Unit tests for fetch_wikipedia_intl pure logic (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pilot2/
import fetch_wikipedia_intl as fwi  # noqa: E402


def test_whitelist_is_locked_seven_editions():
    assert fwi.WHITELIST == ("sv", "fi", "cs", "ru", "de", "sk", "fr")


def test_window_is_a11_fixed_hardcoded():
    assert fwi.WINDOW_START == "20250418"
    assert fwi.WINDOW_END == "20260417"


def test_window_strings_returns_fixed_window_and_today_fetch_date():
    import datetime as dt
    start, end, fetch_date = fwi.window_strings()
    assert (start, end) == ("20250418", "20260417")
    assert fetch_date == dt.date.today().isoformat()
