# External Outcomes — Sources & Matching (pilot2 §9 external validation)

Built by `marchand_index/fetch_external_outcomes.py` -> `marchand_index/external_outcomes.csv` (160 rows).
Run date: 2026-05-27.

---

## ADDENDUM 2026-07-03 (full build, 774 pool — prereg A20)

Everything below this addendum describes the 2026-05-27 pilot-era run (160 set,
V1 not yet retrieved). Current state:

**V1 — RETRIEVED.** NHL Public Relations released the **2025-26 season top-10
selling jerseys** on 2026-04-17/18 (ranking only; the NHL publishes no unit
figures). Retrieved 2026-07-03 via web search; identical top-10 re-reported by
three independent outlets:

- https://www.hockeyfeed.com/nhl-news/nhl-reveals-the-top-10-selling-jerseys-of-2025-26-season (2026-04-18)
- https://thehockeynews.com/nhl/chicago-blackhawks/community/connor-bedard-has-the-nhls-highest-selling-jersey-for-2025-26 (2026-04-18)
- https://www.nhltraderumor.com/top-selling-nhl-jersey-connor-bedard-2026/ (2026-04-19, cites NHL PR)

List: 1 Connor Bedard (CHI), 2 Alex Ovechkin (WSH), 3 Sidney Crosby (PIT),
4 Jack Hughes (NJD), 5 Connor McDavid (EDM), 6 Nathan MacKinnon (COL),
7 Cale Makar (COL), 8 David Pastrnak (BOS), 9 Auston Matthews (TOR),
10 Macklin Celebrini (SJS).

This list covers exactly the A11/A14 attention window [2025-04-18, 2026-04-17].
Per A3's most-recent rule (prereg A20): **V1a** Spearman uses these ranks —
all 10 names are in the 774 pool, n = 10, powered for the first time. **V1b**
membership union is now three official lists (2023-24, 2024-25, 2025-26):
12 members in-pool (13 union names; Patrice Bergeron retired, not in pool).

