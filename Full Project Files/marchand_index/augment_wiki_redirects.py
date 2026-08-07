"""A36: redirect-title pageview summation for the player articles (en + intl).

Extends the A29-class team rule to the 774 player articles: enumerate each
canonical title's redirect titles (MediaWiki `prop=redirects`), fetch
in-window daily pageviews for canonical + every redirect, sum per calendar
day, zero-fill to the full 365-day A11/A14 window, and rewrite the wiki CSVs
with three audit columns (`n_redirect_titles`, `redirect_views_12mo`,
`redirect_share`).

Identity is LOCKED (A36 rule 1): en uses the stored `wikipedia_slug_chosen`
(`wiki_match != none`); intl uses the stored `wikidata_qid` — per-edition
titles derive mechanically from that QID's sitelinks (the CSV stores only
per-edition totals), restricted to the already-fetched edition set. No slug
or QID is re-chosen.

Run modes:
  python augment_wiki_redirects.py              full run, rewrites raw CSVs
  python augment_wiki_redirects.py --limit 5    dry-run, writes raw/_a36_dryrun_*.csv
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONTACT_UA, RAW_DIR, atomic_write_csv, load_csv, session  # noqa: E402
from fetch_wikipedia_intl import fetch_sitelinks, parse_sitelinks  # noqa: E402

PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
WINDOW_START = "20250418"
WINDOW_END = "20260417"
SLEEP_PV = 0.2
SLEEP_MW = 0.15
# Players are independent in both passes; 6 workers overlap the transient-404
# retry ladders (22s+ each) that dominate wall time when the pageviews edge is
# flaky. Aggregate request rate stays ~10 req/s — far under Wikimedia's
# 100 req/s pageviews guideline.
# requests-cache 1.3.2 SQLite backend is thread-safe (shared session OK).
FETCH_WORKERS = 6

# Global pacing for LIVE MediaWiki API calls. Per-worker sleeps do not bound
# the AGGREGATE rate: with cache-served responses consuming no time, 6 workers
# can burst live calls fast enough to draw 429s, and each 429 costs a
# 5/15/30/60s backoff ladder (observed 2026-08-03, enumerate_redirects storm).
# One shared token clock caps live MediaWiki traffic at ~1/SLEEP_MW req/s
# total while cached hits pass through untouched.
_MW_RATE_LOCK = threading.Lock()
_mw_next_ok = 0.0
# 2 req/s aggregate: 6.7 req/s still drew 429s from the anonymous action API
# (ru.wp, observed 2026-08-03 after the pacer first landed at SLEEP_MW).
MW_PACE_INTERVAL = 0.5


def _mw_pace() -> None:
    global _mw_next_ok
    with _MW_RATE_LOCK:
        now = time.monotonic()
        wait = _mw_next_ok - now
        _mw_next_ok = max(now, _mw_next_ok) + MW_PACE_INTERVAL
    if wait > 0:
        time.sleep(wait)


# --------------------------------------------------------------------------- #
# pure functions (unit-tested)                                                 #
# --------------------------------------------------------------------------- #
def parse_redirects(api_json: dict) -> dict[str, list[str]]:
    """MediaWiki prop=redirects response -> {canonical_title: [redirect titles]}.
    Excludes titles containing '(disambiguation)' case-insensitively."""
    out: dict[str, list[str]] = {}
    for pg in api_json.get("query", {}).get("pages", {}).values():
        title = pg.get("title", "")
        rds = [r["title"] for r in pg.get("redirects", [])
               if "(disambiguation)" not in r["title"].lower()]
        if title:
            out.setdefault(title, []).extend(rds)
    return out


def merge_daily_by_date(series: list[list[tuple[str, int]]]) -> list[tuple[str, int]]:
    """Sum multiple (timestamp 'YYYYMMDD00', views) series per calendar day.
    Returns date-sorted list. Handles missing days (API omits zero days)."""
    acc: dict[str, int] = {}
    for ser in series:
        for ts, v in ser:
            acc[ts] = acc.get(ts, 0) + v
    return sorted(acc.items())


def window_day_index() -> dict[str, int]:
    """'YYYYMMDD00' timestamp -> 0-based index inside the fixed 365-day window."""
    start = dt.date(2025, 4, 18)
    out = {}
    for i in range(365):
        d = start + dt.timedelta(days=i)
        out[d.strftime("%Y%m%d") + "00"] = i
    return out


_DAY_INDEX = window_day_index()


def zero_fill_365(merged: list[tuple[str, int]]) -> list[int]:
    """Merged per-day sums -> dense 365-entry vector (index 0 = 2025-04-18).
    Days the API omitted are true zero-view days; out-of-window stamps drop."""
    vec = [0] * 365
    for ts, v in merged:
        i = _DAY_INDEX.get(ts)
        if i is not None:
            vec[i] += v
    return vec


# --------------------------------------------------------------------------- #
# fetch-side helpers                                                           #
# --------------------------------------------------------------------------- #
def enumerate_redirects(s, api_url: str, titles: list[str]) -> dict[str, list[str]]:
    """Batched prop=redirects enumeration (≤50 titles/call, follows continue)."""
    out: dict[str, list[str]] = {t: [] for t in titles}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        params = {"action": "query", "prop": "redirects", "rdlimit": "max",
                  "titles": "|".join(batch), "format": "json",
                  "redirects": 0}
        while True:
            j = None
            for backoff in (0.0, 2.0, 5.0, 15.0, 30.0, 60.0):
                if backoff:
                    time.sleep(backoff)
                try:
                    # api.php replies carry `Vary: Cookie` and set cookies, so
                    # a cookie-bearing request can never match the cached
                    # variant — clearing the jar keeps requests cache-hittable
                    # (observed 2026-08-03: every api.php call re-fetched live
                    # on every run, ~2.7s/player, runs could never finish).
                    s.cookies.clear()
                    r = s.get(api_url, params=params,
                              headers={"User-Agent": CONTACT_UA}, timeout=30)
                    r.raise_for_status()
                    j = r.json()
                    break
                except Exception as e:
                    print(f"  redirects batch retry ({e!r})", file=sys.stderr)
            if j is None:
                raise RuntimeError(
                    "redirect enumeration failed after full retry ladder")
            for title, rds in parse_redirects(j).items():
                out.setdefault(title, []).extend(rds)
            if not getattr(r, "from_cache", False):
                _mw_pace()
            cont = j.get("continue")
            if not cont:
                break
            params.update(cont)
    return out


def fetch_daily_pairs(s, pv_domain: str, title: str,
                      start: str = WINDOW_START,
                      end: str = WINDOW_END) -> list[tuple[str, int]] | None:
    """(timestamp, views) pairs for one title; None once the whole retry
    ladder fails. The pageviews edge intermittently 404s titles that have
    full series (A29, observed live 2026-07-15 and again on the A36 dry-run
    2026-07-18: fr 'Nathan Gaucher' 404 with a stored 2167-view series), so
    404 is retried with backoff like 429/5xx before being accepted as null."""
    slug = quote(title.replace(" ", "_"), safe="")
    url = f"{PV}/{pv_domain}/all-access/all-agents/{slug}/daily/{start}/{end}"
    n404 = 0
    for backoff in (0.0, 2.0, 5.0, 15.0):
        if backoff:
            time.sleep(backoff)
        try:
            r = s.get(url, headers={"User-Agent": CONTACT_UA}, timeout=30)
            if r.status_code == 404:
                # Two 404s a couple of seconds apart is a confirmed absence;
                # only 429/5xx earn the full ladder. The 22s-per-absent-title
                # ladder made a full-pool run impossible to finish (hundreds
                # of rarely-viewed redirect titles genuinely have no data),
                # and canonicals are separately protected by the RETRY
                # second pass + UNRECOVERED stored-keep in _intl_one_player.
                n404 += 1
                if n404 >= 2:
                    break            # confirmed absent -> split fallback
                continue
            if r.status_code != 200:
                continue             # 429/5xx — retry the ladder
            if not getattr(r, "from_cache", False):
                # Politeness sleep lives HERE (per live request) rather than
                # at the call sites, so cache-served replays cost nothing and
                # a warm full-pool re-run can finish inside a task window.
                time.sleep(SLEEP_PV)
            return [(it["timestamp"], int(it["views"]))
                    for it in r.json().get("items", [])]
        except Exception:
            continue
    # Split-window fallback: the edge sometimes 404s a full-window request
    # while sub-windows 200 (observed live 2026-07-18, fr 'Nathan Gaucher':
    # full window 404, 20260301-20260417 200).
    #
    # FAIL-SAFE (A36 fix, 2026-07-21): the full-window request is
    # all-or-nothing — a 200 is ALWAYS the complete series; only this split
    # path can produce a *partial* result. Returning a one-half sum when the
    # other half is unrecoverable silently truncates the total, and the caller
    # would then overwrite a good stored full-year series with that partial via
    # the RESTATED branch (observed live: Brzustewicz full+h2 404 -> h1-only
    # 6508 vs stored 16153; Whitecloud full+h1 404 -> h2-only 61129 vs 85053).
    # So BOTH halves must succeed; otherwise return None and let the caller's
    # canon_total==0 UNRECOVERED guard keep the authoritative stored value.
    if (start, end) == (WINDOW_START, WINDOW_END):
        h1 = fetch_daily_pairs(s, pv_domain, title, "20250418", "20251017")
        h2 = fetch_daily_pairs(s, pv_domain, title, "20251018", "20260417")
        if h1 is None or h2 is None:
            return None
        return merge_daily_by_date([h1, h2])
    return None


def _sum_title_and_redirects(s, pv_domain: str, canonical: str,
                             redirects: list[str]):
    """Returns (merged_pairs, canonical_total, redirect_total)."""
    series = []
    canon_pairs = fetch_daily_pairs(s, pv_domain, canonical)
    canonical_total = 0
    if canon_pairs is not None:
        series.append(canon_pairs)
        canonical_total = sum(v for _, v in canon_pairs)
    redirect_total = 0
    for rt in redirects:
        pairs = fetch_daily_pairs(s, pv_domain, rt)
        if pairs is not None:
            series.append(pairs)
            redirect_total += sum(v for _, v in pairs)
    return merge_daily_by_date(series), canonical_total, redirect_total


# --------------------------------------------------------------------------- #
# en augmentation                                                              #
# --------------------------------------------------------------------------- #
EN_FIELDS = ["player_id", "full_name", "wikipedia_slug_tried",
             "wikipedia_slug_chosen", "wikidata_qid", "wiki_match",
             "wiki_12mo", "fetch_date", "window_start", "window_end",
             "n_redirect_titles", "redirect_views_12mo", "redirect_share"]
DAILY_FIELDS = ["player_id", "full_name", "n_days", "daily_views"]


def _en_one_player(s, r: dict, canonical: str, redirects: list[str]):
    """Per-player en fetch — logic identical to the pre-thread sequential
    version; same worker contract as _intl_one_player. updates is None on
    the UNRECOVERED path (row untouched, audit cols stay blank, as before);
    n_rd is counted for every submitted player, matching the sequential
    code's `n_rd_titles += len(redirects)` before the unrecovered check."""
    log_lines: list[str] = []
    merged, canon_total, rd_total = _sum_title_and_redirects(
        s, "en.wikipedia", canonical, redirects)
    stored = str(r.get("wiki_12mo", "")).strip()
    # A29-style second pass: a canonical that 404-flaked through the
    # ladder while a stored series exists gets one full re-attempt.
    if stored and canon_total == 0 and int(float(stored)) > 0:
        log_lines.append(f"  RETRY {r['full_name']}: canonical empty vs "
                         f"stored {stored} — second pass")
        merged, canon_total, rd_total = _sum_title_and_redirects(
            s, "en.wikipedia", canonical, redirects)
    if stored and canon_total == 0 and int(float(stored)) > 0:
        # Unrecovered fetch failure, NOT a restatement: writing the
        # redirect-only sum would destroy a good stored series. Keep the
        # stored total + daily vector untouched; audit cols stay blank.
        log_lines.append(f"  UNRECOVERED {r['full_name']}: canonical still "
                         "empty — stored series kept, row untouched")
        return None, None, 0, 1, len(redirects), None, log_lines
    n_restated = 0
    if stored and canon_total != int(float(stored)):
        n_restated = 1
        log_lines.append(f"  RESTATED {r['full_name']}: stored {stored} vs "
                         f"re-fetched canonical {canon_total}")
    total = canon_total + rd_total
    share = (rd_total / total) if total else 0.0
    updates = {
        "wiki_12mo": total,
        "n_redirect_titles": len(redirects),
        "redirect_views_12mo": rd_total,
        "redirect_share": f"{share:.6f}",
        "fetch_date": dt.date.today().isoformat(),
    }
    daily_entry = {
        "player_id": r["player_id"], "full_name": r["full_name"],
        "n_days": 365,
        "daily_views": "|".join(str(v) for v in zero_fill_365(merged)),
    }
    log_lines.append(f"  {r['full_name']:<24} rd_titles={len(redirects):<3} "
                     f"total={total} rd_share={share:.4f}")
    return (updates, daily_entry, n_restated, 0, len(redirects), share,
            log_lines)


