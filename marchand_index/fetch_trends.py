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
   pytrends `suggestions()`, not the raw name string — "Will Smith" must
   measure the Sharks forward, not the actor.

A47 (2026-08-01) — the string fallback is RETIRED and a position tie-break is
added. The A16 fallback published a raw-name query whenever no suggestion
qualified OR the call was throttled, and 429s dominate this fetcher's logs. It
put "Will Smith" at rank 1/771 on 9.66x the anchor (the actor) and left
Ovechkin, Brayden Point and Parayko undercounted on string queries. Taking the
FIRST qualifying suggestion also gave the Canucks' two Elias Petterssons one
shared MID and an identical `trends_12mo`.

  - >1 qualifying suggestion -> disambiguate on the player's position
    (`trends_method=topic_position`); an unbroken tie refuses.
  - a refusal writes a NULL `trends_12mo` and stores NO query string
    (`no_hockey_topic` | `ambiguous_topic` | `resolve_failed`).
  - only `no_hockey_topic` is an A25 `no_entity_exists` (raw-0 imputation);
    the other two are `fetch_failed` and renormalize — a 429 is not evidence
    of zero search interest.

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
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (RAW_DIR, WINDOW_END_DATE, WINDOW_START_DATE,  # noqa: E402
                     atomic_write_csv, load_csv, load_players)

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

# A11 fixed window, sourced from _common (A51: start moved back to the 2023-24
# opener, end unchanged). Still FIXED, not run-time anchored. 921 days keeps
# Google Trends on WEEKLY resolution (it switches to monthly only past 5y), so
# `trends_12mo` stays a mean-of-weekly ratio and remains scale-comparable with
# the 365-day values — the ratio to the fixed anchor is unit-free.
TIMEFRAME = f"{WINDOW_START_DATE.isoformat()} {WINDOW_END_DATE.isoformat()}"
ANCHOR_NAME = "Brad Marchand"         # A16 fixed anchor
# A44: anchor MID pinned (verified live 2026-07-22; Google renamed entity
# types to "<Team> <position>" — e.g. "Florida Panthers center" — breaking the
# A16 "hockey"-substring test, so the anchor is never run-time resolved again).
ANCHOR_MID = "/m/027h_8t"
# A35 clause 1: the anchor player's OWN row is anchor/anchor ≡ 1.0
# (degenerate). His row alone is re-measured against this pre-declared
# secondary anchor and chained back onto the common scale.
SECONDARY_ANCHOR_NAME = "Sidney Crosby"
SECONDARY_ANCHOR_POSITION = "C"
SLEEP = 3.0
FIELDS = [
    "player_id", "full_name", "query", "query_mid", "trends_method",
    "trends_12mo", "player_mean_scaled", "anchor_mean_scaled", "n_weeks",
    "fetch_date",
]
OUT_PATH = RAW_DIR / "trends.csv"


def _franchise_names() -> list[str]:
    """Folded NHL franchise names from raw/teams.csv (A44 rule 2)."""
    return [t["team_slug"].replace("-", " ").casefold()
            for t in load_csv(RAW_DIR / "teams.csv")]


def _strip_punct(s: str) -> str:
    """Fold to accent-free, punctuation-free, single-spaced lowercase.

    A47: the A44 franchise test compared a raw casefold of Google's type
    against slugs from teams.csv, so "St. Louis Blues defenseman" failed to
    match "st louis blues" on the period alone — Parayko, Holloway and Suter
    were all refused as `no_hockey_topic`, which A25 imputes as raw 0.
    """
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = "".join(c if c.isalnum() else " " for c in s.casefold())
    return " ".join(s.split())


def _type_qualifies(type_str: str, franchises: list[str]) -> bool:
    """A44 rule 2: 'hockey' in type, or any NHL franchise name in type
    (Google renamed player entity types to '<Team> <position>'). Both sides
    are punctuation- and accent-folded (A47)."""
    t = _strip_punct(type_str)
    return "hockey" in t or any(_strip_punct(f) in t for f in franchises if f)


