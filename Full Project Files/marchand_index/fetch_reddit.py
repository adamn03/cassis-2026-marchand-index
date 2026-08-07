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

First-name collision surnames (A48, option C'): a surname unique in the pool
that is also some pool player's FIRST name (13 of them: beck blake cole colton
connor frank james joshua paul quinn reilly shea thomas) is never handed to its
owner unchecked. Per submission the token is classified: S1 (every occurrence
immediately followed by the surname of a player whose first name it is) ->
proven first-name usage, owner ineligible, disclosed in
`guard_filtered_mentions`; S2 (>=1 standalone occurrence and the owner's A15
checker fires) -> owner eligible; S3 (standalone, no evidence) -> eligible only
in the owner's own team sub, and only if the surname is NOT in the English
top-1000 (P1-strict — own-sub context cannot resolve an ordinary-word
confuser); otherwise disclosed in `ambiguous_mentions`. S1 takes precedence
over S2. For these surnames A48 overrides A42 rule 2 and the A43 P2 guard.

Status ladder (A48 Defect 5): `null` = no corpus file for any counting sub;
`partial`/`ok` = counted; `unmeasurable` = corpus was read but 0 mentions
survived while ambiguous/guard-filtered candidates exist — we failed to
measure, we did not measure zero. Downstream treats it like `null`
(NULL -> renormalize), but disclosure columns stay populated.

Sub selection (A22): r/hockey + the team subreddit of EVERY team the player
was rostered on inside the window, derived from NHL-API landing seasonTotals
(seasons 20242025 + 20252026, gameTypeId 2, leagueAbbrev NHL; cached HTTP).
UTA includes predecessor sub r/UtahHockey (A22 sub-rename rule). Landing
failure falls back to the snapshot team_code (logged).

Descriptive columns (A23 rule 5, never composite): `reddit_mentions_allsubs`
(attributed matches over the full 36-sub corpus incl. r/nhl + r/fantasyhockey)
and `reddit_mentions_fantasy` (r/fantasyhockey only).

Writes: marchand_index/raw/reddit_counts.csv (COUNTS_FIELDS below; status is
one of ok | partial | null | unmeasurable)
  + marchand_index/raw/reddit_detail.csv (player_id, submission_id, score)
    for the §10 bootstrap
  + marchand_index/raw/reddit_detail_allsubs.csv (player_id, submission_id,
    subreddit, score) — every attributed winner over the full 36-sub corpus,
    venue kept, for the A45 affiliation split (descriptive only, never
    composite)
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import unicodedata
from collections import Counter
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
    "reddit_common_word_guard", "guard_filtered_mentions",
    "reddit_firstname_collision",
    "reddit_mentions_allsubs", "reddit_mentions_fantasy", "fetch_date",
]
DETAIL_FIELDS = ["player_id", "submission_id", "score"]
DETAIL_ALLSUBS_FIELDS = ["player_id", "submission_id", "subreddit", "score"]

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


def name_key(s: str) -> str:
    """A50: name key on the SAME fold as the corpus text.

    `fold` only strips accents and case, so it leaves hyphens and apostrophes
    in place ("Nugent-Hopkins" -> "nugent-hopkins"). Corpus text is tokenized
    with `match_fold`, which maps every non-alphanumeric to a space. A key
    carrying a hyphen or apostrophe therefore could never equal any corpus
    token, and those players silently scored zero mentions while still being
    reported as successfully measured.

    Keying through `match_fold` puts both sides in the same space:
    "nugent hopkins", "o reilly", "jean gabriel". Keys containing a space are
    MULTI-TOKEN and must be matched as an adjacent sequence (see
    `contains_sequence`); single-token keys are byte-for-byte what `fold`
    produced before A50, so every unaffected player is untouched.
    """
    return match_fold(s)


def is_multi_token(key: str) -> bool:
    return " " in key


def contains_sequence(toks: list[str], seq: tuple[str, ...]) -> bool:
    """True iff `seq` appears as consecutive tokens in `toks` (A50)."""
    if not seq:
        return False
    first, n = seq[0], len(seq)
    limit = len(toks) - n
    for i, t in enumerate(toks):
        if t == first and i <= limit and tuple(toks[i:i + n]) == seq:
            return True
    return False


