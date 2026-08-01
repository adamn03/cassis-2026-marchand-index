"""A45 — Phase A reddit attention affiliation split."""
from __future__ import annotations

import pandas as pd
import pytest

import affiliation as aff


def _market_proxy() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "team_code": ["BOS", "MON", "UTA", "VEG"],
            "team_sub": ["BostonBruins", "Habs", "utahmammoth", "goldenknights"],
        }
    )


def test_build_venue_map_lowercases_keys():
    vm = aff.build_venue_map(_market_proxy())
    assert vm["bostonbruins"] == "BOS"
    assert vm["habs"] == "MON"


def test_build_venue_map_includes_utah_rename_alias():
    vm = aff.build_venue_map(_market_proxy())
    assert vm["utahmammoth"] == "UTA"
    assert vm["utahhockey"] == "UTA"


def test_venue_team_returns_none_for_neutral_subs():
    vm = aff.build_venue_map(_market_proxy())
    assert aff.venue_team("hockey", vm) is None
    assert aff.venue_team("nhl", vm) is None
    assert aff.venue_team("fantasyhockey", vm) is None


def test_venue_team_is_case_insensitive():
    vm = aff.build_venue_map(_market_proxy())
    assert aff.venue_team("BostonBruins", vm) == "BOS"
    assert aff.venue_team("bostonbruins", vm) == "BOS"


def test_venue_team_returns_none_for_unknown_sub():
    vm = aff.build_venue_map(_market_proxy())
    assert aff.venue_team("soccer", vm) is None


def _movers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_id": [25, 25, 99, 7],
            "old_team": ["Oilers", "Bruins", "Maple Leafs", "Utah Hockey Club"],
            "new_team": ["Bruins", "Canadiens", "Wild", "Mammoth"],
            "event_date": ["2025-07-01", "2026-01-15", "2025-11-20", "2025-06-01"],
            "status": ["dated", "dated", "dated", "excluded_rename_artifact"],
        }
    )


def test_nickname_map_covers_every_mover_team():
    movers = pd.read_csv("mover_dates.csv")
    movers = movers[movers["status"] == "dated"]
    names = set(movers["old_team"].dropna()) | set(movers["new_team"].dropna())
    missing = sorted(n for n in names if n not in aff.NICKNAME_TO_CODE)
    assert missing == [], f"nicknames absent from NICKNAME_TO_CODE: {missing}"


def test_build_move_timeline_drops_rename_artifacts():
    tl = aff.build_move_timeline(_movers())
    assert 7 not in tl


def test_build_move_timeline_is_chronological():
    tl = aff.build_move_timeline(_movers())
    dates = [d for d, _ in tl[25]]
    assert dates == sorted(dates)


def test_team_at_returns_end_team_after_last_move():
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(25, pd.Timestamp("2026-03-01"), "MON", tl)
    assert got == "MON"


def test_team_at_reverts_one_move():
    # Between the two moves: joined BOS 2025-07-01, left for MON 2026-01-15.
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(25, pd.Timestamp("2025-10-01"), "MON", tl)
    assert got == "BOS"


def test_team_at_reverts_all_moves():
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(25, pd.Timestamp("2025-05-01"), "MON", tl)
    assert got == "EDM"


def test_team_at_for_player_with_no_moves():
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(1234, pd.Timestamp("2025-10-01"), "VAN", tl)
    assert got == "VAN"


def test_team_at_on_exact_move_date_uses_new_team():
    # A move dated 2026-01-15 means the player is on the new team that day.
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(25, pd.Timestamp("2026-01-15"), "MON", tl)
    assert got == "MON"


def _submissions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "submission_id": ["s1", "s2", "s3", "s4", "s5"],
            "subreddit": ["BostonBruins", "Habs", "hockey", "BostonBruins", "Habs"],
            "created_at": pd.to_datetime(
                [
                    "2025-10-01",
                    "2025-10-01",
                    "2025-10-01",
                    "2026-03-01",
                    "2020-01-01",  # before the window
                ]
            ),
        }
    )


def _players() -> pd.DataFrame:
    return pd.DataFrame({"player_id": [25], "team_code": ["MON"]})


def _labelled() -> pd.DataFrame:
    detail = pd.DataFrame(
        {
            "player_id": [25, 25, 25, 25, 25],
            "submission_id": ["s1", "s2", "s3", "s4", "s5"],
            "score": [10, 20, 30, 40, 50],
        }
    )
    return aff.label_mentions(
        detail,
        _submissions(),
        _players(),
        aff.build_venue_map(_market_proxy()),
        aff.build_move_timeline(_movers()),
    )


