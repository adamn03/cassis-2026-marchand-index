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
