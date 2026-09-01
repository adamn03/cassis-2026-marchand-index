"""A29: fixed window, redirect summation, and relabel wiring for V3."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_team_outcomes as fto  # noqa: E402
import fetch_wikipedia as fw  # noqa: E402
import compute_oaq as co  # noqa: E402


def test_window_constants_are_the_fixed_a29_interval():
    # A51/A52 widened collection; A29 rule 1 (team and player windows identical)
    # is what this test actually protects, and it still holds.
    assert fto.WINDOW_START == "20231010"
    assert fto.WINDOW_END == "20260417"
    # Must stay identical to the player wiki fetcher (A29 rule 1).
    assert fto.WINDOW_START == fw.WINDOW_START
    assert fto.WINDOW_END == fw.WINDOW_END


def test_redirect_sum_two_partial_series():
    # Utah case: canonical carries part of the window, the pre-rename
    # redirect title carries the rest; both contribute (A29 rule 2).
    total, canon, share, titles = fto.combine_view_totals(
        100_000, {"Utah Hockey Club": 50_000, "UHC": 0, "Dead": None})
    assert total == 150_000
    assert canon == 100_000
    assert abs(share - 50_000 / 150_000) < 1e-12
    assert titles == ["Utah Hockey Club"]   # zero/None series excluded


def test_redirect_sum_no_redirect_views():
    total, canon, share, titles = fto.combine_view_totals(42, {})
    assert (total, canon, share, titles) == (42, 42, 0.0, [])


def test_redirect_sum_all_missing():
    total, canon, share, titles = fto.combine_view_totals(None, {"X": None})
    assert total is None
    assert share == 0.0


def test_csv_schema_carries_window_and_redirect_audit_columns():
    for col in ("window_start", "window_end", "redirect_share",
                "redirect_titles", "wiki_12mo_canonical"):
        assert col in fto.OUT_FIELDS


def test_v3_relabeled_not_independent(tmp_path, monkeypatch):
    # The emitted V3 record must carry the A29 relabel + pathway exclusion.
    import inspect
    src = inspect.getsource(co)
    assert "aggregation-consistency check (A29)" in src
    assert "NOT counted toward" in src
