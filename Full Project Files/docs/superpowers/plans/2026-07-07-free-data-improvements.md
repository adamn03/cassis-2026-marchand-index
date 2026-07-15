# Free-Data Improvements Implementation Plan (supplement to the Airtight Execution Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two low-risk, $0, pre-registered data-quality amendments (A36 player-wiki redirect summation, A37 V1b jersey-list union completion) plus four execution pre-chews (A31 shipping-matrix rows 3–7, BH mechanics pins, Gate-4 quota manifest, source-URL archival) so a weaker model can execute the production run without inventing judgment content.

**Architecture:** This plan SUPPLEMENTS `Full Project Files/docs/airtight_execution_plan.md` v1.1 (panel-approved). It changes NOTHING in that plan's A21–A35 / G4-A1–A3 specifications. New amendments continue the impl numbering (A36, A37) and slot at the END of Phase 0; the pre-chews are ready-to-paste content for tasks that plan already defines. Everything here must land while Reddit is 0/774 (same governing rule).

**Tech Stack:** Python 3 (stdlib + requests via `_common.session`), pytest, Wikimedia REST + MediaWiki Action APIs, git.

## Global Constraints

- **$0 budget; free APIs only; polite rate limits** (existing `time.sleep(0.2)` pattern; `_common.session` cache).
- **Amendment before code:** each amendment's prereg text is committed BEFORE its implementation code. Commit convention: `marchand_index: A<N> <one-line summary>` then `marchand_index: A<N> code + tests`.
- **Reddit must still be 0/774** when A36/A37 land. If any production Reddit data exists, STOP and report — do not log these amendments post-compute.
- **Invariants (never change):** seed `20260526`; A12 weights (wiki_en .29 / wiki_intl .11 / r_mentions .27 / r_upvotes .17 / trends .16); window constants `WINDOW_START="20250418"` / `WINDOW_END="20260417"`; K=10; λ=0.5; the 774-player pool (`players.csv`); all §9/A6 validation floors.
- **Atomic writes:** `.tmp` → rename via `_common.atomic_write_csv` only.
- **Run tests from inside `Full Project Files/marchand_index/` with `pytest -q`** (102 passing at plan time; each task states its expected additions).
- **Prereg-impl** = `Full Project Files/marchand_index/preregistration.md`. Every amendment carries the standard §13 anti-tuning compliance paragraph (see A15/A16 for the pattern) — date, mechanical rule, honest residuals, statement that weights/floors/pool/window are unchanged, statement that Reddit is 0/774.
- **Paths in this doc** are relative to `Full Project Files/` unless absolute.

## Sequencing relative to the Airtight Plan

Execute Airtight Plan Phase 0 (A21–A35, G4-A1–A3) exactly as written there. Then:

| This plan's task | When |
|---|---|
| Task 1–2 (A36) | After A35; parallel-safe with Airtight Phase 1 (trends resume etc.); MUST finish before Phase 2 compute |
| Task 3–4 (A37) | After A36 amendment commit (independent of A36 code); MUST finish before Phase 2 compute |
| Task 5 (A31 pre-chew) | Consumed WHILE writing A31 per Airtight §B — paste, don't invent |
| Task 6 (Gate-4 manifest) | With Airtight Phase 3 launch (right after G4-A1..A3) |
| Task 7 (URL archival) | Any time; cheap; do early |
| Task 8 (conformance crosswalk) | Poster phase (post-Phase-2); tracked here so it isn't lost |

---

### Task 1: A36 amendment text — player-article redirect-title pageview summation

**Files:**
- Modify: `marchand_index/preregistration.md` (append after A20 / after any A21–A35 entries already present)

**Interfaces:**
- Produces: the pre-registered rule Task 2 implements. Task 2 must match this text mechanically.

**Why (context for the implementer):** `fetch_wikipedia.py` resolves each player to a canonical title (A1) but fetches pageviews for the canonical title ONLY. The Wikimedia pageviews API does not follow redirects, so views landing on redirect titles are silently dropped. A1 itself measured the size of this class (the `Alex_Ovechkin` redirect alone carried 7,059 in-window views that are currently uncounted). Airtight-plan A29.2 already adopts redirect summation for the 32 TEAM articles with the rationale "views to a redirect title are legitimate views" — leaving the 774 player articles (composite weight 0.29 en + 0.11 intl) on canonical-only counting is both an undercount and an internal inconsistency a hostile judge can poke. The undercount is non-uniform: heaviest for nickname redirects (Ovechkin), accent-folded redirects (Fehérváry), and any article renamed inside the window (the Utah Mammoth failure class, where the old title carries months of full traffic).

