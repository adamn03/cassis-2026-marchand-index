# Cross-Domain Improvements Implementation Plan (sibling to `2026-07-07-free-data-improvements.md`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import proven ideas from other sports' analytics and from economics into the Marchand Index as (1) one new pre-registered assumption diagnostic (A38: an event-study empirical anchor for the λ = 0.5 portability assumption, borrowed from finance event-study + labor-mobility economics), (2) one new pre-registered descriptive panel (A39: attention-concentration statistics grounded in superstar economics — a quotable-number generator), and (3) a verified citation/framing kit that positions the poster inside the superstar-economics and sports-star-power literatures.

**Architecture:** SUPPLEMENTS both `docs/airtight_execution_plan.md` v1.1 and the sibling plan `2026-07-07-free-data-improvements.md`. Changes NOTHING in the locked model: no weight, floor, pool, window, K, λ, or seed changes. A38/A39 are reporting-side additions whose amendment texts must land while Reddit is 0/774; their analysis scripts run AFTER the Phase-2 one-shot compute (they consume its outputs). The citation kit is pure text. Amendment numbering continues the impl series: **A38, A39** (A36/A37 are claimed by the sibling plan).

**Tech Stack:** Python 3 (numpy/pandas/scipy already in use by `compute_oaq.py`), pytest, existing CSV outputs (`oaq_pilot.csv` emits `peer_player_ids` and `market_z`; `raw/wiki_daily.csv` post-A36 is a zero-filled 365-day vector with dates implicit from `WINDOW_START` — verified against code 2026-07-07).

## Global Constraints

Identical to the sibling plan — read its Global Constraints and Execution Guardrails sections first and treat them as binding here. Additional pins for this plan:

- **A38 and A39 are DESCRIPTIVE.** Neither is a validation pathway, neither counts toward the ≥3-pathway standard, neither has a pass/fail floor, and neither can change the headline under any outcome. This is stated inside each amendment.
- Both amendments extend the Airtight-plan §H forking-paths panel rule: their outputs appear only in designated descriptive panels, "reported as estimates with CIs, never as a ranking, and never eligible to become the headline."
- λ̂ notation below is the *empirical anchor estimate*; the locked primary λ = 0.5 is untouched under every possible result.

## Where the ideas come from (the cross-domain map)

| Domain source | The idea there | The parallel here | Adopted as |
|---|---|---|---|
| Finance event studies (MacKinlay 1997); labor economics natural experiments | Abnormal returns around an event, measured against a counterfactual | Players who CHANGE TEAMS inside the attention window are a natural experiment on the market-portability assumption: their attention is observed under two different market sizes. "Abnormal attention" = own change minus skill-matched peers' change (we already have K=10 peer sets) | **A38** (Task 1–3) |
| Superstar economics: Rosen (1981), Adler (1985) | Talent→reward mapping is convex (Rosen); stardom can snowball independent of talent (Adler) | OAQ is literally an empirical Adler residual — attention not explained by talent. Rosen's convexity is the THEORY behind the A27 star-boundary bias. Concentration statistics (top-share, Gini) are the standard superstar-market evidence | **A39** (Task 4–5) + framing kit |
| Sabermetrics: WAR / replacement-level; xG "over expected" convention | Value expressed as surplus over a defined baseline, communicated as "over expected" | OAQ = attention-over-expected where expectation = skill-matched peers. One-line translation for a stat-literate audience; park-factor analogy for the market adjustment | Framing kit (Task 6) |
| F1 analytics: driver-vs-constructor decomposition (Bell et al. 2016) | Multilevel separation of individual vs team-context contribution | Between-team vs within-team share of attention variance — one ANOVA number that quantifies how much attention is team-context | Folded into **A39** |
| Nowcasting economics: Choi & Varian (2012); Wikipedia-based forecasting (Mestyán et al. 2013); altmetrics (Priem et al. 2010) | Search/pageview/multi-platform attention composites are validated measurement instruments | Each composite component gets a peer-reviewed measurement precedent — pre-empts "you summed random website numbers" | Framing kit (Task 6) |
| Sports star-power economics: Hausman & Leonard (1997), Berri–Schmidt–Brook (2004); soccer market-value models (Müller et al. 2017) | Star attention has measurable economic value; market-value regressions from performance are standard | Related-work positioning: prior work measured star externalities in revenue terms; we measure the attention side honestly and validate against purchase behavior. `expected_cap` = a deliberately simple hedonic market-value model (Rosen 1974 lineage) | Framing kit (Task 6) |

