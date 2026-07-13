"""Compute 12-month Reddit mention + upvote counts per player from the local
Arctic Shift corpus (pre-reg §3.3-3.4; window A11; identity A15/A21; sub
selection A22; source + local matching A23).

Composite weights 0.27 (mentions) + 0.17 (upvotes) per A12. Counts submissions
in r/hockey + the player's A22 window-roster team subreddits whose folded
title+selftext contains the player's surname as a whole token, over the FIXED
window [2025-04-18, 2026-04-18) UTC (A11), deduped by submission id across
subs, upvotes = sum of `score`.

Source lineage (A2 -> A9 -> A23): live Reddit search (capped at 1,000 results,
no date filter, OAuth creds) is replaced by the Arctic Shift archive. The
corpus is pulled once by fetch_reddit_corpus.py into cache/reddit_corpus/;
THIS script never touches the network for Reddit data and is deterministic
and re-runnable from the corpus. The 1,000-cap / `reddit_capped` machinery is
removed (A23 rule 1 — the flag was disclosure-only, no downstream consumer).

Matching (A23 rule 3): NFKD accent-fold, case-fold, every non-alphanumeric
character (incl. curly apostrophes) mapped to a space, whole-token surname
match on title + selftext. The archive's own query search is NOT used
(verified recall misses: possessives, edited posts).

Attribution (A15, extended by A21) for shared surnames, per submission:
  1. First-name evidence (A15 checker) counts only for sharers whose folded
     first name does NOT prefix-collide with another sharer's (A21 rule 1).
     Exactly one such claimant -> attributed; two -> ambiguous.
  2. No evidence claimant, TEAM subreddit: exactly one sharer window-rostered
     on that team -> attributed to him (A21 rule 2); several -> ambiguous.
  3. No evidence claimant, league-wide sub: among prefix-colliding sharers,
     a team-nickname token (final word of the team's full name, from
     raw/teams.csv) naming exactly one sharer's team -> attributed (A21
     rule 4); both teams named or none -> ambiguous.
  4. Fully non-discriminable pairs (identical folded first names AND identical
     window-team sets — the two VAN Elias Petterssons) can never be separated:
     every matching submission is ambiguous and both rows carry
     `reddit_identity_ambiguous = true` (A21 rule 3).
Ambiguous submissions are counted in `ambiguous_mentions` (for every group
member whose counting subs include that subreddit) and excluded from
mentions/upvotes and the bootstrap detail pool.

Sub selection (A22): r/hockey + the team subreddit of EVERY team the player
was rostered on inside the window, derived from NHL-API landing seasonTotals
(seasons 20242025 + 20252026, gameTypeId 2, leagueAbbrev NHL; cached HTTP).
UTA includes predecessor sub r/UtahHockey (A22 sub-rename rule). Landing
failure falls back to the snapshot team_code (logged).

Descriptive columns (A23 rule 5, never composite): `reddit_mentions_allsubs`
(attributed matches over the full 36-sub corpus incl. r/nhl + r/fantasyhockey)
and `reddit_mentions_fantasy` (r/fantasyhockey only).

Writes: marchand_index/raw/reddit_counts.csv
  player_id, full_name, reddit_subs_searched, reddit_mentions_12mo,
  reddit_upvotes_12mo, unique_authors, reddit_status, ambiguous_mentions,
  surname_shared, reddit_identity_ambiguous, reddit_mentions_allsubs,
  reddit_mentions_fantasy, fetch_date
  + marchand_index/raw/reddit_detail.csv (player_id, submission_id, score)
    for the §10 bootstrap
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (CONTACT_UA, RAW_DIR, atomic_write_csv, load_csv,  # noqa: E402
                     load_players, session)

NHL_API = "https://api-web.nhle.com/v1"
WINDOW_SEASONS = {"20242025", "20252026"}   # A22: seasons overlapping the window

# Fixed attention window (pre-reg A11) — identical to fetch_reddit_corpus.py.
WINDOW_END = dt.date(2026, 4, 17)           # last reg-season day, inclusive
WINDOW_DAYS = 365

CORPUS_DIR = Path(__file__).parent / "cache" / "reddit_corpus"

COUNTS_FIELDS = [
    "player_id", "full_name", "reddit_subs_searched", "reddit_mentions_12mo",
    "reddit_upvotes_12mo", "unique_authors", "reddit_status",
    "ambiguous_mentions", "surname_shared", "reddit_identity_ambiguous",
    "reddit_mentions_allsubs", "reddit_mentions_fantasy", "fetch_date",
]
DETAIL_FIELDS = ["player_id", "submission_id", "score"]

# DailyFaceoff team_code -> team subreddit (r/hockey is always counted too).
TEAM_SUB = {
    "ANA": "anaheimducks", "BOS": "BostonBruins", "BUF": "sabres",
    "CGY": "CalgaryFlames", "CAR": "canes", "CHI": "hawks",
    "COL": "ColoradoAvalanche", "CBJ": "BlueJackets", "DAL": "DallasStars",
    "DET": "DetroitRedWings", "EDM": "EdmontonOilers", "FLA": "FloridaPanthers",
    "LA": "losangeleskings", "MIN": "wildhockey", "MON": "Habs",
    "NAS": "Predators", "NJ": "devils", "NYI": "NewYorkIslanders",
    "NYR": "rangers", "OTT": "OttawaSenators", "PHI": "Flyers",
    "PIT": "penguins", "SJ": "SanJoseSharks", "SEA": "SeattleKraken",
    "STL": "stlouisblues", "TB": "TampaBayLightning", "TOR": "leafs",
    "UTA": "utahmammoth", "VAN": "canucks", "VEG": "goldenknights",
    "WAS": "caps", "WPG": "winnipegjets",
}
# A22 sub-rename rule: predecessor subs still active inside the window.
PREDECESSOR_SUB = {"UTA": "UtahHockey"}
LEAGUE_SUBS = ["hockey", "nhl", "fantasyhockey"]   # non-team subs in the corpus
ALL_SUBS = LEAGUE_SUBS + ["UtahHockey"] + sorted(TEAM_SUB.values())


def last_name(full_name: str) -> str:
    return full_name.split()[-1]


# --------------------------------------------------------------------------- #
# A15 — within-pool surname-collision attribution (unchanged by A23)           #
# --------------------------------------------------------------------------- #
def fold(s: str) -> str:
    """Accent-fold + case-fold for name matching (Fehérváry -> fehervary)."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).casefold()


