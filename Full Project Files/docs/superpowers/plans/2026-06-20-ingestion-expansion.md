# Attention-Ingestion Expansion (A12) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Broaden The Marchand Index attention composite with a multi-language Wikipedia flow component (`wiki_intl_12mo`), re-lock the composite weights (drop Instagram, add wiki_intl), and add two honesty diagnostics, all under Amendment A12.

**Architecture:** A new network fetcher (`fetch_wikipedia_intl.py`) reuses each player's already-resolved `wikidata_qid` from `raw/wiki_pageviews.csv`, calls Wikidata sitelinks once per QID, fetches per-edition pageviews over the FIXED A11 window for the locked language whitelist, and writes two raw CSVs. `compute_oaq.py` gains `wiki_intl_12mo` as a sentinel-renormalized composite component with a re-locked weight vector. Two standalone diagnostics read the computed component matrix to quantify source breadth and Reddit-weight robustness without ever feeding back into the locked weights.

**Tech Stack:** Python 3, `requests_cache`, `numpy`, `pandas`, `matplotlib`, `pytest`. Local Windows + SQLite cache. No new dependencies.

**Pending migration note (NOT part of this plan):** the directory rename `pilot2/` -> `Marchand Index/` is a SEPARATE pending migration. This plan builds entirely into the existing `pilot2/` tree where `_common.py` and `compute_oaq.py` live. Do not rename anything here.

**Co-modification warning (shared-file sequencing):** A sibling skill-vector amendment (**A13**) also edits `pilot2/compute_oaq.py` and `pilot2/preregistration.md`. Per amendment order, **A12 commits its shared-file edits BEFORE A13 starts**. Keep A12 edits localized to (a) the composite-weight region (`WEIGHTS` dict + `engagement_from_components`/bootstrap component dicts + `OUT_COLS`) and (b) the `load_inputs` merge block, to minimize collision with A13.

## Global Constraints

- $0 budget, free public APIs only.
- Local Windows + Python + SQLite.
- Atomic `.tmp`->rename writes via `_common.atomic_write_csv`.
- `requests_cache` on, polite sleeps.
- A11 FIXED window [2025-04-18 00:00 UTC, 2026-04-18 00:00 UTC) hardcoded for wiki_intl.
- 774-skater locked pool.
- Anti-tuning: weights locked before any fetch, prior vector retained verbatim, no weight tuned to a result.
- UTF-8 forced (Windows console is cp1252 - no non-ASCII in ad-hoc prints).

---

## File Structure

| File | Create/Modify | Responsibility |
|---|---|---|
| `pilot2/fetch_wikipedia_intl.py` | Create | Fetch multi-language Wikipedia pageviews; write `raw/wiki_intl_pageviews.csv` + `raw/wiki_intl_daily.csv`. |
| `pilot2/raw/wiki_intl_pageviews.csv` | Output | Per-player intl summary (spec §3 schema). |
| `pilot2/raw/wiki_intl_daily.csv` | Output | Per-(player,edition) daily vectors for the §10 bootstrap. |
| `pilot2/compute_oaq.py` | Modify | Add `wiki_intl_12mo` component; re-lock `WEIGHTS`; merge intl in `load_inputs`; extend bootstrap component dict + `OUT_COLS`; drop Instagram from composite. |
| `pilot2/diagnostics/__init__.py` | Create | Marks `diagnostics` a package (empty). |
| `pilot2/diagnostics/source_correlation.py` | Create | Pairwise Spearman across z-scored components -> `diagnostics/source_correlation.csv` + `figure_source_correlation.png`. |
| `pilot2/diagnostics/reddit_robustness.py` | Create | Reddit-weight ladder OAQ re-run -> `diagnostics/reddit_robustness.csv` + `figure_reddit_robustness.png`. |
| `pilot2/preregistration.md` | Modify | Append verbatim A12 amendment text (spec §7). |
| `pilot2/tests/__init__.py` | Create | Marks `tests` a package (empty). NOTE: `pilot2/tests/` does not exist yet; this plan creates it. |
| `pilot2/tests/test_fetch_wikipedia_intl.py` | Create | Unit tests for fetcher pure logic (mocked session). |
| `pilot2/tests/test_compute_oaq_weights.py` | Create | Unit tests for re-locked weights + wiki_intl sentinel renorm. |
| `pilot2/tests/test_diagnostics.py` | Create | Unit tests for diagnostic pure helpers. |

**Test location convention:** the project has NO existing test directory or `pytest.ini`/`pyproject.toml`. This plan creates `pilot2/tests/` with an `__init__.py`. Tests are run with the repo root as CWD; `sys.path.insert(0, ...)` inside test files imports the modules directly (mirroring how `compute_oaq.py` and `fetch_wikipedia.py` do `sys.path.insert(0, str(Path(__file__).parent))`).

---

## Task 1: Scaffold test package + intl fetcher module skeleton

**Files:**
- Create: `pilot2/tests/__init__.py` (empty)
- Create: `pilot2/fetch_wikipedia_intl.py` (constants + pure helpers only this task)
- Test: `pilot2/tests/test_fetch_wikipedia_intl.py`

**Interfaces:**
- Consumes: nothing (constants only).
- Produces:
  - `WHITELIST: tuple[str, ...]` == `("sv", "fi", "cs", "ru", "de", "sk", "fr")`
  - `WINDOW_START: str` == `"20250418"`, `WINDOW_END: str` == `"20260417"` (A11 fixed, hardcoded)
  - `window_strings() -> tuple[str, str, str]` returns `(WINDOW_START, WINDOW_END, fetch_date_iso)` where `fetch_date_iso` is `datetime.date.today().isoformat()` (only the fetch_date is dynamic; the window is fixed).

Steps:

- [ ] (1) Write the failing test. Create `pilot2/tests/__init__.py` (empty), then `pilot2/tests/test_fetch_wikipedia_intl.py`:

```python
"""Unit tests for fetch_wikipedia_intl pure logic (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pilot2/
import fetch_wikipedia_intl as fwi  # noqa: E402


def test_whitelist_is_locked_seven_editions():
    assert fwi.WHITELIST == ("sv", "fi", "cs", "ru", "de", "sk", "fr")


def test_window_is_a11_fixed_hardcoded():
    assert fwi.WINDOW_START == "20250418"
    assert fwi.WINDOW_END == "20260417"


def test_window_strings_returns_fixed_window_and_today_fetch_date():
    import datetime as dt
    start, end, fetch_date = fwi.window_strings()
    assert (start, end) == ("20250418", "20260417")
    assert fetch_date == dt.date.today().isoformat()
```

