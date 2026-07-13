"""Pull the Reddit submission corpus from the Arctic Shift archive (pre-reg A23).

Downloads EVERY submission in each of the 36 covered subreddits (A23 rule 2:
r/hockey, the 32 team subs, r/UtahHockey per the A22 rename rule, plus r/nhl and
r/fantasyhockey for the descriptive columns) whose created_utc falls inside the
fixed A11 window [2025-04-18 00:00 UTC, 2026-04-18 00:00 UTC). No search query
is used — matching happens locally in fetch_reddit.py (A23 rule 3: the archive's
query endpoint has verified recall misses on possessives and edited posts).

Source: https://arctic-shift.photon-reddit.com/api/posts/search, date-windowed
ascending pagination, limit=100, cursor on created_utc, dedup by id at the
window boundaries. No result cap exists (the A9-era 1,000-cap machinery is
removed by A23 rule 1).

Output: marchand_index/cache/reddit_corpus/<sub>.jsonl — one submission per
line, slim fields only (id, created_utc, title, selftext, score, subreddit,
num_comments, author, retrieved_2nd_on). The LOCAL corpus is the source of
record for the production run (A23 residual i); this script is resumable and
a finished sub is skipped entirely on re-run.

Write discipline: pages append to <sub>.jsonl.part (each line self-contained;
a torn final line from a kill is detected and dropped on resume); the file is
renamed to <sub>.jsonl only when the sub's window is fully enumerated, so the
final artifact appears atomically per vault convention.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import PILOT_DIR, ensure_dirs  # noqa: E402

import requests  # noqa: E402

UA = "marchand-index/0.3 (research; contact ana178@sfu.ca)"
API = "https://arctic-shift.photon-reddit.com/api/posts/search"
CORPUS_DIR = PILOT_DIR / "cache" / "reddit_corpus"

# Fixed attention window (pre-reg A11): identical to fetch_reddit.py.
WINDOW_END = dt.date(2026, 4, 17)   # last reg-season day, inclusive
WINDOW_DAYS = 365

PAGE = 100
SLEEP = 1.0                          # polite: ~1 req/s
RETRIES = 5                          # attempts per page before the sub aborts
BACKOFF = [5.0, 10.0, 20.0, 40.0]    # escalating sleep on 422/429/5xx (422s
                                     # observed transient on this API)
CHECKPOINT_PAGES = 10                # flush the .part file every N pages

# Team subreddit map — must stay identical to fetch_reddit.TEAM_SUB.
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

# A23 rule 2: full corpus scope. Order: big general subs first so the long
# tail of team subs finishes fast after them.
EXTRA_SUBS = ["hockey", "nhl", "fantasyhockey", "UtahHockey"]  # UtahHockey: A22 rename rule
ALL_SUBS = EXTRA_SUBS + sorted(TEAM_SUB.values())

KEEP_FIELDS = ["id", "created_utc", "title", "selftext", "score",
               "subreddit", "num_comments", "author"]


def window_cutoffs() -> tuple[int, int]:
    """[lower, upper) epoch bounds, identical to fetch_reddit.main()."""
    upper = dt.datetime(WINDOW_END.year, WINDOW_END.month, WINDOW_END.day,
                        tzinfo=dt.timezone.utc).timestamp() + 86400.0
    return int(upper - WINDOW_DAYS * 86400.0), int(upper)


def slim(post: dict) -> dict:
    row = {k: post.get(k) for k in KEEP_FIELDS}
    row["retrieved_2nd_on"] = (post.get("_meta") or {}).get("retrieved_2nd_on")
    return row


def get_page(sess: requests.Session, sub: str, after: int, before: int) -> list[dict] | None:
    """One ascending page, or None when all retries failed."""
    params = {"subreddit": sub, "after": after, "before": before,
              "limit": PAGE, "sort": "asc"}
    for attempt in range(RETRIES):
        try:
            r = sess.get(API, params=params, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 200:
                return r.json().get("data", [])
            if r.status_code in (422, 429) or 500 <= r.status_code < 600:
                wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
                print(f"  r/{sub}: HTTP {r.status_code}, backoff {wait}s "
                      f"(attempt {attempt + 1}/{RETRIES})", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  r/{sub}: HTTP {r.status_code} (permanent)", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  r/{sub}: {e!r} (attempt {attempt + 1}/{RETRIES})", file=sys.stderr)
            time.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
    return None


def load_part(part: Path) -> tuple[set[str], int, list[str]]:
    """Resume state from an in-progress .part file.

    Returns (seen ids, max created_utc, valid raw lines). A torn final line
    (killed mid-append) fails json.loads and is dropped.
    """
    seen: set[str] = set()
    max_ts = 0
    lines: list[str] = []
    if not part.exists():
        return seen, max_ts, lines
    for line in part.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # torn tail line from a killed run
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        max_ts = max(max_ts, int(row["created_utc"]))
        lines.append(line)
    return seen, max_ts, lines


def pull_sub(sess: requests.Session, sub: str, lower: int, upper: int) -> bool:
    """Enumerate one sub's window into CORPUS_DIR. True when complete."""
    final = CORPUS_DIR / f"{sub}.jsonl"
    part = CORPUS_DIR / f"{sub}.jsonl.part"
    if final.exists():
        print(f"r/{sub}: already complete, skipping")
        return True

    seen, max_ts, lines = load_part(part)
    if lines:
        # Rewrite the part file once, torn tail dropped, then append from there.
        part.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"r/{sub}: resuming with {len(seen)} posts, cursor {max_ts}")
    cursor = max(lower - 1, max_ts - 1)  # -1 + id-dedup covers boundary overlap

    buffer: list[str] = []
    pages = 0
    with part.open("a", encoding="utf-8") as fh:
        while True:
            posts = get_page(sess, sub, cursor, upper)
            time.sleep(SLEEP)
            if posts is None:
                fh.write("".join(buffer))
                fh.flush()
                print(f"r/{sub}: ABORTED after retries at cursor {cursor} "
                      f"({len(seen)} posts so far; resumable)", file=sys.stderr)
                return False
            new = 0
            page_max = cursor
            for p in posts:
                ts = int(p.get("created_utc") or 0)
                page_max = max(page_max, ts)
                pid = p.get("id")
                if not pid or pid in seen or not (lower <= ts < upper):
                    continue
                seen.add(pid)
                buffer.append(json.dumps(slim(p), ensure_ascii=False) + "\n")
                new += 1
            pages += 1
            if pages % CHECKPOINT_PAGES == 0 or len(posts) < PAGE:
                fh.write("".join(buffer))
                fh.flush()
                buffer = []
            if len(posts) < PAGE:
                break  # window exhausted
            # Ascending cursor; -1 + dedup instead of +1 so same-second posts
            # split across a page boundary are never skipped.
            cursor = max(page_max - 1, cursor + 1)
            if pages % 50 == 0:
                day = dt.datetime.fromtimestamp(page_max, dt.timezone.utc).date()
                print(f"r/{sub}: {len(seen)} posts, cursor at {day}")

    part.replace(final)  # atomic finalize per vault convention
    print(f"r/{sub}: COMPLETE, {len(seen)} posts")
    return True


def main() -> None:
    ensure_dirs()
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    lower, upper = window_cutoffs()
    lo = dt.datetime.fromtimestamp(lower, dt.timezone.utc).date()
    hi = dt.datetime.fromtimestamp(upper, dt.timezone.utc).date()
    print(f"Arctic Shift corpus pull: {len(ALL_SUBS)} subs, "
          f"window {lo} .. {hi} (end exclusive)")
    sess = requests.Session()
    done = 0
    failed: list[str] = []
    for sub in ALL_SUBS:
        ok = pull_sub(sess, sub, lower, upper)
        done += int(ok)
        if not ok:
            failed.append(sub)
    print(f"\n{done}/{len(ALL_SUBS)} subs complete."
          + (f" FAILED (resumable): {failed}" if failed else ""))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
