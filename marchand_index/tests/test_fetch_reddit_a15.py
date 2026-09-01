"""Unit tests for the A15 surname-collision attribution filter (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_reddit as fr  # noqa: E402


def _players(*names):
    return [{"full_name": n} for n in names]


def test_fold_strips_accents_and_case():
    assert fr.fold("Martin Fehérváry") == "martin fehervary"
    assert fr.fold("TKACHUK") == "tkachuk"


def test_surname_map_marks_shared_surnames():
    m = fr.build_surname_map(_players(
        "Jack Hughes", "Quinn Hughes", "Luke Hughes", "Leo Carlsson"))
    assert len(m["hughes"]) == 3
    assert len(m["carlsson"]) == 1


def test_unique_surname_gets_no_checker():
    m = fr.build_surname_map(_players("Leo Carlsson", "Jack Hughes"))
    check, shared = fr.make_evidence_check("Leo Carlsson", m)
    assert check is None
    assert shared is False


def test_shared_surname_requires_first_name_evidence():
    m = fr.build_surname_map(_players(
        "Jack Hughes", "Quinn Hughes", "Luke Hughes"))
    check, shared = fr.make_evidence_check("Jack Hughes", m)
    assert shared is True
    assert check("Jack Hughes hat trick vs the Rangers", "") is True
    assert check("Hughes with the OT winner", "") is False       # ambiguous
    assert check("Quinn Hughes 4-point night", "") is False      # other brother


def test_first_name_prefix_credits_formal_name():
    # "Will" must credit a post that writes "William".
    m = fr.build_surname_map(_players("Will Smith", "Dalton Smith"))
    check, _ = fr.make_evidence_check("Will Smith", m)
    assert check("William Smith called up by the Sharks", "") is True


def test_short_first_name_requires_exact_word():
    m = fr.build_surname_map(_players("JJ Peterka", "Bo Peterka"))
    check, _ = fr.make_evidence_check("Bo Peterka", m)
    assert check("Bo Peterka scores", "") is True
    assert check("Body check by Peterka", "") is False   # 'body' != exact 'bo'


def test_initial_pattern_when_unique_among_sharers():
    # Jack/Quinn/Luke Hughes: J is unique -> "J. Hughes" credits Jack.
    m = fr.build_surname_map(_players(
        "Jack Hughes", "Quinn Hughes", "Luke Hughes"))
    check, _ = fr.make_evidence_check("Jack Hughes", m)
    assert check("J. Hughes leads the league", "") is True
    assert check("J Hughes leads the league", "") is True


def test_initial_pattern_rejected_when_initial_collides():
    # Jack/Josh share J -> "J. Hughes" is ambiguous, must NOT credit either.
    m = fr.build_surname_map(_players("Jack Hughes", "Josh Hughes"))
    check, _ = fr.make_evidence_check("Jack Hughes", m)
    assert check("J. Hughes leads the league", "") is False
    assert check("Jack Hughes leads the league", "") is True


def test_selftext_evidence_counts():
    m = fr.build_surname_map(_players("Jack Hughes", "Quinn Hughes"))
    check, _ = fr.make_evidence_check("Quinn Hughes", m)
    assert check("Hughes news", "Quinn had 3 assists tonight") is True


def test_counts_fields_include_a15_columns():
    assert "ambiguous_mentions" in fr.COUNTS_FIELDS
    assert "surname_shared" in fr.COUNTS_FIELDS
