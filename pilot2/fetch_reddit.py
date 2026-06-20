"""Fetch 12-month Reddit mention + upvote counts per player (pre-reg §3.3-3.4,
window amended A11 2026-06-19).

Composite weights 0.250 (mentions) + 0.167 (upvotes). Searches r/hockey + the
team subreddit for the player's last name over a FIXED trailing-365-day window
ENDING the last day of the 2025-26 NHL regular season (2026-04-17 inclusive;
api-web.nhle.com standingsEnd), dedups by submission id, counts matches and
sums their `score`.

Window (pre-reg A11, 2026-06-19): was a trailing 365 days anchored to the
fetch moment (A2/§3.3-3.4). Anchoring to run-time baked the 2026 playoff run
into "attention" while OAQ matches REGULAR-SEASON production -> a made-the-
playoffs confound. The window now ends on the last reg-season day, is identical
for every player, and is independent of when the scrape runs. Reddit `t` is
therefore `all` (not `year`): from a June fetch `t:year` only reaches ~12 months
back and would clip the window's early edge. With sort=new we page newest-first,
SKIP posts newer than the window end, collect the window, and STOP once a post
falls below the window start.

Mechanism (pre-reg §14 A2, 2026-05-27; transport amended A9, 2026-05-28):
authenticated Reddit OAuth search (`oauth.reddit.com/r/<sub>/search` with an
app-only bearer token), after the unauthenticated `www.reddit.com/.../search.json`
endpoint hard-403'd this IP. Transport only: same source, subreddits, query,
window, dedup, and 1,000-result cap as A2. A sub that rate-limits or 404s
contributes 0 and sets reddit_status=partial; if every request fails the row is
NULL (reddit_status=null) and the §4 sentinel renormalizes.

Credentials: a free Reddit "script" app's client_id + client_secret, read from
env (REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET) or pilot2/.env (gitignored). App-only
`client_credentials` grant is used by default (id + secret only, no account
password); if REDDIT_USERNAME + REDDIT_PASSWORD are also present the more-permissive
`password` grant is used instead.

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
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_csv, load_players  # noqa: E402

import requests  # noqa: E402
from requests.auth import HTTPBasicAuth  # noqa: E402

UA = "marchand-index-pilot2/0.2 (research; contact ana178@sfu.ca)"
OAUTH_BASE = "https://oauth.reddit.com"           # authenticated host (A9)
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
# Fixed attention window (pre-reg A11, 2026-06-19): trailing WINDOW_DAYS ending
# the last day of the 2025-26 reg season (inclusive). api-web.nhle.com
# standingsEnd for season 20252026 = 2026-04-17. Decoupled from fetch time.
WINDOW_END = dt.date(2026, 4, 17)                 # last reg-season day, inclusive
WINDOW_DAYS = 365
MAX_RESULTS = 1000          # pre-registered search cap
PAGE = 100
SLEEP = 2.0                 # OAuth allows ~100 req/min; 2s spacing (~30/min) is polite and safe
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


_ENV_MAP = {
    "REDDIT_CLIENT_ID": "client_id", "REDDIT_CLIENT_SECRET": "client_secret",
    "REDDIT_USERNAME": "username", "REDDIT_PASSWORD": "password",
}


def load_creds() -> dict:
    """Reddit OAuth creds from env, falling back to pilot2/.env (gitignored).

    Requires client_id + client_secret. username + password are optional (enable
    the password grant); absent them the app-only client_credentials grant is used.
    """
    creds = {"client_id": "", "client_secret": "", "username": "", "password": ""}
    for env_key, field in _ENV_MAP.items():
        if os.environ.get(env_key):
            creds[field] = os.environ[env_key].strip()
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            field = _ENV_MAP.get(key.strip())
            if field and not creds[field]:
                creds[field] = val.strip().strip('"').strip("'")
    if not creds["client_id"] or not creds["client_secret"]:
        sys.exit("Reddit OAuth creds missing. Set REDDIT_CLIENT_ID and "
                 "REDDIT_CLIENT_SECRET in env or pilot2/.env (see module header).")
    return creds


# Mutable token cache shared across pages; refreshed on expiry or 401.
_TOKEN = {"value": None, "expires_at": 0.0}
_CREDS: dict = {}


def ensure_token(sess, force: bool = False) -> str:
    """Return a valid app-only/user bearer token, fetching/refreshing as needed."""
    if not force and _TOKEN["value"] and time.time() < _TOKEN["expires_at"] - 60:
        return _TOKEN["value"]
    auth = HTTPBasicAuth(_CREDS["client_id"], _CREDS["client_secret"])
    if _CREDS.get("username") and _CREDS.get("password"):
        data = {"grant_type": "password",
                "username": _CREDS["username"], "password": _CREDS["password"]}
    else:
        data = {"grant_type": "client_credentials"}
    r = sess.post(TOKEN_URL, auth=auth, data=data,
                  headers={"User-Agent": UA}, timeout=25)
    r.raise_for_status()
    j = r.json()
    if "access_token" not in j:
        sys.exit(f"Reddit token request returned no access_token: {j}")
    _TOKEN["value"] = j["access_token"]
    _TOKEN["expires_at"] = time.time() + int(j.get("expires_in", 3600))
    return _TOKEN["value"]


def get_page(sess, sub: str, query: str, after: str | None) -> tuple[list, str | None, bool]:
    """One search page. Returns (children, next_after, ok)."""
    params = {"q": query, "restrict_sr": 1, "sort": "new",
              "t": "all", "limit": PAGE, "raw_json": 1}
    if after:
        params["after"] = after
    for attempt in range(RETRIES):
        try:
            tok = ensure_token(sess)
            r = sess.get(f"{OAUTH_BASE}/r/{sub}/search",
                         params=params,
                         headers={"User-Agent": UA, "Authorization": f"bearer {tok}"},
                         timeout=25)
            # 401 => token expired/revoked: refresh once and retry this attempt.
            if r.status_code == 401:
                print(f"  r/{sub} '{query}': HTTP 401, refreshing token "
                      f"(attempt {attempt + 1}/{RETRIES})", file=sys.stderr)
                ensure_token(sess, force=True)
                time.sleep(1.0)
                continue
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


def search_sub(sess, sub: str, query: str, lower_cutoff: float, upper_cutoff: float):
    """Paginate one subreddit over the window [lower_cutoff, upper_cutoff).

    Results are newest-first (sort=new, t=all). Posts NEWER than the window end
    are skipped (e.g. the 2026 playoff run); once a post OLDER than the window
    start appears, paging stops since everything beyond is older still.
    Returns (id->score dict, authors set, capped, ok).
    """
    scores: dict[str, int] = {}
    authors: set[str] = set()
    after = None
    capped = False
    any_ok = False
    reached_floor = False
    while len(scores) < MAX_RESULTS:
        children, after, ok = get_page(sess, sub, query, after)
        any_ok = any_ok or ok
        time.sleep(SLEEP)
        if not ok:
            break
        for c in children:
            d = c.get("data", {})
            ts = d.get("created_utc", 0) or 0
            if ts >= upper_cutoff:
                continue              # newer than window end -> not yet in window
            if ts < lower_cutoff:
                reached_floor = True  # older than window start; stop after this page
                continue
            sid = d.get("name") or d.get("id")
            if not sid:
                continue
            scores[sid] = int(d.get("score", 0) or 0)
            if d.get("author"):
                authors.add(d["author"])
        if reached_floor:
            break
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
    global _CREDS
    fetch_date = dt.date.today().isoformat()
    # Fixed window: end = last reg-season day inclusive -> exclusive bound is the
    # next UTC midnight; start = WINDOW_DAYS earlier. Identical for every player,
    # independent of when the scrape runs (pre-reg A11).
    upper_cutoff = dt.datetime(WINDOW_END.year, WINDOW_END.month, WINDOW_END.day,
                               tzinfo=dt.timezone.utc).timestamp() + 86400.0
    lower_cutoff = upper_cutoff - WINDOW_DAYS * 86400.0
    sess = requests.Session()

    _CREDS = load_creds()
    grant = "password" if (_CREDS.get("username") and _CREDS.get("password")) else "client_credentials"
    ensure_token(sess)  # validate creds up-front; exits clearly if they are wrong
    print(f"Reddit OAuth token acquired ({grant} grant).")
    win_lo = dt.datetime.fromtimestamp(lower_cutoff, dt.timezone.utc).date()
    win_hi = dt.datetime.fromtimestamp(upper_cutoff, dt.timezone.utc).date()
    print(f"Window: {win_lo.isoformat()} .. {win_hi.isoformat()} (end exclusive), "
          f"{WINDOW_DAYS}d, ending reg-season {WINDOW_END.isoformat()}")

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
            sc, au, cap, ok = search_sub(sess, sub, ln, lower_cutoff, upper_cutoff)
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