- [ ] **Step 1: Append the amendment text below to prereg-impl** (adjust the A-number only if A36 is already taken by the time this runs; then cascade A37→next free):

```markdown
**A36 (YYYY-MM-DD) — Player Wikipedia pageviews: redirect-title summation (en + intl),
extending the A29-class team rule to the 774 player articles. Logged BEFORE the
augmentation fetch; Reddit remains 0/774.**

The Wikimedia pageviews API counts views against the exact title requested and does
not follow redirects (A1). The en fetch (§3.1/A1/A14) and intl fetch (A12) therefore
count only canonical-title views and drop views landing on redirect titles — a class
A1 itself measured (the `Alex_Ovechkin` redirect carried 7,059 in-window views). The
team-outcome amendment (A29) already adopts canonical+redirect summation for the 32
team articles ("views to a redirect title are legitimate views"); this amendment
applies the identical rule to the player articles, which carry §4/A12 weight 0.29
(wiki_en) + 0.11 (wiki_intl).

**Mechanical rule (applied identically to all 774; no identity re-resolution):**
1. Identity is LOCKED to the existing `wikipedia_slug_chosen` / `wikidata_qid` in
   `raw/wiki_pageviews.csv` (A1 + A19-audited) and the existing per-edition titles in
   `raw/wiki_intl_pageviews.csv` (`per_edition_json`). No slug is re-chosen; rows with
   `wiki_match = none` stay NULL, untouched.
2. For each canonical title, enumerate its redirect titles via the corresponding
   edition's MediaWiki API (`action=query&prop=redirects&rdlimit=max`, batched ≤50
   titles per request, following `continue`). Redirect titles containing
   "(disambiguation)" (case-insensitive, any language's title copied verbatim) are
   excluded.
3. Fetch in-window daily pageviews [2025-04-18, 2026-04-17] for the canonical title
   AND every enumerated redirect title; sum per calendar day (merge by the API item
   `timestamp`, not by list position — the API omits zero days). The player's
   `wiki_12mo` / `wiki_intl_12mo` becomes the summed total; the §10 bootstrap daily
   vector becomes the per-day-summed vector, **zero-filled to the full 365-day
   window** (index 0 = 2025-04-18 … index 364 = 2026-04-17; days the API omits are
   true zero-view days). Zero-filling aligns the stored vectors with the A26 block
   bootstrap, which already treats them as 365-day rings, and gives every vector a
   deterministic date index.
4. New audit columns in `raw/wiki_pageviews.csv`: `n_redirect_titles`,
   `redirect_views_12mo`, `redirect_share` (= redirect/total, 0 when total = 0);
   equivalents in `raw/wiki_intl_pageviews.csv` aggregated over editions. The top-10
   players by `redirect_share` and the pool-level mean share are reported in
   `results.md` so any surprise (an in-window rename) is visible — mirroring A29's
   per-team redirect-share report.
5. Any future full wiki re-fetch must include this summation (in addition to the
   A19 P3522-first identity rule).

**Honest residuals (disclosed in advance):** (i) a redirect retargeted mid-window
credits all its views to its fetch-date target (rare; direction unknowable at $0);
(ii) redirect enumeration reflects fetch-date redirect existence — redirects deleted
before fetch are missed (undercount persists, smaller); (iii) pageview-API 404 for a
redirect title contributes zero (clean skip).

**Anti-tuning compliance (§13):** uniform, mechanical data-collection completion
decided on measurement-validity and A29-consistency grounds; logged before the
augmentation fetch, while Reddit is 0/774 and no production composite exists; keyed
on article identity only, never on any player's resulting pageviews or rank;
weights (§4/A12), peer features (§6/A13), λ (A5), denominators (A4/A8), pool
(§2/A10), window (A11/A14), and all validation floors (§9, A6/V3) unchanged. The
pre-A36 `wiki_pageviews.csv` / `wiki_daily.csv` / `wiki_intl_pageviews.csv` /
`wiki_intl_daily.csv` are retained in git history per §13.
```

