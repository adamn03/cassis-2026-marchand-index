# Data manifest — marchand_index

Every data file: what it is, which script writes it, and its provenance columns.
Conventions: `raw/` = fetched external data · top-level `.csv` = derived/output ·
`raw/_*.log` = run logs · all writes atomic (`.tmp` → rename) · every fetched CSV
carries `fetch_date`/`fetched_at` and, where applicable, `source_url` +
`window_start`/`window_end`. Attention window (A11): [2025-04-18, 2026-04-17].

## raw/ — fetched inputs

| File | Written by | Contents |
|---|---|---|
| `cap_hits.csv` | `fetch_cap_hits.py` | CapWages 2025-26 cap hit ($M) per pooled skater, nhlId-validated, `cap_quality`/`cap_note` flags. A24 re-fetch adds `contract_type` (rookie-flag key); pre-A24 version lacks that column. |
| `instagram_followers.csv` | `fetch_instagram.py` | IG follower counts, handle + `resolved_from` + `ig_status` per player. |
| `moneypuck_skaters_2025.csv` | `fetch_moneypuck.py` | Raw MoneyPuck skaters download cache (full upstream schema, all situations). Input only — use `nhl_onice.csv` downstream. |
| `nhl_onice.csv` | `fetch_moneypuck.py` | Derived 5v5 on-ice metrics per pooled player (cf_pct, xgf_pct, ozs_pct, TOI) + `onice_status`. |
| `nhl_skill.csv` | `fetch_nhl_api.py` | NHL API skill covariates (ppg, toi_per_game, games_played, age, position). |
| `teams.csv` | static (built once by the deleted dailyfaceoff builder — in git history) | Static 32-team map: team_code, slug, city, division. Join key for market/team files. |
| `trends.csv` | `fetch_trends.py` | Google Trends 12-mo interest per player (`query_mid`, anchor-scaled means, `trends_method`). |
| `wiki_pageviews.csv` | `fetch_wikipedia.py` (repairs: `repair_wiki_identity.py`) | en-wiki 12-mo pageview totals + slug/QID resolution (`wiki_match`). |
| `wiki_daily.csv` | `fetch_wikipedia.py` (repairs: `repair_wiki_identity.py`) | en-wiki daily view vectors (bootstrap input, A26 block resample). |
| `wiki_identity_audit.csv` | `audit_wiki_identity.py` | Slug↔player identity audit: Wikidata QID/NHL-id/birthdate cross-check, `verdict` per row. |
| `wiki_intl_pageviews.csv` | `fetch_wikipedia_intl.py` | Non-en wiki 12-mo totals per player, `per_edition_json`, `intl_match`. |
| `wiki_intl_daily.csv` | `fetch_wikipedia_intl.py` | Non-en daily view vectors per (player, edition) — bootstrap input. |
| `reddit_identity_pairs.md` | A21 identity dry-run | Non-discriminable name pairs + team-sub attribution decisions. Owner eyeball pending. |
| `reddit_counts.csv` | `fetch_reddit.py` | **NOT YET WRITTEN.** Per-player mention/upvote counts matched locally from corpus. Blocked until every amendment text is committed (texts claim "Reddit is 0/774"). |
| `_*.log` | fetch scripts | Run logs, kept for provenance (`_corpus_pull.log`, `_trends*.log`, …). |

## top-level — derived / output CSVs

| File | Written by | Contents |
|---|---|---|
| `players.csv` | `fetch_rosters_league.py` (A10 whole-league builder) → `filter_pool_played.py` | Locked player pool: ids, slugs, roster source + snapshot date. Legacy 160-set builders deleted 2026-07-15 (git history). |
| `pool_gp_audit.csv` | `filter_pool_played.py` | GP-filter audit of pool: `kept` + `drop_reason` per candidate row. |
| `oaq_pilot.csv` | `compute_oaq.py` | Pilot (pilot2) model output: engagement components, OAQ observed/portable + 95% CIs, Marchand Index lenses, quality flags. |
| `external_outcomes.csv` | `fetch_external_outcomes.py` | Validation outcomes: jersey-sales list membership/rank, ASG-2024 fan votes. Sources: `external_outcomes_sources.md`. |
| `market_proxy.csv` | `fetch_market_proxy.py` | 32-team market size components (metro pop, attendance, team social). Sources: `market_proxy_sources.md`. |
| `team_outcomes.csv` | `fetch_team_outcomes.py` | Per-team wiki 12-mo views + subreddit subscribers (PD validation). |

## cache/reddit_corpus/ — GITIGNORED local source of record

| File | Written by | Contents |
|---|---|---|
| `<subreddit>.jsonl` | `fetch_reddit_corpus.py` | Every submission in that sub inside the A11 window, from Arctic Shift archive. One JSON/line: id, created_utc, title, selftext, score, subreddit, num_comments, author, retrieved_2nd_on. Filename = subreddit. Finished subs only. |
| `<subreddit>.jsonl.part` | `fetch_reddit_corpus.py` | In-progress pull for that sub; renamed to `.jsonl` only when its window is fully enumerated. Safe to kill; resume skips finished subs and drops a torn final line. |

This corpus is the production Reddit source (A23): `fetch_reddit.py` matches locally
against these files, no live API. Gitignored — back up locally, do not delete.