def test_label_mentions_own_before_trade():
    # Player 25 was on BOS on 2025-10-01, so r/BostonBruins is own.
    out = _labelled()
    assert out.loc[out.subreddit == "BostonBruins"].iloc[0]["bucket"] == "own"


def test_label_mentions_other_before_trade():
    out = _labelled()
    row = out[(out.subreddit == "Habs")].iloc[0]
    assert row["bucket"] == "other"


def test_label_mentions_flips_after_trade():
    # Traded to MON on 2026-01-15, so r/BostonBruins on 2026-03-01 is other.
    out = _labelled()
    late = out[out.subreddit == "BostonBruins"].iloc[1]
    assert late["bucket"] == "other"


def test_label_mentions_neutral_venue():
    out = _labelled()
    assert (out[out.subreddit == "hockey"]["bucket"] == "neutral").all()


def test_label_mentions_drops_out_of_window_rows():
    out = _labelled()
    assert 50 not in set(out["score"])


def test_label_mentions_drops_unknown_submissions():
    detail = pd.DataFrame(
        {"player_id": [25], "submission_id": ["nope"], "score": [1]}
    )
    out = aff.label_mentions(
        detail,
        _submissions(),
        _players(),
        aff.build_venue_map(_market_proxy()),
        aff.build_move_timeline(_movers()),
    )
    assert len(out) == 0


def _agg_players() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_id": [1, 2],
            "full_name": ["Own Heavy", "Road Show"],
            "team_code": ["BOS", "MON"],
        }
    )


def _agg_labelled() -> pd.DataFrame:
    rows = []
    # Player 1: 6 own mentions in a small sub, 2 other in a big sub.
    rows += [(1, "BostonBruins", "own", 10)] * 6
    rows += [(1, "Habs", "other", 10)] * 2
    # Player 2: 2 own in a big sub, 6 other spread over two rival subs.
    rows += [(2, "Habs", "own", 10)] * 2
    rows += [(2, "BostonBruins", "other", 10)] * 4
    rows += [(2, "leafs", "other", 10)] * 2
    rows += [(2, "hockey", "neutral", 10)] * 5
    return pd.DataFrame(rows, columns=["player_id", "subreddit", "bucket", "score"])


_SUB_VOLUME = {"BostonBruins": 3000, "Habs": 15000, "leafs": 10000, "hockey": 50000}


def test_aggregate_counts_each_bucket():
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    p1 = out.set_index("player_id").loc[1]
    assert p1["own_mentions"] == 6
    assert p1["other_mentions"] == 2
    assert p1["neutral_mentions"] == 0


def test_aggregate_normalizes_by_submission_volume():
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    p1 = out.set_index("player_id").loc[1]
    assert p1["own_intensity"] == pytest.approx(6 / 3000)
    assert p1["other_intensity"] == pytest.approx(2 / 15000)


def test_normalization_changes_the_ranking():
    """Raw counts and normalized rates disagree — that is the whole point.

    Player 2 has more raw other-mentions than player 1 has own-mentions, but
    after dividing by venue volume player 1 is far more own-concentrated.
    """
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    idx = out.set_index("player_id")
    assert idx.loc[1, "own_share"] > idx.loc[2, "own_share"]


def test_own_share_is_a_proportion_of_attributed_only():
    # Neutral mentions must not enter own_share's denominator.
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    p2 = out.set_index("player_id").loc[2]
    expected = (2 / 15000) / ((2 / 15000) + (4 / 3000) + (2 / 10000))
    assert p2["own_share"] == pytest.approx(expected)


def test_rival_reach_counts_distinct_rival_subs():
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    idx = out.set_index("player_id")
    assert idx.loc[1, "rival_reach"] == 1
    assert idx.loc[2, "rival_reach"] == 2


def test_top_rival_is_the_highest_rate_rival_sub():
    # Player 2: BostonBruins 4/3000 beats leafs 2/10000 despite both being
    # rivals, and beats it on rate even though the raw counts are closer.
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    assert out.set_index("player_id").loc[2, "top_rival"] == "BostonBruins"


def test_low_n_flag_set_below_threshold():
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    # Both fixture players are far below LOW_N_MIN=30 attributed mentions.
    assert out["low_n"].all()


def test_player_with_no_mentions_gets_a_row():
    players = pd.DataFrame(
        {"player_id": [1, 2, 3], "full_name": ["a", "b", "c"],
         "team_code": ["BOS", "MON", "VAN"]}
    )
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, players)
    p3 = out.set_index("player_id").loc[3]
    assert p3["attributed_mentions"] == 0
    assert pd.isna(p3["own_share"])
    assert bool(p3["low_n"]) is True
