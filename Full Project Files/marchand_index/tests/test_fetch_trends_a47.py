"""A47 — Google Trends entity-resolution guard (no network).

Defect: `resolve_topic_mid` took the FIRST hockey-typed suggestion and, when
none qualified OR the call was throttled, fell back to a raw name string. That
published "Will Smith" = the actor at rank 1/771 (9.66x the anchor) and gave
the two Elias Petterssons one shared MID. A47 replaces the string fallback with
an explicit refusal and adds a position tie-break.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_trends as ft  # noqa: E402

FRANCHISES = ["vancouver canucks", "san jose sharks", "washington capitals"]


def sug(title, type_str, mid):
    return {"title": title, "type": type_str, "mid": mid}


# --------------------------------------------------------------------------- #
# franchise-name test — punctuation robustness                                 #
# --------------------------------------------------------------------------- #
def test_franchise_test_ignores_punctuation_in_the_google_type():
    """teams.csv folds `st-louis-blues` -> "st louis blues"; Google writes
    "St. Louis Blues defenseman". The bare substring test misses on the period
    and refused Parayko, Holloway and Suter as `no_hockey_topic` — which A25
    then imputes as raw 0."""
    assert ft._type_qualifies("St. Louis Blues defenseman", ["st louis blues"])
    assert ft._type_qualifies("St. Louis Blues center and forward",
                              ["st louis blues"])


def test_franchise_test_ignores_accents():
    assert ft._type_qualifies("Montréal Canadiens goaltender",
                              ["montreal canadiens"])


def test_franchise_test_still_rejects_a_non_hockey_type():
    assert not ft._type_qualifies("New York Jets wide receiver",
                                  ["st louis blues", "new york rangers"])
    assert not ft._type_qualifies("Comedian", ["los angeles kings"])


def test_hockey_substring_test_survives():
    assert ft._type_qualifies("Canadian ice hockey player", [])


# --------------------------------------------------------------------------- #
# select_topic_mid — pure suggestion selection                                 #
# --------------------------------------------------------------------------- #
def test_single_qualifying_suggestion_is_selected():
    s = [sug("Will Smith", "American actor", "/m/actor"),
         sug("Will Smith", "San Jose Sharks center", "/m/sharks_ws")]
    assert ft.select_topic_mid(s, FRANCHISES, "C") == ("/m/sharks_ws", "topic")


def test_no_qualifying_suggestion_refuses_with_no_hockey_topic():
    s = [sug("Will Smith", "American actor", "/m/actor"),
         sug("Will Smith", "American rapper", "/m/rapper")]
    assert ft.select_topic_mid(s, FRANCHISES, "C") == ("", "no_hockey_topic")


def test_empty_suggestion_list_refuses():
    assert ft.select_topic_mid([], FRANCHISES, "D") == ("", "no_hockey_topic")


def test_never_returns_a_raw_name_string():
    """A47 core rule: refusal yields an empty MID, never a searchable string."""
    mid, reason = ft.select_topic_mid([], FRANCHISES, "C")
    assert mid == ""
    assert reason != "string"


# --------------------------------------------------------------------------- #
# position tie-break — the two Elias Petterssons                              #
# --------------------------------------------------------------------------- #
PETTERSSONS = [
    sug("Elias Pettersson", "Vancouver Canucks center", "/g/center_ep"),
    sug("Elias Pettersson", "Vancouver Canucks defenseman", "/g/dman_ep"),
]


def test_position_tiebreak_picks_the_center():
    assert ft.select_topic_mid(PETTERSSONS, FRANCHISES, "C") \
        == ("/g/center_ep", "topic_position")


def test_position_tiebreak_picks_the_defenseman():
    assert ft.select_topic_mid(PETTERSSONS, FRANCHISES, "D") \
        == ("/g/dman_ep", "topic_position")


def test_position_tiebreak_accepts_british_spelling():
    s = [sug("A B", "Vancouver Canucks centre", "/g/c"),
         sug("A B", "Vancouver Canucks defence", "/g/d")]
    assert ft.select_topic_mid(s, FRANCHISES, "D") == ("/g/d", "topic_position")


def test_left_and_right_wing_are_distinguished():
    s = [sug("A B", "San Jose Sharks left wing", "/g/lw"),
         sug("A B", "San Jose Sharks right wing", "/g/rw")]
    assert ft.select_topic_mid(s, FRANCHISES, "L") == ("/g/lw", "topic_position")
    assert ft.select_topic_mid(s, FRANCHISES, "R") == ("/g/rw", "topic_position")


def test_ambiguous_when_position_cannot_break_the_tie():
    """Two qualifying entities, neither typed with a position -> refuse.
    Guessing here is what credited one Pettersson's volume to both."""
    s = [sug("Elias Pettersson", "Vancouver Canucks", "/g/one"),
         sug("Elias Pettersson", "Vancouver Canucks", "/g/two")]
    assert ft.select_topic_mid(s, FRANCHISES, "C") == ("", "ambiguous_topic")