def augment_en(s, limit: int | None = None) -> dict:
    rows = load_csv(RAW_DIR / "wiki_pageviews.csv")
    daily_by_pid = {r["player_id"]: r
                    for r in load_csv(RAW_DIR / "wiki_daily.csv")}
    if limit:
        rows = rows[:limit]
    fetchable = [r for r in rows
                 if r.get("wiki_match") != "none"
                 and r.get("wikipedia_slug_chosen")]
    titles = [r["wikipedia_slug_chosen"].replace("_", " ") for r in fetchable]
    print(f"en: enumerating redirects for {len(titles)} titles ...")
    rmap = enumerate_redirects(s, "https://en.wikipedia.org/w/api.php", titles)
    n_restated = 0
    n_unrecovered = 0
    n_rd_titles = 0
    shares = []
    for r in rows:
        r.setdefault("n_redirect_titles", "")
        r.setdefault("redirect_views_12mo", "")
        r.setdefault("redirect_share", "")
    # Same worker model as the intl pass: CSV row order is preserved (the
    # `rows` list is never reordered) and updates are applied by this thread.
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
        futs = {}
        for r in rows:
            if (r.get("wiki_match") == "none"
                    or not r.get("wikipedia_slug_chosen")):
                continue
            canonical = r["wikipedia_slug_chosen"].replace("_", " ")
            futs[ex.submit(_en_one_player, s, r, canonical,
                           rmap.get(canonical, []))] = r
        for fut in as_completed(futs):
            r = futs[fut]
            (updates, daily_entry, nr, nu, nrd,
             share, log_lines) = fut.result()
            for line in log_lines:
                print(line)
            n_restated += nr
            n_unrecovered += nu
            n_rd_titles += nrd
            if updates is None:
                continue
            r.update(updates)
            shares.append((share, r["full_name"]))
            daily_by_pid[r["player_id"]] = daily_entry
    return {"rows": rows,
            "daily_rows": [daily_by_pid[r["player_id"]] for r in rows
                           if r["player_id"] in daily_by_pid],
            "n_restated": n_restated, "n_unrecovered": n_unrecovered,
            "n_redirect_titles": n_rd_titles, "shares": shares}