# A47: players.csv position code -> substrings Google uses in the entity type
# ("<Team> <position>"). Two-word wing forms also cover "left winger" /
# "right winger"; "defense"/"defence" also cover "defenseman"/"defenceman".
POSITION_WORDS = {
    "C": ("center", "centre"),
    "L": ("left wing",),
    "R": ("right wing",),
    "D": ("defense", "defence"),
}
# Methods that represent a real, entity-resolved measurement.
RESOLUTION_METHODS = ("topic", "topic_position", "topic_secondary_anchor")
# A47: refusals. The pre-A47 "string" method is retired — a raw-name query
# measured whoever else owns the name (Will Smith = the actor, 9.66x anchor).
REFUSAL_REASONS = ("no_hockey_topic", "ambiguous_topic", "resolve_failed")


def select_topic_mid(suggestions: list[dict], franchises: list[str],
                     position: str) -> tuple[str, str]:
    """A47: pick one Google topic MID from pytrends suggestions.

    Returns (mid, reason). A refusal returns ("", <REFUSAL_REASONS member>) —
    never a raw name string.

      0 qualifying suggestions      -> ("", "no_hockey_topic")
      1 qualifying suggestion       -> (mid, "topic")
      >1, exactly one matches the
        player's position           -> (mid, "topic_position")
      >1, tie unbroken              -> ("", "ambiguous_topic")

    The position tie-break exists because two pooled players can share a full
    name (the Canucks' Elias Pettersson C and D), and taking the first
    qualifying suggestion gave both the center's MID and therefore an
    identical trends_12mo.
    """
    qualifying = [s for s in suggestions
                  if _type_qualifies(str(s.get("type", "")), franchises)]
    if not qualifying:
        return "", "no_hockey_topic"
    if len(qualifying) == 1:
        return qualifying[0].get("mid", "") or "", "topic"
    words = POSITION_WORDS.get(str(position).strip().upper(), ())
    matches = [s for s in qualifying
               if any(w in _strip_punct(s.get("type", "")) for w in words)]
    if len(matches) == 1:
        return matches[0].get("mid", "") or "", "topic_position"
    return "", "ambiguous_topic"


def resolve_topic_mid(pytrends: TrendReq, name: str,
                      position: str) -> tuple[str, str]:
    """A47: resolve `name` to a topic MID. Returns (mid, reason).

    A failed/throttled suggestions() call reports "resolve_failed", NOT
    "no_hockey_topic": 429s dominate this fetcher's logs, and A25 gives the two
    opposite null treatments (weight renormalization vs. raw-0 imputation).
    """
    try:
        suggestions = pytrends.suggestions(name)
    except Exception as e:
        print(f"  suggestions({name!r}) failed: {e!r}", file=sys.stderr)
        return "", "resolve_failed"
    return select_topic_mid(suggestions, _franchise_names(), position)


def build_row(pid: str, name: str, mid: str, reason: str,
              p_mean: float | None, a_mean: float | None, n_weeks: int,
              fetch_date: str) -> dict:
    """One trends.csv row. A47: an unresolved entity yields a NULL value and
    stores no searchable query string, so no downstream step can mistake a
    namesake's search volume for the player's."""
    if reason in REFUSAL_REASONS:
        ratio = None
        query = ""
        mid = ""
    else:
        ratio = ratio_from_means(p_mean, a_mean)
        query = name
    return {
        "player_id": pid,
        "full_name": name,
        "query": query,
        "query_mid": mid,
        "trends_method": reason,
        "trends_12mo": "" if ratio is None else f"{ratio:.6f}",
        "player_mean_scaled": "" if p_mean is None else f"{p_mean:.4f}",
        "anchor_mean_scaled": "" if a_mean is None else f"{a_mean:.4f}",
        "n_weeks": n_weeks,
        "fetch_date": fetch_date,
    }


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