- [ ] **Step 2: Commit**

```bash
git add "Full Project Files/marchand_index/preregistration.md"
git commit -m "marchand_index: A36 player-wiki redirect-title summation (en+intl)"
```

---

### Task 2: A36 implementation — `augment_wiki_redirects.py`

**Files:**
- Create: `marchand_index/augment_wiki_redirects.py`
- Test: `marchand_index/tests/test_augment_wiki_redirects_a36.py`
- Rewrites at runtime (atomic): `marchand_index/raw/wiki_pageviews.csv`, `raw/wiki_daily.csv`, `raw/wiki_intl_pageviews.csv`, `raw/wiki_intl_daily.csv`

**Interfaces:**
- Consumes: existing CSVs above; `_common.session`, `_common.atomic_write_csv`, `_common.RAW_DIR`, `_common.CONTACT_UA`, `_common.load_csv`.
- Produces: same CSV schemas + the three new audit columns (`n_redirect_titles`, `redirect_views_12mo`, `redirect_share`). `compute_oaq.py` reads columns by name and needs NO changes — verify that in Step 6.

Pure functions to implement and test (module level, no I/O):

```python
WINDOW_START = "20250418"
WINDOW_END = "20260417"

def parse_redirects(api_json: dict) -> dict[str, list[str]]:
    """MediaWiki prop=redirects response -> {canonical_title: [redirect titles]}.
    Excludes titles containing '(disambiguation)' case-insensitively."""
    out: dict[str, list[str]] = {}
    for pg in api_json.get("query", {}).get("pages", {}).values():
        title = pg.get("title", "")
        rds = [r["title"] for r in pg.get("redirects", [])
               if "(disambiguation)" not in r["title"].lower()]
        if title:
            out.setdefault(title, []).extend(rds)
    return out

def merge_daily_by_date(series: list[list[tuple[str, int]]]) -> list[tuple[str, int]]:
    """Sum multiple (timestamp 'YYYYMMDD00', views) series per calendar day.
    Returns date-sorted list. Handles missing days (API omits zero days)."""
    acc: dict[str, int] = {}
    for ser in series:
        for ts, v in ser:
            acc[ts] = acc.get(ts, 0) + v
    return sorted(acc.items())
```

Fetch-side flow in `main()` (mirror `fetch_wikipedia.py` politeness: `session(expire_hours=24)`, sleep 0.2 s between pageview calls, sleep 0.15 s between MediaWiki calls, print one progress line per player):

1. Load `raw/wiki_pageviews.csv`. Titles = `wikipedia_slug_chosen` with `wiki_match != "none"` (underscores → spaces).
2. Enumerate redirects for all titles: batch ≤50 titles per `action=query&prop=redirects&rdlimit=max&format=json` call against `https://en.wikipedia.org/w/api.php`, following the `continue` / `rdcontinue` token until absent.
3. Per player: fetch canonical daily series with timestamps (same REST URL pattern as `fetch_wikipedia.py:fetch_views` but keep `(item["timestamp"], item["views"])` pairs); fetch each redirect title's series (404 → skip); `merge_daily_by_date`; totals: `wiki_12mo = sum(all)`, `redirect_views_12mo = wiki_12mo − canonical_total`, `redirect_share = redirect_views_12mo / wiki_12mo if wiki_12mo else 0.0`.
4. Sanity check per player: re-fetched canonical total must equal the stored `wiki_12mo` (historical window is deterministic). On mismatch print a `RESTATED` warning line with both values and continue (Wikimedia occasionally restates history; count reported in the final summary).
5. Rewrite `wiki_pageviews.csv` (existing columns + 3 new) and `wiki_daily.csv` (`daily_views` = merged per-day sums zero-filled to exactly 365 entries, index 0 = 2025-04-18, joined with `|`; `n_days` = 365 for every fetched row) atomically. The A38 diagnostic (sibling plan `2026-07-07-cross-domain-improvements.md`) depends on this date-indexed layout — do not skip the zero-fill.
6. Repeat for intl: titles per edition from `per_edition_json` in `raw/wiki_intl_pageviews.csv`; enumeration against `https://{code}.wikipedia.org/w/api.php`; rows keyed `(player_id, edition)` in `wiki_intl_daily.csv`; per-player aggregate audit columns in `wiki_intl_pageviews.csv` (`wiki_intl_12mo` = sum over editions of merged totals).
7. Final summary print: pool mean `redirect_share`, top-10 players by share, count of RESTATED canonicals, count of redirect titles fetched.

