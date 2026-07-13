"""Unit tests for A21 (identity extension) + A23 (Arctic Shift local matching).

All offline: corpus fixtures are mini jsonl files in tmp_path.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_reddit as fr  # noqa: E402
import fetch_reddit_corpus as frc  # noqa: E402


# --------------------------------------------------------------------------- #
# A23 rule 3 — fold-token matching                                             #
# --------------------------------------------------------------------------- #
def test_match_fold_handles_possessives_curly_and_straight():
    assert "mcdavid" in fr.match_tokens("McDavid’s next team?", "")
    assert "mcdavid" in fr.match_tokens("McDavid's IG story", "")


def test_match_fold_accents():
    assert "fehervary" in fr.match_tokens("Fehérváry with the hit", "")


def test_whole_token_guard_no_substring_match():
    # "McDavidson" must NOT produce the token "mcdavid".
    assert "mcdavid" not in fr.match_tokens("McDavidson signs in the ECHL", "")


def test_match_tokens_covers_selftext():
    assert "carlsson" in fr.match_tokens("Game recap", "Leo Carlsson scored twice")


def test_prefix_collides():
    assert fr.prefix_collides("matt", "matthew")
    assert fr.prefix_collides("elias", "elias")
    assert not fr.prefix_collides("jack", "quinn")


# --------------------------------------------------------------------------- #
# A21 — attribution rules                                                      #
# --------------------------------------------------------------------------- #
def _groups(*specs):
    """specs: (full_name, team_codes). Returns fetch_reddit-style groups."""
    players = [{"player_id": str(i + 1), "full_name": n} for i, (n, _) in enumerate(specs)]
    wteams = {str(i + 1): set(t) for i, (_, t) in enumerate(specs)}
    nickname = {"CAR": "hurricanes", "NYI": "islanders", "VAN": "canucks",
                "NJ": "devils", "DAL": "stars", "UTA": "mammoth"}
    smap = fr.build_surname_map(players)
    return fr.build_groups(players, wteams, nickname, smap)


def test_pettersson_pair_ambiguous_everywhere():
    g = _groups(("Elias Pettersson", ["VAN"]), ("Elias Pettersson", ["VAN"]))
    grp = g["pettersson"]
    # Fully non-discriminable flag on both rows (A21 rule 3).
    assert all(m["identity_ambiguous"] for m in grp)
    toks = fr.match_tokens("Elias Pettersson highlight", "")
    # Team sub: both window-rostered on VAN -> ambiguous.
    assert fr.attribute(grp, "Elias Pettersson highlight", "", toks, "VAN") is None
    # r/hockey, even with the team nickname: same team -> ambiguous.
    toks2 = fr.match_tokens("Pettersson leads the Canucks", "")
    assert fr.attribute(grp, "Pettersson leads the Canucks", "", toks2, None) is None


def test_aho_team_sub_and_nickname_rules():
    g = _groups(("Sebastian Aho", ["CAR"]), ("Sebastian Aho", ["NYI"]))
    grp = g["aho"]
    assert not any(m["identity_ambiguous"] for m in grp)   # separable by team
    bare = fr.match_tokens("Aho with the shootout winner", "")
    # r/canes (CAR team sub): only the CAR Aho is rostered -> attributed (rule 2).
    assert fr.attribute(grp, "Aho with the shootout winner", "", bare, "CAR") == "1"
    # r/hockey with "Hurricanes" in title -> CAR Aho (rule 4).
    t = "Aho extends the Hurricanes point streak"
    assert fr.attribute(grp, t, "", fr.match_tokens(t, ""), None) == "1"
    # Bare "Aho" in r/hockey -> ambiguous.
    assert fr.attribute(grp, "Aho with the shootout winner", "", bare, None) is None
    # Both teams' nicknames present -> ambiguous (rule 4).
    t2 = "Aho vs Aho: Hurricanes at Islanders tonight"
    assert fr.attribute(grp, t2, "", fr.match_tokens(t2, ""), None) is None


def test_prefix_collision_detected_matt_matthew():
    g = _groups(("Matt Boldy", ["MIN"]), ("Matthew Boldy", ["DAL"]))
    grp = g["boldy"]
    assert all(not m["discriminating"] for m in grp)


def test_discriminating_evidence_still_attributes():
    g = _groups(("Jack Hughes", ["NJ"]), ("Quinn Hughes", ["VAN"]))
    grp = g["hughes"]
    t = "Jack Hughes hat trick tonight"
    assert fr.attribute(grp, t, "", fr.match_tokens(t, ""), None) == "1"
    # Bare surname in r/hockey stays ambiguous (A15, non-colliding names).
    bare = "Hughes with the OT winner"
    assert fr.attribute(grp, bare, "", fr.match_tokens(bare, ""), None) is None


def test_traded_sharer_follows_window_roster():
    # Sharer 1 was window-rostered on BOTH CAR and DAL (traded); in the DAL sub
    # a bare surname still attributes to him, not the snapshot-team sharer.
    g = _groups(("Sebastian Aho", ["CAR", "DAL"]), ("Sebastian Aho", ["NYI"]))
    grp = g["aho"]
    bare = fr.match_tokens("Aho debuts tonight", "")
    assert fr.attribute(grp, "Aho debuts tonight", "", bare, "DAL") == "1"


def test_unique_surname_always_attributes():
    g = _groups(("Leo Carlsson", ["ANA"]),)
    grp = g["carlsson"]
    bare = fr.match_tokens("Carlsson scores", "")
    assert fr.attribute(grp, "Carlsson scores", "", bare, None) == "1"


# --------------------------------------------------------------------------- #
# A22 — sub selection                                                          #
# --------------------------------------------------------------------------- #
def test_counting_subs_uta_includes_predecessor():
    assert fr.counting_subs({"UTA"}) == ["hockey", "utahmammoth", "UtahHockey"]


def test_counting_subs_traded_two_teams():
    subs = fr.counting_subs({"CAR", "DAL"})
    assert subs[0] == "hockey"
    assert set(subs) == {"hockey", "canes", "DallasStars"}


def test_team_sub_maps_identical_across_modules():
    assert fr.TEAM_SUB == frc.TEAM_SUB


# --------------------------------------------------------------------------- #
# A23 — corpus scan end-to-end (fixtures)                                      #
# --------------------------------------------------------------------------- #
def _write_corpus(dirpath: Path, sub: str, posts: list[dict]) -> None:
    dirpath.mkdir(parents=True, exist_ok=True)
    with (dirpath / f"{sub}.jsonl").open("w", encoding="utf-8") as f:
        for p in posts:
            f.write(json.dumps(p) + "\n")


def _post(pid, title, score=1, selftext="", author="u1"):
    return {"id": pid, "created_utc": 1750000000, "title": title,
            "selftext": selftext, "score": score, "subreddit": "x",
            "num_comments": 0, "author": author}


def test_scan_corpus_end_to_end(tmp_path):
    groups = _groups(("Jack Hughes", ["NJ"]), ("Quinn Hughes", ["VAN"]),
                     ("Leo Carlsson", ["ANA"]))
    counting = {"1": ["hockey", "devils"], "2": ["hockey", "canucks"],
                "3": ["hockey", "anaheimducks"]}
    _write_corpus(tmp_path, "hockey", [
        _post("h1", "Jack Hughes hat trick"),              # -> Jack
        _post("h2", "Hughes with the OT winner"),          # ambiguous
        _post("h3", "Carlsson scores twice", score=50),    # -> Leo (unique)
        _post("h4", "McDavid’s night"),               # not in pool
    ])
    _write_corpus(tmp_path, "canucks", [
        _post("c1", "Hughes 4 point night", score=10),     # bare, VAN sub -> Quinn
        # Crosspost of h2: bare in r/hockey was ambiguous, but in the VAN sub
        # A21 rule 2 attributes it to the sole rostered Hughes (Quinn).
        _post("h2", "Hughes with the OT winner"),
    ])
    _write_corpus(tmp_path, "fantasyhockey", [
        _post("f1", "Stream Leo Carlsson this week"),      # descriptive only
    ])
    acc, missing = fr.scan_corpus(groups, counting, corpus_dir=tmp_path)

    assert set(acc["1"]["scores"]) == {"h1"}
    assert set(acc["2"]["scores"]) == {"c1", "h2"}         # A21 rule 2 recall gain
    assert acc["2"]["scores"]["c1"] == 10
    assert set(acc["3"]["scores"]) == {"h3"}
    # The r/hockey copy of h2 stays ambiguous for both brothers (occurrence-
    # level disclosure); the canucks copy was attributed, not ambiguous.
    assert acc["1"]["ambiguous"] == 1
    assert acc["2"]["ambiguous"] == 1
    # Descriptive: fantasy post counts in allsubs + fantasy, NOT composite.
    assert "f1" in acc["3"]["allsubs_ids"]
    assert "f1" in acc["3"]["fantasy_ids"]
    assert "f1" not in acc["3"]["scores"]
    # Subs without fixture files are reported missing, not fatal.
    assert "nhl" in missing


def test_scan_corpus_dedups_crosspost_across_subs(tmp_path):
    groups = _groups(("Quinn Hughes", ["VAN"]),)
    counting = {"1": ["hockey", "canucks"]}
    _write_corpus(tmp_path, "hockey", [_post("x1", "Quinn Hughes named captain", score=5)])
    _write_corpus(tmp_path, "canucks", [_post("x1", "Quinn Hughes named captain", score=5)])
    acc, _ = fr.scan_corpus(groups, counting, corpus_dir=tmp_path)
    assert len(acc["1"]["scores"]) == 1                     # A22 dedup by id


# --------------------------------------------------------------------------- #
# Corpus puller — window + resume                                              #
# --------------------------------------------------------------------------- #
def test_window_cutoffs_match_a11():
    lower, upper = frc.window_cutoffs()
    assert lower == 1744934400        # 2025-04-18 00:00 UTC
    assert upper == 1776470400        # 2026-04-18 00:00 UTC (exclusive)
    assert (upper - lower) == 365 * 86400


def test_load_part_drops_torn_tail_and_dedups(tmp_path):
    part = tmp_path / "hockey.jsonl.part"
    good1 = json.dumps({"id": "a1", "created_utc": 1750000000, "title": "t"})
    good2 = json.dumps({"id": "a2", "created_utc": 1750000100, "title": "t"})
    dup = good2
    torn = '{"id": "a3", "created_'
    part.write_text("\n".join([good1, good2, dup, torn]), encoding="utf-8")
    seen, max_ts, lines = frc.load_part(part)
    assert seen == {"a1", "a2"}
    assert max_ts == 1750000100
    assert len(lines) == 2


def test_corpus_slim_keeps_required_fields():
    post = {"id": "z", "created_utc": 1, "title": "t", "selftext": "s",
            "score": 3, "subreddit": "hockey", "num_comments": 2,
            "author": "u", "_meta": {"retrieved_2nd_on": 9},
            "unwanted_giant_field": "x" * 100}
    row = frc.slim(post)
    assert row["retrieved_2nd_on"] == 9
    assert "unwanted_giant_field" not in row
    for k in ("id", "created_utc", "title", "selftext", "score", "author"):
        assert k in row


def test_counts_fields_a21_a23_columns():
    assert "reddit_capped" not in fr.COUNTS_FIELDS          # A23 rule 1
    for col in ("reddit_identity_ambiguous", "reddit_subs_searched",
                "reddit_mentions_allsubs", "reddit_mentions_fantasy"):
        assert col in fr.COUNTS_FIELDS
