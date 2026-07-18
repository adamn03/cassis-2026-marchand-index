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
import time
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
            for backoff in (0.0, 2.0, 5.0, 15.0, 30.0):
                if backoff:
                    time.sleep(backoff)
                try:
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
            time.sleep(SLEEP_MW)
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
    for backoff in (0.0, 2.0, 5.0, 15.0):
        if backoff:
            time.sleep(backoff)
        try:
            r = s.get(url, headers={"User-Agent": CONTACT_UA}, timeout=30)
            if r.status_code != 200:
                continue             # 404/429/5xx — retry the ladder
            return [(it["timestamp"], int(it["views"]))
                    for it in r.json().get("items", [])]
        except Exception:
            continue
    # Split-window fallback: the edge sometimes 404s a full-window request
    # while sub-windows 200 (observed live 2026-07-18, fr 'Nathan Gaucher':
    # full window 404, 20260301-20260417 200). Two halves, merged; only a
    # both-halves failure is a real null.
    if (start, end) == (WINDOW_START, WINDOW_END):
        h1 = fetch_daily_pairs(s, pv_domain, title, "20250418", "20251017")
        h2 = fetch_daily_pairs(s, pv_domain, title, "20251018", "20260417")
        if h1 is None and h2 is None:
            return None
        return merge_daily_by_date([h1 or [], h2 or []])
    return None