- [ ] **Step 1: Write failing tests**

```python
"""A36: redirect enumeration + per-date summation (pure functions only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from augment_wiki_redirects import parse_redirects, merge_daily_by_date  # noqa: E402


def test_parse_redirects_extracts_and_filters_disambig():
    api_json = {"query": {"pages": {
        "1": {"title": "Alexander Ovechkin", "redirects": [
            {"title": "Alex Ovechkin"},
            {"title": "Ovechkin (disambiguation)"},
            {"title": "Alexander Owetschkin"},
        ]},
        "2": {"title": "Sidney Crosby"},  # no redirects key
    }}}
    out = parse_redirects(api_json)
    assert out["Alexander Ovechkin"] == ["Alex Ovechkin", "Alexander Owetschkin"]
    assert out["Sidney Crosby"] == []


def test_merge_daily_by_date_sums_and_handles_gaps():
    canonical = [("2025041800", 100), ("2025041900", 120), ("2025042100", 90)]
    redirect = [("2025041900", 5), ("2025042000", 7)]
    merged = merge_daily_by_date([canonical, redirect])
    assert merged == [("2025041800", 100), ("2025041900", 125),
                      ("2025042000", 7), ("2025042100", 90)]


def test_merge_daily_by_date_empty_inputs():
    assert merge_daily_by_date([]) == []
    assert merge_daily_by_date([[], [("2025041800", 3)]]) == [("2025041800", 3)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_augment_wiki_redirects_a36.py -v` (from inside `marchand_index/`)
Expected: FAIL / ERROR with `ModuleNotFoundError: No module named 'augment_wiki_redirects'`

- [ ] **Step 3: Implement `augment_wiki_redirects.py`** — the two pure functions exactly as specified above plus the `main()` flow (steps 1–7). Follow `fetch_wikipedia.py` for imports, session use, UA header, and atomic-write pattern; follow `fetch_wikipedia_intl.py` for the intl edition loop and `per_edition_json` parsing.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q`
Expected: previous count + 3 passing, 0 failures.

- [ ] **Step 5: Dry-run on 5 players** — temporarily run with a `--limit 5` flag (implement it: process only first N rows, write to `raw/_a36_dryrun_*.csv` instead of the real files when `--limit` given). Inspect: Ovechkin-class players show non-zero `redirect_share`; no exceptions; RESTATED count 0 or explained.

- [ ] **Step 6: Full run + compute-compat check**

```bash
python augment_wiki_redirects.py
python - <<'EOF'
import csv
rows = list(csv.DictReader(open('raw/wiki_pageviews.csv', encoding='utf-8')))
assert len(rows) == 774, len(rows)
assert {'n_redirect_titles','redirect_views_12mo','redirect_share'} <= set(rows[0])
EOF
pytest -q
```
Expected: 774 rows, new columns present, all tests green. Also confirm `compute_oaq.py` loads these CSVs by column NAME (grep for `wiki_12mo`, `daily_views`) — no code change needed; if it indexes positionally anywhere, STOP and report before touching it.

- [ ] **Step 7: Commit**

```bash
git add "Full Project Files/marchand_index/augment_wiki_redirects.py" "Full Project Files/marchand_index/tests/test_augment_wiki_redirects_a36.py" "Full Project Files/marchand_index/raw/wiki_pageviews.csv" "Full Project Files/marchand_index/raw/wiki_daily.csv" "Full Project Files/marchand_index/raw/wiki_intl_pageviews.csv" "Full Project Files/marchand_index/raw/wiki_intl_daily.csv"
git commit -m "marchand_index: A36 code + tests + augmented wiki data"
```

---

### Task 3: A37 amendment text — V1b jersey-list union completion sweep

**Files:**
- Modify: `marchand_index/preregistration.md` (append after A36)

**Why:** V1b is the SOLE confirmatory primary (Airtight A31.1) with only 12 positives → a wide AUC CI is the single most likely cause of a headline downgrade (shipping-matrix row 2). The V1b membership rule is already a UNION over official NHL/Fanatics best-selling-jersey lists for seasons 2023-24 / 2024-25 / 2025-26 (A3 + A20) — but only 3 lists have ever been retrieved. The league publishes such lists more than once per season (e.g., "top sellers since the season began" mid-season PR items). A pre-declared, mechanical retrieval sweep completes the data collection under the LOCKED rule class; every additional positive tightens the primary's CI. Both directions are possible (new members could raise or lower AUC) — that is what makes it kosher.

- [ ] **Step 1: Append the amendment text below** (the sweep may NOT run before this text is committed — adoption must be non-discretionary):

```markdown
**A37 (YYYY-MM-DD) — V1b union completion: pre-declared retrieval sweep for ALL
official best-selling-jersey lists in seasons 2023-24 / 2024-25 / 2025-26. Logged
BEFORE the sweep runs; Reddit remains 0/774.**

