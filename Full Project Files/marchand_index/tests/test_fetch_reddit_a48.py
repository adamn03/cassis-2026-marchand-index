"""A48 — first-name collision surname guard (option C') + Defect 5 null-vs-zero.

C': per submission containing a collision surname (unique in the pool AND also
some pool player's first name), classify S1 / S2 / S3; S1 precedes S2; S3
resolves by venue (own team sub only), except P1 (English top-1000) surnames,
which get no own-sub allowance.

Defect 5: a zero is measured only if we looked and found nothing. 0 mentions
with discarded (ambiguous / guard-filtered) candidates is `unmeasurable`, a
third status distinct from both `ok` and `null`, and NULLs both reddit columns
downstream (renormalize, the A47 Trends path).
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compute_oaq as co  # noqa: E402
import fetch_reddit as fr  # noqa: E402


def _write_corpus(tmp_path, name, posts):
    (tmp_path / f"{name}.jsonl").write_text(
        "\n".join(json.dumps(p) for p in posts), encoding="utf-8")


def _post(pid, title, score=1, author="u"):
    return {"id": pid, "title": title, "selftext": "", "score": score,
            "author": author}


def _owner(pid, full_name, fn_surnames, p1, teams):
    """Group member for a collision surname's owner (as build_groups emits)."""
    sn = fr.fold(full_name.split()[-1])
    fn = fr.fold(full_name.split()[0])
    chk, _ = fr.make_evidence_check(full_name, {sn: [fn]}, force=True)
    return {"pid": pid, "fn": fn, "shared": False, "guarded": False,
            "collision": True, "fn_surnames": frozenset(fn_surnames),
            "p1": p1, "teams": set(teams), "nicks": set(), "checker": chk,
            "discriminating": True, "identity_ambiguous": False}


# --------------------------------------------------------------------------- #
# collision set derivation                                                     #
# --------------------------------------------------------------------------- #
def _mini_pool():
    return [
        {"player_id": "1", "full_name": "Jack Quinn"},
        {"player_id": "2", "full_name": "Quinn Hughes"},
        {"player_id": "3", "full_name": "Connor McDavid"},
        {"player_id": "4", "full_name": "Kyle Connor"},
        {"player_id": "5", "full_name": "Cole Caufield"},
        {"player_id": "6", "full_name": "Ian Cole"},
        {"player_id": "7", "full_name": "Erik Cole"},
    ]


def test_collision_surnames_finds_owners_and_fn_surnames():
    col = fr.collision_surnames(_mini_pool())
    assert col["quinn"] == frozenset({"hughes"})
    assert col["connor"] == frozenset({"mcdavid"})


def test_collision_requires_surname_unique_in_pool():
    # "cole" is both a first name (Cole Caufield) and a surname, but TWO pool
    # players carry it as a surname, so the A15/A21 group logic owns it — it
    # must not be a single-owner collision.
    col = fr.collision_surnames(_mini_pool())
    assert set(col) == {"quinn", "connor"}


def test_build_groups_carries_collision_fields_and_forces_checker():
    players = _mini_pool()[:2]
    smap = fr.build_surname_map(players)
    col = fr.collision_surnames(players)
    wteams = {"1": {"BUF"}, "2": {"VAN"}}
    groups = fr.build_groups(players, wteams, {}, smap, None,
                             collisions=col, en1000=frozenset({"paul"}))
    q = groups["quinn"][0]
    assert q["collision"] is True
    assert q["fn_surnames"] == frozenset({"hughes"})
    assert q["p1"] is False
    assert q["checker"] is not None          # forced despite unique surname
    h = groups["hughes"][0]
    assert h["collision"] is False
    assert h["fn_surnames"] is None


# --------------------------------------------------------------------------- #
# 3-state classification in scan_corpus                                        #
# --------------------------------------------------------------------------- #
def _jack_quinn_setup(tmp_path, sub, posts, counting=("hockey", "sabres")):
    _write_corpus(tmp_path, sub, posts)
    groups = {"quinn": [_owner("1", "Jack Quinn", {"hughes"}, False, {"BUF"})]}
    acc, _ = fr.scan_corpus(groups, {"1": list(counting)}, tmp_path)
    return acc["1"]


def test_s1_every_occurrence_followed_by_fn_surname_filters_owner(tmp_path):
    a = _jack_quinn_setup(tmp_path, "hockey",
                          [_post("p1", "Quinn Hughes with a hat trick")])
    assert a["scores"] == {}
    assert a["guard_filtered"] == 1
    assert a["ambiguous"] == 0


def test_s2_standalone_with_evidence_counts(tmp_path):
    a = _jack_quinn_setup(tmp_path, "hockey",
                          [_post("p2", "Jack Quinn scores twice", score=7)])
    assert a["scores"] == {"p2": 7}
    assert a["guard_filtered"] == 0
    assert a["ambiguous"] == 0


