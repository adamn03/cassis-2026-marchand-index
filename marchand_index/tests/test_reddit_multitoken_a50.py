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


def test_no_separator_name_scores_a_false_zero(counts):
    """Pre-A50 there were 10 `ok` rows reporting a false zero, every one of
    them a hyphen/apostrophe name.

    This originally pinned the single legitimate survivor by name. That became
    unstable once V-A11-Window narrowed the counting window from 921 days back
    to the pre-registered 365: a fringe player with a couple of mentions spread
    over two and a half seasons can legitimately have none in one year, and the
    genuine-zero roster grew from 1 to 9 without any matcher defect. What the
    test actually guards is that no SEPARATOR name is among them, which is
    checked directly and does not drift with the window.
    """
    zeros = counts[(counts.reddit_mentions_12mo == 0)
                   & (counts.reddit_status == "ok")]
    assert not (set(zeros.full_name) & set(AFFECTED)),         "a hyphen/apostrophe name is scoring zero again -- matcher regression"
    # The common-word guard must never be the reason someone reads zero --
    # that would be the guard over-firing rather than a genuine absence.
    assert (zeros.guard_filtered_mentions == 0).all()
    # Ambiguous mentions ARE allowed to be non-zero here. A15's collision guard
    # withholds attribution when a surname matches two pooled players, so a
    # player can legitimately have every mention withheld: Fredrik Olofsson
    # reads 0 counted / 43 ambiguous because they cannot be separated from
    # Victor Olofsson inside the 365-day window. That is the guard working, and
    # the count is disclosed rather than silently attributed.


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
