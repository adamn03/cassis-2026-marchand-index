"""Fetch 12-month Reddit mention + upvote counts per player (pre-reg §3.3-3.4).

Composite weights 0.250 (mentions) + 0.167 (upvotes). Searches r/hockey + the
team subreddit for the player's last name over the trailing 365 days, dedups by
submission id, counts matches and sums their `score`.

Mechanism (pre-reg §14 A2, 2026-05-27): the unauthenticated public search JSON
endpoint, not PRAW (which needs OAuth creds unavailable at $0). Same source,
subreddits, query, window, dedup, and 1,000-result cap. A sub that rate-limits
or 404s contributes 0 and sets reddit_status=partial; if every request fails the
row is NULL (reddit_status=null) and the §4 sentinel renormalizes.

Robustness (2026-05-27, not a pre-reg change — transport hardening only):
  * Both CSVs are SNAPSHOT-written after every player, so a killed/detached run
    keeps its progress instead of losing everything at the final write.
  * On restart the script RESUMES: players already on disk with status ok/partial
    are kept (with their detail rows); only missing or NULL players are refetched
    (a NULL is almost always transient throttling, so it earns another attempt).
  * 429s get escalating backoff (5/10/20/40s) so popular players are not falsely
    NULLed by late-run rate limiting.

Writes: pilot2/raw/reddit_counts.csv
  player_id, full_name, subreddits, reddit_mentions_12mo, reddit_upvotes_12mo,
  unique_authors, reddit_capped, reddit_status, fetch_date
  + pilot2/raw/reddit_detail.csv (player_id, submission_id, score) for the §10 bootstrap
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_csv, load_players  # noqa: E402

import requests  # noqa: E402

UA = "marchand-index-pilot2/0.1 (research; contact ana178@sfu.ca)"
WINDOW_DAYS = 365
MAX_RESULTS = 1000          # pre-registered search cap
PAGE = 100
SLEEP = 2.0                 # unauthenticated Reddit tolerates ~1 req / 2s
RETRIES = 4                 # attempts per page before a sub is declared failed
BACKOFF = [5.0, 10.0, 20.0, 40.0]  # escalating sleep on 429 / transient 5xx

COUNTS_FIELDS = [
    "player_id", "full_name", "subreddits", "reddit_mentions_12mo",
    "reddit_upvotes_12mo", "unique_authors", "reddit_capped", "reddit_status",
    "fetch_date",
]
DETAIL_FIELDS = ["player_id", "submission_id", "score"]

# DailyFaceoff team_code -> team subreddit (r/hockey is always searched too).
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


def last_name(full_name: str) -> str:
    return full_name.split()[-1]


def get_page(sess, sub: str, query: str, after: str | None) -> tuple[list, str | None, bool]:
    """One search page. Returns (children, next_after, ok)."""
    params = {"q": query, "restrict_sr": 1, "sort": "new",
              "t": "year", "limit": PAGE, "raw_json": 1}
    if after:
        params["after"] = after
    for attempt in range(RETRIES):
        try:
            r = sess.get(f"https://www.reddit.com/r/{sub}/search.json",
                         params=params, headers={"User-Agent": UA}, timeout=25)
            # 429 (throttle) and transient 5xx are worth a longer wait + retry;
            # any other non-200 (404 dead sub, 403) is permanent for this sub.
            if r.status_code == 429 or 500 <= r.status_code < 600:
                wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
                print(f"  r/{sub} '{query}': HTTP {r.status_code}, backoff {wait}s "
                      f"(attempt {attempt + 1}/{RETRIES})", file=sys.stderr)
                time.sleep(wait)
                continue
            if r.status_code != 200:
                return [], None, False
            data = r.json().get("data", {})
            return data.get("children", []), data.get("after"), True
        except Exception as e:
            print(f"  r/{sub} '{query}': {e!r} (attempt {attempt + 1}/{RETRIES})",
                  file=sys.stderr)
            time.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
    return [], None, False


def search_sub(sess, sub: str, query: str, cutoff: float):
    """Paginate one subreddit. Returns (id->score dict, authors set, capped, ok)."""
    scores: dict[str, int] = {}
    authors: set[str] = set()
    after = None
    capped = False
    any_ok = False
    while len(scores) < MAX_RESULTS:
        children, after, ok = get_page(sess, sub, query, after)
        any_ok = any_ok or ok
        time.sleep(SLEEP)
        if not ok:
            break
        for c in children:
            d = c.get("data", {})
            if d.get("created_utc", 0) < cutoff:
                continue
            sid = d.get("name") or d.get("id")
            if not sid:
                continue
            scores[sid] = int(d.get("score", 0) or 0)
            if d.get("author"):
                authors.add(d["author"])
        if not after or len(children) < PAGE:
            break
        if len(scores) >= MAX_RESULTS:
            capped = True
            break
    return scores, authors, capped, any_ok


def load_resume() -> tuple[dict[str, dict], dict[str, list[dict]]]:
    """Read any on-disk progress. Returns (counts_by_pid, detail_by_pid).

    Only ok/partial rows are treated as done; NULL rows are dropped so the
    re-run gets another attempt (their NULL is almost always transient throttle).
    """
    counts_path = RAW_DIR / "reddit_counts.csv"
    detail_path = RAW_DIR / "reddit_detail.csv"
    counts_by_pid: dict[str, dict] = {}
    detail_by_pid: dict[str, list[dict]] = {}
    if counts_path.exists():
        for r in load_csv(counts_path):
            if r.get("reddit_status") in ("ok", "partial"):
                counts_by_pid[r["player_id"]] = r
    if detail_path.exists():
        for r in load_csv(detail_path):
            detail_by_pid.setdefault(r["player_id"], []).append(
                {"player_id": r["player_id"], "submission_id": r["submission_id"],
                 "score": int(r["score"]) if str(r["score"]).strip() else 0})
    # Keep detail only for players we are actually resuming.
    detail_by_pid = {pid: d for pid, d in detail_by_pid.items() if pid in counts_by_pid}
    return counts_by_pid, detail_by_pid


def snapshot(order: list[str], counts_by_pid: dict[str, dict],
             detail_by_pid: dict[str, list[dict]]) -> None:
    """Atomic-write both CSVs from current state, in player order."""
    rows = [counts_by_pid[pid] for pid in order if pid in counts_by_pid]
    atomic_write_csv(RAW_DIR / "reddit_counts.csv", rows, COUNTS_FIELDS)
    detail_rows = [d for pid in order for d in detail_by_pid.get(pid, [])]
    atomic_write_csv(RAW_DIR / "reddit_detail.csv", detail_rows, DETAIL_FIELDS)


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=WINDOW_DAYS)).timestamp()
    sess = requests.Session()

    players = load_players()
    order = [p["player_id"] for p in players]
    counts_by_pid, detail_by_pid = load_resume()
    if counts_by_pid:
        print(f"Resume: {len(counts_by_pid)} players already done on disk; "
              f"{len(order) - len(counts_by_pid)} to fetch.")

    for p in players:
        pid = p["player_id"]
        if pid in counts_by_pid:
            continue  # already fetched (ok/partial) in a prior run
        ln = last_name(p["full_name"])
        tsub = TEAM_SUB.get(p["team_code"], "")
        subs = ["hockey"] + ([tsub] if tsub and tsub != "hockey" else [])
        all_scores: dict[str, int] = {}
        authors: set[str] = set()
        capped = False
        ok_count = 0
        for sub in subs:
            sc, au, cap, ok = search_sub(sess, sub, ln, cutoff)
            all_scores.update(sc)        # dedup submission ids across subs
            authors |= au
            capped = capped or cap
            ok_count += int(ok)
        if ok_count == 0:
            status, mentions, upvotes = "null", "", ""
        elif ok_count < len(subs):
            status = "partial"
            mentions, upvotes = len(all_scores), sum(all_scores.values())
        else:
            status = "ok"
            mentions, upvotes = len(all_scores), sum(all_scores.values())
        print(f"{p['full_name']:<24} subs={subs} mentions={mentions} "
              f"upvotes={upvotes} authors={len(authors)} cap={capped} {status}")
        counts_by_pid[pid] = {
            "player_id": pid,
            "full_name": p["full_name"],
            "subreddits": "|".join(subs),
            "reddit_mentions_12mo": mentions,
            "reddit_upvotes_12mo": upvotes,
            "unique_authors": len(authors) if status != "null" else "",
            "reddit_capped": str(capped).lower(),
            "reddit_status": status,
            "fetch_date": fetch_date,
        }
        if status != "null":
            detail_by_pid[pid] = [
                {"player_id": pid, "submission_id": sid, "score": score}
                for sid, score in all_scores.items()
            ]
        # Snapshot after every player so a kill never loses progress.
        snapshot(order, counts_by_pid, detail_by_pid)

    snapshot(order, counts_by_pid, detail_by_pid)
    rows = [counts_by_pid[pid] for pid in order if pid in counts_by_pid]
    n_ok = sum(1 for r in rows if r["reddit_status"] == "ok")
    n_part = sum(1 for r in rows if r["reddit_status"] == "partial")
    n_null = sum(1 for r in rows if r["reddit_status"] == "null")
    n_cap = sum(1 for r in rows if r["reddit_capped"] == "true")
    print(f"\nWrote reddit_counts.csv ({len(rows)} rows; {n_ok} ok, "
          f"{n_part} partial, {n_null} null, {n_cap} capped)")


if __name__ == "__main__":
    main()