def test_ambiguous_when_two_suggestions_share_the_position():
    s = [sug("A B", "Vancouver Canucks center", "/g/one"),
         sug("A B", "San Jose Sharks center", "/g/two")]
    assert ft.select_topic_mid(s, FRANCHISES, "C") == ("", "ambiguous_topic")


def test_position_tiebreak_not_applied_when_only_one_qualifies():
    """A lone qualifying suggestion is accepted even if its type carries no
    position — the tie-break exists only to resolve a tie."""
    s = [sug("A B", "Canadian ice hockey player", "/g/solo")]
    assert ft.select_topic_mid(s, FRANCHISES, "D") == ("/g/solo", "topic")


# --------------------------------------------------------------------------- #
# resolve_topic_mid — a failed call is NOT "no topic exists"                   #
# --------------------------------------------------------------------------- #
class _RaisingClient:
    def suggestions(self, name):
        raise RuntimeError("too many 429 error responses")


class _StubClient:
    def __init__(self, payload):
        self.payload = payload

    def suggestions(self, name):
        return self.payload


def test_throttled_call_reports_resolve_failed_not_no_hockey_topic():
    """429s dominate the Trends logs. A blocked call must stay distinguishable
    from a genuine absence of a Google entity — they get opposite A25 null
    treatments (renorm vs. impute 0)."""
    assert ft.resolve_topic_mid(_RaisingClient(), "Alex Ovechkin", "L") \
        == ("", "resolve_failed")


def test_successful_call_delegates_to_select_topic_mid(monkeypatch):
    monkeypatch.setattr(ft, "_franchise_names", lambda: FRANCHISES)
    client = _StubClient([sug("A B", "Washington Capitals left wing", "/m/ao")])
    assert ft.resolve_topic_mid(client, "Alex Ovechkin", "L") == ("/m/ao", "topic")


# --------------------------------------------------------------------------- #
# row construction — refusal must null the value, never publish a string       #
# --------------------------------------------------------------------------- #
def test_unresolved_row_has_null_value_and_carries_the_reason():
    row = ft.build_row(pid="1", name="Will Smith", mid="", reason="no_hockey_topic",
                       p_mean=None, a_mean=None, n_weeks=0, fetch_date="2026-08-01")
    assert row["trends_12mo"] == ""
    assert row["query_mid"] == ""
    assert row["trends_method"] == "no_hockey_topic"
    assert row["query"] == ""      # no searchable fallback string is stored


def test_resolved_row_stores_ratio_and_method():
    row = ft.build_row(pid="1", name="Alex Ovechkin", mid="/m/ao", reason="topic",
                       p_mean=20.0, a_mean=10.0, n_weeks=53,
                       fetch_date="2026-08-01")
    assert row["trends_12mo"] == "2.000000"
    assert row["query_mid"] == "/m/ao"
    assert row["trends_method"] == "topic"


# --------------------------------------------------------------------------- #
# resume — a pre-A47 row must be re-fetched, not kept                          #
# --------------------------------------------------------------------------- #
def test_resume_keeps_entity_resolved_rows():
    rows = [{"player_id": "1", "trends_12mo": "0.5", "trends_method": "topic"},
            {"player_id": "2", "trends_12mo": "0.2",
             "trends_method": "topic_position"},
            {"player_id": "3", "trends_12mo": "1.0",
             "trends_method": "topic_secondary_anchor"}]
    assert set(ft.resume_rows_from(rows)) == {"1", "2", "3"}


def test_resume_discards_pre_a47_string_rows():
    """The contaminated values are already on disk with a non-null
    trends_12mo; without this the re-run would skip every one of them."""
    rows = [{"player_id": "1", "trends_12mo": "9.664671",
             "trends_method": "string"}]
    assert ft.resume_rows_from(rows) == {}


def test_resume_discards_refusal_rows_so_they_are_retried():
    rows = [{"player_id": "1", "trends_12mo": "",
             "trends_method": "resolve_failed"}]
    assert ft.resume_rows_from(rows) == {}


def test_resume_discards_rows_sharing_a_topic_mid():
    """Two players on one MID is prima facie an unbroken tie: the stored value
    is one entity's volume credited to both. Both rows must be re-resolved."""
    rows = [{"player_id": "686", "trends_12mo": "0.222069",
             "trends_method": "topic", "query_mid": "/g/11ddxds8fn"},
            {"player_id": "695", "trends_12mo": "0.222069",
             "trends_method": "topic", "query_mid": "/g/11ddxds8fn"},
            {"player_id": "696", "trends_12mo": "0.002759",
             "trends_method": "topic", "query_mid": "/m/0ztj7c3"}]
    assert set(ft.resume_rows_from(rows)) == {"696"}


def test_resume_discards_rows_with_a_null_value():
    rows = [{"player_id": "1", "trends_12mo": "", "trends_method": "topic"}]
    assert ft.resume_rows_from(rows) == {}


def test_string_method_is_retired():
    """No code path may emit the pre-A47 raw-string method again."""
    assert "string" not in ft.RESOLUTION_METHODS
    assert ft.REFUSAL_REASONS == ("no_hockey_topic", "ambiguous_topic",
                                  "resolve_failed")