---

### Task 1: A38 amendment text — empirical λ anchor from in-window team-changers

**Files:**
- Modify: `marchand_index/preregistration.md` (append after A37)

**Why:** §G's own limitations list calls λ = 0.5 "an unanchored maximum-entropy assumption" — it is the poster's weakest a-priori choice and every judge will ask about it. Players who changed teams inside [2025-04-18, 2026-04-17] were observed under two market sizes; their wiki attention around the move, benchmarked against their K=10 peers (already computed), yields an EMPIRICAL portability estimate at $0 with data already in hand. Reported as a pre-registered assumption diagnostic. No possible result changes the primary.

- [ ] **Step 1: Append the amendment text below to prereg-impl:**

```markdown
**A38 (YYYY-MM-DD) — Empirical market-portability anchor: event-study diagnostic on
in-window team-changers. Logged BEFORE the Phase-2 compute; Reddit remains 0/774.
DESCRIPTIVE — not a validation pathway, no floor, cannot alter the λ = 0.5 primary.**

A5 committed λ = 0.5 as the maximum-entropy midpoint because no empirical anchor
existed for the share of market-driven attention that travels with a player. An
anchor is derivable from data already collected: skaters who changed NHL teams
inside the fixed window were observed under two market sizes, and their K=10 peer
sets (non-movers) provide the counterfactual attention path — the abnormal-attention
construction of the finance event-study literature (MacKinlay 1997).

**Mover set (mechanical):**
1. In-season movers: pool skaters with ≥2 distinct-team NHL `seasonTotals` rows for
   season 20252026 (`gameTypeId==2`, `leagueAbbrev=="NHL"`) — the A22 derivation.
2. Off-season movers: pool skaters whose last 20242025 NHL team differs from their
   first 20252026 NHL team (both season rows present).
3. Event date = the publicly reported transaction date, corroborated by ≥2
   independent URLs per mover (A20 sourcing pattern), recorded in
   `marchand_index/mover_dates.csv` with `move_type ∈ {trade, fa_signing, waiver}`.
   A mover whose date cannot be corroborated by 2 URLs is EXCLUDED and counted.
4. Eligibility: event date t must leave ≥30 in-window days on each side of the
   exclusion gap (below). Movers failing this are excluded and counted.

**Estimator (mechanical; wiki_en daily vectors only — the only component with
per-day resolution; disclosed):**
- Windows: pre = in-window days in [t−63, t−8]; post = in-window days in
  [t+8, t+63]. Days within ±7 of t are excluded (transaction-news spike).
- Per mover i: Δa_i = log1p(mean daily views in post) − log1p(mean daily views in
  pre), from the zero-filled 365-day `wiki_daily.csv` vector (dates implicit:
  index 0 = 2025-04-18).
- Peer control: Δa_peer_i = mean of the same quantity (same calendar windows) over
  i's `peer_player_ids` that are themselves non-movers; ≥5 usable peers required,
  else i is excluded and counted. Abnormal change: Δã_i = Δa_i − Δa_peer_i.
- Market change: Δm_i = market_z(new team) − market_z(old team), using the primary
  MarketSize_team at compute time (post-A30 if adopted; `market_z_lockedv1`
  version reported as a sensitivity row).
- Mover regression: OLS Δã_i = α + β·Δm_i + ε over all eligible movers.
- Cross-sectional market gradient: OLS log1p(wiki_12mo) ~ market_z + position
  indicator + the 6 standardized §6/A13 skill features (group-mean imputation as
  in compute) over all NON-movers; γ̂ = the market_z coefficient.
- **Empirical anchor: λ̂_emp = clip(β̂ / γ̂, 0, 1)** — the share of the
  cross-sectional market gradient that a mover's attention actually loses/gains
  when crossing markets (β̂ ≈ 0 → attention fully portable → λ̂_emp ≈ 0;
  β̂ ≈ γ̂ → attention fully market-attached → λ̂_emp ≈ 1). If γ̂ ≤ 0, λ̂_emp is
  reported as "undefined (non-positive market gradient)" with β̂ and γ̂ shown.
- Uncertainty: 1,000 bootstrap draws, seed 20260526; each draw resamples movers
  (for β̂) and non-movers (for γ̂) with replacement and recomputes λ̂_emp;
  percentile 95% CI. Secondary cut: trade-only movers (FA moves are
  self-selected destinations).

**Interpretation rule (fixed now):** the primary λ = 0.5 is unchanged under every
outcome. If the λ̂_emp 95% CI contains 0.5, the poster may state "the locked
midpoint is consistent with an empirical portability estimate from n=N in-window
team-changers." If the CI excludes 0.5, the poster states the tension verbatim
("the empirical anchor suggests λ nearer X; the pre-committed λ ladder shows the
headline's sensitivity") — and nothing else changes. This diagnostic does not
count toward the ≥3 validation pathways.

**Honest residuals (disclosed in advance):** post-move novelty (new-market
curiosity) inflates post-attention regardless of market direction, biasing β̂
toward 0, i.e. toward the portable conclusion — stated next to the estimate;
deadline-window movers have truncated post-windows (30-day minimum); n is small
(tens, not hundreds) — this is an anchor, not a validation; wiki-only resolution;
market_z is a proxy (A30 disclosures apply).

**Anti-tuning compliance (§13):** logged before the Phase-2 compute while Reddit
is 0/774, so no OAQ, validation, or λ-ladder result could have influenced the
design; mover set, windows, estimator, and interpretation are mechanical and fixed
in advance; weights (§4/A12), peer features (§6/A13), λ (A5), denominators
(A4/A8), pool (§2/A10), window (A11/A14), and all validation floors (§9, A6/V3)
unchanged. Output appears only in the designated descriptive diagnostics panel per
the poster forking-paths rule (§H of the airtight plan), which is extended to name
this diagnostic.
```

