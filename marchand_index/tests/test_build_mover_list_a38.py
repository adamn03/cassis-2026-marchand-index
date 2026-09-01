"""A38: mover derivation from game-log fixtures (no network).

Rewritten 2026-08-31. The original tested `derive_moves`, which read
`seasonTotals` rows and could only say *that* a player changed club, not when.
That approach was replaced by dated game logs: `spells_from_log` collapses a
game log into consecutive (franchise, first_date, last_date) spells, and
`spells_to_moves` turns each change of franchise into a move bracketed by the
last game for the old club and the first for the new one. The bracket is what
makes an event study possible at all, so the old test was removed rather than
adapted -- it asserted the behaviour of a design that no longer exists.

The old league filter case is gone with it: game logs come from an NHL-only
endpoint, so there are no AHL rows left to filter.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from build_mover_list import spells_from_log, spells_to_moves  # noqa: E402

# Traded mid-season: last VAN game 2026-01-10, first NYR game 2026-01-14.
LOG_TRADED = [
    {"gameDate": "2025-10-12", "teamAbbrev": "VAN"},
    {"gameDate": "2026-01-10", "teamAbbrev": "VAN"},
    {"gameDate": "2026-01-14", "teamAbbrev": "NYR"},
    {"gameDate": "2026-03-02", "teamAbbrev": "NYR"},
]
# Changed clubs between seasons.
LOG_OFFSEASON = [
    {"gameDate": "2025-03-01", "teamAbbrev": "BOS"},
    {"gameDate": "2025-10-09", "teamAbbrev": "FLA"},
]
LOG_STAYED = [
    {"gameDate": "2025-10-09", "teamAbbrev": "PIT"},
    {"gameDate": "2026-02-01", "teamAbbrev": "PIT"},
]

SEASON_OF = {
    "2025-03-01": "20242025",
    "2025-10-09": "20252026",
    "2025-10-12": "20252026",
    "2026-01-10": "20252026",
    "2026-01-14": "20252026",
    "2026-02-01": "20252026",
    "2026-03-02": "20252026",
}


def test_spells_collapse_consecutive_games_at_one_club():
    assert spells_from_log(LOG_TRADED) == [
        ("VAN", "2025-10-12", "2026-01-10"),
        ("NYR", "2026-01-14", "2026-03-02"),
    ]


def test_spells_are_order_independent():
    """Game logs arrive in arbitrary order; the function sorts by date."""
    assert spells_from_log(list(reversed(LOG_TRADED))) == \
        spells_from_log(LOG_TRADED)


def test_in_season_move_is_bracketed_and_typed():
    m = spells_to_moves(spells_from_log(LOG_TRADED), SEASON_OF)
    assert len(m) == 1
    mv = m[0]
    assert (mv["old_team"], mv["new_team"]) == ("VAN", "NYR")
    assert (mv["date_lower"], mv["date_upper"]) == ("2026-01-10", "2026-01-14")
    assert mv["bracket_days"] == 4      # the move happened inside this window
    assert mv["move_type"] == "in_season"


def test_offseason_move_detected():
    m = spells_to_moves(spells_from_log(LOG_OFFSEASON), SEASON_OF)
    assert len(m) == 1
    assert (m[0]["old_team"], m[0]["new_team"]) == ("BOS", "FLA")
    assert m[0]["move_type"] == "off_season"


def test_non_mover_produces_no_move():
    assert spells_to_moves(spells_from_log(LOG_STAYED), SEASON_OF) == []


def test_rows_without_a_date_are_ignored():
    noisy = LOG_STAYED + [{"teamAbbrev": "TOR"}]
    assert spells_from_log(noisy) == spells_from_log(LOG_STAYED)
