"""Fetch 12-month Google Trends interest for the locked pool (pre-reg §3.2,
window A11, method A16).

A16 (2026-07-03) — two measurement fixes over the original single-term fetch:

1. **Cross-player comparability.** A single-term Trends series is normalized
   to its OWN peak = 100, so its mean is a within-player shape statistic, not
   relative volume. Every fetch is now a TWO-TERM payload [ANCHOR, player];
   Google scales the pair jointly, and the stored quantity is the ratio
   `trends_12mo = mean(player) / mean(anchor)`, comparable across players.
   Anchor fixed in advance (A16): the topic entity for "Brad Marchand"
   (mid-magnitude, hockey-native — preserves resolution at both tail ends).
2. **Entity resolution.** The query is the Google Trends topic MID from
   pytrends `suggestions()` (first suggestion whose type contains "hockey"),
   not the raw name string — "Will Smith" must measure the Sharks forward,
   not the actor. No hockey topic -> raw-string fallback, flagged
   `trends_method=string` for a disclosed sensitivity cut.

Window (pre-reg A11): FIXED [2025-04-18, 2026-04-17], NOT run-time anchored.

pytrends throttles hard; the run RESUMES: rows already on disk with a
non-null trends_12mo are kept, only missing/null players are re-tried, and
the CSV is snapshot-written after every player.

Writes: marchand_index/raw/trends.csv
  player_id, full_name, query, query_mid, trends_method, trends_12mo,
  player_mean_scaled, anchor_mean_scaled, n_weeks, fetch_date
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_csv, load_players  # noqa: E402

# pytrends passes Retry(method_whitelist=...); urllib3>=2.0 renamed that kwarg
# to allowed_methods. Shim the alias so TrendReq builds under urllib3 2.6.x.
import urllib3.util.retry as _retry  # noqa: E402

_orig_retry_init = _retry.Retry.__init__


def _retry_init(self, *args, **kwargs):  # noqa: ANN001
    if "method_whitelist" in kwargs:
        kwargs["allowed_methods"] = kwargs.pop("method_whitelist")
    _orig_retry_init(self, *args, **kwargs)


_retry.Retry.__init__ = _retry_init

from pytrends.request import TrendReq  # noqa: E402

TIMEFRAME = "2025-04-18 2026-04-17"   # A11 fixed window
ANCHOR_NAME = "Brad Marchand"         # A16 fixed anchor (topic resolved at run)
# A35 clause 1: the anchor player's OWN row is anchor/anchor ≡ 1.0
# (degenerate). His row alone is re-measured against this pre-declared
# secondary anchor and chained back onto the common scale.
SECONDARY_ANCHOR_NAME = "Sidney Crosby"
SLEEP = 3.0
FIELDS = [
    "player_id", "full_name", "query", "query_mid", "trends_method",
    "trends_12mo", "player_mean_scaled", "anchor_mean_scaled", "n_weeks",
    "fetch_date",
]
OUT_PATH = RAW_DIR / "trends.csv"


def resolve_topic_mid(pytrends: TrendReq, name: str) -> str:
    """First pytrends suggestion whose type mentions hockey -> its MID, else ''."""
    try:
        for s in pytrends.suggestions(name):
            if "hockey" in str(s.get("type", "")).casefold():
                return s.get("mid", "") or ""
    except Exception as e:
        print(f"  suggestions({name!r}) failed: {e!r}", file=sys.stderr)
    return ""


def ratio_from_means(player_mean: float | None,
                     anchor_mean: float | None) -> float | None:
    """A16 comparable quantity: mean(player)/mean(anchor) on the joint scale.

    None when either side is missing; None (retry-worthy) when the anchor
    scaled to 0 in this batch (throttle artifact — the anchor is mid-tier by
    construction, a true-zero anchor batch is not a valid scale).
    """
    if player_mean is None or anchor_mean is None:
        return None
    if anchor_mean <= 0:
        return None
    return player_mean / anchor_mean


def fetch_pair(pytrends: TrendReq, anchor_kw: str, player_kw: str):
    """One two-term payload. Returns (player_mean, anchor_mean, n_weeks)."""
    pytrends.build_payload([anchor_kw, player_kw], cat=0,
                           timeframe=TIMEFRAME, geo="")
    df = pytrends.interest_over_time()
    if df.empty:
        return None, None, 0
    a = df[anchor_kw].dropna() if anchor_kw in df.columns else None
    p = df[player_kw].dropna() if player_kw in df.columns else None
    a_mean = float(a.mean()) if a is not None and len(a) else None
    if p is not None and len(p):
        p_mean = float(p.mean())
        n_weeks = int(len(p))
    elif a_mean is not None and a_mean > 0:
        # Anchor scaled fine but the player column is absent: interest below
        # Trends' reporting threshold on the joint scale -> a true 0.
        p_mean = 0.0
        n_weeks = int(len(a))
    else:
        p_mean = None
        n_weeks = 0
    return p_mean, a_mean, n_weeks


def _fold(s: str) -> str:
    return " ".join(str(s).casefold().split())


def chain_secondary_ratio(m_over_c: float | None,
                          crosby_ratio: float | None) -> float | None:
    """A35 clause 1: put the anchor player's row on the common
    (Marchand-anchor) scale: (M/C measured) × (C/M already stored from the
    standard fetch). Both factors are real measurements, so the product is
    an empirical estimate rather than the degenerate identical 1.0."""
    if m_over_c is None or crosby_ratio is None:
        return None
    if not crosby_ratio > 0:
        return None
    return m_over_c * crosby_ratio


def a35_remeasure_anchor_row(rows_by_pid: dict[str, dict], pair_fetch,
                             secondary_kw: str) -> bool:
    """Re-measure ONLY the anchor player's row against the secondary anchor
    (A35 clause 1). `pair_fetch(anchor_kw, player_kw)` returns
    (player_mean, anchor_mean, n_weeks). Returns True when the row was
    updated; refuses (False) when the anchor or Crosby row is absent or the
    chain factor is unusable — the degenerate value is then left in place
    and the caller should warn, never invent."""
    anchor_row = crosby_row = None
    for r in rows_by_pid.values():
        if _fold(r.get("full_name")) == _fold(ANCHOR_NAME):
            anchor_row = r
        elif _fold(r.get("full_name")) == _fold(SECONDARY_ANCHOR_NAME):
            crosby_row = r
    if anchor_row is None or crosby_row is None:
        return False
    try:
        crosby_ratio = float(crosby_row.get("trends_12mo", ""))
    except (TypeError, ValueError):
        return False
    player_kw = anchor_row.get("query_mid") or anchor_row.get("query") \
        or ANCHOR_NAME
    p_mean, a_mean, n_weeks = pair_fetch(secondary_kw, player_kw)
    ratio_mc = ratio_from_means(p_mean, a_mean)
    chained = chain_secondary_ratio(ratio_mc, crosby_ratio)
    if chained is None:
        return False
    anchor_row["trends_12mo"] = f"{chained:.6f}"
    anchor_row["trends_method"] = "topic_secondary_anchor"
    anchor_row["player_mean_scaled"] = f"{p_mean:.4f}"
    anchor_row["anchor_mean_scaled"] = f"{a_mean:.4f}"
    anchor_row["n_weeks"] = n_weeks
    anchor_row["fetch_date"] = dt.date.today().isoformat()
    return True


def zero_quant_count(rows: list[dict]) -> int:
    """A35 clause 1 report: players whose Trends series quantizes to 0
    against the anchor on the joint scale."""
    n = 0
    for r in rows:
        try:
            if float(r.get("trends_12mo", "")) == 0.0:
                n += 1
        except (TypeError, ValueError):
            continue
    return n


def load_resume_rows() -> dict[str, dict]:
    """player_id -> existing row, kept only if trends_12mo is non-null."""
    if not OUT_PATH.exists():
        return {}
    out = {}
    for r in load_csv(OUT_PATH):
        if str(r.get("trends_12mo", "")).strip() != "":
            out[r["player_id"]] = r
    return out


def a35_marchand_row_mode() -> None:
    """`--a35-marchand-row`: live secondary-anchor re-measure of the anchor
    player's row only (A35 clause 1); rewrites trends.csv in place."""
    pytrends = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=1.5,
                        timeout=(10, 30))
    sec_mid = resolve_topic_mid(pytrends, SECONDARY_ANCHOR_NAME)
    sec_kw = sec_mid or SECONDARY_ANCHOR_NAME
    print(f"A35 secondary anchor: {SECONDARY_ANCHOR_NAME!r} -> "
          f"{'topic ' + sec_mid if sec_mid else 'STRING FALLBACK'}")
    time.sleep(SLEEP)
    rows_by_pid = {r["player_id"]: r for r in load_csv(OUT_PATH)}

    def live_pair(anchor_kw, player_kw):
        return fetch_pair(pytrends, anchor_kw, player_kw)

    if a35_remeasure_anchor_row(rows_by_pid, live_pair, sec_kw):
        order = list(rows_by_pid)
        atomic_write_csv(OUT_PATH, [rows_by_pid[q] for q in order], FIELDS)
        print("Anchor row re-measured against the secondary anchor; "
              f"{OUT_PATH} rewritten.")
    else:
        print("REFUSED: anchor/Crosby row missing or chain factor unusable; "
              "degenerate value left in place.", file=sys.stderr)


