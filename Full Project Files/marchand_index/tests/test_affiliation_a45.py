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