# --------------------------------------------------------------------------- #
# intl augmentation                                                            #
# --------------------------------------------------------------------------- #
INTL_FIELDS = ["player_id", "full_name", "wikidata_qid", "editions_available",
               "editions_fetched", "wiki_intl_12mo", "per_edition_json",
               "window_start", "window_end", "fetch_date", "intl_match",
               "n_redirect_titles", "redirect_views_12mo", "redirect_share"]
INTL_DAILY_FIELDS = ["player_id", "edition", "n_days", "daily_views"]


# Wikidata is far stricter than the pageviews edge: under the 6-worker load
# that pageviews absorbed all day, wbgetentities started returning 429 for
# every call (observed live 2026-07-22: 689/771 sitelinks fetches rejected).
# So sitelinks calls are serialized behind one lock and 429/5xx retry with
# backoff; only the pageview/redirect fetches run 6-wide.
_WD_LOCK = threading.Lock()


def _sitelinks_serial(s, qid: str) -> dict:
    with _WD_LOCK:
        last: Exception | None = None
        for backoff in (0.0, 5.0, 15.0, 30.0, 60.0):
            if backoff:
                time.sleep(backoff)
            try:
                t0 = time.monotonic()
                j = fetch_sitelinks(s, qid)
                # fetch_sitelinks returns parsed JSON, not the response, so
                # cache-served calls are detected by elapsed time instead of
                # from_cache; sub-50ms means no network round-trip happened.
                if time.monotonic() - t0 >= 0.05:
                    time.sleep(SLEEP_MW)
                return j
            except Exception as e:
                last = e
        raise last