def main() -> None:
    if "--a35-marchand-row" in sys.argv:
        a35_marchand_row_mode()
        return
    fetch_date = dt.date.today().isoformat()
    pytrends = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=1.5,
                        timeout=(10, 30))

    anchor_mid = resolve_topic_mid(pytrends, ANCHOR_NAME)
    anchor_kw = anchor_mid or ANCHOR_NAME
    print(f"A16 anchor: {ANCHOR_NAME!r} -> "
          f"{'topic ' + anchor_mid if anchor_mid else 'STRING FALLBACK'}")
    time.sleep(SLEEP)

    players = load_players()
    order = [p["player_id"] for p in players]
    done = load_resume_rows()
    if done:
        print(f"Resume: {len(done)} players already non-null on disk; "
              f"{len(order) - len(done)} to fetch.")

    rows_by_pid: dict[str, dict] = dict(done)
    for p in players:
        pid = p["player_id"]
        if pid in rows_by_pid:
            continue
        name = p["full_name"]
        mid = resolve_topic_mid(pytrends, name)
        time.sleep(SLEEP)
        player_kw = mid or name
        method = "topic" if mid else "string"
        try:
            p_mean, a_mean, n_weeks = fetch_pair(pytrends, anchor_kw, player_kw)
            ratio = ratio_from_means(p_mean, a_mean)
        except Exception as e:
            print(f"{name}: FAILED {e!r}", file=sys.stderr)
            p_mean, a_mean, n_weeks, ratio = None, None, 0, None
        print(f"{name:<24} method={method} ratio={ratio} "
              f"(player={p_mean}, anchor={a_mean}, n={n_weeks})")
        rows_by_pid[pid] = {
            "player_id": pid,
            "full_name": name,
            "query": player_kw if not mid else name,
            "query_mid": mid,
            "trends_method": method,
            "trends_12mo": "" if ratio is None else f"{ratio:.6f}",
            "player_mean_scaled": "" if p_mean is None else f"{p_mean:.4f}",
            "anchor_mean_scaled": "" if a_mean is None else f"{a_mean:.4f}",
            "n_weeks": n_weeks,
            "fetch_date": fetch_date,
        }
        # Snapshot after every player so a kill / 429 never loses progress.
        rows = [rows_by_pid[q] for q in order if q in rows_by_pid]
        atomic_write_csv(OUT_PATH, rows, FIELDS)
        time.sleep(SLEEP)

    rows = [rows_by_pid[q] for q in order if q in rows_by_pid]
    atomic_write_csv(OUT_PATH, rows, FIELDS)
    n_ok = sum(1 for r in rows if str(r["trends_12mo"]).strip() != "")
    n_topic = sum(1 for r in rows if r.get("trends_method") == "topic")
    print(f"\nWrote {OUT_PATH} ({len(rows)} rows, {n_ok} non-null, "
          f"{n_topic} topic-resolved)")
    print(f"A35 zero-quantization count (trends_12mo == 0): "
          f"{zero_quant_count(rows)}")


if __name__ == "__main__":
    main()