- [ ] **Step 2: Commit**

```bash
git add "Full Project Files/marchand_index/preregistration.md"
git commit -m "marchand_index: A38 empirical lambda anchor (mover event study)"
```

---

### Task 2: A38 mover list + transaction dates

**Files:**
- Create: `marchand_index/build_mover_list.py`
- Create: `marchand_index/mover_dates.csv` (generated skeleton, then filled)
- Create: `marchand_index/mover_dates_sources.md`
- Test: `marchand_index/tests/test_build_mover_list_a38.py`

**Interfaces:**
- Consumes: `players.csv` (`nhl_player_id`), NHL API `https://api-web.nhle.com/v1/player/{id}/landing` (`seasonTotals` — the same endpoint/fields the A22 roster derivation uses).
- Produces: `mover_dates.csv` with columns `player_id, full_name, nhl_player_id, old_team, new_team, move_type, event_date, url_1, url_2, status` — consumed by Task 3.

- [ ] **Step 1: Write failing tests** — pure derivation function on fixture seasonTotals:

```python
"""A38: mover derivation from seasonTotals fixtures (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from build_mover_list import derive_moves  # noqa: E402

ROWS_TRADED = [  # in-season: two 2025-26 NHL teams
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Canucks"},
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Rangers"},
]
ROWS_OFFSEASON = [  # 2024-25 team != first 2025-26 team
    {"season": 20242025, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Bruins"},
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Panthers"},
]
ROWS_STAYED = [
    {"season": 20242025, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Penguins"},
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Penguins"},
]
ROWS_AHL_NOISE = [  # non-NHL rows never count
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "AHL", "teamCommonName": "Checkers"},
    {"season": 20252026, "gameTypeId": 2, "leagueAbbrev": "NHL", "teamCommonName": "Panthers"},
]


def test_in_season_mover_detected():
    m = derive_moves(ROWS_TRADED)
    assert m == [("Canucks", "Rangers", "in_season")]


def test_offseason_mover_detected():
    assert derive_moves(ROWS_OFFSEASON) == [("Bruins", "Panthers", "off_season")]


def test_non_mover_and_league_filter():
    assert derive_moves(ROWS_STAYED) == []
    assert derive_moves(ROWS_AHL_NOISE) == []
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/test_build_mover_list_a38.py -v` → `ModuleNotFoundError`.
- [ ] **Step 3: Implement `build_mover_list.py`** — `derive_moves(season_rows) -> list[tuple[old, new, kind]]` pure function (NHL rows only, `gameTypeId==2`; in-season = consecutive distinct 20252026 teams in row order; off-season = last 20242025 team ≠ first 20252026 team); `main()` iterates the 774 via the cached session, writes the `mover_dates.csv` skeleton with `event_date` blank, `status=needs_date`. Politeness: sleep 0.2 s.
- [ ] **Step 4: Tests pass** — `pytest -q`.
- [ ] **Step 5: Fill dates.** For each skeleton row: web-search the transaction ("<player> traded <old team> <new team> 2025/2026" / "<player> signs with <new team> July 2025"), record `event_date` (ISO), `move_type`, 2 URLs; log each in `mover_dates_sources.md`. Rows that cannot be corroborated: `status=excluded_no_source`. Expect roughly 30–80 movers (July-2025 FA class + deadline trades). This is lookup work, not judgment — any qualifying source pair settles a row.
- [ ] **Step 6: Commit**

