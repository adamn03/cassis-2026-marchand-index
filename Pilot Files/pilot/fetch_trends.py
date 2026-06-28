"""Fetch 12-month Google Trends mean interest for each pilot player.

Per pre-registration section 3.2 (composite weight 0.139). Query string =
"<First name> <Last name>". Worldwide, no geo restriction.

pytrends returns weekly interest values (0-100) over a 12-month window.
We take the unweighted mean across all weeks.

Writes: pilot/raw/trends.csv with columns
  player_id, full_name, query, trends_12mo, n_weeks, fetch_date
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import RAW_DIR, atomic_write_csv, load_players  # noqa: E402

from pytrends.request import TrendReq  # noqa: E402


def main() -> None:
    fetch_date = dt.date.today().isoformat()
    pytrends = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=1.5, timeout=(10, 30))

    rows = []
    players = load_players()
    for p in players:
        query = p["full_name"]
        try:
            pytrends.build_payload([query], cat=0, timeframe="today 12-m", geo="")
            df = pytrends.interest_over_time()
            if df.empty or query not in df.columns:
                mean_val = None
                n_weeks = 0
            else:
                series = df[query].dropna()
                mean_val = float(series.mean())
                n_weeks = int(len(series))
            print(f"{p['full_name']:<22} mean={mean_val}  n={n_weeks}")
        except Exception as e:
            print(f"{p['full_name']}: FAILED {e!r}", file=sys.stderr)
            mean_val = None
            n_weeks = 0

        rows.append({
            "player_id": p["player_id"],
            "full_name": p["full_name"],
            "query": query,
            "trends_12mo": "" if mean_val is None else f"{mean_val:.4f}",
            "n_weeks": n_weeks,
            "fetch_date": fetch_date,
        })
        # pytrends throttles aggressively; pause between calls.
        time.sleep(2.0)

    out = RAW_DIR / "trends.csv"
    atomic_write_csv(out, rows, [
        "player_id", "full_name", "query", "trends_12mo", "n_weeks", "fetch_date",
    ])
    print(f"\nWrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
