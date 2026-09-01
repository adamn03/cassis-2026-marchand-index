"""Unit tests for the A19 identity-repair pure logic (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import repair_wiki_identity as rw  # noqa: E402


def _entity(p3522=None, enwiki=None, birth=None):
    ent = {"claims": {}, "sitelinks": {}}
    if p3522:
        ent["claims"]["P3522"] = [
            {"mainsnak": {"datavalue": {"value": v}}} for v in p3522]
    if enwiki:
        ent["sitelinks"]["enwiki"] = {"site": "enwiki", "title": enwiki}
    return ent


# --- selection: exactly the audit-flagged rows -------------------------------

def test_needs_repair_bad_verdict():
    assert rw.needs_repair({"verdict": "bad_nhl_id", "wiki_match": "occupation"})
    assert rw.needs_repair({"verdict": "bad_dob", "wiki_match": "occupation"})


def test_needs_repair_unresolved_none_row():
    assert rw.needs_repair({"verdict": "unverified", "wiki_match": "none"})


def test_no_repair_for_verified_rows():
    assert not rw.needs_repair({"verdict": "ok_nhl_id", "wiki_match": "occupation"})
    assert not rw.needs_repair({"verdict": "ok_dob", "wiki_match": "occupation"})


# --- entity verification: exact P3522 equality, not substring ----------------

def test_entity_matches_exact_nhl_id():
    assert rw.entity_matches_nhl_id(_entity(p3522=["8483678"]), "8483678")


def test_entity_rejects_other_nhl_id():
    assert not rw.entity_matches_nhl_id(_entity(p3522=["8480012"]), "8483678")


def test_entity_rejects_substring_id():
    # "848001" is a prefix of "8480012" — exact equality required.
    assert not rw.entity_matches_nhl_id(_entity(p3522=["8480012"]), "848001")


def test_entity_without_p3522_never_matches():
    assert not rw.entity_matches_nhl_id(_entity(), "8483678")


# --- sitelink extraction -----------------------------------------------------

def test_enwiki_title_extracted():
    ent = _entity(p3522=["1"], enwiki="Elias Pettersson (ice hockey, born 2004)")
    assert rw.entity_enwiki_title(ent) == "Elias Pettersson (ice hockey, born 2004)"


def test_missing_enwiki_sitelink_is_empty():
    assert rw.entity_enwiki_title(_entity(p3522=["1"])) == ""


# --- row update: repaired fields only, slug underscored ----------------------

def test_apply_repair_updates_pv_row():
    pv = {"player_id": "695", "full_name": "Elias Pettersson",
          "wikipedia_slug_tried": "Elias_Pettersson",
          "wikipedia_slug_chosen": "Elias_Pettersson",
          "wikidata_qid": "Q28057083", "wiki_match": "occupation",
          "wiki_12mo": "999999", "fetch_date": "2026-06-17",
          "window_start": "20250418", "window_end": "20260417"}
    out = rw.apply_repair(pv, qid="Q106602297",
                          title="Elias Pettersson (ice hockey, born 2004)",
                          total=12345, fetch_date="2026-07-03")
    assert out["wikipedia_slug_chosen"] == "Elias_Pettersson_(ice_hockey,_born_2004)"
    assert out["wikidata_qid"] == "Q106602297"
    assert out["wiki_match"] == "nhl_id"
    assert out["wiki_12mo"] == 12345
    assert out["fetch_date"] == "2026-07-03"
    # A14 window untouched
    assert out["window_start"] == "20250418"
    assert out["window_end"] == "20260417"
    assert out["wikipedia_slug_tried"] == "Elias_Pettersson"


def test_apply_repair_null_total_is_empty_sentinel():
    pv = {"player_id": "69", "wikipedia_slug_chosen": "", "wikidata_qid": "",
          "wiki_match": "none", "wiki_12mo": "", "fetch_date": "2026-06-17",
          "window_start": "20250418", "window_end": "20260417"}
    out = rw.apply_repair(pv, qid="Q1", title="Some Page", total=None,
                          fetch_date="2026-07-03")
    assert out["wiki_12mo"] == ""


# --- constants align with the en-wiki fetcher (A14) --------------------------

def test_window_is_a14_fixed():
    assert rw.WINDOW_START == "20250418"
    assert rw.WINDOW_END == "20260417"


def test_pv_fields_match_fetcher_schema():
    assert rw.PV_FIELDS == [
        "player_id", "full_name", "wikipedia_slug_tried",
        "wikipedia_slug_chosen", "wikidata_qid", "wiki_match", "wiki_12mo",
        "fetch_date", "window_start", "window_end"]
