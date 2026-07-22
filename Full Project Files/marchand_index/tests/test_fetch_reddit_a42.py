"""A42 — common-word surname guard (DF pre-pass, forced checker, scan filter)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fetch_reddit as fr


# --------------------------------------------------------------------------- #
# forced evidence checker                                                      #
# --------------------------------------------------------------------------- #
def test_forced_checker_on_unique_surname_requires_first_name():
    smap = {"but": ["daniil"]}
    chk, shared = fr.make_evidence_check("Daniil But", smap, force=True)
    assert shared is False
    assert chk is not None
    assert not chk("No NHL hockey today but there is AHL hockey!", "")
    assert chk("Daniil But with a highlight goal", "")


def test_forced_checker_accepts_unique_initial_pattern():
    chk, _ = fr.make_evidence_check("Daniil But", {"but": ["daniil"]},
                                    force=True)
    assert chk("D. But called up", "")


def test_unforced_unique_surname_unchanged():
    chk, shared = fr.make_evidence_check("Connor McDavid",
                                         {"mcdavid": ["connor"]})
    assert chk is None
    assert shared is False


# --------------------------------------------------------------------------- #
# DF pre-pass + guard set                                                      #
# --------------------------------------------------------------------------- #
def _write_corpus(tmp_path, name, posts):
    (tmp_path / f"{name}.jsonl").write_text(
        "\n".join(json.dumps(p) for p in posts), encoding="utf-8")


def test_df_counts_whole_tokens_and_guard_threshold(tmp_path):
    _write_corpus(tmp_path, "hockey", [
        {"id": "a", "title": "no hockey today but AHL", "selftext": ""},
        {"id": "b", "title": "power play tips", "selftext": ""},
        {"id": "c", "title": "McDavid hat trick", "selftext": ""},
        {"id": "d", "title": "but the power outage", "selftext": ""},
    ])
    df = fr.surname_document_frequency({"but", "power", "mcdavid"}, tmp_path)
    assert df["but"] == 0.5
    assert df["power"] == 0.5
    assert df["mcdavid"] == 0.25
    assert fr.guard_set(df, 0.5) == {"but", "power"}
    assert fr.guard_set(df, 0.6) == set()


def test_df_dedups_ids_and_folds_accents(tmp_path):
    _write_corpus(tmp_path, "hockey", [
        {"id": "a", "title": "Bäck to back wins", "selftext": ""},
        {"id": "a", "title": "Bäck to back wins", "selftext": ""},  # dupe id
        {"id": "b", "title": "nothing here", "selftext": ""},
    ])
    df = fr.surname_document_frequency({"back"}, tmp_path)
    assert df["back"] == 0.5  # 1 of 2 unique posts; fold("Bäck") == "back"


# --------------------------------------------------------------------------- #
# scan-level guard behavior                                                    #
# --------------------------------------------------------------------------- #
def _member(pid, fn, checker, guarded):
    return {"pid": pid, "fn": fn, "shared": False, "guarded": guarded,
            "teams": set(), "nicks": set(), "checker": checker,
            "discriminating": True, "identity_ambiguous": False}


def test_scan_guarded_singleton_counts_only_evidence_posts(tmp_path):
    _write_corpus(tmp_path, "hockey", [
        {"id": "p1", "title": "no hockey today but AHL", "selftext": "",
         "score": 5, "author": "u1"},
        {"id": "p2", "title": "Daniil But highlight goal", "selftext": "",
         "score": 7, "author": "u2"},
    ])
    chk, _ = fr.make_evidence_check("Daniil But", {"but": ["daniil"]},
                                    force=True)
    groups = {"but": [_member("1", "daniil", chk, guarded=True)]}
    counting = {"1": ["hockey"]}
    acc, _missing = fr.scan_corpus(groups, counting, tmp_path)
    assert acc["1"]["scores"] == {"p2": 7}
    assert acc["1"]["guard_filtered"] == 1
    assert acc["1"]["ambiguous"] == 0


def test_scan_unguarded_singleton_still_counts_all_hits(tmp_path):
    _write_corpus(tmp_path, "hockey", [
        {"id": "p1", "title": "McDavid is unreal", "selftext": "",
         "score": 3, "author": "u1"},
    ])
    groups = {"mcdavid": [_member("9", "connor", None, guarded=False)]}
    counting = {"9": ["hockey"]}
    acc, _missing = fr.scan_corpus(groups, counting, tmp_path)
    assert acc["9"]["scores"] == {"p1": 3}
    assert acc["9"]["guard_filtered"] == 0