def resume_rows_from(rows: list[dict]) -> dict[str, dict]:
    """player_id -> row, kept only if it is a non-null, entity-resolved
    measurement. A47: pre-A47 `trends_method=string` rows carry a non-null
    value, so without the method test the re-run would skip exactly the
    contaminated players it exists to replace."""
    shared_mids = {m for m in
                   (str(r.get("query_mid", "")).strip() for r in rows) if m
                   and sum(1 for q in rows
                           if str(q.get("query_mid", "")).strip() == m) > 1}
    out = {}
    for r in rows:
        if str(r.get("trends_12mo", "")).strip() == "":
            continue
        if str(r.get("trends_method", "")).strip() not in RESOLUTION_METHODS:
            continue
        if str(r.get("query_mid", "")).strip() in shared_mids:
            # Two players on one MID: one entity's volume credited to both.
            continue
        out[r["player_id"]] = r
    return out


def load_resume_rows() -> dict[str, dict]:
    if not OUT_PATH.exists():
        return {}
    return resume_rows_from(load_csv(OUT_PATH))


def a35_marchand_row_mode() -> None:
    """`--a35-marchand-row`: live secondary-anchor re-measure of the anchor
    player's row only (A35 clause 1); rewrites trends.csv in place."""
    pytrends = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=1.5,
                        timeout=(10, 30))
    sec_mid, sec_reason = resolve_topic_mid(pytrends, SECONDARY_ANCHOR_NAME,
                                            SECONDARY_ANCHOR_POSITION)
    if not sec_mid:
        # A47: a raw-string secondary anchor would put the whole chained scale
        # on whoever else owns the name. Abort instead.
        print(f"REFUSED: secondary anchor {SECONDARY_ANCHOR_NAME!r} did not "
              f"resolve ({sec_reason}); anchor row left unchanged.",
              file=sys.stderr)
        return
    sec_kw = sec_mid
    print(f"A35 secondary anchor: {SECONDARY_ANCHOR_NAME!r} -> topic {sec_mid}")
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

    # A44 rule 1: the anchor MID is pinned — never run-time resolved.
    anchor_mid = ANCHOR_MID
    anchor_kw = anchor_mid
    print(f"A16/A44 anchor: {ANCHOR_NAME!r} -> pinned topic {anchor_mid}")

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
        mid, reason = resolve_topic_mid(pytrends, name, p.get("position", ""))
        time.sleep(SLEEP)
        p_mean = a_mean = None
        n_weeks = 0
        if mid:
            # A47: only an entity-resolved player is ever measured. A refusal
            # is written as a NULL row and never queried as a raw name.
            try:
                p_mean, a_mean, n_weeks = fetch_pair(pytrends, anchor_kw, mid)
            except Exception as e:
                print(f"{name}: FAILED {e!r}", file=sys.stderr)
                p_mean, a_mean, n_weeks = None, None, 0
        row = build_row(pid, name, mid, reason, p_mean, a_mean, n_weeks,
                        fetch_date)
        print(f"{name:<24} method={row['trends_method']} "
              f"ratio={row['trends_12mo'] or None} "
              f"(player={p_mean}, anchor={a_mean}, n={n_weeks})")
        rows_by_pid[pid] = row
        # Snapshot after every player so a kill / 429 never loses progress.
        rows = [rows_by_pid[q] for q in order if q in rows_by_pid]
        atomic_write_csv(OUT_PATH, rows, FIELDS)
        time.sleep(SLEEP)

    rows = [rows_by_pid[q] for q in order if q in rows_by_pid]
    atomic_write_csv(OUT_PATH, rows, FIELDS)
    n_ok = sum(1 for r in rows if str(r["trends_12mo"]).strip() != "")
    n_topic = sum(1 for r in rows
                  if r.get("trends_method") in RESOLUTION_METHODS)
    print(f"\nWrote {OUT_PATH} ({len(rows)} rows, {n_ok} non-null, "
          f"{n_topic} topic-resolved)")
    for reason in REFUSAL_REASONS:
        n = sum(1 for r in rows if r.get("trends_method") == reason)
        if n:
            print(f"A47 refusal {reason}: {n}")
    print(f"A35 zero-quantization count (trends_12mo == 0): "
          f"{zero_quant_count(rows)}")


if __name__ == "__main__":
    main()
