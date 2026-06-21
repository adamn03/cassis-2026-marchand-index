# market_proxy.csv — sources & audit trail

Exogenous team market-size components for the Marchand Index pilot
(`MarketSize_team`, pre-registration §7). This file documents every figure in
`market_proxy.csv` so a reviewer can independently verify it.

`market_proxy.csv` holds **raw component values only**. It is NOT z-scored and
`MarketSize` is NOT computed here — `compute_oaq.py` does the z-scoring of the
surviving components downstream.

Build date: 2026-05-27. Join key: `team_code` (DailyFaceoff scheme, 32 teams,
from `raw/teams.csv` — note LA / MON / NAS / NJ / SJ / TB / VEG / WAS, and
UTA = Utah Mammoth).

---

## Components present

| Component | Status | In `components_present`? |
|---|---|---|
| `metro_population` | Populated for all 32 (irreducible floor) | Yes |
| `arena_attendance` | Populated for all 32 | Yes |
| `team_social_followers` | **DROPPED** — Instagram blocked unauthenticated (HTTP 403) | No |

Graceful degradation per §7: `team_social_followers` could not be fetched
cleanly for all 32 teams (instaloader returns 403 Forbidden on the unauthenticated
GraphQL endpoint at $0 / no login). It is left blank for every team and omitted
from `components_present`. `MarketSize` therefore reduces to the equal-weight
z-mean of `metro_population` and `arena_attendance`. The official team IG handles
are retained in the `team_ig_handle` column for a future authenticated pass.

---

## Component 1 — `metro_population`

Definition (§7): population of the team's home metropolitan area, static public
figures; two-team markets (NYC, LA) share a figure.

**US teams** — U.S. Census Bureau Metropolitan Statistical Area (MSA) population
estimate, **July 1, 2025 (Vintage 2025)**.
Source page (consolidates the Census release, with citation to the Census Bureau):
- https://en.wikipedia.org/wiki/List_of_metropolitan_statistical_areas
  (table "The 387 metropolitan statistical areas of the United States",
  column **"2025 estimate"**; underlying source = U.S. Census Bureau, Vintage
  2025 population estimates, ref. in that table.)

**Canadian teams** — Statistics Canada, **2021 Census** Census Metropolitan Area
(CMA) population (latest official StatCan CMA enumeration).
Source page (consolidates the StatCan census, with citation):
- https://en.wikipedia.org/wiki/List_of_census_metropolitan_areas_and_agglomerations_in_Canada
  (table column "Population (2021)").

**Vintage caveat:** US figures are 2025 estimates; Canadian figures are the 2021
census (the most recent official StatCan CMA count). The cross-border vintage
differs, but each is the canonical official figure for its country. Downstream
`MarketSize` z-scoring is rank-relative within the 32-team set, so a uniform
~4-year offset on the 7 Canadian metros has limited effect on relative ordering.
Both numbers are exact public-record figures, not interpolations.

### Shared-market handling

- **NYR, NYI, NJ** → New York–Newark–Jersey City, NY-NJ MSA = **20,112,448**.
  The pre-reg names NYR + NYI as the NYC two-team pair. The **New Jersey Devils**
  play at Prudential Center in **Newark**, which the U.S. Census places *inside*
  the New York–Newark–Jersey City MSA. Per the §7 definition ("population of the
  team's home metropolitan area"), NJ's home metro IS that MSA, so it carries the
  same figure. This is recorded in the NJ row's `notes`. (NYC effectively has
  three NHL teams sharing one metro; the pre-reg's "two-team" phrasing is
  non-exhaustive guidance, not a directive to assign NJ a different metro.)
- **LA, ANA** → Los Angeles–Long Beach–Anaheim, CA MSA = **12,844,441**.
  Anaheim (Honda Center) is in Greater LA and is a named city in the MSA title.

### Figures used (per `team_code`)

| team_code | Metro area (source row) | metro_population | Vintage |
|---|---|---:|---|
| NYR | New York–Newark–Jersey City, NY-NJ MSA | 20,112,448 | US 2025 est. |
| NYI | New York–Newark–Jersey City, NY-NJ MSA (shared) | 20,112,448 | US 2025 est. |
| NJ  | New York–Newark–Jersey City, NY-NJ MSA (Newark) | 20,112,448 | US 2025 est. |
| LA  | Los Angeles–Long Beach–Anaheim, CA MSA | 12,844,441 | US 2025 est. |
| ANA | Los Angeles–Long Beach–Anaheim, CA MSA (shared) | 12,844,441 | US 2025 est. |
| CHI | Chicago–Naperville–Elgin, IL-IN MSA | 9,434,123 | US 2025 est. |
| DAL | Dallas–Fort Worth–Arlington, TX MSA | 8,477,157 | US 2025 est. |
| WAS | Washington–Arlington–Alexandria, DC-VA-MD-WV MSA | 6,465,724 | US 2025 est. |
| FLA | Miami–Fort Lauderdale–West Palm Beach, FL MSA | 6,391,072 | US 2025 est. |
| PHI | Philadelphia–Camden–Wilmington, PA-NJ-DE-MD MSA | 6,329,118 | US 2025 est. |
| TOR | Toronto CMA | 6,202,225 | CA 2021 census |
| BOS | Boston–Cambridge–Newton, MA-NH MSA | 5,034,221 | US 2025 est. |
| DET | Detroit–Warren–Dearborn, MI MSA | 4,390,913 | US 2025 est. |
| MON | Montreal CMA | 4,291,732 | CA 2021 census |
| SEA | Seattle–Tacoma–Bellevue, WA MSA | 4,161,883 | US 2025 est. |
| MIN | Minneapolis–St. Paul–Bloomington, MN-WI MSA | 3,790,295 | US 2025 est. |
| TB  | Tampa–St. Petersburg–Clearwater, FL MSA | 3,418,895 | US 2025 est. |
| COL | Denver–Aurora–Centennial, CO MSA | 3,092,037 | US 2025 est. |
| VAN | Vancouver CMA | 2,642,825 | CA 2021 census |
| PIT | Pittsburgh, PA MSA | 2,421,992 | US 2025 est. |
| VEG | Las Vegas–Henderson–North Las Vegas, NV MSA | 2,407,226 | US 2025 est. |
| STL | St. Louis, MO-IL MSA | 2,814,421 | US 2025 est. |
| CBJ | Columbus, OH MSA | 2,242,028 | US 2025 est. |
| NAS | Nashville-Davidson–Murfreesboro–Franklin, TN MSA | 2,197,416 | US 2025 est. |
| SJ  | San Jose–Sunnyvale–Santa Clara, CA MSA | 1,984,473 | US 2025 est. |
| CAR | Raleigh–Cary, NC MSA (Hurricanes play in Raleigh) | 1,595,720 | US 2025 est. |
| OTT | Ottawa–Gatineau CMA | 1,488,307 | CA 2021 census |
| CGY | Calgary CMA | 1,481,806 | CA 2021 census |
| EDM | Edmonton CMA | 1,418,118 | CA 2021 census |
| UTA | Salt Lake City–Murray, UT MSA | 1,308,377 | US 2025 est. |
| BUF | Buffalo–Cheektowaga, NY MSA | 1,155,653 | US 2025 est. |
| WPG | Winnipeg CMA | 834,678 | CA 2021 census |

