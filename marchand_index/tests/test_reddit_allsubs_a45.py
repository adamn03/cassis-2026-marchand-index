"""A45 (Defect 2) — allsubs detail: venue + score for every attributed winner.

`scan_corpus` has always streamed all 36 subs and tracked winners in
`allsubs_ids`; this claims the fix that keeps (subreddit, score) per post and
writes raw/reddit_detail_allsubs.csv so the affiliation split can see rival
venues. Ordering constraint honored: these tests assume the A48 collision
guard is active (rival-sub S3 for a collision surname must NOT leak in).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fetch_reddit as fr  # noqa: E402


def _write_corpus(tmp_path, name, posts):
    (tmp_path / f"{name}.jsonl").write_text(
        "\n".join(json.dumps(p) for p in posts), encoding="utf-8")


def _post(pid, title, score=1, author="u"):
    return {"id": pid, "title": title, "selftext": "", "score": score,
            "author": author}


def _member(pid, fn, checker=None, guarded=False, teams=()):
    return {"pid": pid, "fn": fn, "shared": False, "guarded": guarded,
            "teams": set(teams), "nicks": set(), "checker": checker,
            "discriminating": True, "identity_ambiguous": False}


def test_allsubs_records_venue_and_score(tmp_path):
    # Winner in a NON-counting rival sub is captured with its venue + score.
    _write_corpus(tmp_path, "winnipegjets",
                  [_post("w1", "McDavid torched us again", score=9)])
    groups = {"mcdavid": [_member("9", "connor")]}
    acc, _ = fr.scan_corpus(groups, {"9": ["hockey", "EdmontonOilers"]},
                            tmp_path)
    assert acc["9"]["allsubs_ids"] == {"w1": ("winnipegjets", 9)}
    assert acc["9"]["scores"] == {}          # not a counting sub


def test_allsubs_len_semantics_unchanged(tmp_path):
    # reddit_mentions_allsubs is len(allsubs_ids); dict len == old set len.
    _write_corpus(tmp_path, "hockey",
                  [_post("h1", "McDavid hat trick", score=3)])
    _write_corpus(tmp_path, "winnipegjets",
                  [_post("w1", "McDavid again", score=9)])
    groups = {"mcdavid": [_member("9", "connor")]}
    acc, _ = fr.scan_corpus(groups, {"9": ["hockey"]}, tmp_path)
    assert len(acc["9"]["allsubs_ids"]) == 2
    assert acc["9"]["allsubs_ids"]["h1"] == ("hockey", 3)


def test_collision_s3_rival_sub_stays_out_of_allsubs(tmp_path):
    # The A48 ordering rule in miniature: bare "Quinn" in a rival sub must not
    # enter the allsubs detail for Jack Quinn.
    _write_corpus(tmp_path, "winnipegjets", [_post("r1", "thoughts on Quinn")])
    sn = fr.fold("Quinn")
    chk, _ = fr.make_evidence_check("Jack Quinn", {sn: ["jack"]}, force=True)
    owner = dict(_member("1", "jack", checker=chk, teams={"BUF"}),
                 collision=True, fn_surnames=frozenset({"hughes"}), p1=False)
    acc, _ = fr.scan_corpus({"quinn": [owner]}, {"1": ["hockey", "sabres"]},
                            tmp_path)
    assert acc["1"]["allsubs_ids"] == {}


def test_collision_s2_rival_sub_does_enter_allsubs(tmp_path):
    # First-name evidence resolves it even in a rival venue.
    _write_corpus(tmp_path, "winnipegjets",
                  [_post("r2", "Jack Quinn buried one on us", score=4)])
    sn = fr.fold("Quinn")
    chk, _ = fr.make_evidence_check("Jack Quinn", {sn: ["jack"]}, force=True)
    owner = dict(_member("1", "jack", checker=chk, teams={"BUF"}),
                 collision=True, fn_surnames=frozenset({"hughes"}), p1=False)
    acc, _ = fr.scan_corpus({"quinn": [owner]}, {"1": ["hockey", "sabres"]},
                            tmp_path)
    assert acc["1"]["allsubs_ids"] == {"r2": ("winnipegjets", 4)}
