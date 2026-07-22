"""A38: mover derivation from seasonTotals fixtures (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from build_mover_list import derive_moves  # noqa: E402

ROWS_TRADED = [  # in-season: two 2025-26 NHL teams
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Canucks"},
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Rangers"},
]
ROWS_OFFSEASON = [  # 2024-25 team != first 2025-26 team
    {"season": 20242025, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Bruins"},
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Panthers"},
]
ROWS_STAYED = [
    {"season": 20242025, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Penguins"},
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Penguins"},
]
ROWS_AHL_NOISE = [  # non-NHL rows never count
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "AHL", "teamCommonName": "Checkers"},
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Panthers"},
]


def test_in_season_mover_detected():
    m = derive_moves(ROWS_TRADED)
    assert m == [("Canucks", "Rangers", "in_season")]


def test_offseason_mover_detected():
    assert derive_moves(ROWS_OFFSEASON) == [("Bruins", "Panthers", "off_season")]


def test_non_mover_and_league_filter():
    assert derive_moves(ROWS_STAYED) == []
    assert derive_moves(ROWS_AHL_NOISE) == []