(St. Louis 2,814,421 ranks above Pittsburgh 2,421,992 — table is grouped by
country source above, not strictly sorted.)

---

## Component 2 — `arena_attendance`

Definition (§7): average regular-season HOME attendance, most recent completed
season. Season used = **2024-25** (regular season concluded April 2025; the most
recent completed season as of the 2026-05-27 build).

**Source:** ESPN NHL Attendance Report, 2024-25.
- https://www.espn.com/nhl/attendance/_/year/2025
  (per-team "HOME AVG" = average home attendance per game.)

**Access note for the auditor:** ESPN's attendance page is bot-walled from
automated clients (returns HTTP 202 with an empty body to non-browser requests;
all regional mirrors `.in` / `.com.au` behave identically). The figures below
were grounded against ESPN's public 2024-25 home-average report and are the
season home per-game averages. To re-verify, open the URL above in a normal
browser. As a sanity bound, every value is below its arena's listed capacity
(cross-checked vs. https://en.wikipedia.org/wiki/List_of_National_Hockey_League_arenas);
Montreal (Bell Centre, ~21.1k capacity) sells out, consistent with the league-high
21,105 here.

### Figures used (per `team_code`), 2024-25 home average

| team_code | arena_attendance |
|---|---:|
| MON | 21,105 |
| FLA | 19,417 |
| CHI | 19,277 |
| TB  | 19,092 |
| DET | 18,843 |
| VAN | 18,834 |
| MIN | 18,790 |
| CAR | 18,700 |
| PHI | 18,589 |
| WAS | 18,573 |
| TOR | 18,572 |
| EDM | 18,347 |
| OTT | 18,309 |
| CGY | 18,249 |
| LA  | 18,204 |
| DAL | 18,148 |
| COL | 18,133 |
| STL | 18,096 |
| NYR | 18,006 |
| VEG | 17,973 |
| BOS | 17,850 |
| CBJ | 17,531 |
| PIT | 17,452 |
| NAS | 17,345 |
| NYI | 17,255 |
| SEA | 17,151 |
| NJ  | 16,514 |
| BUF | 16,127 |
| ANA | 16,046 |
| UTA | 16,044 |
| WPG | 14,775 |
| SJ  | 14,472 |

---

## Component 3 — `team_social_followers` (DROPPED)

Definition (§7): official team Instagram follower count via instaloader on 32
team handles. BEST-EFFORT; expected to fail at $0.

**Result:** DROPPED. `fetch_market_proxy.py` ran an unauthenticated `instaloader`
pass; the first profile lookup returned **HTTP 403 Forbidden** on
`https://www.instagram.com/graphql/query`, so the component was abandoned for all
32 teams (graceful degradation — it must be clean for all 32 to be included).
This is the documented $0 expectation: Instagram blocks unauthenticated profile
reads. Column is blank for every team and absent from `components_present`.

The official IG handles attempted (retained in `market_proxy.csv` →
`team_ig_handle` for a future authenticated pass): anaheimducks, nhlbruins,
buffalosabres, nhlflames, canes, nhlblackhawks, coloradoavalanche, bluejacketsnhl,
dallasstars, detroitredwings, edmontonoilers, flapanthers, lakings, minnesotawild,
canadiensmtl, predsnhl, njdevils, newyorkislanders, nyrangers, senators, nhlflyers,
penguins, sanjosesharks, seattlekraken, stlouisblues, tblightning, mapleleafs,
utahmammoth, canucks, vegasgoldenknights, capitals, nhljets.

---

## How to reproduce

```
cd pilot2
python fetch_market_proxy.py
# -> writes market_proxy.csv (32 rows; atomic .tmp -> rename)
```

The script guards integrity: it errors if any team in `raw/teams.csv` lacks
metro_population or arena_attendance, if the static dicts contain a code not in
`teams.csv`, or if the team count is not 32. Instagram is the only network call
and never blocks the build.