- [ ] (2) Run it (expected FAIL — module does not exist):

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py::test_whitelist_is_locked_seven_editions -v
```

Expected: `ModuleNotFoundError: No module named 'fetch_wikipedia_intl'` (collection error / FAIL).

- [ ] (3) Minimal implementation. Create `pilot2/fetch_wikipedia_intl.py`:

```python
"""Fetch multi-language Wikipedia pageviews for the 774-skater pool (A12).

Adds a SEPARATE flow component `wiki_intl_12mo` = sum of per-article pageviews
over the locked non-English hockey-market editions {sv,fi,cs,ru,de,sk,fr},
over the FIXED A11 window [2025-04-18, 2026-04-17] (hardcoded — diverges from
the en fetcher's run-time window). Each player's wikidata_qid is REUSED from
raw/wiki_pageviews.csv (A1 occupation-checked resolver); no re-resolution.

Writes:
  pilot2/raw/wiki_intl_pageviews.csv
    player_id, full_name, wikidata_qid, editions_available, editions_fetched,
    wiki_intl_12mo, per_edition_json, window_start, window_end, fetch_date,
    intl_match
  pilot2/raw/wiki_intl_daily.csv
    player_id, edition, n_days, daily_views
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

PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
WD = "https://www.wikidata.org/w/api.php"

# A11 FIXED window, hardcoded (NOT run-time). [2025-04-18 00:00 UTC, 2026-04-18).
WINDOW_START = "20250418"
WINDOW_END = "20260417"

# Locked hockey-market edition whitelist (A12; locked before fetch).
WHITELIST = ("sv", "fi", "cs", "ru", "de", "sk", "fr")


def window_strings() -> tuple[str, str, str]:
    """Return (fixed_start, fixed_end, today_iso). Only fetch_date is dynamic."""
    return WINDOW_START, WINDOW_END, dt.date.today().isoformat()
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py -v
```

Expected: 3 passed.

- [ ] (5) Commit:

```
git add pilot2/tests/__init__.py pilot2/tests/test_fetch_wikipedia_intl.py pilot2/fetch_wikipedia_intl.py
git commit -m "pilot2: A12 scaffold intl-wiki fetcher (constants + fixed A11 window) + test pkg"
```

---

## Task 2: Sitelink whitelist filtering

**Files:**
- Modify: `pilot2/fetch_wikipedia_intl.py`
- Test: `pilot2/tests/test_fetch_wikipedia_intl.py`

**Interfaces:**
- Consumes: a Wikidata `wbgetentities&props=sitelinks` JSON dict.
- Produces:
  - `parse_sitelinks(entity_json: dict, qid: str) -> dict[str, str]` — returns `{edition_code: article_title}` for ONLY the whitelisted non-English editions present. Keys are bare codes (`sv`, not `svwiki`); titles are verbatim from the sitelink `title` field. Returns `{}` if QID missing or no whitelisted sitelink.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_fetch_wikipedia_intl.py`:

```python
def _entity(qid, sitelinks):
    return {"entities": {qid: {"sitelinks": sitelinks}}}


def test_parse_sitelinks_keeps_only_whitelisted_editions():
    js = _entity("Q1", {
        "enwiki": {"site": "enwiki", "title": "David Pastrnak"},
        "cswiki": {"site": "cswiki", "title": "David Pastrnak"},
        "svwiki": {"site": "svwiki", "title": "David Pastrnak"},
        "plwiki": {"site": "plwiki", "title": "David Pastrnak"},  # not whitelisted
    })
    out = fwi.parse_sitelinks(js, "Q1")
    assert out == {"cs": "David Pastrnak", "sv": "David Pastrnak"}
    assert "en" not in out and "pl" not in out


def test_parse_sitelinks_uses_verbatim_nonlatin_title():
    js = _entity("Q2", {"ruwiki": {"site": "ruwiki", "title": "Кай Капризов"}})
    assert fwi.parse_sitelinks(js, "Q2") == {"ru": "Кай Капризов"}


def test_parse_sitelinks_empty_when_qid_missing_or_anglophone_only():
    assert fwi.parse_sitelinks({"entities": {}}, "Q9") == {}
    js = _entity("Q3", {"enwiki": {"site": "enwiki", "title": "Connor Bedard"}})
    assert fwi.parse_sitelinks(js, "Q3") == {}
```

- [ ] (2) Run it (expected FAIL — `parse_sitelinks` undefined):

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py::test_parse_sitelinks_keeps_only_whitelisted_editions -v
```

Expected: `AttributeError: module 'fetch_wikipedia_intl' has no attribute 'parse_sitelinks'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_wikipedia_intl.py`:

```python
def parse_sitelinks(entity_json: dict, qid: str) -> dict[str, str]:
    """Map whitelisted edition code -> verbatim article title for one QID.

    entity_json is a wbgetentities response. Returns {} if the QID is absent
    or has no whitelisted sitelink. Sitelink keys look like 'svwiki'; we strip
    the 'wiki' suffix to the bare code and keep only WHITELIST codes.
    """
    ent = entity_json.get("entities", {}).get(qid, {})
    sitelinks = ent.get("sitelinks", {})
    out: dict[str, str] = {}
    for site, info in sitelinks.items():
        if not site.endswith("wiki"):
            continue
        code = site[:-len("wiki")]
        if code in WHITELIST:
            out[code] = info.get("title", "")
    return {k: v for k, v in out.items() if v}
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py -v
```

Expected: 6 passed.

- [ ] (5) Commit:

```
git add pilot2/fetch_wikipedia_intl.py pilot2/tests/test_fetch_wikipedia_intl.py
git commit -m "pilot2: A12 sitelink whitelist filtering (verbatim titles, bare codes)"
```

---

## Task 3: Per-edition fetch URL building + daily/total parsing

**Files:**
- Modify: `pilot2/fetch_wikipedia_intl.py`
- Test: `pilot2/tests/test_fetch_wikipedia_intl.py`

**Interfaces:**
- Consumes: an edition code + verbatim title; a mocked `session()`-like object exposing `.get(url, headers=..., timeout=...) -> response` where `response.status_code` and `response.json()` exist.
- Produces:
  - `edition_pv_url(edition: str, title: str, start: str, end: str) -> str` — builds `{PV}/{edition}.wikipedia/all-access/all-agents/{quoted_title}/daily/{start}/{end}` with `quote(title.replace(" ", "_"), safe="")`.
  - `fetch_edition_views(s, edition: str, title: str, start: str, end: str) -> tuple[int, list[int]] | None` — `None` on 404 (skip that edition); otherwise `(total, daily_list)` summing `int(it["views"])`.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_fetch_wikipedia_intl.py`:

```python
class _Resp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 404:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Session:
    def __init__(self, resp):
        self._resp = resp
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        return self._resp


def test_edition_pv_url_encodes_title_and_uses_edition_domain():
    url = fwi.edition_pv_url("cs", "David Pastrnak", "20250418", "20260417")
    assert url == (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        "cs.wikipedia/all-access/all-agents/David_Pastrnak/daily/"
        "20250418/20260417"
    )


def test_edition_pv_url_percent_encodes_nonlatin():
    url = fwi.edition_pv_url("ru", "Кай", "20250418", "20260417")
    assert "ru.wikipedia/all-access/all-agents/%" in url  # cyrillic percent-encoded


def test_fetch_edition_views_sums_daily():
    payload = {"items": [{"views": 3}, {"views": 5}, {"views": 2}]}
    s = _Session(_Resp(200, payload))
    total, daily = fwi.fetch_edition_views(s, "sv", "X", "20250418", "20260417")
    assert total == 10
    assert daily == [3, 5, 2]


def test_fetch_edition_views_returns_none_on_404():
    s = _Session(_Resp(404))
    assert fwi.fetch_edition_views(s, "fi", "X", "20250418", "20260417") is None
```

- [ ] (2) Run it (expected FAIL — functions undefined):

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py::test_fetch_edition_views_sums_daily -v
```

Expected: `AttributeError: module 'fetch_wikipedia_intl' has no attribute 'fetch_edition_views'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_wikipedia_intl.py`:

```python
def edition_pv_url(edition: str, title: str, start: str, end: str) -> str:
    """Wikimedia REST per-article URL for a given language edition + window."""
    slug = quote(title.replace(" ", "_"), safe="")
    return f"{PV}/{edition}.wikipedia/all-access/all-agents/{slug}/daily/{start}/{end}"


def fetch_edition_views(s, edition: str, title: str, start: str,
                        end: str) -> tuple[int, list[int]] | None:
    """Return (12-mo total, daily vector) for one edition; None on 404 (skip).

    The daily vector is kept so the §10 bootstrap can resample intl signal.
    """
    url = edition_pv_url(edition, title, start, end)
    r = s.get(url, headers={"User-Agent": CONTACT_UA}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    daily = [int(it["views"]) for it in r.json().get("items", [])]
    return sum(daily), daily
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py -v
```

Expected: 10 passed.

- [ ] (5) Commit:

```
git add pilot2/fetch_wikipedia_intl.py pilot2/tests/test_fetch_wikipedia_intl.py
git commit -m "pilot2: A12 per-edition pageview URL build + daily/total parse (404-skip)"
```

---

## Task 4: Per-player aggregation (sum editions, intl_match, NULL handling)

**Files:**
- Modify: `pilot2/fetch_wikipedia_intl.py`
- Test: `pilot2/tests/test_fetch_wikipedia_intl.py`

**Interfaces:**
- Consumes: an edition->title dict and a callable that returns `(total, daily)|None` per edition (so the test injects results without a session).
- Produces:
  - `aggregate_player(sitelinks: dict[str, str], fetch_fn) -> dict` — `fetch_fn(edition, title) -> tuple[int, list[int]] | None`. Returns a dict with keys: `editions_available` (sorted pipe-list of whitelisted codes present), `editions_fetched` (sorted pipe-list of codes that returned non-None), `wiki_intl_12mo` (int sum over fetched editions, or `None` if no edition fetched), `per_edition` (`dict[str,int]` of edition->total), `daily_by_edition` (`dict[str, list[int]]`), `intl_match` (`"ok"` if any edition fetched else `"none"`).

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_fetch_wikipedia_intl.py`:

```python
def test_aggregate_player_sums_fetched_editions():
    sitelinks = {"cs": "P", "sv": "P", "ru": "P"}
    results = {"cs": (100, [50, 50]), "sv": (40, [40]), "ru": None}  # ru 404

    def fetch_fn(edition, title):
        return results[edition]

    agg = fwi.aggregate_player(sitelinks, fetch_fn)
    assert agg["wiki_intl_12mo"] == 140
    assert agg["editions_available"] == "cs|ru|sv"
    assert agg["editions_fetched"] == "cs|sv"
    assert agg["per_edition"] == {"cs": 100, "sv": 40}
    assert agg["daily_by_edition"] == {"cs": [50, 50], "sv": [40]}
    assert agg["intl_match"] == "ok"


def test_aggregate_player_none_when_no_sitelinks():
    agg = fwi.aggregate_player({}, lambda e, t: (1, [1]))
    assert agg["wiki_intl_12mo"] is None
    assert agg["editions_available"] == ""
    assert agg["editions_fetched"] == ""
    assert agg["intl_match"] == "none"


def test_aggregate_player_none_when_all_editions_404():
    agg = fwi.aggregate_player({"de": "P", "fr": "P"}, lambda e, t: None)
    assert agg["wiki_intl_12mo"] is None
    assert agg["editions_available"] == "de|fr"
    assert agg["editions_fetched"] == ""
    assert agg["intl_match"] == "none"
```

- [ ] (2) Run it (expected FAIL — `aggregate_player` undefined):

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py::test_aggregate_player_sums_fetched_editions -v
```

Expected: `AttributeError: module 'fetch_wikipedia_intl' has no attribute 'aggregate_player'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_wikipedia_intl.py`:

```python
def aggregate_player(sitelinks: dict[str, str], fetch_fn) -> dict:
    """Sum pageviews over whitelisted editions for one player.

    fetch_fn(edition, title) -> (total, daily) | None (None = edition skipped).
    wiki_intl_12mo is NULL (None) when no edition was successfully fetched, so
    the §4/§5 sentinel renorm drops the component for that player.
    """
    available = sorted(sitelinks.keys())
    fetched: list[str] = []
    per_edition: dict[str, int] = {}
    daily_by_edition: dict[str, list[int]] = {}
    total = 0
    for ed in available:
        res = fetch_fn(ed, sitelinks[ed])
        if res is None:
            continue
        ed_total, daily = res
        fetched.append(ed)
        per_edition[ed] = ed_total
        daily_by_edition[ed] = daily
        total += ed_total
    has = len(fetched) > 0
    return {
        "editions_available": "|".join(available),
        "editions_fetched": "|".join(fetched),
        "wiki_intl_12mo": total if has else None,
        "per_edition": per_edition,
        "daily_by_edition": daily_by_edition,
        "intl_match": "ok" if has else "none",
    }
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py -v
```

Expected: 13 passed.

- [ ] (5) Commit:

```
git add pilot2/fetch_wikipedia_intl.py pilot2/tests/test_fetch_wikipedia_intl.py
git commit -m "pilot2: A12 per-player intl aggregation (sum editions, intl_match, NULL rule)"
```

---

## Task 5: Row builders for the two output CSVs

**Files:**
- Modify: `pilot2/fetch_wikipedia_intl.py`
- Test: `pilot2/tests/test_fetch_wikipedia_intl.py`

**Interfaces:**
- Consumes: a player dict (`player_id`, `full_name`, `wikidata_qid`), an `aggregate_player` result dict, the window/fetch_date strings.
- Produces:
  - `PAGEVIEWS_FIELDS: list[str]` and `DAILY_FIELDS: list[str]` matching spec §3 schema exactly.
  - `build_summary_row(player: dict, qid: str, agg: dict, start: str, end: str, fetch_date: str) -> dict` — one `wiki_intl_pageviews.csv` row; `wiki_intl_12mo` written as `""` when None; `per_edition_json` is `json.dumps(agg["per_edition"], ensure_ascii=True)` (ASCII-safe for the cp1252 console / CSV).
  - `build_daily_rows(player: dict, agg: dict) -> list[dict]` — one `wiki_intl_daily.csv` row per fetched edition.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_fetch_wikipedia_intl.py`:

```python
import json as _json


def test_summary_fields_match_spec_schema():
    assert fwi.PAGEVIEWS_FIELDS == [
        "player_id", "full_name", "wikidata_qid", "editions_available",
        "editions_fetched", "wiki_intl_12mo", "per_edition_json",
        "window_start", "window_end", "fetch_date", "intl_match",
    ]
    assert fwi.DAILY_FIELDS == ["player_id", "edition", "n_days", "daily_views"]


def test_build_summary_row_ok():
    player = {"player_id": "7", "full_name": "David Pastrnak"}
    agg = {
        "editions_available": "cs|sv", "editions_fetched": "cs|sv",
        "wiki_intl_12mo": 140, "per_edition": {"cs": 100, "sv": 40},
        "daily_by_edition": {}, "intl_match": "ok",
    }
    row = fwi.build_summary_row(player, "Q2924461", agg,
                               "20250418", "20260417", "2026-06-20")
    assert row["player_id"] == "7"
    assert row["wikidata_qid"] == "Q2924461"
    assert row["wiki_intl_12mo"] == 140
    assert row["intl_match"] == "ok"
    assert row["window_start"] == "20250418" and row["window_end"] == "20260417"
    assert _json.loads(row["per_edition_json"]) == {"cs": 100, "sv": 40}


def test_build_summary_row_null_writes_empty_string():
    player = {"player_id": "9", "full_name": "Connor Bedard"}
    agg = {"editions_available": "", "editions_fetched": "",
           "wiki_intl_12mo": None, "per_edition": {},
           "daily_by_edition": {}, "intl_match": "none"}
    row = fwi.build_summary_row(player, "Q123", agg,
                               "20250418", "20260417", "2026-06-20")
    assert row["wiki_intl_12mo"] == ""
    assert row["intl_match"] == "none"


def test_build_daily_rows_one_per_fetched_edition():
    player = {"player_id": "7"}
    agg = {"daily_by_edition": {"cs": [50, 50], "sv": [40]}}
    rows = fwi.build_daily_rows(player, agg)
    rows = sorted(rows, key=lambda r: r["edition"])
    assert rows == [
        {"player_id": "7", "edition": "cs", "n_days": 2, "daily_views": "50|50"},
        {"player_id": "7", "edition": "sv", "n_days": 1, "daily_views": "40"},
    ]
```

- [ ] (2) Run it (expected FAIL — fields/builders undefined):

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py::test_summary_fields_match_spec_schema -v
```

Expected: `AttributeError: module 'fetch_wikipedia_intl' has no attribute 'PAGEVIEWS_FIELDS'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_wikipedia_intl.py`:

```python
PAGEVIEWS_FIELDS = [
    "player_id", "full_name", "wikidata_qid", "editions_available",
    "editions_fetched", "wiki_intl_12mo", "per_edition_json",
    "window_start", "window_end", "fetch_date", "intl_match",
]
DAILY_FIELDS = ["player_id", "edition", "n_days", "daily_views"]


def build_summary_row(player: dict, qid: str, agg: dict, start: str, end: str,
                      fetch_date: str) -> dict:
    val = agg["wiki_intl_12mo"]
    return {
        "player_id": player["player_id"],
        "full_name": player["full_name"],
        "wikidata_qid": qid,
        "editions_available": agg["editions_available"],
        "editions_fetched": agg["editions_fetched"],
        "wiki_intl_12mo": "" if val is None else val,
        "per_edition_json": json.dumps(agg["per_edition"], ensure_ascii=True),
        "window_start": start,
        "window_end": end,
        "fetch_date": fetch_date,
        "intl_match": agg["intl_match"],
    }


def build_daily_rows(player: dict, agg: dict) -> list[dict]:
    rows = []
    for ed, daily in agg["daily_by_edition"].items():
        rows.append({
            "player_id": player["player_id"],
            "edition": ed,
            "n_days": len(daily),
            "daily_views": "|".join(str(v) for v in daily),
        })
    return rows
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py -v
```

Expected: 17 passed.

- [ ] (5) Commit:

```
git add pilot2/fetch_wikipedia_intl.py pilot2/tests/test_fetch_wikipedia_intl.py
git commit -m "pilot2: A12 intl CSV row builders (spec-3 schema, NULL->'', ASCII json)"
```

---

## Task 6: QID source loader + `main()` wiring + INTEGRATION fetch

**Files:**
- Modify: `pilot2/fetch_wikipedia_intl.py`
- Test: `pilot2/tests/test_fetch_wikipedia_intl.py`

**Interfaces:**
- Consumes: `raw/wiki_pageviews.csv` (reuse `player_id`, `full_name`, `wikidata_qid`); `_common.session`, `atomic_write_csv`, `load_csv`, `CONTACT_UA`.
- Produces:
  - `load_qids() -> list[dict]` — reads `raw/wiki_pageviews.csv` via `_common.load_csv`, returns rows with non-empty `wikidata_qid`; each row keeps `player_id`, `full_name`, `wikidata_qid`. (A QID-less row gets no intl row at all -> downstream merge leaves `wiki_intl_12mo` NaN -> sentinel renorm, same as `intl_match=none`.)
  - `fetch_sitelinks(s, qid: str) -> dict` — one `wbgetentities&props=sitelinks` call; returns parsed JSON dict (used by `parse_sitelinks`).
  - `main() -> None` — loops QIDs: sitelinks call (`sleep(0.15)`), per-edition pageviews (`sleep(0.2)`), aggregate, build rows, `atomic_write_csv` both outputs.

Steps:

- [ ] (1) Write the failing test (loader logic only; main() is exercised by the integration step, not unit-tested against network). Append to `pilot2/tests/test_fetch_wikipedia_intl.py`:

```python
def test_load_qids_filters_blank_qid(tmp_path, monkeypatch):
    import _common
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "wiki_pageviews.csv").write_text(
        "player_id,full_name,wikidata_qid\n"
        "1,David Pastrnak,Q2924461\n"
        "2,Anglophone Only,\n"
        "3,Kirill Kaprizov,Q21155114\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(_common, "RAW_DIR", raw)
    monkeypatch.setattr(fwi, "RAW_DIR", raw)
    rows = fwi.load_qids()
    assert [r["wikidata_qid"] for r in rows] == ["Q2924461", "Q21155114"]
    assert [r["full_name"] for r in rows] == ["David Pastrnak", "Kirill Kaprizov"]
```

- [ ] (2) Run it (expected FAIL — `load_qids` undefined):

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py::test_load_qids_filters_blank_qid -v
```

Expected: `AttributeError: module 'fetch_wikipedia_intl' has no attribute 'load_qids'` (FAIL).

- [ ] (3) Minimal implementation. Add to `pilot2/fetch_wikipedia_intl.py`:

```python
def load_qids() -> list[dict]:
    """Reuse the A1-resolved wikidata_qid per player from wiki_pageviews.csv."""
    rows = load_csv(RAW_DIR / "wiki_pageviews.csv")
    out = []
    for r in rows:
        qid = (r.get("wikidata_qid") or "").strip()
        if not qid:
            continue
        out.append({"player_id": r["player_id"], "full_name": r["full_name"],
                    "wikidata_qid": qid})
    return out


def fetch_sitelinks(s, qid: str) -> dict:
    """One wbgetentities sitelinks call; returns the parsed JSON dict."""
    r = s.get(WD, params={"action": "wbgetentities", "ids": qid,
                          "props": "sitelinks", "format": "json"},
              headers={"User-Agent": CONTACT_UA}, timeout=20)
    r.raise_for_status()
    return r.json()


def main() -> None:
    start, end, fetch_date = window_strings()
    s = session(expire_hours=24)
    summary_rows = []
    daily_rows = []
    for p in load_qids():
        qid = p["wikidata_qid"]
        try:
            entity = fetch_sitelinks(s, qid)
        except Exception as e:
            print(f"  sitelinks {qid}: {e!r}", file=sys.stderr)
            entity = {"entities": {}}
        time.sleep(0.15)
        sitelinks = parse_sitelinks(entity, qid)

        def fetch_fn(edition, title):
            try:
                res = fetch_edition_views(s, edition, title, start, end)
            except Exception as e:
                print(f"  views {edition}:{title!r}: {e!r}", file=sys.stderr)
                res = None
            time.sleep(0.2)
            return res

        agg = aggregate_player(sitelinks, fetch_fn)
        print(f"{p['full_name']:<28} {agg['editions_fetched']:<20} "
              f"{agg['wiki_intl_12mo']} ({agg['intl_match']})")
        summary_rows.append(
            build_summary_row(p, qid, agg, start, end, fetch_date))
        daily_rows.extend(build_daily_rows(p, agg))

    out = RAW_DIR / "wiki_intl_pageviews.csv"
    atomic_write_csv(out, summary_rows, PAGEVIEWS_FIELDS)
    atomic_write_csv(RAW_DIR / "wiki_intl_daily.csv", daily_rows, DAILY_FIELDS)
    n_ok = sum(1 for r in summary_rows if r["intl_match"] == "ok")
    print(f"\nWrote {out} ({len(summary_rows)} rows, {n_ok} intl_match=ok)")
    print(f"Wrote {RAW_DIR / 'wiki_intl_daily.csv'} (daily vectors for bootstrap)")


if __name__ == "__main__":
    main()
```

- [ ] (4) Run pass (unit):

```
python -m pytest pilot2/tests/test_fetch_wikipedia_intl.py -v
```

Expected: 18 passed.

- [ ] (4b) INTEGRATION (real network — run once, requires `raw/wiki_pageviews.csv` present for the 774 pool):

```
python pilot2/fetch_wikipedia_intl.py
```

Expected output:
- Writes `pilot2/raw/wiki_intl_pageviews.csv` with one row per QID-bearing player (≈774 minus any QID-less rows).
- `wiki_intl_12mo` non-null (`intl_match=ok`) for European players — e.g. **Pastrnak** has `cs` (Czech), **Kaprizov** has `ru` (Russian); spot-check those rows are non-empty and `per_edition_json` contains the expected edition keys.
- Anglophone-only players (most North-American-born skaters, e.g. **Connor Bedard**) show `editions_fetched=""`, `wiki_intl_12mo=""`, `intl_match=none`.
- `pilot2/raw/wiki_intl_daily.csv` has one row per (player, fetched edition).
- Re-run is free via `requests_cache`.

- [ ] (5) Commit:

```
git add pilot2/fetch_wikipedia_intl.py pilot2/tests/test_fetch_wikipedia_intl.py
git commit -m "pilot2: A12 wire intl fetcher main() + QID reuse loader + integration fetch"
```

---

## Task 7: Re-lock composite weights in `compute_oaq.py` (drop Instagram, add wiki_intl)

**Files:**
- Modify: `pilot2/compute_oaq.py` (the `WEIGHTS` dict region only)
- Test: `pilot2/tests/test_compute_oaq_weights.py`

**Interfaces:**
- Consumes: nothing (constant edit).
- Produces (in `compute_oaq.py`): re-locked module-level `WEIGHTS` dict; `COMPONENTS = list(WEIGHTS.keys())` re-derives automatically.

A12 locked vector (spec §5, sums to 1.00): `wiki_en_12mo` 0.29, `wiki_intl_12mo` 0.11, `reddit_mentions_12mo` 0.27, `reddit_upvotes_12mo` 0.17, `trends_12mo` 0.16. **Implementation note:** the existing English component column is named `wiki_12mo` in code (see `wiki_pageviews.csv` + `load_inputs`). The spec's `wiki_en_12mo` is that same column; keep the code key `wiki_12mo` to avoid touching the en fetcher and `load_inputs` en-merge, and document the alias in a comment.

Steps:

- [ ] (1) Write the failing test. Create `pilot2/tests/test_compute_oaq_weights.py`:

```python
"""Unit tests for the A12 re-locked composite + wiki_intl sentinel renorm."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pilot2/
import compute_oaq as co  # noqa: E402


