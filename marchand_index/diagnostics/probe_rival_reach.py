"""DIAGNOSTIC (2026-07-31) — upper bound on rival-subreddit attention.

Counts own/rival/neutral mentions for pool-unique, guard-clean surnames only.
Deliberately does NOT apply the A42/A43 guards, so the rival figure is a
CEILING, not a measurement. Cross-check: reddit_counts.reddit_mentions_allsubs
implies ~53-58k rival mentions with guards applied.

Result 2026-07-31: own 85,103 / RIVAL 59,777 / neutral 69,497.
median rival_reach = 20 subreddits (vs max 3 in the A22-scoped data).

Run from inside marchand_index/:  python diagnostics/probe_rival_reach.py
"""
import json, glob, re, sys, unicodedata
from pathlib import Path
import pandas as pd
sys.path.insert(0, ".")
import affiliation as aff
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
import _common as _C  # noqa: E402

def fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.casefold()
NON = re.compile(r"[^a-z0-9]+")
def toks(t, b): return set(NON.sub(" ", fold(f"{t} {b}")).strip().split())

players = pd.read_csv("players.csv")
market  = pd.read_csv("market_proxy.csv")
movers  = pd.read_csv("mover_dates.csv")
vmap = aff.build_venue_map(market)
tl   = aff.build_move_timeline(movers)
endteam = dict(zip(players.player_id.astype(int), players.team_code.astype(str)))

# surname -> list of pids
sur = {}
for r in players.itertuples(index=False):
    sur.setdefault(fold(str(r.full_name).split()[-1]), []).append(int(r.player_id))
uniq = {s: p[0] for s, p in sur.items() if len(p) == 1}
shared = {s for s, p in sur.items() if len(p) > 1}
print(f"pool surnames: {len(sur)}  unique: {len(uniq)}  shared: {len(shared)}")

en1000 = set(Path("english_top1000.txt").read_text(encoding="utf-8").split())
common = {s for s in uniq if s in en1000}
print(f"unique surnames that are common English words (guard risk): {len(common)}")

W0, W1 = pd.Timestamp(_C.WINDOW_START_DATE), pd.Timestamp(_C.WINDOW_END_DATE)  # A51
allsur = set(sur)
own = other = neutral = 0
per_player_other = {}
rival_subs_seen = {}
for f in sorted(glob.glob("cache/reddit_corpus/*.jsonl")):
    for line in open(f, encoding="utf-8"):
        try: rec = json.loads(line)
        except: continue
        ts = pd.Timestamp(int(rec["created_utc"]), unit="s")
        if not (W0 <= ts <= W1): continue
        hits = toks(rec.get("title") or "", rec.get("selftext") or "") & allsur
        if not hits: continue
        sub = rec["subreddit"]
        owner = aff.venue_team(sub, vmap)
        for h in hits:
            if h not in uniq or h in common: continue
            pid = uniq[h]
            if owner is None:
                neutral += 1
            else:
                pt = aff.team_at(pid, ts, endteam.get(pid, ""), tl)
                if owner == pt: own += 1
                else:
                    other += 1
                    per_player_other[pid] = per_player_other.get(pid, 0) + 1
                    rival_subs_seen.setdefault(pid, set()).add(sub)

tot = own + other + neutral
print(f"\nUNIQUE-SURNAME, guard-clean players only ({len(uniq)-len(common)} players):")
print(f"  own     {own:>8,}  ({own/tot:.1%})")
print(f"  RIVAL   {other:>8,}  ({other/tot:.1%})")
print(f"  neutral {neutral:>8,}  ({neutral/tot:.1%})")
print(f"\nplayers with >=1 rival mention: {len(per_player_other)}")
reach = pd.Series({p: len(s) for p, s in rival_subs_seen.items()})
print(f"rival_reach: median {reach.median():.0f}  mean {reach.mean():.1f}  max {reach.max()}")
name = dict(zip(players.player_id.astype(int), players.full_name))
top = sorted(per_player_other.items(), key=lambda kv: -kv[1])[:12]
print("\ntop rival-attention players:")
for pid, n in top:
    print(f"  {name[pid]:<24} rival={n:<6} reach={len(rival_subs_seen[pid])}")