```bash
git add "Full Project Files/marchand_index/build_mover_list.py" "Full Project Files/marchand_index/tests/test_build_mover_list_a38.py" "Full Project Files/marchand_index/mover_dates.csv" "Full Project Files/marchand_index/mover_dates_sources.md"
git commit -m "marchand_index: A38 code + mover dates (n=<N>)"
```

---

### Task 3: A38 diagnostic script

**Files:**
- Create: `marchand_index/diagnostics/lambda_portability.py`
- Test: `marchand_index/tests/test_lambda_portability_a38.py`

**Interfaces:**
- Consumes: `mover_dates.csv` (Task 2), `raw/wiki_daily.csv` (post-A36 zero-filled 365-day vectors, index 0 = 2025-04-18), `oaq_pilot.csv` (`peer_player_ids`, `market_z`, skill feature columns), `raw/wiki_pageviews.csv` (`wiki_12mo`), `market_proxy.csv`.
- Produces: `diagnostics/lambda_portability_report.md` + a machine block appended to `results.md` by hand-off (β̂, γ̂, λ̂_emp, CI, n, exclusion counts, trade-only cut, lockedv1-market sensitivity row).
- **Runs AFTER Phase-2 compute** (needs `oaq_pilot.csv`). Script is written and tested (pure functions) BEFORE.

Pure functions (module level):

```python
WINDOW_START_ORD = 0          # index of 2025-04-18
WINDOW_LEN = 365

def event_windows(t_idx: int) -> tuple[range, range]:
    """Pre/post day-index ranges for an event at vector index t_idx,
    clipped to [0, 365): pre=[t-63, t-8], post=[t+8, t+63], ±7 excluded."""
    pre = range(max(0, t_idx - 63), max(0, t_idx - 7))       # t-63 .. t-8
    post = range(min(WINDOW_LEN, t_idx + 8), min(WINDOW_LEN, t_idx + 64))
    return pre, post

def delta_log_attention(daily: list[int], t_idx: int, min_days: int = 30) -> float | None:
    """log1p(mean post) - log1p(mean pre); None if either side < min_days days."""
    import math
    pre, post = event_windows(t_idx)
    if len(pre) < min_days or len(post) < min_days:
        return None
    mp = sum(daily[i] for i in pre) / len(pre)
    mq = sum(daily[i] for i in post) / len(post)
    return math.log1p(mq) - math.log1p(mp)

def lambda_emp(beta: float, gamma: float) -> float | None:
    """clip(beta/gamma, 0, 1); None when gamma <= 0 (undefined per A38)."""
    if gamma <= 0:
        return None
    return min(1.0, max(0.0, beta / gamma))
```