def test_weights_are_a12_vector_summing_to_one():
    assert co.WEIGHTS == {
        "wiki_12mo": 0.29,
        "wiki_intl_12mo": 0.11,
        "reddit_mentions_12mo": 0.27,
        "reddit_upvotes_12mo": 0.17,
        "trends_12mo": 0.16,
    }
    assert abs(sum(co.WEIGHTS.values()) - 1.0) < 1e-9


def test_instagram_dropped_from_composite():
    assert "instagram_followers" not in co.WEIGHTS
    assert "instagram_followers" not in co.COMPONENTS


def test_wiki_intl_is_a_component():
    assert "wiki_intl_12mo" in co.COMPONENTS
```

- [ ] (2) Run it (expected FAIL — old weights still present):

```
python -m pytest pilot2/tests/test_compute_oaq_weights.py::test_weights_are_a12_vector_summing_to_one -v
```

Expected: `AssertionError` (WEIGHTS still has instagram / wiki_12mo 0.306) FAIL.

- [ ] (3) Minimal implementation. In `pilot2/compute_oaq.py`, replace the `WEIGHTS` block:

```python
# A12 (2026-06-XX) — composite re-locked by demographic-coverage reasoning,
# BEFORE the wiki_intl fetch. Instagram (stock) DROPPED; wiki_intl_12mo (flow)
# ADDED. Prior vector retained in preregistration.md A12 for audit. The code
# key `wiki_12mo` IS the spec's `wiki_en_12mo` (same en-Wikipedia column).
WEIGHTS = {
    "wiki_12mo": 0.29,           # wiki_en_12mo: EN encyclopedic / casual lookup
    "wiki_intl_12mo": 0.11,      # non-anglophone hockey markets (A12)
    "reddit_mentions_12mo": 0.27,
    "reddit_upvotes_12mo": 0.17,
    "trends_12mo": 0.16,
}
COMPONENTS = list(WEIGHTS.keys())
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_compute_oaq_weights.py -v
```

Expected: 3 passed.

- [ ] (5) Commit:

```
git add pilot2/compute_oaq.py pilot2/tests/test_compute_oaq_weights.py
git commit -m "pilot2: A12 re-lock composite weights (drop instagram, add wiki_intl, sum 1.00)"
```

---

## Task 8: Merge `wiki_intl_12mo` in `load_inputs` + drop instagram dependency

**Files:**
- Modify: `pilot2/compute_oaq.py` (`load_inputs` merge block + the instagram `_to_num` reference + bootstrap component dict + `OUT_COLS`)
- Test: `pilot2/tests/test_compute_oaq_weights.py`

**Interfaces:**
- Consumes: `raw/wiki_intl_pageviews.csv` (columns `player_id`, `wiki_intl_12mo`, `intl_match`).
- Produces: `load_inputs()` returns a DataFrame that now contains a numeric `wiki_intl_12mo` column (NaN where intl_match=none or player absent from the intl file) and an `intl_match` string column. `engagement_from_components` already iterates `WEIGHTS`, so once the column exists the renorm is automatic.

**Co-modification note:** the merge block and `OUT_COLS` are the two collision points with A13. Insert the intl merge directly after the existing en-wiki merge (`df = df.merge(wiki[...])`), keep it to two added lines, and add `wiki_intl_12mo` to `_to_num`'s list. Do NOT remove the `instagram_followers` read from `load_inputs` wholesale in a way that breaks the bootstrap until Task 9 — instead this task removes instagram from the COMPOSITE only (already done via WEIGHTS in Task 7) and Task 9 cleans the bootstrap component dict. Removing instagram from `load_inputs`/`OUT_COLS` is done here since they are co-located; the bootstrap still references `ig_fixed` until Task 9, so run the full pipeline check only after Task 9.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_compute_oaq_weights.py`:

```python
def test_engagement_renorm_drops_null_wiki_intl():
    # 3 players: P0 has all five components; P1 has wiki_intl NULL (anglophone);
    # constant non-wiki_intl columns so z-scores are well-defined.
    import pandas as pd
    n = 3
    df = pd.DataFrame({
        "wiki_12mo": [10.0, 20.0, 30.0],
        "wiki_intl_12mo": [5.0, np.nan, 15.0],
        "reddit_mentions_12mo": [1.0, 2.0, 3.0],
        "reddit_upvotes_12mo": [4.0, 5.0, 6.0],
        "trends_12mo": [7.0, 8.0, 9.0],
    })
    er, dropped = co.compute_engagement_raw(df)
    # P1 dropped wiki_intl; its weights renorm over the other 4 -> finite value.
    assert dropped[1] == "wiki_intl_12mo"
    assert np.isfinite(er[1])
    # P0/P2 keep all five.
    assert dropped[0] == "" and dropped[2] == ""


def test_load_inputs_has_wiki_intl_column(monkeypatch):
    # Smoke: the real load_inputs reads raw/wiki_intl_pageviews.csv if present.
    # Skip if raw inputs are not materialized in this checkout.
    import pandas as pd
    try:
        df = co.load_inputs()
    except FileNotFoundError:
        import pytest
        pytest.skip("raw inputs not materialized")
    assert "wiki_intl_12mo" in df.columns
    assert pd.api.types.is_numeric_dtype(df["wiki_intl_12mo"])
```