A3/A20 define V1b membership as the union of official NHL/Fanatics best-selling-
jersey lists over the three named seasons, but only three lists have been retrieved
(A3's two + A20's 2025-26 top-10), giving n = 12 in-pool positives for the sole
confirmatory primary. This amendment pre-declares a retrieval sweep that completes
the union under the SAME class rule. It changes no floor, no test statistic, and no
definition — it completes data collection for an already-locked outcome.

**Qualification rule (mechanical; fixed before the sweep):** a list qualifies iff ALL of:
1. League-wide (not one team's store, not a per-team breakdown);
2. Attributed to NHL, NHL PR, NHLPA, NHL Shop, or Fanatics as the data source;
3. Player-level ranked list or top-N membership list;
4. Coverage period lies within one of the seasons 2023-24, 2024-25, 2025-26
   (full-season, partial-season, or since-a-stated-date lists all qualify);
5. Corroborated by ≥2 independent URLs (the A20 pattern), captured in
   `marchand_index/external_outcomes_sources.md`.

**Adoption is all-or-none:** EVERY list found that qualifies is adopted; no
discretionary selection. Membership = appeared on ANY adopted list (same union
semantics). Join is NHL-id-keyed per the A20 namesake guard. A list that fails any
clause is recorded in the sources doc with the failing clause, not silently skipped.

**Search manifest (fixed; execute every line; record hit/no-hit per line):**
- Web search: `site:nhl.com "best-selling" OR "top-selling" jerseys` (each season year pair)
- Web search: `NHL PR top selling jerseys 2024`, `... 2025`, `... 2026`
- Web search: `Fanatics NHL best selling jerseys list 2024 / 2025 / 2026`
- Web search: `NHLPA most popular jerseys 2024 / 2025 / 2026`
- Wayback Machine (web.archive.org): snapshots of `shop.nhl.com` "top sellers" /
  "best sellers" landing pages within each season's date range (note: retailer
  category pages are dynamic inventory, NOT ranked lists — they qualify ONLY if a
  snapshot shows an explicit ranked/top-N editorial list; record the verdict)
- Web search: `"top-selling jerseys" NHL midseason 2023-24 / 2024-25 / 2025-26`

**Outcome handling:** rebuild `raw/external_outcomes.csv` with the enlarged union;
report old n (12) and new n; if the sweep finds nothing new, log the null result
here (sweep executed, zero qualifying additions) and V1b proceeds at n = 12
exactly as before.

**Honest residuals:** press-reported lists inherit outlet transcription risk
(mitigated by the ≥2-URL rule); partial-season lists overweight early-season
sellers; the union remains temporally impure for the two pre-window seasons
exactly as A31.3/§G already disclose.