def test_s3_own_team_sub_counts_for_owner(tmp_path):
    a = _jack_quinn_setup(tmp_path, "sabres",
                          [_post("p3", "Quinn looked great tonight", score=4)])
    assert a["scores"] == {"p3": 4}
    assert a["ambiguous"] == 0


def test_s3_league_sub_is_ambiguous(tmp_path):
    a = _jack_quinn_setup(tmp_path, "hockey",
                          [_post("p4", "Quinn looked great tonight")])
    assert a["scores"] == {}
    assert a["ambiguous"] == 1
    assert a["guard_filtered"] == 0


def test_s3_rival_sub_counts_for_nobody(tmp_path):
    # r/winnipegjets is not BUF's sub and not in Jack Quinn's counting set:
    # no credit, no disclosure, and no allsubs credit either.
    a = _jack_quinn_setup(tmp_path, "winnipegjets",
                          [_post("p5", "thoughts on Quinn")])
    assert a["scores"] == {}
    assert a["ambiguous"] == 0
    assert a["guard_filtered"] == 0
    assert a["allsubs_ids"] == set()


def test_trailing_occurrence_is_standalone(tmp_path):
    # Last token of the text: no next token, so it cannot be first-name usage.
    a = _jack_quinn_setup(tmp_path, "sabres",
                          [_post("p6", "what a play by Quinn", score=2)])
    assert a["scores"] == {"p6": 2}


def test_one_standalone_occurrence_defeats_s1(tmp_path):
    # "Quinn Hughes" is first-name usage but the second "Quinn" is standalone,
    # so the post is not S1; no first-name evidence -> S3, own sub -> counted.
    a = _jack_quinn_setup(tmp_path, "sabres",
                          [_post("p7", "Quinn Hughes on Quinn tonight")])
    assert a["scores"] == {"p7": 1}
    assert a["guard_filtered"] == 0


def test_s1_takes_precedence_over_s2_lauren_kyle(tmp_path):
    # The A15 checker fires ("Kyle" appears) but every "connor" is followed by
    # a first-name-owner surname — proven first-name usage wins.
    _write_corpus(tmp_path, "hockey", [_post(
        "p8", "Instagram story posted by Lauren Kyle (Connor McDavid's wife)")])
    groups = {"connor": [_owner("9", "Kyle Connor", {"mcdavid", "bedard"},
                                False, {"WPG"})]}
    acc, _ = fr.scan_corpus(groups, {"9": ["hockey", "winnipegjets"]}, tmp_path)
    assert acc["9"]["scores"] == {}
    assert acc["9"]["guard_filtered"] == 1
    assert acc["9"]["ambiguous"] == 0


def test_p1_surname_gets_no_own_sub_allowance(tmp_path):
    # P1-strict: own-sub context cannot resolve an ordinary-word confuser.
    _write_corpus(tmp_path, "TampaBayLightning",
                  [_post("p9", "Paul with a big hit")])
    groups = {"paul": [_owner("5", "Nick Paul", {"cotter"}, True, {"TB"})]}
    acc, _ = fr.scan_corpus(groups, {"5": ["hockey", "TampaBayLightning"]},
                            tmp_path)
    assert acc["5"]["scores"] == {}
    assert acc["5"]["ambiguous"] == 1


def test_p1_surname_still_counts_with_evidence(tmp_path):
    _write_corpus(tmp_path, "TampaBayLightning",
                  [_post("p10", "Nick Paul with a big hit", score=2)])
    groups = {"paul": [_owner("5", "Nick Paul", {"cotter"}, True, {"TB"})]}
    acc, _ = fr.scan_corpus(groups, {"5": ["hockey", "TampaBayLightning"]},
                            tmp_path)
    assert acc["5"]["scores"] == {"p10": 2}


# --------------------------------------------------------------------------- #
# non-collision guards must be untouched                                       #
# --------------------------------------------------------------------------- #
def _guarded_member(pid, full_name, teams=()):
    sn = fr.fold(full_name.split()[-1])
    fn = fr.fold(full_name.split()[0])
    chk, _ = fr.make_evidence_check(full_name, {sn: [fn]}, force=True)
    return {"pid": pid, "fn": fn, "shared": False, "guarded": True,
            "teams": set(teams), "nicks": set(), "checker": chk,
            "discriminating": True, "identity_ambiguous": False}


def test_guarded_non_collision_surname_still_guarded(tmp_path):
    _write_corpus(tmp_path, "hockey", [
        _post("g1", "no hockey today but AHL"),
        _post("g2", "Daniil But highlight goal", score=7)])
    groups = {"but": [_guarded_member("1", "Daniil But")]}
    acc, _ = fr.scan_corpus(groups, {"1": ["hockey"]}, tmp_path)
    assert acc["1"]["scores"] == {"g2": 7}
    assert acc["1"]["guard_filtered"] == 1


