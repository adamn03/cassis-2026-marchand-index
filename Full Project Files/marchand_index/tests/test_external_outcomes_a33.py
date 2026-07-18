"""A33: V2 membership = union of official fan-vote All-Star selections
2022 + 2023 + 2024 (winners only; replacements are league-named, excluded)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_external_outcomes as eo  # noqa: E402


def test_2022_list_is_captains_plus_last_men_in_winners():
    names = {nm for nm, _, _, _ in eo.ASG2022_FAN_VOTE}
    assert names == {
        "Alex Ovechkin", "Auston Matthews", "Nathan MacKinnon",
        "Connor McDavid",                       # fan-vote captains
        "Steven Stamkos", "Nazem Kadri", "Mika Zibanejad", "Troy Terry",
    }                                           # Last Men In winners
    # Winners only: Zibanejad withdrew but WON the vote; his roster
    # replacement Guentzel (and injury/COVID replacements Pavelski, Josi,
    # Giroux) were league-named, never fan-voted.
    assert "Jake Guentzel" not in names
    assert "Joe Pavelski" not in names
    assert "Claude Giroux" not in names


def test_2023_list_is_the_final_12_fan_ballot():
    entries = {nm: pid for nm, pid, _, _ in eo.ASG2023_FAN_VOTE}
    assert len(entries) == 12
    assert entries["David Pastrnak"] == "8477956"
    assert entries["Bo Horvat"] == "8477500"
    assert entries["Stuart Skinner"] == "8479973"    # goalies coded too


def test_union_ids_span_three_seasons():
    assert eo.SEASON_FAN_VOTE_IDS["2024"] == eo.ASG2024_IDS
    assert "8474564" in eo.ASG_FANVOTE_IDS          # Stamkos 2022
    assert "8478550" in eo.ASG_FANVOTE_IDS          # Panarin 2023
    assert "8480069" in eo.ASG_FANVOTE_IDS          # Makar 2024
    assert "8478873" in eo.ASG_FANVOTE_IDS          # Terry (corrected id)


def test_rows_union_membership_and_seasons_column():
    rows = {r["full_name"]: r for r in eo.build_rows()}
    assert rows["Steven Stamkos"]["asg2024_member"] == 1
    assert rows["Mika Zibanejad"]["asg2024_member"] == 1   # winner, withdrew
    assert rows["Jake Guentzel"]["asg2024_member"] == 0    # replacement
    assert rows["Bo Horvat"]["asg2024_member"] == 1
    # Multi-season member: Matthews = 2022 captain + 2023 ballot.
    assert rows["Auston Matthews"]["asg_fanvote_seasons"] == "2022,2023"
    assert rows["Cale Makar"]["asg_fanvote_seasons"] == "2024"
    assert rows["Steven Stamkos"]["asg_fanvote_seasons"] == "2022"


def test_namesake_guard_still_holds_under_union():
    rows = {r["player_id"]: r for r in eo.build_rows()}
    assert rows["686"]["asg2024_member"] == 1   # E. Pettersson C (8480012)
    assert rows["695"]["asg2024_member"] == 0   # E. Pettersson D (8483678)


def test_union_overlap_reaches_power_threshold():
    # A33 rule 4: with 2022+2023+2024 pooled the in-pool overlap must be
    # printed and compared to 10; on the locked 774 pool it clears it.
    n = sum(r["asg2024_member"] for r in eo.build_rows())
    assert n >= 10


def test_seasons_column_in_fieldnames():
    assert "asg_fanvote_seasons" in eo.FIELDNAMES