**Anti-tuning compliance (§13):** the qualification rule and search manifest are
fixed and committed before any search result is seen; adoption is all-or-none, so
no name can be cherry-picked in or out; outcome lists are independent of all model
inputs (wiki/Reddit/Trends); logged while Reddit is 0/774 and no production OAQ or
V1b exists, so no result could have influenced the rule; floors, AUC construction,
bootstrap (per A31.1), weights, pool, window unchanged. Pre-A37
`external_outcomes.csv` retained in git history per §13.
```

- [ ] **Step 2: Commit**

```bash
git add "Full Project Files/marchand_index/preregistration.md"
git commit -m "marchand_index: A37 V1b union-completion sweep (pre-declared)"
```

---

### Task 4: A37 execution — run the sweep, rebuild outcomes

**Files:**
- Modify: `marchand_index/external_outcomes_sources.md` (append findings, hit/no-hit per manifest line, ≥2 URLs per adopted list)
- Modify: `marchand_index/fetch_external_outcomes.py` (only if adopted lists exist: add them to the jersey-union input — follow the existing A20 list-encoding pattern in that file)
- Rewrite at runtime: `marchand_index/raw/external_outcomes.csv`
- Test: `marchand_index/tests/test_external_outcomes_a20.py` (extend)

**Interfaces:**
- Consumes: the A37 manifest (Task 3), existing `fetch_external_outcomes.py` union builder.
- Produces: `external_outcomes.csv` with final V1b membership; the in-pool positive count that A31/V1b consumes.

- [ ] **Step 1: Execute every manifest line** (WebSearch/WebFetch or browser). For each hit, capture: publisher, publication date, coverage period, full ranked list, 2+ URLs. Apply the 5 qualification clauses mechanically; record verdicts in `external_outcomes_sources.md`.
- [ ] **Step 2: If zero qualifying additions:** append the null-result note to the A37 entry ("sweep executed YYYY-MM-DD, zero qualifying additions"), commit (`marchand_index: A37 sweep executed — null result`), and STOP this task (skip steps 3–5).
- [ ] **Step 3: Write failing test** — extend `test_external_outcomes_a20.py` with a fixture asserting a player appearing ONLY on a newly adopted list gets `jersey_member = 1` (mirror the existing union-fixture style in that file), and that the namesake guard still keys on NHL id.
- [ ] **Step 4: Add the adopted list(s) to `fetch_external_outcomes.py`** following the existing per-list encoding pattern; run `python fetch_external_outcomes.py`; verify: printed old n → new n; `pytest -q` green.
- [ ] **Step 5: Commit**

```bash
git add "Full Project Files/marchand_index/fetch_external_outcomes.py" "Full Project Files/marchand_index/tests/test_external_outcomes_a20.py" "Full Project Files/marchand_index/raw/external_outcomes.csv" "Full Project Files/marchand_index/external_outcomes_sources.md"
git commit -m "marchand_index: A37 sweep executed — union rebuilt (n=<old>-><new>)"
```

---

### Task 5: A31 pre-chewed content (ready-to-paste; do NOT invent alternatives)

**Files:**
- Consumed by: the A31 amendment written per Airtight Plan §B (in `marchand_index/preregistration.md`).

Airtight A31.6 requires the amendment to contain the full 8-row shipping matrix but only words rows 1, 2, 8. Rows 3–7, the BH mechanics, and one optional clause are pre-drafted HERE. When writing A31, paste this content verbatim (placeholder n=12 becomes the post-A37 count).

**Definitions (paste into A31):** `V1b-strong` = point AUC ≥ 0.70 AND 95% stratified-bootstrap CI excludes 0.50. `V1b-point` = point AUC ≥ 0.70, CI includes 0.50. `V1b-fail` = point AUC < 0.70. `Secondary-pass` = ≥2 of {V1a, V2, V3} meet their pre-registered floors (BH governs only the "statistically supported after multiplicity control" label, per A31.2). `G4-pass` = pooled outside-star floor met per docs/preregistration.md §8.

**Shipping-matrix rows 3–7 (rows 1, 2, 8 already worded in Airtight A31.6):**

| Row | V1b | Secondary | Gate-4 | Headline tier |
|---|---|---|---|---|
| 3 | strong | pass | fail | "OAQ_portable separated the N official jersey-list players from the other 774−N skaters with AUC = X.XX (95% CI a–b), replicated across the secondary fan-vote family. The pre-registered outside-star generalization test did not meet its floor: validity is claimed for the star tier only." Depth/Reaves-archetype framing removed; honest pathway count = 2, stated on the poster. |
| 4 | strong | fail | pass | "OAQ_portable separated the N official jersey-list players ... with AUC = X.XX (95% CI a–b), and generalized to an outside-star YouTube attention test. The secondary fan-vote family did not clear its pre-registered floors and is reported as unsupported." Pathway count = 2 (jersey + YouTube). |
| 5 | strong | fail | fail | Headline = the AUC sentence ONLY, no replication clause. Poster carries verbatim: "Validated on a single external pathway (jersey-list membership); no independent replication was achieved. The pre-registered ≥3-pathway standard was not met." |
| 6 | fail | pass (and/or G4 pass) | any | No validation language in the headline under any combination. Validation panel reports all estimates + CIs; any secondary/G4 passes carry the fixed label "isolated secondary signal — not interpretable as validation absent the confirmatory primary." Index framed as an exploratory descriptive instrument. |
| 7 | any | any | NO-GO / not run | OVERLAY row: take the tier from rows 1–6 using V1b + Secondary alone, then (a) delete any generalization clause, (b) cap the stated pathway count at 2, (c) add verbatim: "The pre-registered outside-star generalization test was not run; external validity outside the star tier is untested." |

**BH mechanics pins (paste into A31.2):** one-sided directions — V1a: ρ > 0; V2: statistic > its null (AUC > 0.5 / ρ > 0 per its post-A33 form); V3: ρ > 0. P-values by Monte-Carlo permutation, 100,000 permutations, seed 20260526, additive-smoothed `p = (1 + #{perm ≥ observed}) / (1 + 100000)` (Phipson & Smyth 2010). V1a permutes the n=10 outcome ranks; V2 permutes membership labels; V3 permutes the 32 team labels. BH step-up at q = 0.05 across exactly these three.

**Optional clause (include unless the owner objects — reporting-only):** V1b additionally reports the one-sided Mann-Whitney U p-value (asymptotic, continuity-corrected; `scipy.stats.mannwhitneyu(..., alternative="greater")`) as a descriptive companion to the bootstrap CI. It is NOT a gate and appears only in the validation panel.

- [x] **Step 1:** When executing Airtight §B A31, paste the three blocks above into the amendment. Mark this task complete in the same commit. — DONE 2026-07-15 (A31 committed with definitions, rows 3–7, BH pins, MWU clause verbatim).

---

### Task 6: Gate-4 quota manifest + resumable fetch state (execution note, no rule changes)

**Files:**
- Create: `marchand_index/g4_query_manifest.csv` (generated)
- Create: `marchand_index/build_g4_manifest.py`

**Constraints (transport-level only — sampling frame, allow-list, dedup, snapshot rule all stay per `docs/preregistration.md` §5–§8 as amended by G4-A1..A3; this task adds ZERO selection logic):**

- YouTube Data API free quota = 10,000 units/day; `search.list` = 100 units, `videos.list` = 1 unit per call (≤50 ids). Budget ≤95 searches/day + reserve for `videos.list`.
- [ ] **Step 1:** `build_g4_manifest.py` emits one row per (player × allow-listed-channel query) required by §6–§7: columns `player_id, full_name, band, query, priority, status`. Priority: outside-star cohort (regular + depth bands) FIRST — they are load-bearing for the pooled gate; star band last. Print: total queries, est. fetch days at 95 searches/day.
- [ ] **Step 2:** The Gate-4 fetcher (built per Airtight Phase 3) must read/update `status` in this manifest as its resume state, so a mid-run quota exhaustion or crash resumes exactly (no re-spend). Snapshot date D is locked on the FIRST fetch day per prereg-spec §6 and recorded in the manifest header comment.
- [ ] **Step 3:** Commit manifest builder + generated manifest before the fetch launches: `git commit -m "marchand_index: Gate-4 quota manifest + resume state"`.

---

### Task 7: Source-URL archival (reproducibility insurance)

**Files:**
- Modify: `marchand_index/external_outcomes_sources.md`, `marchand_index/market_proxy_sources.md`

The V1/V2 outcome sources are X posts and small outlets (HockeyFeed, NHLTradeRumor, RMNB) — real link-rot risk before the September poster QA.

- [ ] **Step 1:** For every URL in both sources docs (plus any added by A33/A37): request `https://web.archive.org/save/<url>` (politely, ~1 per 10 s; skip URLs already archived within 90 days — check `https://archive.org/wayback/available?url=<url>` first).
- [ ] **Step 2:** Append the resulting `web.archive.org/web/<ts>/<url>` snapshot link beside each original in the docs. X-post URLs often fail archiving — record `archive: failed (X)` honestly; the ≥2-independent-URL rule already covers them.
- [ ] **Step 3:** Commit: `git commit -m "marchand_index: archive outcome/market source URLs (Wayback)"`.

---

### Task 8: Abstract→poster conformance crosswalk (poster phase — tracked now, executed post-Phase-2)

**Files:**
- Create: `Full Project Files/docs/poster_conformance.md`

The accepted abstract (`Pilot Files/submission/abstract_v1.md`) makes specific promises the poster must honor. Two need active reconciliation with the A31 headline change:

- [ ] **Step 1:** Build a two-column table: every claim/promise sentence in the abstract → the poster section (or results.md artifact) that honors it. Flag any promise with no home.
- [ ] **Step 2:** Apply these two pre-decided reconciliations in poster copy:
  1. Abstract: "A single pre-registered headline metric — the hybrid Marchand Index — is reported." Poster: the hybrid MI remains the named headline METRIC of the index (its leaderboard appears in the descriptive per-dollar panel, "finalized on the whole-league rerun" exactly as promised); the quoted headline FINDING is the A31 validation sentence. The poster must contain one sentence making this relationship explicit.
  2. Abstract: "the leaguewide rerun (~700 active skaters) will recover power for these gates" — the validation panel must explicitly show the n growth (V1b 8→N positives, V1a 4→10, V2 4→post-A33 n) so the promise is visibly kept.
- [ ] **Step 3:** Commit: `git commit -m "marchand_index: abstract->poster conformance crosswalk"`.

---

## Evaluated and REJECTED (do not re-propose; reasons recorded so a future session doesn't re-derive them)

| Idea | Why rejected |
|---|---|
| Reddit comments via Arctic Shift / Pushshift-style archives | Changes the measured construct on 0.44 of locked A12 weight (submissions-only is pre-registered + disclosed, A35.4); ToS-grey; days of new fetch risk. Rehaul, not improvement. |
| Re-add Instagram followers (`fetch_instagram.py` exists) | A12 removed it deliberately (stock vs flow, fake-follower noise); anonymous instaloader access is dead (documented 0/160 403 in the pilot). |
| GDELT news volume | Already rejected in A12 — its ~3-month window cannot honor the A11 fixed window. |
| More Wikipedia language editions | wiki_intl whitelist + weights locked (A12). |
| 2026 All-Star fan vote for V2 | No 2026 ASG (Olympic break). A33's 2022+2023+2024 union stands. |
| NHLPA player poll as a validation pathway | Peer perception, not fan attention — construct mismatch. |
| Propagate peer-set uncertainty into the bootstrap | Panel settled on the A26 propagated/not-propagated disclosure table; a real fix is a design change. |
| Refactor `compute_oaq.py` (1,677 lines) | Zero-benefit risk before the one-shot production compute. Post-conference housekeeping at most. |
| Multiple YouTube API keys to speed Gate-4 | Quota circumvention — against ToS. The Task-6 manifest makes the ~8 days predictable instead. |

## Execution guardrails for the implementing model (read before every task)

1. **Never modify:** `players.csv` (locked pool), seed, A12 weights, window constants, λ, K, any §9/A6 floor, anything in `Pilot Files/`.
2. **Amendment text commits BEFORE implementation code.** No exceptions. If you notice the order was violated, stop and report — do not quietly fix history.
3. **Post-Phase-2 rule:** anything discovered after the one-shot compute is REPORTED, never fixed (Airtight §E). This includes bugs. Verbatim rule from the Airtight plan.
4. **Fetch failure playbook:** HTTP 429/403 → back off and resume the same transport; never swap transports or endpoints without a new amendment. Trends throttle → re-run `fetch_trends.py` (resumable). MediaWiki/Wikimedia 429 → double sleep values, continue.
5. **If a step's precondition fails** (file missing, count mismatch, test red) → STOP that task, report state, do not improvise a workaround.
6. **Trends first:** `raw/trends.csv` is at 331/774 — resume `python fetch_trends.py` (Airtight Phase 1.1) before or in parallel with Task 1; it is the longest-running data gap besides Reddit.
7. Every claim of completion needs the verification command output shown (pytest counts, row counts).