def build_surname_map(players: list[dict]) -> dict[str, list[str]]:
    """Folded surname -> list of folded first names of pool players sharing it.

    A surname is SHARED (A15) iff its list has length >= 2.
    """
    out: dict[str, list[str]] = {}
    for p in players:
        parts = p["full_name"].split()
        if not parts:
            continue
        sn = fold(parts[-1])
        fn = fold(parts[0])
        out.setdefault(sn, []).append(fn)
    return out


def make_evidence_check(full_name: str, surname_map: dict[str, list[str]]):
    """Return (checker, shared) for a player. checker(title, selftext) -> bool.

    checker is None when the surname is unique in the pool (A2 rule unchanged).
    For shared surnames a submission is attributed only if:
      (a) a word in the folded text STARTS WITH the folded first name
          (len >= 3; shorter first names require an exact word match), or
      (b) the text matches "<initial>. <surname>" / "<initial> <surname>" and
          that initial is unique among pool players sharing the surname.
    """
    parts = full_name.split()
    sn = fold(parts[-1])
    fn = fold(parts[0])
    sharers = surname_map.get(sn, [fn])
    shared = len(sharers) >= 2
    if not shared:
        return None, False

    initial = fn[:1]
    initial_unique = sum(1 for f in sharers if f[:1] == initial) == 1
    initial_re = (
        re.compile(rf"\b{re.escape(initial)}\.?\s+{re.escape(sn)}\b")
        if initial_unique else None
    )
    word_re = re.compile(r"[a-z0-9']+")

    def check(title: str, selftext: str) -> bool:
        text = fold(f"{title} {selftext}")
        tokens = word_re.findall(text)
        if len(fn) >= 3:
            if any(t.startswith(fn) for t in tokens):
                return True
        else:
            if fn in tokens:
                return True
        if initial_re is not None and initial_re.search(text):
            return True
        return False

    return check, True