def build_surname_map(players: list[dict]) -> dict[str, list[str]]:
    """Folded surname -> list of folded first names of pool players sharing it.

    A surname is SHARED (A15) iff its list has length >= 2.
    """
    out: dict[str, list[str]] = {}
    for p in players:
        parts = p["full_name"].split()
        if not parts:
            continue
        sn = name_key(parts[-1])
        fn = name_key(parts[0])
        out.setdefault(sn, []).append(fn)
    return out


def make_evidence_check(full_name: str, surname_map: dict[str, list[str]],
                        force: bool = False):
    """Return (checker, shared) for a player. checker(title, selftext) -> bool.

    checker is None when the surname is unique in the pool (A2 rule unchanged),
    UNLESS force=True (A42 common-word guard: guarded players require the same
    first-name evidence even with a pool-unique surname).
    For shared surnames a submission is attributed only if:
      (a) a word in the folded text STARTS WITH the folded first name
          (len >= 3; shorter first names require an exact word match), or
      (b) the text matches "<initial>. <surname>" / "<initial> <surname>" and
          that initial is unique among pool players sharing the surname.
    """
    parts = full_name.split()
    sn = name_key(parts[-1])
    fn = name_key(parts[0])
    sharers = surname_map.get(sn, [fn])
    shared = len(sharers) >= 2
    if not shared and not force:
        return None, False

    initial = fn[:1]
    initial_unique = sum(1 for f in sharers if f[:1] == initial) == 1
    # A50: `sn` may now be multi-token ("nugent hopkins"). The initial pattern
    # is built on the match_fold'd text, where the separator is a space, so
    # `re.escape(sn)` matches the sequence directly.
    initial_re = (
        re.compile(rf"\b{re.escape(initial)}\.?\s+{re.escape(sn)}\b")
        if initial_unique else None
    )
    word_re = re.compile(r"[a-z0-9']+")
    fn_seq = tuple(fn.split()) if is_multi_token(fn) else ()

    def check(title: str, selftext: str) -> bool:
        text = fold(f"{title} {selftext}")
        tokens = word_re.findall(text)
        if fn_seq:
            # A50: a hyphenated/apostrophed first name is an adjacent token
            # sequence in the match_fold'd text ("Jean-Gabriel" ->
            # "jean gabriel"). Prefix matching on the joined form can never
            # fire, which is the same defect as the surname bug.
            if contains_sequence(match_fold(f"{title} {selftext}").split(),
                                 fn_seq):
                return True
        elif len(fn) >= 3:
            if any(t.startswith(fn) for t in tokens):
                return True
        else:
            if fn in tokens:
                return True
        if initial_re is not None:
            # Single-token surnames keep the pre-A50 `fold` basis exactly (on
            # that text "e.pettersson" has no separator and must NOT match).
            # Only a multi-token surname needs the match_fold basis, because
            # its separator only exists there.
            basis = (match_fold(f"{title} {selftext}")
                     if is_multi_token(sn) else text)
            if initial_re.search(basis):
                return True
        return False

    return check, shared


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
# A42 — common-word surname guard                                              #
# --------------------------------------------------------------------------- #
GUARD_DF_THRESHOLD = 0.01
GUARD_DF_SENSITIVITY = (0.005, 0.02)


def surname_document_frequency(surnames: set[str],
                               corpus_dir: Path = CORPUS_DIR) -> dict[str, float]:
    """DF(sn) = fraction of corpus submissions whose folded whole-token set
    contains sn (A42 rule 1). One streaming pass, dedup by id per sub —
    identical dedup to scan_corpus so numerator and denominator agree."""
    hits = {sn: 0 for sn in surnames}
    total = 0
    target = frozenset(surnames)
    multi = {k: tuple(k.split()) for k in target if is_multi_token(k)}
    for path in sorted(corpus_dir.glob("*.jsonl")):
        seen: set[str] = set()
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    post = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pid = post.get("id")
                if pid in seen:
                    continue
                seen.add(pid)
                total += 1
                toks = match_fold(f"{post.get('title') or ''} "
                                  f"{post.get('selftext') or ''}").split()
                for sn in (set(toks) & target):
                    hits[sn] += 1
                # A50: multi-token surnames are sequences, not set members.
                for key, seq in multi.items():
                    if contains_sequence(toks, seq):
                        hits[key] += 1
    return {sn: (hits[sn] / total if total else 0.0) for sn in surnames}


