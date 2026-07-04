"""Unit tests for the A20 jersey-list update (pure data/logic, no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_external_outcomes as eo  # noqa: E402


def test_2025_26_list_is_nhl_pr_top10_in_order():
    assert [nm for _, nm in eo.JERSEY_2025_26] == [
        "Connor Bedard", "Alex Ovechkin", "Sidney Crosby", "Jack Hughes",
        "Connor McDavid", "Nathan MacKinnon", "Cale Makar", "David Pastrnak",
        "Auston Matthews", "Macklin Celebrini"]
    assert [rk for rk, _ in eo.JERSEY_2025_26] == list(range(1, 11))


def test_v1a_rank_map_uses_most_recent_2025_26():
    # A3 rule: most-recent list drives jersey_rank. Bedard 1 (was 2 in
    # 2024-25); Matthews 9 (was 3); Celebrini present (new).
    assert eo.JERSEY_RANK_FOLD[eo.fold("Connor Bedard")] == 1
    assert eo.JERSEY_RANK_FOLD[eo.fold("Auston Matthews")] == 9
    assert eo.JERSEY_RANK_FOLD[eo.fold("Macklin Celebrini")] == 10
    assert len(eo.JERSEY_RANK_FOLD) == 10


def test_v1b_union_spans_all_three_official_lists():
    for nm in ("Brad Marchand",      # 2023-10 list only
               "Auston Matthews",    # 2024-25 list
               "Macklin Celebrini"):  # 2025-26 list only
        assert eo.fold(nm) in eo.JERSEY_UNION_FOLD


def test_v1b_union_has_no_soft_sourced_names():
    expected = ({eo.fold(nm) for _, nm in eo.JERSEY_2025_26}
                | {eo.fold(nm) for _, nm in eo.JERSEY_2024_25}
                | {eo.fold(nm) for nm in eo.JERSEY_2023})
    assert eo.JERSEY_UNION_FOLD == expected


def test_asg_id_decides_when_present_no_namesake_false_positive():
    # Pool has TWO Elias Petterssons. Fan-vote pick = the center (8480012).
    # The defenseman (8483678) must not inherit membership via name-fold.
    rows = {r["player_id"]: r for r in eo.build_rows()}
    assert rows["686"]["asg2024_member"] == 1   # center, id match
    assert rows["695"]["asg2024_member"] == 0   # defenseman, id mismatch