# --------------------------------------------------------------------------- #
# A23 rule 3 — local corpus matching                                           #
# --------------------------------------------------------------------------- #
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def match_fold(s: str) -> str:
    """A23 fold: accent-fold, case-fold, non-alphanumerics (incl. curly
    apostrophes) to spaces — "McDavid's" folds to "mcdavid s"."""
    return _NON_ALNUM.sub(" ", fold(s)).strip()


def match_tokens(title: str, selftext: str) -> set[str]:
    """Whole-token set of the folded submission text."""
    return set(match_fold(f"{title} {selftext}").split())


def prefix_collides(a: str, b: str) -> bool:
    """A21 rule 1: folded first names collide iff one prefixes the other."""
    return a.startswith(b) or b.startswith(a)


# --------------------------------------------------------------------------- #
# A22 — window-roster team derivation                                          #
# --------------------------------------------------------------------------- #
def load_team_maps() -> tuple[dict[str, str], dict[str, str]]:
    """(folded full team name -> team_code, team_code -> nickname token).

    Team names come from raw/teams.csv `team_slug` (e.g. "st-louis-blues");
    the nickname token is the final word (A21 rule 4). The 2024-25 Utah
    franchise name is aliased per the A22 rename rule.
    """
    name_to_code: dict[str, str] = {}
    nickname: dict[str, str] = {}
    for t in load_csv(RAW_DIR / "teams.csv"):
        words = match_fold(t["team_slug"].replace("-", " ")).split()
        name_to_code[" ".join(words)] = t["team_code"]
        nickname[t["team_code"]] = words[-1]
    name_to_code["utah hockey club"] = "UTA"
    return name_to_code, nickname


def window_teams(sess, p: dict, name_to_code: dict[str, str]) -> set[str]:
    """Team codes the player was NHL-rostered on inside the window (A22)."""
    codes: set[str] = set()
    pid = str(p.get("nhl_player_id", "") or "")
    if pid.isdigit():
        try:
            r = sess.get(f"{NHL_API}/player/{pid}/landing",
                         headers={"User-Agent": CONTACT_UA}, timeout=20)
            r.raise_for_status()
            for row in (r.json().get("seasonTotals") or []):
                if (str(row.get("season")) in WINDOW_SEASONS
                        and row.get("gameTypeId") == 2
                        and row.get("leagueAbbrev") == "NHL"):
                    nm = (row.get("teamName") or {}).get("default", "")
                    code = name_to_code.get(match_fold(nm))
                    if code:
                        codes.add(code)
        except Exception as e:
            print(f"  landing {pid}: {e!r}", file=sys.stderr)
    if not codes and p.get("team_code"):
        # Fallback to the snapshot roster team; logged so the run is auditable.
        print(f"  window_teams fallback to snapshot team for "
              f"{p.get('full_name', pid)}", file=sys.stderr)
        codes = {p["team_code"]}
    return codes


def counting_subs(codes: set[str]) -> list[str]:
    """A22 counting set: r/hockey + every window team's sub (+ predecessors)."""
    subs = ["hockey"]
    for c in sorted(codes):
        if c in TEAM_SUB:
            subs.append(TEAM_SUB[c])
        if c in PREDECESSOR_SUB:
            subs.append(PREDECESSOR_SUB[c])
    return subs


