"""A36: redirect enumeration + per-date summation (pure functions only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from augment_wiki_redirects import parse_redirects, merge_daily_by_date  # noqa: E402


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