`main()` flow: load movers with `status` having a date → map `event_date` to vector index (`(date − 2025-04-18).days`; skip if outside window) → Δa per mover → Δa_peer from `peer_player_ids` minus movers (≥5 peers else exclude) → Δã → OLS β̂ (`numpy.polyfit` degree 1 or statsmodels, either fine) → γ̂ from the non-mover cross-sectional OLS spec in the amendment (reuse the skill-feature matrix construction pattern from `compute_oaq.py`'s expected_cap section) → λ̂_emp → bootstrap (seed 20260526, 1,000 draws, resample movers and non-movers) → write report with every exclusion count and both market_z variants.

- [ ] **Step 1: Write failing tests**

```python
"""A38: event-window mechanics + lambda mapping (no I/O)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from diagnostics.lambda_portability import (  # noqa: E402
    event_windows, delta_log_attention, lambda_emp)


def test_event_windows_interior():
    pre, post = event_windows(100)
    assert (min(pre), max(pre)) == (37, 92)      # t-63 .. t-8
    assert (min(post), max(post)) == (108, 163)  # t+8 .. t+63


def test_event_windows_clip_at_window_end():
    pre, post = event_windows(340)               # deadline-class mover
    assert max(post) == 364 and len(post) == 17  # truncated


def test_delta_log_attention_min_days_guard():
    daily = [10] * 365
    assert delta_log_attention(daily, 340) is None          # post too short
    assert delta_log_attention(daily, 100) == 0.0           # flat series


def test_lambda_emp_mapping():
    assert lambda_emp(0.0, 0.4) == 0.0        # fully portable
    assert lambda_emp(0.2, 0.4) == 0.5        # midpoint
    assert lambda_emp(0.9, 0.4) == 1.0        # clipped
    assert lambda_emp(0.2, 0.0) is None       # undefined gradient
```

- [ ] **Step 2: Verify failure** — `pytest tests/test_lambda_portability_a38.py -v` → import error.
- [ ] **Step 3: Implement** the pure functions exactly as above + `main()` per flow. Match `diagnostics/` conventions (see `diagnostics/source_correlation.py` for the report-writing pattern).
- [ ] **Step 4: Tests pass** — `pytest -q`.
- [ ] **Step 5: Commit** — `git commit -m "marchand_index: A38 lambda-portability diagnostic + tests"`. Execution against real data happens in the Phase-2 diagnostics step (add `python diagnostics/lambda_portability.py` to the Airtight §E diagnostics list).

---

### Task 4: A39 amendment text — attention-concentration descriptive panel

**Files:**
- Modify: `marchand_index/preregistration.md` (append after A38)

**Why:** Criterion 5 (striking, quotable finding) currently depends entirely on the validation AUC landing well. Superstar economics (Rosen 1981) predicts extreme attention concentration; measuring it is trivial from data in hand and yields a judge-memorable, zero-risk sentence of the form "8 players capture X% of all NHL player Wikipedia attention — attention is Y× more concentrated than payroll." Pre-registering it keeps the forking-paths story clean.

- [ ] **Step 1: Append the amendment text below:**

```markdown
**A39 (YYYY-MM-DD) — Attention-concentration descriptive panel (superstar-economics
statistics). Logged BEFORE the Phase-2 compute; Reddit remains 0/774. DESCRIPTIVE —
no floor, no gate, not a validation pathway.**

Superstar economics (Rosen 1981 AER; Adler 1985 AER) predicts convex, highly
concentrated attention markets. The poster reports the following pre-registered
concentration statistics, computed once, in a single designated descriptive panel:

1. **Base quantity (fixed now): `wiki_12mo`** (post-A36, canonical+redirect,
   en-Wikipedia) — chosen because it is the one composite component with NO
   censoring (the Reddit 1,000-result cap floors star counts, A23), so star-tier
   concentration is measured, not truncated. The same statistics on
   `engagement_raw` are reported as a secondary row with the censoring caveat.
2. Top-share: share of the pool total held by the top 8 players (= ceil(1% of
   774)) and the top 77 (= ceil(10%)).
3. Gini coefficient of `wiki_12mo` across the 774 (discrete formula
   G = Σᵢ Σⱼ |xᵢ − xⱼ| / (2 n² x̄); NULL rows excluded and counted).
4. The same top-shares and Gini for `cap_hit_M` (cap_quality=low rows excluded
   and counted) — the payroll-vs-attention concentration contrast
   (tournament-theory framing, Lazear & Rosen 1981).
5. Between-team share of attention variance: R² of a one-way ANOVA of
   log1p(wiki_12mo) on team (SS_between / SS_total) — the driver-vs-constructor
   decomposition idea (Bell et al. 2016, F1), quantifying how much player
   attention is team-context before any market adjustment.
6. Bootstrap 95% CIs on every number: 1,000 player-level resamples, seed 20260526.

**Presentation rule (fixed now):** these are descriptive market facts, reported
with CIs in one panel; they support the Rosen/Adler framing of WHY a peer-matched
residual is the right construct, and make no validity claim about OAQ itself. No
concentration number may be promoted to the headline unless the headline slot is
already in shipping-matrix rows 6–8 (no validation language available), in which
case the concentration sentence MAY serve as the poster's quotable descriptive
fact — explicitly labeled descriptive.

**Anti-tuning compliance (§13):** logged before the Phase-2 compute while Reddit
is 0/774; statistic list, base quantity, exclusion rules, and presentation rule
fixed in advance; nothing in the composite, peer matching, denominators,
validation floors, or hypotheses changes. Output confined to a single designated
panel per the §H forking-paths rule, which is extended to name this panel.
```

- [ ] **Step 2: Commit** — `git commit -m "marchand_index: A39 attention-concentration panel (pre-registered)"`.

---

### Task 5: A39 script

**Files:**
- Create: `marchand_index/diagnostics/attention_concentration.py`
- Test: `marchand_index/tests/test_attention_concentration_a39.py`

**Interfaces:**
- Consumes: `raw/wiki_pageviews.csv` (post-A36 `wiki_12mo`), `raw/cap_hits.csv` (`cap_hit_M`, `cap_quality`), `players.csv` (team), `oaq_pilot.csv` (`engagement_raw`, secondary row — post-compute only).
- Produces: `diagnostics/attention_concentration_report.md` with the six pre-registered statistics + CIs + exclusion counts.

Pure functions:

```python
def gini(values: list[float]) -> float:
    """Discrete Gini: sum_i sum_j |xi-xj| / (2 n^2 mean). Requires n>0, mean>0."""
    n = len(values)
    mean = sum(values) / n
    num = sum(abs(a - b) for a in values for b in values)
    return num / (2 * n * n * mean)

def top_share(values: list[float], k: int) -> float:
    """Share of total held by the k largest values."""
    s = sorted(values, reverse=True)
    return sum(s[:k]) / sum(s)

def between_team_r2(values: list[float], teams: list[str]) -> float:
    """One-way ANOVA R^2 = SS_between / SS_total of values grouped by teams."""
    from collections import defaultdict
    grand = sum(values) / len(values)
    groups = defaultdict(list)
    for v, t in zip(values, teams):
        groups[t].append(v)
    ss_total = sum((v - grand) ** 2 for v in values)
    ss_between = sum(len(g) * ((sum(g) / len(g)) - grand) ** 2 for g in groups.values())
    return ss_between / ss_total if ss_total > 0 else 0.0
```

- [ ] **Step 1: Write failing tests**

```python
"""A39: concentration statistics (no I/O)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from diagnostics.attention_concentration import (  # noqa: E402
    gini, top_share, between_team_r2)


def test_gini_known_value():
    # [0,0,10]: sum|diff| over ordered pairs = 40; mean=10/3
    # G = 40 / (2*9*10/3) = 0.6667
    assert gini([0, 0, 10]) == pytest.approx(2 / 3)


def test_gini_equality_is_zero():
    assert gini([5, 5, 5, 5]) == pytest.approx(0.0)


def test_top_share():
    assert top_share([1, 1, 1, 7], 1) == pytest.approx(0.7)


def test_between_team_r2_extremes():
    # identical within teams, different across -> R2 = 1
    assert between_team_r2([1, 1, 9, 9], ["A", "A", "B", "B"]) == pytest.approx(1.0)
    # identical everywhere -> ss_total = 0 -> 0.0 guard
    assert between_team_r2([3, 3, 3, 3], ["A", "A", "B", "B"]) == 0.0
```

- [ ] **Step 2: Verify failure**, **Step 3: implement** (pure functions above + `main()` computing the six A39 statistics, log1p applied ONLY in the ANOVA per the amendment, bootstrap with seed 20260526, report writer per `diagnostics/` conventions; `engagement_raw` secondary row skipped with a notice when `oaq_pilot.csv` predates Phase 2), **Step 4: `pytest -q` green**.
- [ ] **Step 5: Commit** — `git commit -m "marchand_index: A39 concentration diagnostic + tests"`. Add `python diagnostics/attention_concentration.py` to the Airtight §E diagnostics list.

---

### Task 6: Citation and framing kit (poster related-work content — paste-ready)

**Files:**
- Create: `Full Project Files/docs/poster_related_work.md`

**Why this is written HERE and not left to the implementing model:** citations are the single highest hallucination-risk content class for any LLM. The list below was written from a stronger model's knowledge and each entry must still be VERIFIED by web search (title + first author + venue + year must all match a real record) before poster print. The implementing model must not add, substitute, or "improve" citations from memory.

- [ ] **Step 1: Create the file with exactly this content:**

```markdown
# Poster related-work + framing kit (verify every entry before print)

## Verification protocol (execute per entry)
Web-search "<first author> <year> <title fragment>"; confirm title, venue, year.
Mark [ ] -> [x] with the verification URL. An entry that fails verification is
REMOVED, not repaired from memory. No new citations may be added without the
same protocol.

## Framing spine (poster intro / method panel, 3 sentences)
1. Economics has two canonical accounts of stardom: Rosen (1981) — convex returns
   to talent — and Adler (1985) — popularity that snowballs beyond talent
   differences. The Marchand Index operationalizes the Adler residual for NHL
   skaters: attention NOT explained by skill, measured as attention-over-expected
   against K=10 skill-matched peers ("over expected", the xG convention).
2. The market adjustment is the park factor of attention: team context inflates a
   player's raw numbers; λ controls how much of that inflation travels with him.
3. Rosen's convexity is also why star-tier matching bias is EXPECTED (the A27
   diagnostic exists because theory predicts it, not as an afterthought).

## Citations

### Superstar economics (framing)
- [ ] Rosen, S. (1981). "The Economics of Superstars." American Economic Review
      71(5), 845–858.  USE: intro framing; A27 theoretical grounding; A39 panel.
- [ ] Adler, M. (1985). "Stardom and Talent." American Economic Review 75(1),
      208–212.  USE: the OAQ construct = empirical Adler residual (intro).
- [ ] Lazear, E. & Rosen, S. (1981). "Rank-Order Tournaments as Optimum Labor
      Contracts." Journal of Political Economy 89(5), 841–864.
      USE: A39 payroll-vs-attention concentration contrast (one clause).

### Star power in sports (related work / differentiation)
- [ ] Hausman, J. & Leonard, G. (1997). "Superstars in the National Basketball
      Association: Economic Value and Policy." Journal of Labor Economics 15(4),
      586–624.  USE: prior work measures star externalities in revenue terms; we
      measure the attention side and validate on purchase behavior (jersey lists).
- [ ] Berri, D., Schmidt, M. & Brook, S. (2004). "Stars at the Gate: The Impact
      of Star Power on NBA Gate Revenues." Journal of Sports Economics 5(1),
      33–50.  USE: same panel, second anchor.
- [ ] Müller, O., Simons, A. & Weinmann, M. (2017). "Beyond crowd judgments:
      Data-driven estimation of market value in association football." European
      Journal of Operational Research 263(2), 611–624.
      USE: expected_cap = deliberately simple market-value regression; the
      soccer literature does the same with richer features (limitations panel).
- [ ] Rosen, S. (1974). "Hedonic Prices and Implicit Markets." Journal of
      Political Economy 82(1), 34–55.  USE: one-word lineage tag ("hedonic")
      for expected_cap; OPTIONAL — cut first if space is tight.

### Measurement validity of the composite components (method panel footnote)
- [ ] Choi, H. & Varian, H. (2012). "Predicting the Present with Google Trends."
      Economic Record 88(s1), 2–9.  USE: Trends as validated economic signal.
- [ ] Mestyán, M., Yasseri, T. & Kertész, J. (2013). "Early prediction of movie
      box office success based on Wikipedia activity big data." PLOS ONE 8(8),
      e71226.  USE: Wikipedia pageviews as validated attention/demand proxy.
- [ ] Priem, J., Taraborelli, D., Groth, P. & Neylon, C. (2010). "Altmetrics: a
      manifesto."  USE: precedent for weighted multi-platform attention
      composites (one clause beside the A12 weight table).

### Methods (cited where the method appears)
- [ ] MacKinlay, A.C. (1997). "Event Studies in Economics and Finance." Journal
      of Economic Literature 35(1), 13–39.  USE: A38 diagnostic construction.
- [ ] Bell, A., Smith, J., Sabel, C.E. & Jones, K. (2016). "Formula for success:
      Multilevel modelling of Formula One driver and constructor performance,
      1950–2014." Journal of Quantitative Analysis in Sports 12(2).
      USE: A39 between-team variance share (driver-vs-car decomposition analog).
(Abadie & Imbens 2011, Politis–Romano, Duan 1983, Hanley & McNeil 1982,
Hosmer–Lemeshow, Benjamini–Hochberg, Phipson & Smyth 2010, Nosek et al. 2018 are
already mandated by the airtight plan's amendments — keep them there.)

## One-line translations for a hockey-analytics audience (poster copy, use verbatim)
- "OAQ is attention over expected — the xG construction applied to fame."
- "The market adjustment is a park factor for attention."
- "The index asks Adler's question with hockey data: how much stardom is left
  after talent is matched away?"
```

- [ ] **Step 2: Commit** — `git commit -m "marchand_index: poster related-work + framing kit (verification required)"`.
- [ ] **Step 3 (poster phase):** run the verification protocol on every entry; then hand the verified list to the poster-copy task alongside the sibling plan's Task 8 conformance crosswalk.

---

## Evaluated and REJECTED cross-domain ideas (recorded so no future session re-derives)

| Idea (source domain) | Why rejected |
|---|---|
| Elo/TrueSkill-style dynamic attention ratings (chess/gaming) | Time-dynamic model = rehaul; window is locked as a fixed 365-day aggregate. |
| RAPM/regularized plus-minus style attention regression (NBA) | Replaces the peer-matching METHOD — the poster's named contribution. Rehaul. |
| Oaxaca–Blinder decomposition lens (labor econ) | A27's regression-based bc lens IS the regression analog; a second one adds a forking path for zero new information. |
| Betting-market prices as a validation outcome (sports econ) | Measures expected performance, not fan attention — construct mismatch; odds-history APIs are paywalled/ToS-grey. |
| MVP/award-vote modelling as a new validation gate (baseball) | Award votes mix skill + narrative; construct-impure as an attention outcome; a new gate is scope creep when Gate-4 is already load-bearing. |
| Q Score / Davie Brown celebrity-index replication (marketing) | Proprietary data; kept only as a differentiation sentence in related work. |
| Transfermarkt-style crowd valuation scrape (soccer) | No NHL equivalent with free player-level attention pricing; Müller et al. citation carries the idea at $0. |
| TV-ratings star effects (Hausman-Leonard replication) | Nielsen data is paid; jersey lists + Gate-4 already cover the attention-value premise at $0. |
| Spotify/music popularity-vs-listeners stock-flow ideas | Stock-vs-flow already resolved by A12 (Instagram removal rationale). |
| Herfindahl of per-player THEME shares (media econ) | H1–H4/theme layer is explicitly deferred; touching it reopens deferred scope. |

## Sequencing

| Task | When |
|---|---|
| 1 (A38 text), 4 (A39 text) | Phase-0 tail, after sibling A37; MUST precede Phase-2 compute; Reddit still 0/774 |
| 2 (mover list + dates) | Parallel with Airtight Phase 1 (it is fetch-light + web lookups) |
| 3, 5 (diagnostic scripts + tests) | Any time after their amendment commits; EXECUTION of both scripts joins the Airtight §E diagnostics step, immediately after the one-shot compute |
| 6 (citation kit) | Any time; verification protocol runs at poster phase |

**Airtight-plan touchpoints (one commit):** add `python diagnostics/lambda_portability.py` and `python diagnostics/attention_concentration.py` to §E's diagnostics list; extend §H's designated-panel sentence to name the A38 diagnostic and A39 panel; add A38/A39 lines to the §I checklist. Commit: `marchand_index: register A38/A39 in airtight plan (SE/SH/SI)`.

**Guardrails:** the sibling plan's guardrail section applies verbatim. One addition: if the A38 mover count after exclusions is < 10, the diagnostic is still run and reported with an "n too small to anchor" sentence — do NOT loosen the window or sourcing rules to grow n.