# --------------------------------------------------------------------------- #
# A21 — group-level attribution                                                #
# --------------------------------------------------------------------------- #
def build_groups(players: list[dict], wteams: dict[str, set[str]],
                 nickname: dict[str, str],
                 surname_map: dict[str, list[str]]) -> dict[str, list[dict]]:
    """Folded surname -> attribution group (one member per pool player)."""
    groups: dict[str, list[dict]] = {}
    for p in players:
        parts = p["full_name"].split()
        sn, fn = fold(parts[-1]), fold(parts[0])
        checker, shared = make_evidence_check(p["full_name"], surname_map)
        groups.setdefault(sn, []).append({
            "pid": p["player_id"], "fn": fn, "shared": shared,
            "teams": wteams[p["player_id"]],
            "nicks": {nickname[c] for c in wteams[p["player_id"]] if c in nickname},
            "checker": checker,
        })
    for group in groups.values():
        for m in group:
            others = [o for o in group if o is not m]
            m["discriminating"] = not any(prefix_collides(m["fn"], o["fn"])
                                          for o in others)
            # A21 rule 3: colliding first name AND identical window-team set
            # -> the pair is fully non-discriminable (the two VAN Petterssons).
            m["identity_ambiguous"] = any(
                prefix_collides(m["fn"], o["fn"]) and m["teams"] == o["teams"]
                for o in others)
    return groups


def attribute(group: list[dict], title: str, selftext: str,
              tokens: set[str], sub_team: str | None) -> str | None:
    """Attribute one surname-matching submission. Returns the winning pid,
    or None for ambiguous (A21). Single-member groups always win (A2 rule)."""
    if len(group) == 1:
        return group[0]["pid"]
    # 1. Discriminating first-name evidence (A15 gated by A21 rule 1).
    claimants = [m for m in group
                 if m["discriminating"] and m["checker"] is not None
                 and m["checker"](title, selftext)]
    if len(claimants) == 1:
        return claimants[0]["pid"]
    if len(claimants) > 1:
        return None
    # 2. Team-subreddit context (A21 rule 2).
    if sub_team is not None:
        rostered = [m for m in group if sub_team in m["teams"]]
        if len(rostered) == 1:
            return rostered[0]["pid"]
        return None
    # 3. League-wide sub: nickname token among prefix-colliding sharers
    #    (A21 rule 4). Tokens naming both sharers' teams -> ambiguous.
    colliding = [m for m in group if not m["discriminating"]]
    hits = [m for m in colliding if m["nicks"] & tokens]
    if len(hits) == 1:
        return hits[0]["pid"]
    return None


# --------------------------------------------------------------------------- #
# Matcher                                                                      #
# --------------------------------------------------------------------------- #
def sub_team_code(sub: str) -> str | None:
    """Team code a subreddit belongs to, None for league-wide subs."""
    for code, s in TEAM_SUB.items():
        if s == sub:
            return code
    for code, s in PREDECESSOR_SUB.items():
        if s == sub:
            return code
    return None