def _intl_one_player(s, r: dict, eds: list[str], qid: str):
    """Per-player intl fetch — logic identical to the pre-thread sequential
    version. Touches no shared state and prints nothing: returns
    (updates | None, daily_entries, n_restated, n_unrecovered, n_rd_player,
    share, log_lines) and the caller applies updates / emits log lines
    atomically per player, so the log format the monitor greps is unchanged.
    updates is None only on sitelinks failure (player skipped, as before)."""
    log_lines: list[str] = []
    try:
        sitelinks = parse_sitelinks(_sitelinks_serial(s, qid), qid)
    except Exception as e:
        log_lines.append(f"  sitelinks {qid}: {e!r}")
        return None, [], 0, 0, 0, 0.0, log_lines
    stored_per = {}
    try:
        stored_per = json.loads(r.get("per_edition_json") or "{}")
    except json.JSONDecodeError:
        pass
    per_edition = {}
    rd_total_all = 0
    total_all = 0
    n_rd_player = 0
    n_restated = 0
    n_unrecovered = 0
    daily_entries: list[dict] = []
    for ed in eds:
        title = sitelinks.get(ed, "")
        if not title:
            continue
        rmap = enumerate_redirects(
            s, f"https://{ed}.wikipedia.org/w/api.php", [title])
        redirects = rmap.get(title, [])
        n_rd_player += len(redirects)
        merged, canon_total, rd_total = _sum_title_and_redirects(
            s, f"{ed}.wikipedia", title, redirects)
        stored_ed = stored_per.get(ed)
        if stored_ed is not None and canon_total == 0 and int(stored_ed) > 0:
            log_lines.append(f"  RETRY {r['full_name']} [{ed}]: canonical "
                             f"empty vs stored {stored_ed} — second pass")
            merged, canon_total, rd_total = _sum_title_and_redirects(
                s, f"{ed}.wikipedia", title, redirects)
        if stored_ed is not None and canon_total == 0 and int(stored_ed) > 0:
            # Unrecovered fetch failure: keep the stored edition total +
            # daily vector; never replace a good series with a flake.
            n_unrecovered += 1
            log_lines.append(f"  UNRECOVERED {r['full_name']} [{ed}]: stored "
                             "series kept")
            per_edition[ed] = int(stored_ed)
            total_all += int(stored_ed)
            continue
        if stored_ed is not None and canon_total != int(stored_ed):
            n_restated += 1
            log_lines.append(f"  RESTATED {r['full_name']} [{ed}]: stored "
                             f"{stored_ed} vs re-fetched canonical "
                             f"{canon_total}")
        total = canon_total + rd_total
        per_edition[ed] = total
        rd_total_all += rd_total
        total_all += total
        daily_entries.append({
            "player_id": r["player_id"], "edition": ed, "n_days": 365,
            "daily_views": "|".join(str(v)
                                    for v in zero_fill_365(merged)),
        })
    share = (rd_total_all / total_all) if total_all else 0.0
    updates = {
        "per_edition_json": json.dumps(per_edition, ensure_ascii=True),
        "wiki_intl_12mo": total_all,
        "n_redirect_titles": n_rd_player,
        "redirect_views_12mo": rd_total_all,
        "redirect_share": f"{share:.6f}",
        "fetch_date": dt.date.today().isoformat(),
    }
    log_lines.append(f"  {r['full_name']:<24} intl rd_titles={n_rd_player:<3} "
                     f"total={total_all} rd_share={share:.4f}")
    return (updates, daily_entries, n_restated, n_unrecovered, n_rd_player,
            share, log_lines)