- [ ] (2) Run it (expected FAIL — `wiki_intl_12mo` not produced by `compute_engagement_raw` because the column is absent from the test df path / KeyError in `engagement_from_components`):

```
python -m pytest pilot2/tests/test_compute_oaq_weights.py::test_engagement_renorm_drops_null_wiki_intl -v
```

Expected: PASS only after WEIGHTS includes `wiki_intl_12mo` (Task 7) AND `compute_engagement_raw` can read the column. Since Task 7 added the key, this test should pass once the test df supplies the column; if `load_inputs` doesn't yet add it, `test_load_inputs_has_wiki_intl_column` FAILs with missing column. Run both — expect the load_inputs test to FAIL pre-implementation.

- [ ] (3) Minimal implementation. In `pilot2/compute_oaq.py` `load_inputs()`, add the intl read near the other reads:

```python
    wiki_intl = pd.read_csv(RAW_DIR / "wiki_intl_pageviews.csv",
                            dtype={"player_id": int})
```

Immediately after the existing en-wiki merge line
`df = df.merge(wiki[["player_id", "wiki_12mo", "wiki_match"]], on="player_id", how="left")`
add:

```python
    df = df.merge(
        wiki_intl[["player_id", "wiki_intl_12mo", "intl_match"]],
        on="player_id", how="left",
    )
```

Remove the instagram read + merge (these two lines):

```python
    ig = pd.read_csv(RAW_DIR / "instagram_followers.csv", dtype={"player_id": int})
```
```python
    df = df.merge(
        ig[["player_id", "instagram_followers"]], on="player_id", how="left"
    )
```

In the `_to_num(df, SKILL_COLS + [...])` call, replace `"instagram_followers"` with `"wiki_intl_12mo"` so the list becomes:

```python
    _to_num(
        df,
        SKILL_COLS
        + ["games_played", "wiki_12mo", "wiki_intl_12mo", "trends_12mo",
           "cap_hit_M", "jersey_rank"],
    )
```

In `OUT_COLS`, replace `"instagram_followers",` with `"wiki_intl_12mo", "intl_match",` (place next to `wiki_12mo`):

```python
    "wiki_12mo", "wiki_intl_12mo", "intl_match",
    "trends_12mo", "reddit_mentions_12mo", "reddit_upvotes_12mo",
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_compute_oaq_weights.py -v
```

Expected: `test_engagement_renorm_drops_null_wiki_intl` PASS; `test_load_inputs_has_wiki_intl_column` PASS or SKIP (skips only if raw inputs absent).

- [ ] (5) Commit:

```
git add pilot2/compute_oaq.py pilot2/tests/test_compute_oaq_weights.py
git commit -m "pilot2: A12 merge wiki_intl_12mo in load_inputs; drop instagram col + OUT_COLS"
```

---

## Task 9: Update bootstrap component dict (intl resampled, instagram removed)

**Files:**
- Modify: `pilot2/compute_oaq.py` (`bootstrap_player_cis` only)
- Test: `pilot2/tests/test_compute_oaq_weights.py`