**V2 on the 774 pool:** 8 of the 12 fan-vote picks are in-sample (the 8
skaters; 4 goalies excluded by pool construction) — still < 10, underpowered
per §9 as pre-declared. Namesake guard (A20): the NHL id decides membership
whenever present; the folded-name backup applies only to blank-id rows
(prevents the pool's second Elias Pettersson, D 8483678, inheriting the
center's membership).

These are the two **independent, published** fan-attention targets the Marchand Index
(OAQ_portable) is validated against. They are independent of all model inputs
(Wikipedia pageviews, Reddit, Google Trends, Instagram). **No rank or vote total was
fabricated.** Where a published figure does not exist or could not be retrieved, the
field is left blank and the gap is documented below.

Environment note (why some retrieval failed): the assistant's `WebSearch` / `WebFetch`
tools were disabled in this run. All fetching was done with plain `requests` against
public APIs/pages. Structured APIs (Wikipedia, NHL stats `api-web.nhle.com`) worked;
JavaScript-rendered marketing pages (NHLPA, Sportsnet) did not expose their content,
and the NHL.com `forge` content-search API ignored query/tag filters.

---

## V2 (secondary) — 2024 NHL All-Star Game fan vote — DELIVERED (membership-only)

**Event:** 68th NHL All-Star Game, Scotiabank Arena, Toronto, **Feb 3 2024** (the last
ASG before the 2025 4 Nations Face-Off replacement). Roster = 32 NHL Hockey-Ops
selections (announced Jan 4 2024) **+ 12 fan-vote selections** (8 skaters + 4 goalies),
fan vote run Jan 4–11 2024, **results announced Jan 13 2024**.

**Primary source (live, verified 2026-05-27):** NHL.com — "Nylander, Marner, Rielly of
Maple Leafs, 4 Canucks added to All-Star roster" (Jan 13 2024)
`https://www.nhl.com/news/final-seven-players-added-to-2024-nhl-all-star-weekend-via-fan-vote`

**Cross-check source:** Wikipedia, "2024 National Hockey League All-Star Game", *Fan
vote* table (cites the NHL.com release above)
`https://en.wikipedia.org/wiki/2024_National_Hockey_League_All-Star_Game`

### Definition used for `asg2024_member`
`1` **iff** the player was one of the **12 fan-vote selections**. The 32 NHL Hockey-Ops
selections are **not** fan-vote members (they were chosen by the league, not fans), so
they are coded `0`. This is the cleanest fan-attention signal the ASG provides.

### `asg2024_votes` — BLANK FOR EVERYONE (no per-player totals published)
The NHL announced **membership only** for the 2024 fan vote. It did **not** publish
per-player vote counts or vote share. Therefore `asg2024_votes` is blank for all 160
rows, and **V2 is a membership/binary outcome, not a vote-count outcome.** The §9
Spearman-on-vote-share test is not computable; V2 reduces to a membership comparison.

### The 12 fan-vote selections (raw list, with NHL id — all verified vs api-web.nhle.com)
| # | Player | Team (at selection) | Pos | nhl_player_id | In 160 set? |
|---|--------|---------------------|-----|---------------|-------------|
| 1 | Jeremy Swayman | Boston | G | 8480280 | no (goalie) |
| 2 | Alexandar Georgiev | Colorado | G | 8480382 | no (goalie) |
| 3 | Cale Makar | Colorado | D | 8480069 | **YES (#34)** |
| 4 | Leon Draisaitl | Edmonton | F | 8477934 | **YES (#51)** |
| 5 | Sergei Bobrovsky | Florida | G | 8475683 | no (goalie) |
| 6 | Mitch Marner | Toronto | F | 8478483 | no (not on TOR f1/d1 in set) |
| 7 | William Nylander | Toronto | F | 8477939 | **YES (#132)** |
| 8 | Morgan Rielly | Toronto | D | 8476853 | **YES (#134)** |
| 9 | Brock Boeser | Vancouver | F | 8478444 | no |
| 10 | Thatcher Demko | Vancouver | G | 8477967 | no (goalie) |
| 11 | J.T. Miller | Vancouver | F | 8476468 | no |
| 12 | Elias Pettersson | Vancouver | F | 8480012 | no |

(Goalies are excluded from this skater-only 160 set by construction; the §9 plan also
excludes goalies from headline analysis. Marner/Boeser/Miller/Pettersson are real NHL
players simply not occupying their team's first-line/first-pair slot in this set.)

### V2 overlap against the 160
**4 fan-vote members are in-sample:** Cale Makar, Leon Draisaitl, William Nylander,
Morgan Rielly (matched by verified `nhl_player_id`, name-fold as backup).

**4 < 10 → V2 is UNDERPOWERED per the pre-reg §9 underpowered-overlap rule** and is
reported as inconclusive, not pass/fail. (Compounding this, no vote totals exist, so
even the membership signal is only 4 positives in 160.)

---

## V1 (primary) — NHL/NHLPA top-selling jersey list — DATA NOT RETRIEVED

`jersey_list_member` is `0` for all 160 rows and `jersey_rank` is blank for all.
**No ranks were invented.** The most-recent published ranked player-jersey list could
not be obtained from any source reachable in this run. Channels attempted (reproducible
via `python fetch_external_outcomes.py --discover`):

1. **Wikipedia** — no article for an NHL jersey-sales / most-popular-jersey list exists
   (search returns only franchise pages). No structured data to read.
2. **NHLPA.com** — the league's canonical "most popular player jerseys and products of
   the <season>" article. The 2023-24 article URL resolves
   (`https://www.nhlpa.com/news/1-21127/the-most-popular-player-jerseys-and-products-of-the-2023-24-nhl-season`)
   but the page is a **client-rendered SPA backed by a Sanity CMS** (`cdn.sanity.io`):
   the ranked player names are **not present in the static HTML** (checked — no
   "McDavid"/"Ovechkin"/"Crosby" strings), and no public Sanity GROQ endpoint / project
   id could be recovered to query the body. A 2024-25 article was not confirmed to exist
   at a guessable slug.
3. **NHL.com article slugs** — every guessed best-selling/most-popular jersey slug
   (e.g. `/news/nhl-best-selling-jerseys-2024-25-season`,
   `/news/nhl-fanatics-best-selling-jerseys-2024-25-season`) returns a **soft-404 React
   shell** (HTTP 200 but "page not found"/no article content).
4. **NHL.com `forge` content API** (`forge-dapi.d3.nhle.com/v2/content/en-us/stories`) —
   reachable and returns JSON, but **ignores `$searchString` / tag / category filters**
   (a search query returns the same generic most-recent stories as no query), so the
   jersey story cannot be located through it.
5. **Sportsnet** (server-side news that re-reports the NHLPA/Fanatics list) — site
   search is also JS-rendered; no article links in static HTML.
6. `WebSearch` / `WebFetch` — **disabled** in this environment (permission denied), so
   the normal route to find the exact published list + URL was unavailable.

### V1 status for §9
Overlap = **0 of 160** (list empty). Per the §9 underpowered-overlap rule (< 10 →
inconclusive), **V1 is reported as inconclusive — specifically DATA-NOT-RETRIEVED**, not
a model failure. The pre-registered V1 tests (Spearman on jersey rank; AUC discriminating
list members) are **not computable** until a real ranked list is supplied.

### How to complete V1 later (no code change to the join logic needed)
Populate `JERSEY_LIST` in `fetch_external_outcomes.py` with `(rank, display_name,
nhl_player_id_or_empty)` tuples from the real published list, record the source URL +
date here, and re-run. The build matches on `nhl_player_id` first (stable) then folded
name, so accented/nickname names join correctly. Recommended retrieval once web tools
are available: find the current "NHL/NHLPA most popular jerseys" or Fanatics top-25
release for the most recently completed season (the 2024-25 list, published ~June 2025;
the 2025-26 list will not publish until ~June 2026, after this run's 2026-05-27 date).

---

## Name-matching decisions / caveats

- **Sebastian Aho (player_id 21, nhl_player_id 8478427)** = the **Carolina Hurricanes
  forward** (born 1997), confirmed by `nhl_player_id`. This is **not** the New York
  Islanders defenseman Sebastian Aho (8480222). The Carolina Aho appeared in the 2024
  ASG as an **NHL Hockey-Ops selection**, **not** a fan-vote pick, so `asg2024_member=0`.
  This disambiguation is written into the row's `match_note`. No jersey-list entry needed
  disambiguation because V1 is empty.
- **Matching method:** ASG membership is matched by `nhl_player_id` first (stable across
  spelling), with accent-folded full-name as a backup. All 12 ASG ids were verified
  against `api-web.nhle.com/v1/player/<id>/landing` (`--verify-asg`): names match; current
  team abbreviations differ for players traded since Feb 2024 (e.g. Marner now VGK,
  Miller now NYR), which does not affect 2024 membership.
- **player_id 60 (Michael Benning, FLA)** has an empty `nhl_player_id` in players.csv;
  he is not on either outcome list, so the blank id is immaterial here (coded 0/blank).

---

## Overlap summary

| Outcome | Published data type | In-set overlap | §9 verdict |
|---------|---------------------|----------------|------------|
| V1 jersey list | ranked list (not retrieved) | 0 / 160 | inconclusive — DATA NOT RETRIEVED |
| V2 ASG-2024 fan vote | membership only (no vote totals) | 4 / 160 | underpowered (< 10) |