def test_guarded_non_collision_gets_no_own_sub_allowance(tmp_path):
    # The own-sub allowance is scoped to collision surnames ONLY (A48 scoping
    # rule 2): a P1/P2b-guarded player gets nothing from team context.
    _write_corpus(tmp_path, "winnipegjets",
                  [_post("g3", "Stanley with a goal")])
    groups = {"stanley": [_guarded_member("2", "Logan Stanley", {"WPG"})]}
    acc, _ = fr.scan_corpus(groups, {"2": ["hockey", "winnipegjets"]}, tmp_path)
    assert acc["2"]["scores"] == {}
    assert acc["2"]["guard_filtered"] == 1


def test_mcdavid_p2b_exemption_survives():
    # The dominant bigram partner "connor" IS a pool first name, so P2b must
    # not guard mcdavid — while "stanley cup" still guards stanley.
    en1000 = frozenset()
    stats = {
        "mcdavid": {"occ": 100, "next_pool_sn": 0,
                    "bigrams": Counter({("prev", "connor"): 90})},
        "stanley": {"occ": 100, "next_pool_sn": 0,
                    "bigrams": Counter({("next", "cup"): 90})},
    }
    guarded = fr.guard_set_a43({"mcdavid": 0.02, "stanley": 0.02}, en1000,
                               stats, pool_first_names={"connor"})
    assert "mcdavid" not in guarded
    assert "stanley" in guarded


# --------------------------------------------------------------------------- #
# Defect 5 — status ladder                                                     #
# --------------------------------------------------------------------------- #
def test_status_unmeasurable_via_ambiguous():
    assert fr.resolve_status(2, 2, 0, 433, 0) == "unmeasurable"


def test_status_unmeasurable_via_guard_filtered_only():
    assert fr.resolve_status(2, 2, 0, 0, 5) == "unmeasurable"


def test_status_true_zero_stays_ok():
    assert fr.resolve_status(2, 2, 0, 0, 0) == "ok"


def test_status_mentions_with_ambiguous_stays_ok():
    # Ambiguity alone must NOT trigger; only a wiped-out measurement does.
    assert fr.resolve_status(2, 2, 10, 400, 0) == "ok"


def test_status_null_wins_when_no_corpus_present():
    assert fr.resolve_status(0, 2, 0, 0, 0) == "null"
    assert fr.resolve_status(0, 2, 0, 12, 3) == "null"


def test_status_partial_ladder():
    assert fr.resolve_status(1, 2, 0, 1, 0) == "unmeasurable"
    assert fr.resolve_status(1, 2, 0, 0, 0) == "partial"
    assert fr.resolve_status(1, 2, 4, 0, 0) == "partial"


# --------------------------------------------------------------------------- #
# Defect 5 — compute_oaq NULL + renormalize                                    #
# --------------------------------------------------------------------------- #
def _oaq_df(n=12, seed=3):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "player_id": range(1, n + 1),
        "full_name": [f"P{i}" for i in range(n)],
        "wiki_12mo": rng.uniform(1e3, 1e6, n),
        "wiki_intl_12mo": rng.uniform(0, 1e4, n),
        "reddit_mentions_12mo": rng.integers(0, 400, n).astype(float),
        "reddit_upvotes_12mo": rng.integers(0, 9000, n).astype(float),
        "trends_12mo": rng.uniform(0, 30, n),
        "reddit_status": ["ok"] * n,
    })


def _apply_reddit_null(df):
    # The exact two lines load_inputs runs.
    mask = co.reddit_null_mask(df["reddit_status"])
    df.loc[mask, ["reddit_mentions_12mo", "reddit_upvotes_12mo"]] = np.nan
    return df


def test_reddit_null_mask_taxonomy():
    s = pd.Series(["ok", "partial", "null", "", None, "unmeasurable",
                   " Unmeasurable "])
    assert list(co.reddit_null_mask(s)) == [False, False, True, True, True,
                                            True, True]


def test_unmeasurable_nulls_both_reddit_columns():
    df = _oaq_df()
    df.loc[3, "reddit_status"] = "unmeasurable"
    out = _apply_reddit_null(df)
    assert np.isnan(out.loc[3, "reddit_mentions_12mo"])
    assert np.isnan(out.loc[3, "reddit_upvotes_12mo"])
    assert not np.isnan(out.loc[4, "reddit_mentions_12mo"])


def test_unmeasurable_renormalizes_weights():
    """Renormalization == imputing the weighted mean of the present components
    (same identity test_trends_null_taxonomy_a47 asserts for Trends)."""
    df = _oaq_df()
    df.loc[3, "reddit_status"] = "unmeasurable"
    out = _apply_reddit_null(df)
    er, _ = co.compute_engagement_raw(out)

    comp_z = {c: co.zscore_array(out[c].to_numpy(dtype=float))
              for c in co.COMPONENTS}
    present = [c for c in co.COMPONENTS
               if c not in ("reddit_mentions_12mo", "reddit_upvotes_12mo")]
    w = sum(co.WEIGHTS[c] for c in present)
    m = sum(co.WEIGHTS[c] * comp_z[c][3] for c in present) / w
    assert abs(er[3] - m) < 1e-12
