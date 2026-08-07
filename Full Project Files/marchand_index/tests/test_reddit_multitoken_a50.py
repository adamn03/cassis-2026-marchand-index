"""A50: hyphen/apostrophe names are multi-token keys and must be matched as
adjacent token sequences, not as a single whole token."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_reddit as fr  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "raw"


# --------------------------------------------------------------------- #
# key construction                                                      #
# --------------------------------------------------------------------- #
@pytest.mark.parametrize("raw,expect", [
    ("Nugent-Hopkins", "nugent hopkins"),
    ("O'Reilly", "o reilly"),
    ("D'Astous", "d astous"),
    ("Ekman-Larsson", "ekman larsson"),
    ("Jean-Gabriel", "jean gabriel"),
    ("J.T.", "j t"),
])
def test_name_key_splits_separators(raw, expect):
    assert fr.name_key(raw) == expect


@pytest.mark.parametrize("raw", ["Pettersson", "Fehérváry", "Slafkovský",
                                 "McDavid", "Stützle"])
def test_name_key_identical_to_fold_for_single_token(raw):
    """The pre-A50 path must be byte-identical for names without separators."""
    assert fr.name_key(raw) == fr.fold(raw)
    assert not fr.is_multi_token(fr.name_key(raw))


def test_hyphen_names_are_multi_token():
    assert fr.is_multi_token(fr.name_key("Nugent-Hopkins"))
    assert fr.is_multi_token(fr.name_key("O'Reilly"))


# --------------------------------------------------------------------- #
# sequence matching                                                     #
# --------------------------------------------------------------------- #
def test_contains_sequence_finds_adjacent_run():
    toks = "the oilers ryan nugent hopkins scored again".split()
    assert fr.contains_sequence(toks, ("nugent", "hopkins"))


def test_contains_sequence_rejects_wrong_order():
    toks = "hopkins and nugent are different people".split()
    assert not fr.contains_sequence(toks, ("nugent", "hopkins"))


def test_contains_sequence_rejects_non_adjacent():
    toks = "nugent then later hopkins".split()
    assert not fr.contains_sequence(toks, ("nugent", "hopkins"))


def test_contains_sequence_matches_at_end_of_text():
    toks = "goal by ryan nugent hopkins".split()
    assert fr.contains_sequence(toks, ("nugent", "hopkins"))


def test_contains_sequence_no_overrun_past_end():
    """A trailing partial match must not read past the token list."""
    assert not fr.contains_sequence(["nugent"], ("nugent", "hopkins"))


def test_contains_sequence_empty_is_false():
    assert not fr.contains_sequence(["a", "b"], ())


def test_hyphenated_surname_matches_real_post_text():
    """End-to-end on the fold the corpus scanner actually uses."""
    title = "Ryan Nugent-Hopkins scores on the power play"
    toks = fr.match_fold(title).split()
    key = fr.name_key("Nugent-Hopkins")
    assert key not in set(toks), "single-token lookup is the defect"
    assert fr.contains_sequence(toks, tuple(key.split()))


def test_apostrophe_surname_matches_possessive_form():
    toks = fr.match_fold("O'Reilly's faceoff win sealed it").split()
    assert fr.contains_sequence(toks, tuple(fr.name_key("O'Reilly").split()))


# --------------------------------------------------------------------- #
# shipped data: the defect must be gone                                 #
# --------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def counts():
    return pd.read_csv(RAW / "reddit_counts.csv")


AFFECTED = ["Ryan Nugent-Hopkins", "Ryan O'Reilly", "Oliver Ekman-Larsson",
            "Charle-Edouard D'Astous", "Drew O'Connor", "Logan O'Connor",
            "Jacob Bernard-Docker", "Liam O'Brien", "Nicolas Aube-Kubel"]


@pytest.mark.parametrize("name", AFFECTED)
def test_separator_names_have_nonzero_mentions(name, counts):
    row = counts[counts.full_name == name]
    assert len(row) == 1, name
    assert row.reddit_mentions_12mo.iloc[0] > 0, f"{name} still scoring zero"


def test_only_genuine_zero_remains(counts):
    """Pre-A50 there were 10 `ok` rows reporting a false zero, every one of
    them a hyphen/apostrophe name. A genuine zero is still possible for a
    fringe player, so this pins the survivor by name rather than asserting
    none can exist — if a NEW name appears here, a matcher defect is back.
    """
    zeros = counts[(counts.reddit_mentions_12mo == 0)
                   & (counts.reddit_status == "ok")]
    assert sorted(zeros.full_name) == ["Maksymilian Szuber"]
    # A genuine zero has nothing pending: no ambiguous, no guard-filtered.
    assert (zeros.ambiguous_mentions == 0).all()
    assert (zeros.guard_filtered_mentions == 0).all()


def test_separator_names_are_not_flagged_measured_zero(counts):
    sep = counts[counts.full_name.str.contains(r"[-']", regex=True, na=False)]
    assert len(sep) >= 13
    bad = sep[(sep.reddit_mentions_12mo == 0) & (sep.reddit_status == "ok")]
    assert bad.empty, sorted(bad.full_name)


def test_pettersson_pair_still_unmeasurable(counts):
    """A48's handling must survive A50 untouched."""
    p = counts[counts.full_name == "Elias Pettersson"]
    assert len(p) == 2
    assert set(p.reddit_status) == {"unmeasurable"}
    assert (p.ambiguous_mentions > 0).all()