**Interfaces:**
- Consumes: `load_wiki_intl_daily() -> dict[int, dict[str, np.ndarray]]` is NOT required; the bootstrap may resample the intl TOTAL daily vector. Per spec §3 the intl daily file is per-(player,edition); for the bootstrap we resample the summed intl daily vector. Add a loader `load_wiki_intl_daily_summed() -> dict[int, np.ndarray]` that sums the per-edition daily vectors element-wise where lengths match, else concatenates (a player's intl daily pool resampled with replacement, same role as `wiki_daily`).
- Produces: `bootstrap_player_cis` component dict uses `wiki_intl_12mo` (resampled like wiki) and NO LONGER references `instagram_followers`.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_compute_oaq_weights.py`:

```python
def test_bootstrap_component_dict_has_no_instagram():
    import inspect
    src = inspect.getsource(co.bootstrap_player_cis)
    assert "instagram_followers" not in src
    assert "wiki_intl_12mo" in src


def test_load_wiki_intl_daily_summed_concats_pool(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "wiki_intl_daily.csv").write_text(
        "player_id,edition,n_days,daily_views\n"
        "1,cs,2,50|50\n"
        "1,sv,1,40\n"
        "2,ru,3,1|2|3\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(co, "RAW_DIR", raw)
    out = co.load_wiki_intl_daily_summed()
    import numpy as np
    assert set(out.keys()) == {1, 2}
    assert sorted(out[1].tolist()) == [40.0, 50.0, 50.0]  # pooled cs+sv days
    assert out[2].tolist() == [1.0, 2.0, 3.0]
```

- [ ] (2) Run it (expected FAIL — instagram still in bootstrap; loader undefined):

```
python -m pytest pilot2/tests/test_compute_oaq_weights.py::test_bootstrap_component_dict_has_no_instagram -v
```

Expected: `AssertionError` (instagram_followers still in bootstrap source) FAIL.

- [ ] (3) Minimal implementation. In `pilot2/compute_oaq.py`:

Add the loader near `load_wiki_daily`:

```python
def load_wiki_intl_daily_summed() -> dict[int, np.ndarray]:
    """player_id -> pooled intl daily-view array (all whitelisted editions
    concatenated) for bootstrap resampling. Empty for anglophone-only players."""
    path = RAW_DIR / "wiki_intl_daily.csv"
    out: dict[int, np.ndarray] = {}
    if not path.exists():
        return out
    wd = pd.read_csv(path, dtype={"player_id": int})
    for pid, grp in wd.groupby("player_id"):
        pool: list[float] = []
        for raw in grp["daily_views"]:
            if isinstance(raw, str) and raw.strip():
                pool.extend(float(x) for x in raw.split("|") if x.strip() != "")
        out[int(pid)] = np.array(pool, dtype=float)
    return out
```

In `bootstrap_player_cis`, change the signature to accept the intl daily dict and resample it. Replace the instagram-fixed line and the component dict:

Change the function signature:

```python
def bootstrap_player_cis(
    df: pd.DataFrame,
    peers: list[list[int]],
    market_z: np.ndarray,
    wiki_daily: dict[int, np.ndarray],
    reddit_scores: dict[int, np.ndarray],
    wiki_intl_daily: dict[int, np.ndarray],
    n_draws: int = BOOTSTRAP_DRAWS,
    seed: int = SEED,
):
```

After the `daily_arrays`/`reddit_arrays` precompute, add:

```python
    intl_arrays = [wiki_intl_daily.get(int(p), np.empty(0)) for p in pids]
    base_intl = df["wiki_intl_12mo"].to_numpy(dtype=float)
    intl_present = np.isfinite(base_intl)
```

Remove the instagram fixed line:

```python
    ig_fixed = df["instagram_followers"].to_numpy(dtype=float)
```

Inside the draw loop, after `rup_draw = base_rup.copy()`, add:

```python
        intl_draw = base_intl.copy()
```

and inside the `for i in range(n):` loop add intl resampling mirroring wiki:

```python
            if intl_present[i]:
                arr = intl_arrays[i]
                if arr.size:
                    samp = arr[rng.integers(0, arr.size, arr.size)]
                    intl_draw[i] = samp.sum()
```

Replace the component dict in the draw loop:

```python
        comp_z = {
            "wiki_12mo": zscore_array(wiki_draw),
            "wiki_intl_12mo": zscore_array(intl_draw),
            "reddit_mentions_12mo": zscore_array(rmen_draw),
            "reddit_upvotes_12mo": zscore_array(rup_draw),
            "trends_12mo": zscore_array(trends_fixed),
        }
```

In `main()`, load + pass the intl daily dict:

```python
    wiki_intl_daily = load_wiki_intl_daily_summed()
```
and update the call:

```python
    ci = bootstrap_player_cis(df, peers, market_z, wiki_daily, reddit_scores,
                              wiki_intl_daily)
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_compute_oaq_weights.py -v
```

Expected: all tests in file passed (instagram-free bootstrap, loader pools correctly).

- [ ] (4b) INTEGRATION (full pipeline; requires all 774 raw inputs incl. `wiki_intl_pageviews.csv`/`wiki_intl_daily.csv` from Task 6):

```
python pilot2/compute_oaq.py
```

Expected: runs end-to-end, prints `Wrote .../oaq_pilot.csv`, and `oaq_pilot.csv` now contains `wiki_intl_12mo` + `intl_match` columns and NO `instagram_followers` column. The "Sentinel / dropped-component summary" in `results.md` lists `wiki_intl_12mo` with a large drop count (anglophone-only players).

- [ ] (5) Commit:

```
git add pilot2/compute_oaq.py pilot2/tests/test_compute_oaq_weights.py
git commit -m "pilot2: A12 bootstrap resamples wiki_intl, drops instagram component"
```

---

## Task 10: Strip residual Instagram references from `results.md` writer

**Files:**
- Modify: `pilot2/compute_oaq.py` (`write_results_md` / docstring header references to instagram, if any remain that break the run)
- Test: `pilot2/tests/test_compute_oaq_weights.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: no code path references `instagram_followers` as a DataFrame column (it no longer exists after Task 8), so any lingering reference would raise `KeyError` at runtime. This task is a guard: confirm none remain.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_compute_oaq_weights.py`:

```python
def test_no_instagram_column_reference_in_results_writer():
    import inspect
    src = inspect.getsource(co.write_results_md)
    assert "instagram_followers" not in src
```

- [ ] (2) Run it:

```
python -m pytest pilot2/tests/test_compute_oaq_weights.py::test_no_instagram_column_reference_in_results_writer -v
```

Expected: PASS if no reference remains (the audited writer body does not currently reference the `instagram_followers` column — the WEIGHTS/COMPONENTS-driven sentinel table and leaderboards do not name it). If a reference is found, it FAILs and step (3) removes it.

- [ ] (3) Implementation (only if step 2 FAILs): delete the offending line(s) referencing `instagram_followers` from `write_results_md`. The sentinel-summary table iterates `COMPONENTS`, so it auto-updates. No other change.

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_compute_oaq_weights.py -v
```

Expected: all passed.

- [ ] (5) Commit (only if a change was made in step 3; otherwise skip — the test passing confirms cleanliness):

```
git add pilot2/compute_oaq.py pilot2/tests/test_compute_oaq_weights.py
git commit -m "pilot2: A12 guard against residual instagram refs in results writer"
```

---

## Task 11: Diagnostic A — source-correlation matrix

**Files:**
- Create: `pilot2/diagnostics/__init__.py` (empty)
- Create: `pilot2/diagnostics/source_correlation.py`
- Test: `pilot2/tests/test_diagnostics.py`

**Interfaces:**
- Consumes: `compute_oaq.load_inputs`, `compute_oaq.zscore_array`, `compute_oaq.spearman_rho`, `compute_oaq.COMPONENTS`, `_common.PILOT_DIR`, `_common.atomic_write_csv`.
- Produces:
  - `pairwise_spearman(z_by_comp: dict[str, np.ndarray], components: list[str]) -> tuple[np.ndarray, np.ndarray]` — returns `(rho_matrix, n_matrix)`, both `len(components) x len(components)`, pairwise-complete (only rows finite in BOTH components), per-cell n; diagonal rho=1.0, n=count finite.
  - `DIAG_COMPONENTS: list[str]` == `["wiki_12mo", "wiki_intl_12mo", "reddit_mentions_12mo", "reddit_upvotes_12mo", "trends_12mo"]`.
  - `main() -> None` — z-scores each component across the pool, computes the matrix, writes `diagnostics/source_correlation.csv` (long form: `comp_a, comp_b, spearman_rho, n`) + `figure_source_correlation.png` heatmap.

Steps:

- [ ] (1) Write the failing test. Create `pilot2/tests/test_diagnostics.py`:

```python
"""Unit tests for diagnostic pure helpers (no network, no figure render)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pilot2/
from diagnostics import source_correlation as sc  # noqa: E402


def test_diag_components_are_the_five_zscored_components():
    assert sc.DIAG_COMPONENTS == [
        "wiki_12mo", "wiki_intl_12mo", "reddit_mentions_12mo",
        "reddit_upvotes_12mo", "trends_12mo",
    ]


def test_pairwise_spearman_pairwise_complete_per_cell_n():
    comps = ["a", "b"]
    z = {
        "a": np.array([1.0, 2.0, 3.0, 4.0]),
        "b": np.array([1.0, 2.0, np.nan, 4.0]),  # one NULL -> pair drops to n=3
    }
    rho, n = sc.pairwise_spearman(z, comps)
    assert rho.shape == (2, 2) and n.shape == (2, 2)
    assert n[0, 1] == 3            # pairwise-complete excludes the NaN row
    assert abs(rho[0, 1] - 1.0) < 1e-9   # perfectly monotone on the 3 shared
    assert rho[0, 0] == 1.0 and rho[1, 1] == 1.0
    assert n[0, 0] == 4 and n[1, 1] == 3
```

- [ ] (2) Run it (expected FAIL — module/dir absent):

```
python -m pytest pilot2/tests/test_diagnostics.py::test_pairwise_spearman_pairwise_complete_per_cell_n -v
```

Expected: `ModuleNotFoundError: No module named 'diagnostics'` (FAIL).

- [ ] (3) Minimal implementation. Create `pilot2/diagnostics/__init__.py` (empty), then `pilot2/diagnostics/source_correlation.py`:

```python
"""A12 diagnostic (a): pairwise Spearman across z-scored composite components.

Pairwise-complete, per-cell n reported. Descriptive ONLY — never feeds back
into weights. Output: diagnostics/source_correlation.csv + heatmap PNG.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pilot2/
from _common import PILOT_DIR, atomic_write_csv  # noqa: E402
import compute_oaq as co  # noqa: E402

DIAG_COMPONENTS = [
    "wiki_12mo", "wiki_intl_12mo", "reddit_mentions_12mo",
    "reddit_upvotes_12mo", "trends_12mo",
]
DIAG_DIR = PILOT_DIR / "diagnostics"


def pairwise_spearman(z_by_comp: dict[str, np.ndarray],
                      components: list[str]):
    k = len(components)
    rho = np.full((k, k), np.nan)
    n = np.zeros((k, k), dtype=int)
    for i in range(k):
        zi = z_by_comp[components[i]]
        for j in range(k):
            zj = z_by_comp[components[j]]
            mask = np.isfinite(zi) & np.isfinite(zj)
            n[i, j] = int(mask.sum())
            if i == j:
                rho[i, j] = 1.0 if mask.sum() else np.nan
            elif mask.sum() >= 2:
                rho[i, j] = co.spearman_rho(zi[mask], zj[mask])
    return rho, n


def main() -> None:
    df = co.load_inputs()
    z_by_comp = {
        c: co.zscore_array(df[c].to_numpy(dtype=float)) for c in DIAG_COMPONENTS
    }
    rho, n = pairwise_spearman(z_by_comp, DIAG_COMPONENTS)

    rows = []
    for i, a in enumerate(DIAG_COMPONENTS):
        for j, b in enumerate(DIAG_COMPONENTS):
            rows.append({"comp_a": a, "comp_b": b,
                         "spearman_rho": rho[i, j], "n": n[i, j]})
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(DIAG_DIR / "source_correlation.csv", rows,
                     ["comp_a", "comp_b", "spearman_rho", "n"])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(rho, vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(DIAG_COMPONENTS)))
    ax.set_yticks(range(len(DIAG_COMPONENTS)))
    ax.set_xticklabels(DIAG_COMPONENTS, rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels(DIAG_COMPONENTS, fontsize=7)
    for i in range(len(DIAG_COMPONENTS)):
        for j in range(len(DIAG_COMPONENTS)):
            if np.isfinite(rho[i, j]):
                ax.text(j, i, f"{rho[i, j]:.2f}\nn={n[i, j]}",
                        ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=ax, label="Spearman rho")
    ax.set_title("Source-correlation matrix (z-scored components)")
    fig.tight_layout()
    fig.savefig(DIAG_DIR / "figure_source_correlation.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {DIAG_DIR / 'source_correlation.csv'}")
    print(f"Wrote {DIAG_DIR / 'figure_source_correlation.png'}")


if __name__ == "__main__":
    main()
```

- [ ] (4) Run pass (unit):

```
python -m pytest pilot2/tests/test_diagnostics.py -v
```

Expected: `test_diag_components_*` + `test_pairwise_spearman_*` passed.

- [ ] (4b) INTEGRATION (requires computed inputs):

```
python pilot2/diagnostics/source_correlation.py
```

Expected: writes `pilot2/diagnostics/source_correlation.csv` (25 rows for 5x5) + `figure_source_correlation.png`. Sanity: `corr(wiki_intl, reddit_*)` rows show a LOWER rho than `corr(wiki_en, reddit_*)` rows (spec §6 pre-registered descriptive expectation — reported regardless of direction).

- [ ] (5) Commit:

```
git add pilot2/diagnostics/__init__.py pilot2/diagnostics/source_correlation.py pilot2/tests/test_diagnostics.py
git commit -m "pilot2: A12 diagnostic (a) source-correlation matrix (pairwise Spearman + heatmap)"
```

---

## Task 12: Diagnostic B — Reddit-downweight robustness

**Files:**
- Create: `pilot2/diagnostics/reddit_robustness.py`
- Test: `pilot2/tests/test_diagnostics.py`

**Interfaces:**
- Consumes: `compute_oaq` (`WEIGHTS`, `load_inputs`, `compute_market_z`, `compute_peers`, `compute_oaq`, `spearman_rho`), `_common.PILOT_DIR`, `_common.atomic_write_csv`.
- Produces:
  - `REDDIT_KEYS: tuple[str, str]` == `("reddit_mentions_12mo", "reddit_upvotes_12mo")`.
  - `LADDER: tuple[float, ...]` == `(1.0, 0.5, 0.0)`.
  - `scaled_weights(base: dict[str, float], factor: float) -> dict[str, float]` — scales the Reddit family weights by `factor`, redistributes the freed weight PROPORTIONALLY across the non-Reddit components, and returns a dict summing to 1.0 (within 1e-9). At `factor=0.0` Reddit weights are 0 and non-Reddit weights renorm to 1.0.
  - `top_overlap(a_names: list[str], b_names: list[str], k: int = 20) -> int` — size of intersection of the two top-k name lists.
  - `main() -> None` — for each ladder factor, monkeypatch-free recompute by passing a temporary `WEIGHTS` into the OAQ math (set `co.WEIGHTS`/`co.COMPONENTS`, restore after), compute `OAQ_portable` across the pool, compare to the headline (factor=1.0 == locked A12) via Spearman + top-20 overlap; write `diagnostics/reddit_robustness.csv` + PNG.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_diagnostics.py`:

```python
from diagnostics import reddit_robustness as rr  # noqa: E402


def test_ladder_and_keys_locked():
    assert rr.LADDER == (1.0, 0.5, 0.0)
    assert rr.REDDIT_KEYS == ("reddit_mentions_12mo", "reddit_upvotes_12mo")


def test_scaled_weights_sum_to_one_and_halve_reddit():
    base = {
        "wiki_12mo": 0.29, "wiki_intl_12mo": 0.11,
        "reddit_mentions_12mo": 0.27, "reddit_upvotes_12mo": 0.17,
        "trends_12mo": 0.16,
    }
    half = rr.scaled_weights(base, 0.5)
    assert abs(sum(half.values()) - 1.0) < 1e-9
    # Reddit family halved relative ratio preserved before renorm:
    assert half["reddit_mentions_12mo"] < base["reddit_mentions_12mo"]
    # non-reddit grew proportionally (wiki:intl ratio preserved)
    assert (half["wiki_12mo"] / half["wiki_intl_12mo"]) == \
           (base["wiki_12mo"] / base["wiki_intl_12mo"])


def test_scaled_weights_zero_drops_reddit_entirely():
    base = {
        "wiki_12mo": 0.29, "wiki_intl_12mo": 0.11,
        "reddit_mentions_12mo": 0.27, "reddit_upvotes_12mo": 0.17,
        "trends_12mo": 0.16,
    }
    zero = rr.scaled_weights(base, 0.0)
    assert zero["reddit_mentions_12mo"] == 0.0
    assert zero["reddit_upvotes_12mo"] == 0.0
    assert abs(sum(zero.values()) - 1.0) < 1e-9


def test_top_overlap_counts_intersection():
    a = ["A", "B", "C", "D"]
    b = ["C", "D", "E", "F"]
    assert rr.top_overlap(a, b, k=4) == 2
    assert rr.top_overlap(a, b, k=2) == 0
```

- [ ] (2) Run it (expected FAIL — module absent):

```
python -m pytest pilot2/tests/test_diagnostics.py::test_scaled_weights_sum_to_one_and_halve_reddit -v
```

Expected: `ModuleNotFoundError: No module named 'diagnostics.reddit_robustness'` (FAIL).

- [ ] (3) Minimal implementation. Create `pilot2/diagnostics/reddit_robustness.py`:

```python
"""A12 diagnostic (b): Reddit-downweight robustness sensitivity analysis.

Re-runs the OAQ pipeline at a pre-declared Reddit-weight ladder {1.0,0.5,0.0}x
the A12 Reddit family weight, redistributing the freed weight PROPORTIONALLY
across non-Reddit flows. Compares each variant's OAQ_portable to the locked
A12 headline (factor=1.0) via Spearman + top-20 overlap. Sensitivity analysis
ONLY — the headline stays the locked A12 vector; never a weight search.

Output: diagnostics/reddit_robustness.csv + figure_reddit_robustness.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pilot2/
from _common import PILOT_DIR, atomic_write_csv  # noqa: E402
import compute_oaq as co  # noqa: E402

REDDIT_KEYS = ("reddit_mentions_12mo", "reddit_upvotes_12mo")
LADDER = (1.0, 0.5, 0.0)
DIAG_DIR = PILOT_DIR / "diagnostics"


def scaled_weights(base: dict[str, float], factor: float) -> dict[str, float]:
    """Scale Reddit family by `factor`; redistribute freed weight to non-Reddit
    components proportionally so the vector re-sums to 1.0."""
    reddit_base = sum(base[k] for k in REDDIT_KEYS)
    nonreddit = {k: v for k, v in base.items() if k not in REDDIT_KEYS}
    nonreddit_sum = sum(nonreddit.values())
    freed = reddit_base * (1.0 - factor)
    out: dict[str, float] = {}
    for k, v in base.items():
        if k in REDDIT_KEYS:
            out[k] = v * factor
        else:
            share = (v / nonreddit_sum) if nonreddit_sum > 0 else 0.0
            out[k] = v + freed * share
    return out


def top_overlap(a_names: list[str], b_names: list[str], k: int = 20) -> int:
    return len(set(a_names[:k]) & set(b_names[:k]))


def _portable_for_weights(df, peers, market_z, weights):
    """Recompute OAQ_portable under a temporary WEIGHTS vector."""
    old_w, old_c = co.WEIGHTS, co.COMPONENTS
    try:
        co.WEIGHTS = weights
        co.COMPONENTS = list(weights.keys())
        out = co.compute_oaq(df, peers=peers, market_z=market_z)
    finally:
        co.WEIGHTS, co.COMPONENTS = old_w, old_c
    return out


def main() -> None:
    df = co.load_inputs()
    market_z, _ = co.compute_market_z(df)
    df["market_z"] = market_z
    peers = co.compute_peers(df)

    base = dict(co.WEIGHTS)
    headline = _portable_for_weights(df, peers, market_z, base)
    head_port = headline["OAQ_portable"].to_numpy(dtype=float)
    head_top = (headline.dropna(subset=["OAQ_portable"])
                .sort_values("OAQ_portable", ascending=False)["full_name"].tolist())

    rows = []
    for factor in LADDER:
        w = scaled_weights(base, factor)
        variant = _portable_for_weights(df, peers, market_z, w)
        v_port = variant["OAQ_portable"].to_numpy(dtype=float)
        mask = np.isfinite(head_port) & np.isfinite(v_port)
        rho = co.spearman_rho(head_port[mask], v_port[mask])
        v_top = (variant.dropna(subset=["OAQ_portable"])
                 .sort_values("OAQ_portable", ascending=False)["full_name"].tolist())
        rows.append({
            "reddit_factor": factor,
            "reddit_weight": round(sum(w[k] for k in REDDIT_KEYS), 6),
            "spearman_vs_headline": rho,
            "top20_overlap": top_overlap(head_top, v_top, 20),
            "n": int(mask.sum()),
        })

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(DIAG_DIR / "reddit_robustness.csv", rows,
                     ["reddit_factor", "reddit_weight",
                      "spearman_vs_headline", "top20_overlap", "n"])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    factors = [r["reddit_factor"] for r in rows]
    rhos = [r["spearman_vs_headline"] for r in rows]
    overlaps = [r["top20_overlap"] for r in rows]
    fig, ax1 = plt.subplots(figsize=(6, 4))
    ax1.plot(factors, rhos, "o-", color="C0", label="Spearman vs headline")
    ax1.set_xlabel("Reddit weight factor")
    ax1.set_ylabel("Spearman rho vs A12 headline", color="C0")
    ax1.set_ylim(0, 1.02)
    ax2 = ax1.twinx()
    ax2.plot(factors, overlaps, "s--", color="C1", label="top-20 overlap")
    ax2.set_ylabel("top-20 overlap (of 20)", color="C1")
    ax1.set_title("Reddit-downweight robustness")
    fig.tight_layout()
    fig.savefig(DIAG_DIR / "figure_reddit_robustness.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {DIAG_DIR / 'reddit_robustness.csv'}")
    print(f"Wrote {DIAG_DIR / 'figure_reddit_robustness.png'}")


if __name__ == "__main__":
    main()
```

- [ ] (4) Run pass (unit):

```
python -m pytest pilot2/tests/test_diagnostics.py -v
```

Expected: all diagnostic tests passed.

- [ ] (4b) INTEGRATION (requires computed inputs):

```
python pilot2/diagnostics/reddit_robustness.py
```

Expected: writes `pilot2/diagnostics/reddit_robustness.csv` (3 ladder rows) + PNG. Sanity: `factor=1.0` row has `spearman_vs_headline == 1.0` and `top20_overlap == 20` (identity); `factor=0.5` row `spearman_vs_headline >= ~0.9` (spec §6 expectation, reported regardless); `factor=0.0` still strongly positive.

- [ ] (5) Commit:

```
git add pilot2/diagnostics/reddit_robustness.py pilot2/tests/test_diagnostics.py
git commit -m "pilot2: A12 diagnostic (b) reddit-downweight robustness ladder {1,0.5,0}x"
```

---

## Task 13: Append A12 amendment text to `preregistration.md`

**Files:**
- Modify: `pilot2/preregistration.md` (append only, after A11)
- Test: `pilot2/tests/test_diagnostics.py` (text presence assertion)

**Interfaces:**
- Consumes: spec §7 verbatim amendment text.
- Produces: A12 block appended to `pilot2/preregistration.md`.

**Co-modification note:** this is the second shared file with A13. A12 appends its block now; A13 appends its own block AFTER A12's commit (per amendment order / spec §7 "letter reconciliation: A13"). Append only — do not edit A1–A11.

Steps:

- [ ] (1) Write the failing test. Append to `pilot2/tests/test_diagnostics.py`:

```python
def test_a12_amendment_appended_to_prereg():
    txt = (Path(__file__).resolve().parents[1] / "preregistration.md").read_text(
        encoding="utf-8")
    assert "A12 (2026-06-" in txt
    assert "multi-language Wikipedia" in txt
    assert "wiki_en 0.29, wiki_intl 0.11" in txt
    assert "Instagram follower count" in txt
    # A12 must come AFTER A11 in the file (append order).
    assert txt.index("A11 (2026-06-19)") < txt.index("A12 (2026-06-")
```

- [ ] (2) Run it (expected FAIL — A12 text absent):

```
python -m pytest pilot2/tests/test_diagnostics.py::test_a12_amendment_appended_to_prereg -v
```

Expected: `AssertionError` (no "A12 (2026-06-" in file) FAIL.

- [ ] (3) Implementation. Append to the END of `pilot2/preregistration.md` (after the A11 block), the verbatim A12 text from spec §7. Render each spec blockquote line as a Markdown blockquote (`> ...`), exactly as the spec shows:

```markdown

**A12 (2026-06-20) — Attention ingestion broadened: multi-language Wikipedia added as a flow component; Instagram/X follower count removed from the composite; GDELT news rejected on A11-window grounds. New §4 flow-weight vector logged BEFORE any new-source fetch. Anti-tuning: weights derived by demographic-coverage reasoning, prior vector retained.**

> Motivation: the §4 composite reached only English-language and engaged-fan-community demographics, leaving the whole-league (A10) coverage claim open to the "this just measures Anglophone Reddit fame" attack. A breadth flow is added — `wiki_intl_12mo` (pageviews summed over the fixed hockey-market edition set {sv, fi, cs, ru, de, sk, fr}, A11 window, Wikidata-QID reused from A1).
>
> The Instagram follower count — a lifetime STOCK that is noisy and inflatable (documented fake-follower rates; public sources disagree ~2×) and conceptually mismatched with the A11 flow window — is removed from the composite (prior weight 0.139 → dropped); X followers are not added. GDELT mainstream-news volume was considered and rejected: its DOC 2.0 API has a hard ~3-month rolling window that cannot honor the A11 12-month window, and a single source on a divergent window is not worth the integrity cost; the mainstream-reach demographic is carried instead by the broad-demographic YouTube validation gate.
>
> New §4 flow weights: wiki_en 0.29, wiki_intl 0.11, reddit_mentions 0.27, reddit_upvotes 0.17, trends 0.16 (sum 1.00). Prior vector (wiki 0.306, reddit_mentions 0.250, reddit_upvotes 0.167, trends 0.139, instagram 0.139) retained here for audit. Sentinel renorm (§4) applies unchanged to the new component; the dropped follower stock never participates. Peer features (§6), λ (§7/A5), denominators (A4/A8), OAuth transport (A9), the A10 774-pool + small_sample flag, the A11 window, and all validation floors (§9, A6/V3) are unchanged.
>
> **Letter reconciliation:** the sibling skill-vector amendment commits as the next free letter (A13).
```

- [ ] (4) Run pass:

```
python -m pytest pilot2/tests/test_diagnostics.py::test_a12_amendment_appended_to_prereg -v
```

Expected: PASS.

- [ ] (5) Commit:

```
git add pilot2/preregistration.md pilot2/tests/test_diagnostics.py
git commit -m "pilot2: log A12 amendment in preregistration (before any new-source fetch)"
```

---

## Task 14: Full-suite green + end-to-end verification

**Files:**
- Test: all of `pilot2/tests/`

**Interfaces:** none (verification task).

Steps:

- [ ] (1) Run the full unit suite:

```
python -m pytest pilot2/tests/ -v
```

Expected: ALL tests pass (fetcher 18, weights 7, diagnostics 8+ — counts approximate; zero failures).

- [ ] (2) Run the full pipeline + both diagnostics end-to-end (requires Task 6 raw outputs materialized):

```
python pilot2/compute_oaq.py
python pilot2/diagnostics/source_correlation.py
python pilot2/diagnostics/reddit_robustness.py
```

Expected: all three exit 0; `oaq_pilot.csv` has `wiki_intl_12mo` + `intl_match`, no `instagram_followers`; `diagnostics/source_correlation.csv`, `diagnostics/reddit_robustness.csv`, and both PNGs exist.

- [ ] (3) (no code) Confirm the spec self-review checklist (below) is fully covered.

- [ ] (4) Commit any final fixups:

```
git add -A
git commit -m "pilot2: A12 full-suite green + end-to-end verification"
```

---

## Self-review against the spec

**Spec-section -> task coverage:**

| Spec section | Covered by |
|---|---|
| §1 Purpose (broaden input demographic via multilang Wiki; drop IG; re-lock weights; 2 diagnostics) | Tasks 1–13 collectively |
| §2 Locked decisions: wiki_intl separate component | Tasks 7, 8 |
| §2: language whitelist {sv,fi,cs,ru,de,sk,fr} | Task 1 (`WHITELIST`), Task 2 (filter) |
| §2: GDELT rejected | Task 13 (amendment text); no code (correctly nothing to build) |
| §2: Instagram dropped entirely | Tasks 7, 8, 9, 10 |
| §2: window = A11 fixed | Task 1 (`WINDOW_START/END` hardcoded) |
| §3 Method 1 (player_id->qid map) | Task 6 (`load_qids`) |
| §3 Method 2 (sitelinks call + whitelist intersect) | Tasks 2, 6 (`fetch_sitelinks`, `parse_sitelinks`) |
| §3 Method 3 (per-article pageviews, fixed window hardcoded) | Tasks 1, 3 |
| §3 Method 4 (verbatim title, quote safe="") | Tasks 2, 3 (`edition_pv_url`) |
| §3 Method 5 (sum per edition + overall) | Task 4 (`aggregate_player`) |
| §3 Aggregation (separate wiki_intl_12mo) | Tasks 4, 7, 8 |
| §3 Output schema wiki_intl_pageviews.csv | Task 5 (`PAGEVIEWS_FIELDS`, `build_summary_row`) |
| §3 Output schema wiki_intl_daily.csv | Task 5 (`DAILY_FIELDS`, `build_daily_rows`) |
| §3 Fetcher reuse (session, CONTACT_UA, atomic_write_csv, UTF-8) + sleeps | Tasks 1, 3, 6 (sleep 0.15 sitelinks / 0.2 articles) |
| §3 Failure/NULL (no sitelink -> NULL + intl_match=none; single 404 skip) | Tasks 3 (404->None), 4 (NULL rule) |
| §4 Considered/rejected (GDELT, IG/X) | Task 13 (text only) |
| §5 Composite weights vector (sum 1.00) | Task 7 |
| §5 wiki_intl as component, sentinel renorm extends to it | Tasks 8, 9 |
| §5 dropped IG never participates in flow renorm | Tasks 7–10 |
| §6(a) source-correlation matrix (pairwise Spearman, pairwise-complete, per-cell n, CSV+PNG) | Task 11 |
| §6(b) Reddit-downweight robustness ({1,0.5,0}x, proportional redistribution, Spearman + top-20 overlap, CSV+PNG) | Task 12 |
| §7 amendment text appended verbatim | Task 13 |
| §8 anti-tuning (weights before fetch; diagnostics never feed back) | Task 7 (weights locked pre-fetch ordering), Tasks 11/12 (descriptive only) |
| §9 open items/risks (coverage skew NULL for anglophone; re-confirm gates) | Surfaced in `results.md` sentinel summary (Task 9 integration); gate re-confirmation is the existing `compute_oaq.py` validation path (unchanged), no new task needed |

**Placeholder scan:** no "TODO", "add error handling", "similar to Task N", or undefined-function references. Every function used in a later task is defined in an earlier task (`window_strings`, `parse_sitelinks`, `edition_pv_url`, `fetch_edition_views`, `aggregate_player`, `build_summary_row`, `build_daily_rows`, `load_qids`, `fetch_sitelinks`, `load_wiki_intl_daily_summed`, `pairwise_spearman`, `scaled_weights`, `top_overlap`, `_portable_for_weights`). Reused codebase symbols (`atomic_write_csv`, `RAW_DIR`, `PILOT_DIR`, `load_csv`, `session`, `CONTACT_UA`, `WEIGHTS`, `COMPONENTS`, `zscore_array`, `spearman_rho`, `compute_oaq`, `compute_peers`, `compute_market_z`, `load_inputs`, `compute_engagement_raw`, `engagement_from_components`, `bootstrap_player_cis`, `OUT_COLS`) match real signatures verified in `_common.py`, `fetch_wikipedia.py`, and `compute_oaq.py`.

**Type/name consistency:** the code column `wiki_12mo` is consistently used as the spec's `wiki_en_12mo` (alias documented in Task 7). `wiki_intl_12mo` is `int|""` in CSV, numeric (NaN for NULL) in the DataFrame. `intl_match` is `"ok"|"none"`. Edition codes are bare (`cs`, not `cswiki`) everywhere. The bootstrap signature gains a trailing `wiki_intl_daily` param (Task 9) and the `main()` call is updated in the same task.

**Known gaps / could-not-map (surfaced to caller):**
1. **§6(a) pre-registered descriptive expectation** (`corr(wiki_intl,reddit_*) < corr(wiki_en,reddit_*)`) and **§6(b) expectation** (`rho(full,half) >= ~0.9`) are *reported regardless of direction*, not gates — captured as INTEGRATION sanity notes (Tasks 11, 12), not as test assertions (they depend on real data and must not be asserted, since asserting them would convert a descriptive diagnostic into a tuning target — anti-tuning). This is intentional, not a gap.
2. **§9 risk-4 "re-confirmation re-rolls every gate (V1/V2/V3)"** requires no new code — `external_validation`/`evaluate_patterns` in `compute_oaq.py` already run on the new component automatically. No task builds it because nothing new is needed; the Task 14 end-to-end run exercises it. Flagging so the caller knows it is deliberately not a separate task.
3. **`per_edition_json` ASCII encoding** (`ensure_ascii=True`) is a defensive choice for the cp1252 console / CSV (spec does not specify encoding); article *titles* are still stored verbatim/UTF-8 in the daily file via `atomic_write_csv` (utf-8). Noted in case the caller wants UTF-8 JSON instead.