def augment_intl(s, limit: int | None = None) -> dict:
    rows = load_csv(RAW_DIR / "wiki_intl_pageviews.csv")
    if limit:
        rows = rows[:limit]
    keep_pids = {r["player_id"] for r in rows}
    # Existing daily entries are the baseline; processed (pid, edition) pairs
    # overwrite in place so unprocessed players never lose their vectors.
    daily_by_key = {(r["player_id"], r["edition"]): r
                    for r in load_csv(RAW_DIR / "wiki_intl_daily.csv")
                    if r["player_id"] in keep_pids}
    n_restated = 0
    n_unrecovered = 0
    n_rd_titles = 0
    shares = []
    eligible: list[tuple[dict, list[str], str]] = []
    for r in rows:
        r.setdefault("n_redirect_titles", "")
        r.setdefault("redirect_views_12mo", "")
        r.setdefault("redirect_share", "")
        # editions_available, not editions_fetched: an article renamed after
        # the window makes the fetcher 404 its NEW canonical title (zero
        # in-window days) and drop the edition, but the OLD title is now a
        # redirect of the canonical — so the redirect summation below is
        # exactly what recovers the edition's in-window views. Observed
        # 2026-08-03: 39 players lost an edition to post-window renames.
        eds = [e for e in str(r.get("editions_available", "")).split("|") if e]
        qid = str(r.get("wikidata_qid", "")).strip()
        if eds and qid:
            eligible.append((r, eds, qid))
    # CSV row order is preserved: workers only compute; the `rows` list is
    # never reordered and each row's updates are applied by this thread.
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
        futs = {ex.submit(_intl_one_player, s, r, eds, qid): r
                for r, eds, qid in eligible}
        for fut in as_completed(futs):
            r = futs[fut]
            (updates, daily_entries, nr, nu, nrd,
             share, log_lines) = fut.result()
            for line in log_lines:
                print(line)
            n_restated += nr
            n_unrecovered += nu
            if updates is None:
                continue
            r.update(updates)
            n_rd_titles += nrd
            shares.append((share, r["full_name"]))
            for d in daily_entries:
                daily_by_key[(d["player_id"], d["edition"])] = d
    return {"rows": rows, "daily_rows": list(daily_by_key.values()),
            "n_restated": n_restated, "n_unrecovered": n_unrecovered,
            "n_redirect_titles": n_rd_titles, "shares": shares}