def scan_corpus(groups: dict[str, list[dict]], counting: dict[str, list[str]],
                corpus_dir: Path = CORPUS_DIR):
    """Stream every corpus file once, distributing matches to players.

    Returns (acc by pid, missing_subs). acc fields: scores (id->score, counting
    subs, deduped), authors, ambiguous, allsubs_ids, fantasy_ids.
    """
    acc: dict[str, dict] = {}
    for group in groups.values():
        for m in group:
            acc[m["pid"]] = {"scores": {}, "authors": set(), "ambiguous": 0,
                             "allsubs_ids": set(), "fantasy_ids": set()}
    count_pids: dict[str, set[str]] = {}   # sub -> pids counting it
    for pid, subs in counting.items():
        for s in subs:
            count_pids.setdefault(s, set()).add(pid)

    missing: list[str] = []
    surnames = frozenset(groups)
    for sub in ALL_SUBS:
        path = corpus_dir / f"{sub}.jsonl"
        if not path.exists():
            missing.append(sub)
            continue
        steam = sub_team_code(sub)
        n_posts = 0
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    post = json.loads(line)
                except json.JSONDecodeError:
                    continue
                n_posts += 1
                title = post.get("title") or ""
                selftext = post.get("selftext") or ""
                tokens = match_tokens(title, selftext)
                hit_surnames = tokens & surnames
                if not hit_surnames:
                    continue
                for sn in hit_surnames:
                    group = groups[sn]
                    winner = attribute(group, title, selftext, tokens, steam)
                    if winner is None:
                        # Ambiguous: disclosed for every member counting this sub.
                        for m in group:
                            if sub in counting[m["pid"]]:
                                acc[m["pid"]]["ambiguous"] += 1
                        continue
                    a = acc[winner]
                    a["allsubs_ids"].add(post["id"])
                    if sub == "fantasyhockey":
                        a["fantasy_ids"].add(post["id"])
                    if sub in counting[winner]:
                        a["scores"][post["id"]] = int(post.get("score") or 0)
                        if post.get("author"):
                            a["authors"].add(post["author"])
        print(f"r/{sub}: scanned {n_posts} posts")
    return acc, missing


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    players = load_players()
    order = [p["player_id"] for p in players]
    surname_map = build_surname_map(players)
    name_to_code, nickname = load_team_maps()

    sess = session(expire_hours=24 * 7)   # landing JSONs are already cached
    wteams = {p["player_id"]: window_teams(sess, p, name_to_code) for p in players}
    counting = {p["player_id"]: counting_subs(wteams[p["player_id"]]) for p in players}

    groups = build_groups(players, wteams, nickname, surname_map)
    n_shared = sum(1 for g in groups.values() if len(g) >= 2 for _ in g)
    print(f"A15/A21 identity: {n_shared}/{len(players)} players share a surname; "
          f"{sum(1 for g in groups.values() for m in g if m['identity_ambiguous'])} "
          "flagged fully non-discriminable (A21 rule 3).")
    multi = {p['player_id']: counting[p['player_id']] for p in players
             if len(counting[p['player_id']]) > 2}
    print(f"A22 multi-sub players: {len(multi)}")

    acc, missing = scan_corpus(groups, counting)
    if missing:
        print(f"WARNING: corpus missing for {missing} — affected players get "
              "partial/null status.", file=sys.stderr)

    counts_rows, detail_rows = [], []
    by_pid = {p["player_id"]: p for p in players}
    for pid in order:
        p = by_pid[pid]
        a = acc[pid]
        subs = counting[pid]
        present = [s for s in subs if s not in missing]
        if not present:
            status, mentions, upvotes = "null", "", ""
        elif len(present) < len(subs):
            status = "partial"
            mentions, upvotes = len(a["scores"]), sum(a["scores"].values())
        else:
            status = "ok"
            mentions, upvotes = len(a["scores"]), sum(a["scores"].values())
        sn = fold(p["full_name"].split()[-1])
        me = next(m for m in groups[sn] if m["pid"] == pid)
        counts_rows.append({
            "player_id": pid,
            "full_name": p["full_name"],
            "reddit_subs_searched": "|".join(subs),
            "reddit_mentions_12mo": mentions,
            "reddit_upvotes_12mo": upvotes,
            "unique_authors": len(a["authors"]) if status != "null" else "",
            "reddit_status": status,
            "ambiguous_mentions": a["ambiguous"] if status != "null" else "",
            "surname_shared": str(me["shared"]).lower(),
            "reddit_identity_ambiguous": str(me["identity_ambiguous"]).lower(),
            "reddit_mentions_allsubs": len(a["allsubs_ids"]) if status != "null" else "",
            "reddit_mentions_fantasy": len(a["fantasy_ids"]) if status != "null" else "",
            "fetch_date": fetch_date,
        })
        if status != "null":
            detail_rows.extend(
                {"player_id": pid, "submission_id": sid, "score": score}
                for sid, score in a["scores"].items())

    atomic_write_csv(RAW_DIR / "reddit_counts.csv", counts_rows, COUNTS_FIELDS)
    atomic_write_csv(RAW_DIR / "reddit_detail.csv", detail_rows, DETAIL_FIELDS)
    n_ok = sum(1 for r in counts_rows if r["reddit_status"] == "ok")
    n_part = sum(1 for r in counts_rows if r["reddit_status"] == "partial")
    n_null = sum(1 for r in counts_rows if r["reddit_status"] == "null")
    print(f"\nWrote reddit_counts.csv ({len(counts_rows)} rows; {n_ok} ok, "
          f"{n_part} partial, {n_null} null) + reddit_detail.csv "
          f"({len(detail_rows)} rows)")


if __name__ == "__main__":
    main()
