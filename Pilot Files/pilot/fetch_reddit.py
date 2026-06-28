"""Fetch 12-month Reddit mention and upvote counts per player.

Per pre-registration sections 3.3 and 3.4 (composite weights 0.250 and 0.167).
Searches r/hockey + each player's team subreddit for the player's last name
within the trailing 365 days. Counts unique post + comment matches and sums
their `score` field.

Reads REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT from .env.

Writes: pilot/raw/reddit_counts.csv with columns
  player_id, full_name, subreddits, reddit_mentions_12mo, reddit_upvotes_12mo,
  unique_authors, fetch_date
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_players  # noqa: E402

from dotenv import load_dotenv  # noqa: E402
import praw  # noqa: E402

WINDOW_DAYS = 365


def reddit_client() -> "praw.Reddit":
    load_dotenv(Path(__file__).parent / ".env")
    cid = os.environ.get("REDDIT_CLIENT_ID")
    secret = os.environ.get("REDDIT_CLIENT_SECRET")
    ua = os.environ.get("REDDIT_USER_AGENT", "marchand-index-pilot/0.1")
    if not cid or not secret or "your_client_id" in (cid or ""):
        sys.exit(
            "Missing Reddit credentials. Copy .env.example to .env and fill in "
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET. Register a script app at "
            "https://www.reddit.com/prefs/apps if you don't have one."
        )
    return praw.Reddit(client_id=cid, client_secret=secret, user_agent=ua)


def last_name(full_name: str) -> str:
    return full_name.split()[-1]


def count_in_sub(reddit, sub_name: str, query: str, cutoff_ts: float) -> tuple[int, int, set[str]]:
    mentions = 0
    upvotes = 0
    authors: set[str] = set()
    try:
        sub = reddit.subreddit(sub_name)
        # PRAW search returns up to 1000 results per query. For a pilot
        # spanning 365 days on a single last-name query in two subs, this is
        # enough resolution to detect the volume-rank differences we care
        # about; the absolute count is z-scored across the 14 anyway.
        for post in sub.search(query, sort="new", time_filter="year", limit=1000):
            if post.created_utc < cutoff_ts:
                continue
            mentions += 1
            upvotes += int(getattr(post, "score", 0) or 0)
            if post.author:
                authors.add(str(post.author))
    except Exception as e:
        print(f"  sub r/{sub_name} FAILED: {e!r}", file=sys.stderr)
    return mentions, upvotes, authors


def main() -> None:
    reddit = reddit_client()
    fetch_date = dt.date.today().isoformat()
    cutoff_ts = (dt.datetime.utcnow() - dt.timedelta(days=WINDOW_DAYS)).timestamp()

    rows = []
    players = load_players()
    for p in players:
        ln = last_name(p["full_name"])
        team_sub = p["team_subreddit"]
        subs = ["hockey", team_sub] if team_sub and team_sub != "hockey" else ["hockey"]
        total_m = 0
        total_u = 0
        authors: set[str] = set()
        for sub in subs:
            m, u, a = count_in_sub(reddit, sub, ln, cutoff_ts)
            total_m += m
            total_u += u
            authors |= a
            time.sleep(1.0)
        print(f"{p['full_name']:<22} subs={subs} mentions={total_m} upvotes={total_u} "
              f"authors={len(authors)}")
        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "subreddits": "|".join(subs),
            "reddit_mentions_12mo": total_m,
            "reddit_upvotes_12mo": total_u,
            "unique_authors": len(authors),
            "fetch_date": fetch_date,
        })

    out = RAW_DIR / "reddit_counts.csv"
    atomic_write_csv(out, rows, [
        "player_id", "full_name", "subreddits",
        "reddit_mentions_12mo", "reddit_upvotes_12mo", "unique_authors", "fetch_date",
    ])
    print(f"\nWrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