def _summary(tag: str, res: dict) -> None:
    shares = sorted(res["shares"], reverse=True)
    mean_share = (sum(x for x, _ in shares) / len(shares)) if shares else 0.0
    print(f"\n{tag}: mean redirect_share = {mean_share:.4f}; "
          f"redirect titles fetched = {res['n_redirect_titles']}; "
          f"RESTATED canonicals = {res['n_restated']}; "
          f"UNRECOVERED (stored kept) = {res.get('n_unrecovered', 0)}")
    print(f"{tag}: top-10 by redirect_share:")
    for share, name in shares[:10]:
        print(f"  {share:.4f}  {name}")


def main() -> None:
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    # Phase flags: each pass alone fits a 10-minute task window (retry
    # ladders for genuinely-absent titles are re-paid every run because 404s
    # are uncacheable); the combined run does not. Default runs both.
    run_en = "--intl-only" not in sys.argv
    run_intl = "--en-only" not in sys.argv
    s = session(expire_hours=24)

    prefix = "_a36_dryrun_" if limit else ""
    if run_en:
        en = augment_en(s, limit)
        atomic_write_csv(RAW_DIR / f"{prefix}wiki_pageviews.csv",
                         en["rows"], EN_FIELDS)
        atomic_write_csv(RAW_DIR / f"{prefix}wiki_daily.csv",
                         en["daily_rows"], DAILY_FIELDS)
    if run_intl:
        intl = augment_intl(s, limit)
        atomic_write_csv(RAW_DIR / f"{prefix}wiki_intl_pageviews.csv",
                         intl["rows"], INTL_FIELDS)
        atomic_write_csv(RAW_DIR / f"{prefix}wiki_intl_daily.csv",
                         intl["daily_rows"], INTL_DAILY_FIELDS)
    if run_en:
        _summary("en", en)
    if run_intl:
        _summary("intl", intl)
    if limit:
        print(f"\nDRY-RUN: wrote raw/{prefix}*.csv (real files untouched)")


if __name__ == "__main__":
    main()
