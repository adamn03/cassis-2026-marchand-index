"""Unit tests for fetch_wikipedia_intl pure logic (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import fetch_wikipedia_intl as fwi  # noqa: E402


def test_whitelist_is_locked_seven_editions():
    assert fwi.WHITELIST == ("sv", "fi", "cs", "ru", "de", "sk", "fr")


def test_collection_window_is_the_widened_a51_interval():
    """A51/A52 widened COLLECTION to 2023-10-10 so the three-season panel comes
    from one pass. The composite is still the A11 365-day window -- it is sliced
    back out of the daily vectors by repair_window_a11.py, not re-fetched."""
    assert fwi.WINDOW_START == "20231010"
    assert fwi.WINDOW_END == "20260417"


def test_window_strings_returns_fixed_window_and_today_fetch_date():
    import datetime as dt
    start, end, fetch_date = fwi.window_strings()
    assert (start, end) == ("20231010", "20260417")
    assert fetch_date == dt.date.today().isoformat()


def test_a11_window_is_still_recoverable_from_the_widened_collection():
    """The composite's locked window must remain a suffix of what is collected,
    or V-A11-Window's repair could not slice it back out."""
    import _common as c
    assert c.LEGACY_WINDOW_START_DATE > c.WINDOW_START_DATE
    assert (c.WINDOW_END_DATE - c.LEGACY_WINDOW_START_DATE).days + 1 == 365


# --- Task 2: sitelink whitelist filtering ---

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


# --- Task 3: per-edition fetch URL + daily/total parsing ---

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


# --- fetch_edition_safe: classify ok / absent (404) / error (transient) ---

def test_fetch_edition_safe_ok(monkeypatch):
    monkeypatch.setattr(fwi.time, "sleep", lambda *_: None)
    s = _Session(_Resp(200, {"items": [{"views": 3}, {"views": 5}]}))
    status, payload = fwi.fetch_edition_safe(s, "sv", "X", "20250418", "20260417")
    assert status == "ok"
    assert payload == (8, [3, 5])


def test_fetch_edition_safe_absent_on_404(monkeypatch):
    monkeypatch.setattr(fwi.time, "sleep", lambda *_: None)
    s = _Session(_Resp(404))
    status, payload = fwi.fetch_edition_safe(s, "fi", "X", "20250418", "20260417")
    assert status == "absent" and payload is None


def test_fetch_edition_safe_error_on_transient(monkeypatch):
    """A 5xx (not 404) is a transient error, NOT an absent article."""
    monkeypatch.setattr(fwi.time, "sleep", lambda *_: None)
    s = _Session(_Resp(503))
    status, payload = fwi.fetch_edition_safe(s, "de", "X", "20250418", "20260417")
    assert status == "error" and payload is None


# --- Task 4: per-player aggregation (fetch_fn -> (status, payload)) ---

def test_aggregate_player_sums_fetched_editions():
    sitelinks = {"cs": "P", "sv": "P", "ru": "P"}
    results = {  # ru is a genuine 404 (absent), cleanly skipped
        "cs": ("ok", (100, [50, 50])),
        "sv": ("ok", (40, [40])),
        "ru": ("absent", None),
    }

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
    agg = fwi.aggregate_player({}, lambda e, t: ("ok", (1, [1])))
    assert agg["wiki_intl_12mo"] is None
    assert agg["editions_available"] == ""
    assert agg["editions_fetched"] == ""
    assert agg["intl_match"] == "none"


def test_aggregate_player_none_when_all_editions_404():
    agg = fwi.aggregate_player({"de": "P", "fr": "P"}, lambda e, t: ("absent", None))
    assert agg["wiki_intl_12mo"] is None
    assert agg["editions_available"] == "de|fr"
    assert agg["editions_fetched"] == ""
    assert agg["intl_match"] == "none"


def test_aggregate_player_partial_flags_transient_error():
    """One edition fetched, one transient error -> intl_match=partial (the
    error is NOT silently summed away like a 404)."""
    results = {"cs": ("ok", (100, [100])), "de": ("error", None)}
    agg = fwi.aggregate_player({"cs": "P", "de": "P"},
                               lambda e, t: results[e])
    assert agg["wiki_intl_12mo"] == 100
    assert agg["editions_fetched"] == "cs"
    assert agg["intl_match"] == "partial"


def test_aggregate_player_error_when_all_editions_transient():
    """0 fetched but a transient error occurred -> intl_match=error, NOT none
    (the value is lost to flakiness, not a genuine anglophone-only player)."""
    agg = fwi.aggregate_player({"de": "P", "fr": "P"}, lambda e, t: ("error", None))
    assert agg["wiki_intl_12mo"] is None
    assert agg["editions_fetched"] == ""
    assert agg["intl_match"] == "error"


# --- Task 5: row builders ---

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


# --- Task 6: QID loader ---

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
