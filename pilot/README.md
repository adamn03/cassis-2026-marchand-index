# Pilot — The Marchand Index (CASSIS 2026 abstract)

Worked-example pilot of the Off-Ice Attention Quotient (OAQ) and Marchand Index on N=14 NHLers. Produces ONE figure and ONE CSV for §4 of the CASSIS abstract.

**This is illustrative, not validation.** Full leaguewide K=10 results are post-submission.

## Method is pre-registered

See `preregistration.md` — committed at git `9774a68` (2026-05-20), **before any fetch code exists**. Player list, composite weights, market-baseline formula, figure spec, and the three falsifiable expected patterns are locked there. No silent edits.

## Setup (one-time, ~5 min owner effort)

```powershell
cd "C:\Local Only\Ai projects\Sports Analytics Conference Projeccts\pilot"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Register a Reddit script app at https://www.reddit.com/prefs/apps (5 min), then:

```powershell
copy .env.example .env
# Edit .env and paste your client_id / client_secret / user_agent
```

No other credentials needed. Wikipedia, Google Trends, NHL API, Instagram, and PuckPedia are unauthenticated.

## Run (after fetch scripts are implemented)

```powershell
python fetch_wikipedia.py        # 12-mo daily pageviews per player
python fetch_trends.py           # Google Trends 12-mo mean
python fetch_reddit.py           # mention + upvote counts
python fetch_instagram.py        # public follower counts (resolves IG handles)
python fetch_nhl_api.py          # PPG, TOI/G, GP, position, age + team rosters
python fetch_cap_hits.py         # cap hits via PuckPedia/CapWages WebFetch
python compute_oaq.py            # joins all CSVs → oaq_pilot.csv
python render_figure.py          # produces figure.png
```

Atomic writes (`.tmp` → rename) per vault convention. Output goes under `pilot/raw/` (raw fetches) and `pilot/` (derived tables + figure).

## Files

| File | Purpose |
|---|---|
| `preregistration.md` | Locked method, weights, expected patterns, fallback rule |
| `players.csv` | 14-player roster: names, Wikipedia slugs, IG handles (auto-resolved), team codes, subreddit names |
| `requirements.txt` | Python deps |
| `.env.example` | Reddit credentials template |
| `fetch_*.py` | Per-source data fetchers (atomic writes) |
| `compute_oaq.py` | Pipeline: raw → oaq_pilot.csv |
| `render_figure.py` | Pipeline: oaq_pilot.csv → figure.png |
| `raw/*.csv` | Fetched raw data (committed for reproducibility) |
| `oaq_pilot.csv` | Final per-player table with engagement_raw, OAQ_observed, OAQ_portable, marchand_index, bootstrap CIs |
| `figure.png` | Final figure (real or schematic per §11 of preregistration.md) |
| `results.md` | Observed-vs-expected narrative (regardless of direction) |

## What this pilot is NOT

- LLM theme classification (Wk 4-5 of full build, post-submission)
- Three full validations (jersey list ρ, All-Star ρ, FA event study — Wk 7-8)
- H1-H4 hypothesis tests (Wk 8)
- Goalies
- The full ~700-NHLer leaguewide K=10 result