def guard_set(df: dict[str, float],
              threshold: float = GUARD_DF_THRESHOLD) -> set[str]:
    """A42 guard membership at a threshold (superseded as trigger by A43;
    retained because A43 prong 2 reuses the DF threshold)."""
    return {sn for sn, f in df.items() if f >= threshold}


# --------------------------------------------------------------------------- #
# A43 — two-prong guard trigger                                                #
# --------------------------------------------------------------------------- #
GUARD_BIGRAM_SHARE = 0.5
GUARD_BIGRAM_SENSITIVITY = (0.4, 0.6)


def load_english_top1000(path: Path | None = None) -> frozenset[str]:
    """A43 prong 1: repo-pinned top-1000 English list (comment lines skipped)."""
    p = path or (Path(__file__).parent / "english_top1000.txt")
    return frozenset(
        w.strip() for w in p.read_text(encoding="utf-8-sig").splitlines()
        if w.strip() and not w.lstrip().startswith("#"))


def surname_occurrence_stats(candidates: set[str], pool_surnames: set[str],
                             corpus_dir: Path = CORPUS_DIR) -> dict[str, dict]:
    """A43 prong-2 statistics over the corpus token stream: per candidate,
    occurrence count, occurrences followed by a pool surname (first-name
    usage), and adjacent-token bigram counts (both sides). Dedup by id per
    sub, matching surname_document_frequency."""
    stats = {sn: {"occ": 0, "next_pool_sn": 0, "bigrams": Counter()}
             for sn in candidates}
    target = frozenset(candidates)
    for path in sorted(corpus_dir.glob("*.jsonl")):
        seen: set[str] = set()
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    post = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pid = post.get("id")
                if pid in seen:
                    continue
                seen.add(pid)
                toks = match_fold(f"{post.get('title') or ''} "
                                  f"{post.get('selftext') or ''}").split()
                for i, t in enumerate(toks):
                    if t not in target:
                        continue
                    st = stats[t]
                    st["occ"] += 1
                    if i + 1 < len(toks):
                        nxt = toks[i + 1]
                        st["bigrams"][("next", nxt)] += 1
                        if nxt in pool_surnames:
                            st["next_pool_sn"] += 1
                    if i > 0:
                        st["bigrams"][("prev", toks[i - 1])] += 1
    return stats


def guard_set_a43(df: dict[str, float], en1000: frozenset[str],
                  stats: dict[str, dict], pool_first_names: set[str],
                  share: float = GUARD_BIGRAM_SHARE,
                  df_threshold: float = GUARD_DF_THRESHOLD) -> dict[str, str]:
    """A43 trigger. Returns {guarded surname -> reason string} for the log.

    P1: surname in the pinned English top-1000.
    P2 (DF >= threshold only): (a) >=share of occurrences followed by a pool
    surname (first-name usage), or (b) one adjacent bigram covers >=share of
    occurrences and its partner is not a pool first name (so "connor mcdavid"
    cannot guard mcdavid, while "stanley cup" guards stanley)."""
    guarded: dict[str, str] = {}
    for sn in sorted(df):
        if sn in en1000:
            guarded[sn] = "P1 english-top1000"
            continue
        if df[sn] < df_threshold:
            continue
        st = stats.get(sn)
        if not st or not st["occ"]:
            continue
        occ = st["occ"]
        if st["next_pool_sn"] / occ >= share:
            guarded[sn] = f"P2a first-name-usage {st['next_pool_sn']}/{occ}"
            continue
        # Any single bigram covering >= share of occurrences with a partner
        # that is not a pool first name (per A43 text: "a single adjacent-token
        # bigram (previous or next side)"; the exemption spares famous names
        # whose only dominant neighbor is their own first name).
        for (side, partner), n in st["bigrams"].most_common():
            if n / occ < share:
                break
            if partner not in pool_first_names:
                guarded[sn] = f"P2b dominant-bigram {side} '{partner}' {n}/{occ}"
                break
    return guarded


