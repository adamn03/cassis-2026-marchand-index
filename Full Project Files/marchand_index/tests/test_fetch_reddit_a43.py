"""A43 — two-prong guard trigger (English list + phrase collision)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fetch_reddit as fr


def _write_corpus(tmp_path, name, posts):
    (tmp_path / f"{name}.jsonl").write_text(
        "\n".join(json.dumps(p) for p in posts), encoding="utf-8")


def test_wordlist_loads_and_contains_expected():
    words = fr.load_english_top1000()
    assert len(words) == 1000
    for w in ("but", "back", "power", "point", "york"):
        assert w in words
    for w in ("stanley", "mcdavid", "hughes"):
        assert w not in words


def test_prong1_guards_english_word_regardless_of_df():
    df = {"but": 0.001}   # below DF threshold — P1 fires anyway
    g = fr.guard_set_a43(df, frozenset({"but"}), {}, set())
    assert g["but"].startswith("P1")


def test_prong2b_dominant_bigram_guards_stanley(tmp_path):
    _write_corpus(tmp_path, "hockey", [
        {"id": str(i), "title": "stanley cup run", "selftext": ""}
        for i in range(9)
    ] + [{"id": "x", "title": "logan stanley hit", "selftext": ""}])
    df = {"stanley": 1.0}
    stats = fr.surname_occurrence_stats({"stanley"}, {"stanley"}, tmp_path)
    g = fr.guard_set_a43(df, frozenset(), stats, {"logan"})
    assert "stanley" in g
    assert "cup" in g["stanley"]


def test_pool_first_name_exemption_spares_mcdavid(tmp_path):
    # Dominant prev-bigram is "connor mcdavid" (pool first name -> exempt);
    # next tokens vary like real usage, so no other bigram reaches the share.
    nexts = ["scores", "dangles", "shoots", "wins", "flies",
             "returns", "leads", "rules", "delivers", "again"]
    _write_corpus(tmp_path, "hockey", [
        {"id": str(i), "title": f"connor mcdavid {nxt}", "selftext": ""}
        for i, nxt in enumerate(nexts)
    ])
    df = {"mcdavid": 1.0}
    stats = fr.surname_occurrence_stats({"mcdavid"}, {"mcdavid"}, tmp_path)
    g = fr.guard_set_a43(df, frozenset(), stats, {"connor"})
    assert "mcdavid" not in g


def test_prong2a_first_name_usage_guards_connor(tmp_path):
    # "connor" is mostly followed by pool surnames -> guarded as first-name
    # usage even though "connor" is itself a pool surname (Kyle Connor).
    _write_corpus(tmp_path, "hockey", [
        {"id": str(i), "title": "connor mcdavid again", "selftext": ""}
        for i in range(6)
    ] + [
        {"id": f"b{i}", "title": "kyle connor scores", "selftext": ""}
        for i in range(2)
    ])
    df = {"connor": 1.0}
    stats = fr.surname_occurrence_stats({"connor"}, {"mcdavid", "connor"},
                                        tmp_path)
    g = fr.guard_set_a43(df, frozenset(), stats, {"connor", "kyle"})
    assert "connor" in g
    assert g["connor"].startswith("P2a")


def test_below_df_threshold_not_guarded_without_prong1(tmp_path):
    _write_corpus(tmp_path, "hockey", [
        {"id": "1", "title": "stanley cup", "selftext": ""}])
    df = {"stanley": 0.001}
    stats = fr.surname_occurrence_stats({"stanley"}, set(), tmp_path)
    g = fr.guard_set_a43(df, frozenset(), stats, set())
    assert g == {}
