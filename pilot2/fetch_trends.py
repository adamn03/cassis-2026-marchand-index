"""Fetch 12-month Google Trends mean interest for the 160-skater set (pre-reg §3.2).

Composite weight 0.139. Query = "<First> <Last>", worldwide. pytrends returns
weekly interest (0-100) over a 12-month window; we take the unweighted mean.

pytrends throttles hard; at 160 players a 429 mid-run is likely. Any player
that fails (empty frame / rate-limit) is written NULL and handled by the
sentinel renorm (§4); re-running resumes from cache for the ones that succeeded.

Writes: pilot2/raw/trends.csv
  player_id, full_name, query, trends_12mo, n_weeks, fetch_date
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_players  # noqa: E402

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


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    pytrends = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=1.5, timeout=(10, 30))

    rows = []
    for p in load_players():
        query = p["full_name"]
        try:
            # A11: FIXED reg-season-end window (2025-04-18 .. 2026-04-17), NOT run-time
            # anchored ("today 12-m"), to match the Reddit/Wikipedia window and avoid the
            # 2026-playoff confound (attention matched against regular-season production).
            pytrends.build_payload([query], cat=0, timeframe="2025-04-18 2026-04-17", geo="")
            df = pytrends.interest_over_time()
            if df.empty or query not in df.columns:
                mean_val, n_weeks = None, 0
            else:
                series = df[query].dropna()
                mean_val, n_weeks = float(series.mean()), int(len(series))
            print(f"{p['full_name']:<24} mean={mean_val}  n={n_weeks}")
        except Exception as e:
            print(f"{p['full_name']}: FAILED {e!r}", file=sys.stderr)
            mean_val, n_weeks = None, 0
        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "query": query,
            "trends_12mo": "" if mean_val is None else f"{mean_val:.4f}",
            "n_weeks": n_weeks,
            "fetch_date": fetch_date,
        })
        time.sleep(2.0)

    out = RAW_DIR / "trends.csv"
    atomic_write_csv(out, rows, [
        "player_id", "full_name", "query", "trends_12mo", "n_weeks", "fetch_date",
    ])
    n_ok = sum(1 for r in rows if r["trends_12mo"] != "")
    print(f"\nWrote {out} ({len(rows)} rows, {n_ok} non-null)")


if __name__ == "__main__":
    main()
