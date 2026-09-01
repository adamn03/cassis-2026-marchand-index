"""A36: redirect enumeration + per-date summation + split-window fail-safe."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import augment_wiki_redirects as awr  # noqa: E402
from augment_wiki_redirects import (  # noqa: E402
    fetch_daily_pairs, merge_daily_by_date, parse_redirects,
)


# --------------------------------------------------------------------------- #
# fake HTTP session for split-window fail-safe tests                           #
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, status, items=None):
        self.status_code = status
        self._items = items or []

    def json(self):
        return {"items": self._items}

    def raise_for_status(self):
        pass


class _FakeSession:
    """Routes s.get(url) by the '/daily/{start}/{end}' substring in the URL."""

    def __init__(self, routes):
        self.routes = routes            # {"/daily/START/END": _Resp}
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        for key, resp in self.routes.items():
            if key in url:
                return resp
        return _Resp(404)


_FULL = "/daily/20250418/20260417"
_H1 = "/daily/20250418/20251017"
_H2 = "/daily/20251018/20260417"


def test_parse_redirects_extracts_and_filters_disambig():
    api_json = {"query": {"pages": {
        "1": {"title": "Alexander Ovechkin", "redirects": [
            {"title": "Alex Ovechkin"},
            {"title": "Ovechkin (disambiguation)"},
            {"title": "Alexander Owetschkin"},
        ]},
        "2": {"title": "Sidney Crosby"},  # no redirects key
    }}}
    out = parse_redirects(api_json)
    assert out["Alexander Ovechkin"] == ["Alex Ovechkin", "Alexander Owetschkin"]
    assert out["Sidney Crosby"] == []


def test_merge_daily_by_date_sums_and_handles_gaps():
    canonical = [("2025041800", 100), ("2025041900", 120), ("2025042100", 90)]
    redirect = [("2025041900", 5), ("2025042000", 7)]
    merged = merge_daily_by_date([canonical, redirect])
    assert merged == [("2025041800", 100), ("2025041900", 125),
                      ("2025042000", 7), ("2025042100", 90)]


def test_merge_daily_by_date_empty_inputs():
    assert merge_daily_by_date([]) == []
    assert merge_daily_by_date([[], [("2025041800", 3)]]) == [("2025041800", 3)]


# --------------------------------------------------------------------------- #
# split-window fail-safe (A36 fix 2026-07-21): a partial (one-half) fetch must  #
# NOT be returned — it would truncate a good stored full-year total via RESTATE #
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(awr.time, "sleep", lambda *a, **k: None)


def test_full_window_200_returns_complete_series_without_splitting():
    items = [{"timestamp": "2025041800", "views": 71385}]
    s = _FakeSession({_FULL: _Resp(200, items)})
    out = fetch_daily_pairs(s, "en.wikipedia", "Leo Carlsson")
    assert out == [("2025041800", 71385)]
    assert not any(_H1 in u or _H2 in u for u in s.calls)  # no split needed


def test_one_half_404_returns_none_not_partial():
    # Brzustewicz live case: full 404, h1 200 (6508), h2 404 -> MUST be None,
    # so the caller keeps the authoritative stored 16153 instead of overwriting.
    s = _FakeSession({
        _FULL: _Resp(404),
        _H1: _Resp(200, [{"timestamp": "2025041800", "views": 6508}]),
        _H2: _Resp(404),
    })
    assert fetch_daily_pairs(s, "en.wikipedia", "Hunter Brzustewicz") is None


def test_other_half_404_also_returns_none():
    # Whitecloud live case: full 404, h1 404, h2 200 (61129) -> None.
    s = _FakeSession({
        _FULL: _Resp(404),
        _H1: _Resp(404),
        _H2: _Resp(200, [{"timestamp": "2025120100", "views": 61129}]),
    })
    assert fetch_daily_pairs(s, "en.wikipedia", "Zach Whitecloud") is None


def test_both_halves_200_recovers_complete_merged_series():
    # Genuine recovery: full flakes but BOTH halves 200 -> merged, non-null.
    s = _FakeSession({
        _FULL: _Resp(404),
        _H1: _Resp(200, [{"timestamp": "2025041800", "views": 100}]),
        _H2: _Resp(200, [{"timestamp": "2025120100", "views": 250}]),
    })
    out = fetch_daily_pairs(s, "en.wikipedia", "Someone")
    assert out == [("2025041800", 100), ("2025120100", 250)]


def test_full_404_all_sub_windows_404_returns_none():
    s = _FakeSession({_FULL: _Resp(404), _H1: _Resp(404), _H2: _Resp(404)})
    assert fetch_daily_pairs(s, "en.wikipedia", "Nobody") is None