# --------------------------------------------------------------------------- #
# A48 — first-name collision surnames (option C')                              #
# --------------------------------------------------------------------------- #
def collision_surnames(players: list[dict]) -> dict[str, frozenset[str]]:
    """Folded surnames that are unique in the pool AND also some pool player's
    FIRST name -> surnames of the players carrying that token as a first name.

    These are the tokens `attribute()` would hand to their owner unchecked
    (single-member group); the 3-state rule in scan_corpus decides instead.
    """
    by_surname: dict[str, list[str]] = {}
    fn_to_surnames: dict[str, set[str]] = {}
    for p in players:
        parts = p["full_name"].split()
        if not parts:
            continue
        sn, fn = name_key(parts[-1]), name_key(parts[0])
        by_surname.setdefault(sn, []).append(fn)
        fn_to_surnames.setdefault(fn, set()).add(sn)
    return {sn: frozenset(fn_to_surnames[sn])
            for sn, firsts in by_surname.items()
            if len(firsts) == 1 and sn in fn_to_surnames}


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
                 surname_map: dict[str, list[str]],
                 guarded: set[str] | None = None,
                 collisions: dict[str, frozenset[str]] | None = None,
                 en1000: frozenset[str] | None = None) -> dict[str, list[dict]]:
    """Folded surname -> attribution group (one member per pool player).
    `guarded` = A42 common-word surnames: members get a forced checker.
    `collisions` = A48 first-name collision surnames (collision_surnames());
    their owners also get a forced checker plus the fields the 3-state rule in
    scan_corpus reads: `collision`, `fn_surnames`, `p1` (English top-1000)."""
    guarded = guarded or set()
    collisions = collisions or {}
    en1000 = en1000 or frozenset()
    groups: dict[str, list[dict]] = {}
    for p in players:
        parts = p["full_name"].split()
        sn, fn = name_key(parts[-1]), name_key(parts[0])
        checker, shared = make_evidence_check(
            p["full_name"], surname_map,
            force=(sn in guarded or sn in collisions))
        groups.setdefault(sn, []).append({
            "pid": p["player_id"], "fn": fn, "shared": shared,
            "guarded": sn in guarded,
            "collision": sn in collisions,
            "fn_surnames": collisions.get(sn),
            "p1": sn in en1000,
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
    subs, deduped), authors, ambiguous, guard_filtered,
    allsubs_ids ({id: (subreddit, score)} over the full 36-sub corpus),
    fantasy_ids.
    """
    acc: dict[str, dict] = {}
    for group in groups.values():
        for m in group:
            acc[m["pid"]] = {"scores": {}, "authors": set(), "ambiguous": 0,
                             "guard_filtered": 0,
                             "allsubs_ids": {}, "fantasy_ids": set()}
    count_pids: dict[str, set[str]] = {}   # sub -> pids counting it
    for pid, subs in counting.items():
        for s in subs:
            count_pids.setdefault(s, set()).add(pid)

    missing: list[str] = []
    surnames = frozenset(groups)
    # A50: split single- from multi-token keys once. The set intersection
    # below is the unchanged fast path for every single-token surname.
    multi_surnames = {k: tuple(k.split()) for k in surnames if is_multi_token(k)}
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
                # A48: the bigram test needs token ORDER; the set is derived
                # from the same split (identical work to match_tokens).
                toks = match_fold(f"{title} {selftext}").split()
                tokens = set(toks)
                hit_surnames = tokens & surnames
                # A50: multi-token surnames ("nugent hopkins") cannot appear
                # in the token SET; they are adjacent token sequences.
                for key, seq in multi_surnames.items():
                    if contains_sequence(toks, seq):
                        hit_surnames.add(key)
                if not hit_surnames:
                    continue
                for sn in hit_surnames:
                    group = groups[sn]
                    eligible = []
                    for m in group:
                        fn_sns = m.get("fn_surnames")
                        if fn_sns:
                            # A48 3-state rule (option C') for first-name
                            # collision surnames; overrides A42 rule 2 / A43 P2
                            # for these tokens. S1 precedes S2.
                            nxt = [toks[i + 1] if i + 1 < len(toks) else None
                                   for i, t in enumerate(toks) if t == sn]
                            if all(n in fn_sns for n in nxt):
                                # S1: every occurrence is "<sn> <surname of a
                                # player whose first name is sn>" — proven
                                # first-name usage, not the owner.
                                if sub in counting[m["pid"]]:
                                    acc[m["pid"]]["guard_filtered"] += 1
                            elif (m["checker"] is not None
                                    and m["checker"](title, selftext)):
                                eligible.append(m)          # S2
                            elif (not m.get("p1") and steam is not None
                                    and steam in m["teams"]):
                                eligible.append(m)          # S3 own team sub
                            elif sub in counting[m["pid"]]:
                                # S3 unresolved: counted for nobody, disclosed.
                                acc[m["pid"]]["ambiguous"] += 1
                            continue
                        # A42 rule 2: a guarded member without first-name
                        # evidence is excluded from contention; team context
                        # never suffices for guarded surnames.
                        if (not m["guarded"]
                                or (m["checker"] is not None
                                    and m["checker"](title, selftext))):
                            eligible.append(m)
                        elif sub in counting[m["pid"]]:
                            acc[m["pid"]]["guard_filtered"] += 1
                    if not eligible:
                        continue
                    winner = attribute(eligible, title, selftext, tokens, steam)
                    if winner is None:
                        # Ambiguous: disclosed for every eligible member
                        # counting this sub (guard-excluded members are in
                        # guard_filtered, not ambiguous).
                        for m in eligible:
                            if sub in counting[m["pid"]]:
                                acc[m["pid"]]["ambiguous"] += 1
                        continue
                    a = acc[winner]
                    # A45: venue + score kept so the affiliation split can use
                    # the full 36-sub corpus (raw/reddit_detail_allsubs.csv).
                    a["allsubs_ids"][post["id"]] = (sub,
                                                    int(post.get("score") or 0))
                    if sub == "fantasyhockey":
                        a["fantasy_ids"].add(post["id"])
                    if sub in counting[winner]:
                        a["scores"][post["id"]] = int(post.get("score") or 0)
                        if post.get("author"):
                            a["authors"].add(post["author"])
        print(f"r/{sub}: scanned {n_posts} posts")
    return acc, missing


def resolve_status(n_present: int, n_subs: int, mentions: int,
                   ambiguous: int, guard_filtered: int) -> str:
    """A48 Defect 5 status ladder.

    null         no corpus file for any counting sub (nothing was read)
    partial/ok   corpus read (some / all counting subs present)
    unmeasurable corpus read but 0 mentions survived while ambiguous or
                 guard-filtered candidates exist: the surname appeared and
                 every occurrence was discarded. We failed to measure — that
                 must not share a status with a measured zero. A player with
                 0 mentions and 0 discarded candidates is a genuine zero and
                 stays ok/partial.
    """
    if n_present == 0:
        return "null"
    if mentions == 0 and (ambiguous > 0 or guard_filtered > 0):
        return "unmeasurable"
    return "partial" if n_present < n_subs else "ok"


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    players = load_players()
    order = [p["player_id"] for p in players]
    surname_map = build_surname_map(players)
    name_to_code, nickname = load_team_maps()

    sess = session(expire_hours=24 * 7)   # landing JSONs are already cached
    wteams = {p["player_id"]: window_teams(sess, p, name_to_code) for p in players}
    counting = {p["player_id"]: counting_subs(wteams[p["player_id"]]) for p in players}

    # A42 pre-pass: corpus document frequency of every pool surname.
    pool_surnames = {name_key(p["full_name"].split()[-1]) for p in players}
    pool_first_names = {name_key(p["full_name"].split()[0]) for p in players}
    print("A42: computing corpus document frequency for "
          f"{len(pool_surnames)} surnames ...")
    df = surname_document_frequency(pool_surnames)
    # A43 trigger: English-top-1000 prong + phrase-collision prong.
    en1000 = load_english_top1000()
    candidates = guard_set(df)   # DF >= threshold: prong-2 candidates
    print(f"A43: prong-2 candidates (DF >= {GUARD_DF_THRESHOLD}): "
          + ", ".join(f"{sn}={df[sn]:.4f}" for sn in sorted(candidates)))
    stats = surname_occurrence_stats(candidates, pool_surnames)
    guarded_map = guard_set_a43(df, en1000, stats, pool_first_names)
    for shr in GUARD_BIGRAM_SENSITIVITY:
        alt = set(guard_set_a43(df, en1000, stats, pool_first_names, share=shr))
        print(f"A43 sensitivity: occurrence-share {shr} -> "
              f"{'IDENTICAL' if alt == set(guarded_map) else 'DIFFERS: ' + str(sorted(alt ^ set(guarded_map)))}")
    print(f"A43 guard set ({len(guarded_map)}):")
    for sn, reason in sorted(guarded_map.items()):
        print(f"  {sn:<14} DF={df[sn]:.4f}  {reason}")
    guarded = set(guarded_map)

    # A48: first-name collision surnames get the 3-state C' rule instead of
    # the unconditional single-member win (and instead of A42/A43-P2).
    collisions = collision_surnames(players)
    print(f"A48 collision surnames ({len(collisions)}): "
          + " ".join(sorted(collisions)))
    p1_strict = sorted(sn for sn in collisions if sn in en1000)
    print(f"A48 P1-strict (no own-sub allowance): {' '.join(p1_strict)}")

    groups = build_groups(players, wteams, nickname, surname_map, guarded,
                          collisions=collisions, en1000=en1000)
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

    counts_rows, detail_rows, detail_allsubs_rows = [], [], []
    by_pid = {p["player_id"]: p for p in players}
    for pid in order:
        p = by_pid[pid]
        a = acc[pid]
        subs = counting[pid]
        present = [s for s in subs if s not in missing]
        status = resolve_status(len(present), len(subs), len(a["scores"]),
                                a["ambiguous"], a["guard_filtered"])
        if status == "null":
            mentions, upvotes = "", ""
        else:
            # `unmeasurable` keeps its (zero) counts and every disclosure
            # column below — the evidence for why the row is NULL downstream
            # must stay visible in the CSV.
            mentions, upvotes = len(a["scores"]), sum(a["scores"].values())
        sn = name_key(p["full_name"].split()[-1])
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
            "reddit_common_word_guard": str(me["guarded"]).lower(),
            "guard_filtered_mentions": a["guard_filtered"] if status != "null" else "",
            "reddit_firstname_collision": str(me.get("collision", False)).lower(),
            "reddit_mentions_allsubs": len(a["allsubs_ids"]) if status != "null" else "",
            "reddit_mentions_fantasy": len(a["fantasy_ids"]) if status != "null" else "",
            "fetch_date": fetch_date,
        })
        if status != "null":
            detail_rows.extend(
                {"player_id": pid, "submission_id": sid, "score": score}
                for sid, score in a["scores"].items())
            detail_allsubs_rows.extend(
                {"player_id": pid, "submission_id": sid, "subreddit": s,
                 "score": score}
                for sid, (s, score) in a["allsubs_ids"].items())

    atomic_write_csv(RAW_DIR / "reddit_counts.csv", counts_rows, COUNTS_FIELDS)
    atomic_write_csv(RAW_DIR / "reddit_detail.csv", detail_rows, DETAIL_FIELDS)
    atomic_write_csv(RAW_DIR / "reddit_detail_allsubs.csv",
                     detail_allsubs_rows, DETAIL_ALLSUBS_FIELDS)
    n_ok = sum(1 for r in counts_rows if r["reddit_status"] == "ok")
    n_part = sum(1 for r in counts_rows if r["reddit_status"] == "partial")
    n_null = sum(1 for r in counts_rows if r["reddit_status"] == "null")
    n_unm = sum(1 for r in counts_rows if r["reddit_status"] == "unmeasurable")
    print(f"\nWrote reddit_counts.csv ({len(counts_rows)} rows; {n_ok} ok, "
          f"{n_part} partial, {n_null} null, {n_unm} unmeasurable) + "
          f"reddit_detail.csv ({len(detail_rows)} rows) + "
          f"reddit_detail_allsubs.csv ({len(detail_allsubs_rows)} rows)")


if __name__ == "__main__":
    main()
