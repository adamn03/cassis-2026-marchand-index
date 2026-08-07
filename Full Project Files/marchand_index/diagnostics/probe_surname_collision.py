"""DIAGNOSTIC (2026-07-31) — surname vs pool first-name collisions.

13 pool surnames are also another pool player's FIRST name. For each, reports
what share of token hits ALSO name the player whose first name it is — strong
evidence (not proof) that the mention refers to the other player.

Result 2026-07-31: cole 77%, connor 67%, quinn 64%, colton 63%, shea 53%,
beck 50%, frank 46%, reilly 38%, thomas 34%, james 35%, blake 27%, paul 14%,
joshua 5%. Only connor/james/paul were guarded; the rest contaminate live CES.

Run from inside marchand_index/:  python diagnostics/probe_surname_collision.py
"""
import json, glob, re, unicodedata
import pandas as pd
def fold(s):
    s=unicodedata.normalize("NFKD",str(s)); return "".join(c for c in s if not unicodedata.combining(c)).casefold()
NON=re.compile(r"[^a-z0-9]+")
def toks(t,b): return set(NON.sub(" ",fold(f"{t} {b}")).strip().split())
players=pd.read_csv("players.csv")
first={}; 
for r in players.itertuples(index=False):
    p=str(r.full_name).split(); first.setdefault(fold(p[0]),[]).append(str(r.full_name))
sur={}
for r in players.itertuples(index=False):
    sur.setdefault(fold(str(r.full_name).split()[-1]),[]).append(str(r.full_name))
# surnames that are ALSO another pool player's first name, and not shared
risk={s:(sur[s][0],first[s]) for s in sur if len(sur[s])==1 and s in first}
print(f"surnames colliding with another pool player's FIRST name: {len(risk)}")
W0,W1=pd.Timestamp("2025-04-18"),pd.Timestamp("2026-04-17")
watch={s:{"total":0,"withother":0} for s in risk}
for f in sorted(glob.glob("cache/reddit_corpus/*.jsonl")):
    for line in open(f,encoding="utf-8"):
        try: rec=json.loads(line)
        except: continue
        ts=pd.Timestamp(int(rec["created_utc"]),unit="s")
        if not (W0<=ts<=W1): continue
        tk=toks(rec.get("title") or "",rec.get("selftext") or "")
        for s in tk & set(watch):
            watch[s]["total"]+=1
            # does the post also name a player whose FIRST name is s?
            others=[n for n in first[s] if fold(n.split()[-1]) in tk]
            if others: watch[s]["withother"]+=1
rows=[]
for s,d in watch.items():
    if d["total"]>=100:
        rows.append((s,risk[s][0],d["total"],d["withother"],d["withother"]/d["total"]))
rows.sort(key=lambda r:-r[3])
print(f"\n{'token':<12}{'attributed to':<22}{'hits':>7}{'ALSO names a':>14}{'contam':>9}")
print(f"{'':12}{'':22}{'':7}{'first-name player':>14}")
for s,who,t,w,p in rows[:15]:
    print(f"{s:<12}{who:<22}{t:>7}{w:>14}{p:>8.0%}")