def _sum_title_and_redirects(s, pv_domain: str, canonical: str,
                             redirects: list[str]):
    """Returns (merged_pairs, canonical_total, redirect_total)."""
    series = []
    canon_pairs = fetch_daily_pairs(s, pv_domain, canonical)
    time.sleep(SLEEP_PV)
    canonical_total = 0
    if canon_pairs is not None:
        series.append(canon_pairs)
        canonical_total = sum(v for _, v in canon_pairs)
    redirect_total = 0
    for rt in redirects:
        pairs = fetch_daily_pairs(s, pv_domain, rt)
        time.sleep(SLEEP_PV)
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
        if r.get("wiki_match") == "none" or not r.get("wikipedia_slug_chosen"):
            continue
        canonical = r["wikipedia_slug_chosen"].replace("_", " ")
        redirects = rmap.get(canonical, [])
        n_rd_titles += len(redirects)
        merged, canon_total, rd_total = _sum_title_and_redirects(
            s, "en.wikipedia", canonical, redirects)
        stored = str(r.get("wiki_12mo", "")).strip()
        # A29-style second pass: a canonical that 404-flaked through the
        # ladder while a stored series exists gets one full re-attempt.
        if stored and canon_total == 0 and int(float(stored)) > 0:
            print(f"  RETRY {r['full_name']}: canonical empty vs stored "
                  f"{stored} — second pass")
            merged, canon_total, rd_total = _sum_title_and_redirects(
                s, "en.wikipedia", canonical, redirects)
        if stored and canon_total == 0 and int(float(stored)) > 0:
            # Unrecovered fetch failure, NOT a restatement: writing the
            # redirect-only sum would destroy a good stored series. Keep the
            # stored total + daily vector untouched; audit cols stay blank.
            n_unrecovered += 1
            print(f"  UNRECOVERED {r['full_name']}: canonical still empty — "
                  "stored series kept, row untouched")
            continue
        if stored and canon_total != int(float(stored)):
            n_restated += 1
            print(f"  RESTATED {r['full_name']}: stored {stored} vs "
                  f"re-fetched canonical {canon_total}")
        total = canon_total + rd_total
        share = (rd_total / total) if total else 0.0
        shares.append((share, r["full_name"]))
        r["wiki_12mo"] = total
        r["n_redirect_titles"] = len(redirects)
        r["redirect_views_12mo"] = rd_total
        r["redirect_share"] = f"{share:.6f}"
        r["fetch_date"] = dt.date.today().isoformat()
        vec = zero_fill_365(merged)
        daily_by_pid[r["player_id"]] = {
            "player_id": r["player_id"], "full_name": r["full_name"],
            "n_days": 365, "daily_views": "|".join(str(v) for v in vec),
        }
        print(f"  {r['full_name']:<24} rd_titles={len(redirects):<3} "
              f"total={total} rd_share={share:.4f}")
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
    for r in rows:
        r.setdefault("n_redirect_titles", "")
        r.setdefault("redirect_views_12mo", "")
        r.setdefault("redirect_share", "")
        eds = [e for e in str(r.get("editions_fetched", "")).split("|") if e]
        qid = str(r.get("wikidata_qid", "")).strip()
        if not eds or not qid:
            continue
        try:
            sitelinks = parse_sitelinks(fetch_sitelinks(s, qid), qid)
        except Exception as e:
            print(f"  sitelinks {qid}: {e!r}", file=sys.stderr)
            continue
        time.sleep(SLEEP_MW)
        stored_per = {}
        try:
            stored_per = json.loads(r.get("per_edition_json") or "{}")
        except json.JSONDecodeError:
            pass
        per_edition = {}
        rd_total_all = 0
        total_all = 0
        n_rd_player = 0
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
                print(f"  RETRY {r['full_name']} [{ed}]: canonical empty vs "
                      f"stored {stored_ed} — second pass")
                merged, canon_total, rd_total = _sum_title_and_redirects(
                    s, f"{ed}.wikipedia", title, redirects)
            if stored_ed is not None and canon_total == 0 and int(stored_ed) > 0:
                # Unrecovered fetch failure: keep the stored edition total +
                # daily vector; never replace a good series with a flake.
                n_unrecovered += 1
                print(f"  UNRECOVERED {r['full_name']} [{ed}]: stored "
                      "series kept")
                per_edition[ed] = int(stored_ed)
                total_all += int(stored_ed)
                continue
            if stored_ed is not None and canon_total != int(stored_ed):
                n_restated += 1
                print(f"  RESTATED {r['full_name']} [{ed}]: stored "
                      f"{stored_ed} vs re-fetched canonical {canon_total}")
            total = canon_total + rd_total
            per_edition[ed] = total
            rd_total_all += rd_total
            total_all += total
            daily_by_key[(r["player_id"], ed)] = {
                "player_id": r["player_id"], "edition": ed, "n_days": 365,
                "daily_views": "|".join(str(v)
                                        for v in zero_fill_365(merged)),
            }
        share = (rd_total_all / total_all) if total_all else 0.0
        shares.append((share, r["full_name"]))
        n_rd_titles += n_rd_player
        r["per_edition_json"] = json.dumps(per_edition, ensure_ascii=True)
        r["wiki_intl_12mo"] = total_all
        r["n_redirect_titles"] = n_rd_player
        r["redirect_views_12mo"] = rd_total_all
        r["redirect_share"] = f"{share:.6f}"
        r["fetch_date"] = dt.date.today().isoformat()
        print(f"  {r['full_name']:<24} intl rd_titles={n_rd_player:<3} "
              f"total={total_all} rd_share={share:.4f}")
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
    s = session(expire_hours=24)

    en = augment_en(s, limit)
    intl = augment_intl(s, limit)

    prefix = "_a36_dryrun_" if limit else ""
    atomic_write_csv(RAW_DIR / f"{prefix}wiki_pageviews.csv",
                     en["rows"], EN_FIELDS)
    atomic_write_csv(RAW_DIR / f"{prefix}wiki_daily.csv",
                     en["daily_rows"], DAILY_FIELDS)
    atomic_write_csv(RAW_DIR / f"{prefix}wiki_intl_pageviews.csv",
                     intl["rows"], INTL_FIELDS)
    atomic_write_csv(RAW_DIR / f"{prefix}wiki_intl_daily.csv",
                     intl["daily_rows"], INTL_DAILY_FIELDS)
    _summary("en", en)
    _summary("intl", intl)
    if limit:
        print(f"\nDRY-RUN: wrote raw/{prefix}*.csv (real files untouched)")


if __name__ == "__main__":
    main()
