# Phase A — Reddit Attention Affiliation Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For every pool player, compute what share of their Reddit attention comes from their own fanbase vs. rival fanbases vs. neutral venues, normalized for subreddit volume — with no sentiment classification and no LLM.

**Architecture:** Pure-function core (`affiliation.py`) holding venue mapping, player team-timeline reconstruction, mention labeling, and rate normalization; a thin I/O driver (`compute_affiliation.py`) that reads the existing corpus + CSVs, calls the core, and writes `attention_affiliation.csv`. No new data collection — every input already exists on disk.

**Tech Stack:** Python 3, pandas, numpy, pytest. Same conventions as the rest of `marchand_index/`.

---

## STATUS (2026-08-02) — Tasks 1–5 built, output NOT publishable

Tasks 1–5 are implemented; Tasks 6–7 were skipped. `attention_affiliation.csv`
is deliberately **untracked** because its `other_*` columns are invalid: A22
searched only r/hockey, r/nhl, r/fantasyhockey and own-team subs, so the rival
bucket came out at **3.1%** (max `rival_reach` = 3) when the real signal is
68,396 off-sub mentions across 756/771 players, median `rival_reach` 20.

**Two blockers, in order. Neither is optional and the order matters.**

| # | Blocker | Effect on this plan |
|---|---|---|
| **0** | **Defect 1 — first-name surname collisions** (Task 0 below) | Rewrites `raw/reddit_detail.csv`, this plan's primary input. Every Task 3–5 number is computed from contaminated attribution until it lands. |
| **1** | **Defect 2 — `allsubs_ids` never written out** | The rival split needs `raw/reddit_detail_allsubs.csv`, which does not exist yet. ~1 h. |

**Defect 1 must be fixed BEFORE Defect 2.** Opening the rival subs first would
multiply the collision across 31 more subreddits instead of 1.

Tasks 3–5 are the template for the corrected re-run — **do not delete this plan
until both blockers are cleared**, then delete per the owner's instruction.

## Global Constraints

- Working directory for all commands is `Full Project Files/marchand_index/`. `pytest` runs from inside that directory.
- Measurement window is `[2025-04-18, 2026-04-17]` inclusive (matches `CARRY-FORWARD` in SESSION.md). Mentions outside it are excluded.
- Atomic writes only: write `.tmp`, then `os.replace` to the final path. Vault convention, already implemented in `_common.py`.
- Team codes are the project's own set, **not** standard NHL abbreviations: `LA` (not LAK), `NAS` (not NSH), `MON` (not MTL), `VEG` (not VGK), `NJ`, `SJ`, `TB`, `WAS`.
- No sentiment, no LLM, no network calls anywhere in this phase.
- `cache/reddit_corpus/` is gitignored and is the local source of record. Never modify it.
- New pre-registration amendment number for this work is **A45** (next free per SESSION.md). Do not reuse A1–A44. **Task 0 carries its own number, A48** — do not merge the two amendments; they are separate rules with separate evidence.
- **`raw/reddit_detail.csv` row counts quoted throughout this plan (163,937 rows, 61,163 r/hockey pairs) are PRE-Task-0 figures.** They change when Task 0 runs. Re-derive them from the regenerated file rather than trusting the numbers inline below.
- Do not modify `compute_oaq.py`. Phase A is a companion output, not a change to OAQ.
- Do not run a production `compute_oaq` — it remains gated on Phase-1 hygiene + Gate-4.

---

## File Structure

| File | Responsibility |
|---|---|
| `affiliation.py` (create) | Pure logic. Venue↔team maps, nickname↔code map, team-at-time reconstruction, mention labeling, rate normalization, per-player aggregation. No file I/O, no network. |
| `compute_affiliation.py` (create) | Driver. Reads corpus + CSVs, builds the submission index, calls `affiliation.py`, writes `attention_affiliation.csv` atomically. Also prints the Montreal/Boston diagnostic. |
| `tests/test_affiliation_a45.py` (create) | Unit tests for every pure function in `affiliation.py`, using small hand-built fixtures. |
| `attention_affiliation.csv` (output) | One row per pool player. Top level, alongside `market_proxy.csv` and `team_outcomes.csv`. |
| `preregistration.md` (modify) | Append amendment A45 documenting the measure, the normalizer choice, and the `low_n` threshold. |

Inputs, all already on disk:

| Input | Provides |
|---|---|
| `cache/reddit_corpus/*.jsonl` | `id`, `subreddit`, `created_utc` per submission (38 files, 125MB) |
| `raw/reddit_detail.csv` | 163,937 rows of `player_id, submission_id, score` |
| `players.csv` | `player_id, full_name, team_code, team_slug` — 771 players |
| `mover_dates.csv` | 211 rows of `player_id, old_team, new_team, event_date, status` |
| `market_proxy.csv` | `team_code, team_sub` — the 32-team subreddit mapping |

---

### Task 0 (BLOCKING, added 2026-08-02): Defect 1 — first-name surname collision guard, option C'

**Amendment A48. ~2.5–3.5 h. Requires a full `python fetch_reddit.py` re-run.**
Nothing in Tasks 1–7 is trustworthy until this lands, because it rewrites
`raw/reddit_detail.csv`.

#### The bug

13 pool surnames are also another pool player's FIRST name, and each is unique
in the pool — so `attribute()` (`fetch_reddit.py:437`, *"Single-member groups
always win"*) hands every hit over with no evidence check. Every "Quinn Hughes"
mention credits **Jack Quinn**; every "Cole Caufield" credits **Ian Cole**.

The 13: `beck blake cole colton connor frank james joshua paul quinn reilly
shea thomas`. Only `connor` / `james` / `paul` are guarded today.

Root cause is a threshold artifact, not a design flaw. Prong **P2a** in
`guard_set_a43` already implements the right rule (*"≥share of occurrences
followed by a pool surname"*), but `fetch_reddit.py:317` gates all of P2 behind
`GUARD_DF_THRESHOLD = 0.01`, and `quinn` DF is 0.00931 — short by 0.0007.
`cole` 0.00865, `thomas` 0.00518.

#### The rule — C'

Per submission containing collision surname `sn` (owner = the player carrying
it as a surname), classify into exactly one state:

| state | condition | verdict |
|---|---|---|
| **S1** | EVERY occurrence of `sn` is immediately followed by the surname of a pool player whose FIRST name is `sn` | proven first-name usage → owner ineligible |
| **S2** | ≥1 standalone occurrence AND the owner's A15 checker fires | owner eligible |
| **S3** | ≥1 standalone occurrence, no first-name evidence | UNKNOWN → resolve by venue |

S3 resolution: **eligible if the submission is in the owner's own team sub;
otherwise ambiguous** (disclosed, counted for nobody). r/hockey never resolves
S3 — that is precisely where the contamination lives.

**S1 takes precedence over S2.** Verified: 14 r/hockey posts have every
`connor` followed by a pool surname *and* the checker firing, e.g.
`"Instagram story posted by Lauren Kyle (Connor McDavid's wife)"`. Kyle Connor
is credited for those today.

#### Two scoping rules — do not drop either

1. **P1-strict (this is the `'` in C').** A surname already guarded by A43
   prong **P1** (common English word) gets **NO own-sub allowance**. Own-sub
   context resolves a *rival-player* confuser; it cannot resolve an
   *ordinary-word* confuser, which appears in every sub equally. Verified: of
   the 13, exactly **`james` and `paul`** are in `english_top1000.txt`. Without
   this rule, bare "stanley" in r/winnipegjets counts for **Logan Stanley** and
   reopens open item #2.
2. **The own-sub allowance applies ONLY to collision surnames**, never to
   P1/P2b guards generally. The other 6 guarded players stay untouched, so the
   13 below are the **complete blast radius** — no unmeasured spillover.

#### Measured evidence (probe, live corpus, 250,004 submissions)

| token | owner | hits | S1 | S2 | S3 | S3 own-sub | S3 r/hockey |
|---|---|---|---|---|---|---|---|
| connor | Kyle Connor | 1539 | 55% | 18% | 27% | 84 | 325 |
| quinn | Jack Quinn | 735 | 44% | 35% | 21% | 95 | 56 |
| cole | Ian Cole | 589 | **75%** | 9% | 17% | 1 | 97 |
| thomas | Robert Thomas | 495 | 27% | 36% | 38% | 71 | 116 |
| paul | Nick Paul | 421 | 10% | 22% | **68%** | 49 | 239 |
| blake | Jackson Blake | 404 | 21% | 43% | 36% | 103 | 43 |
| frank | Ethen Frank | 355 | 31% | 23% | 47% | 27 | 139 |
| reilly | Mike Reilly | 286 | 16% | 15% | **69%** | 22 | 174 |
| james | Dominic James | 240 | 13% | 24% | 62% | 52 | 98 |
| colton | Ross Colton | 219 | 53% | 32% | 16% | 23 | 12 |
| beck | Owen Beck | 215 | 20% | 40% | 40% | 79 | 6 |
| joshua | Dakota Joshua | 212 | 4% | 48% | 48% | 78 | 24 |
| shea | Ryan Shea | 212 | 31% | 35% | 34% | 54 | 19 |

| option | mentions | delta | → ambiguous |
|---|---|---|---|
| today | 4152 | — | |
| **A** blanket guard (the original SESSION plan) | 1545 | **−2607 (−63%)** | 0 |
| **B** bigram only | 3631 | −521 | 0 |
| **C** bigram + own-sub | 2283 | −1869 | 1348 |
| **C' SELECTED** | **2182** | **−1970** | 1449 |

**Option A is rejected** — do not re-propose the 4-line blanket guard. It
destroys 63% of these players' Reddit signal, which is a worse error than the
contamination it removes.

Expect **Ian Cole 589 → 53** (should close the Ian Cole half of open item #2)
and **Kyle Connor 280 → 364 (+84)**. That increase is the point: C' is also a
**recall** fix, because the existing A42 guard has been silently deleting real
mentions for the 9 guarded players.

Bigram rule is **not knife-edge**: tight (next token = surname of a player
whose first name is `sn`) vs loose (next token = any pool surname) differ by
≤26 posts per name, and by **1** for `cole`. Use tight.

#### Steps

- [ ] **Step 1: Implement C' — 4 edit sites in `fetch_reddit.py`**

| # | Site | Change |
|---|---|---|
| 1 | ~line 564 | Build the collision set (surname unique in pool AND in `pool_first_names`), plus per surname `fn_surnames` = surnames of players whose first name is that token. |
| 2 | `build_groups` (~400) | Carry `collision`, `fn_surnames`, `p1` onto each member dict. |
| 3 | `scan_corpus` (~512, 521) | `tokens` is currently a SET (`match_tokens`); the bigram test needs ORDER. Restructure to `toks = match_fold(...).split()` then `tokens = set(toks)` — same work, no extra cost. Then the 3-state eligibility block replaces lines 521–524. |
| 4 | counts output (~626) | Disclosure column(s). |

**Read the new member fields via `m.get(...)`, not `m[...]`.** That keeps
`test_fetch_reddit_a42.py`'s `_member` helper and all 43 existing reddit tests
passing untouched, with no signature change to `scan_corpus` / `build_groups`.

Confirmed safe: **no non-test code reads the guard columns** (`affiliation.py`
only says "guard" in prose). Downstream is `reddit_counts.csv` +
`reddit_detail.csv` consumers only, and there is still no production
`compute_oaq` run, so nothing cascades.

- [ ] **Step 2: Tests — `tests/test_fetch_reddit_a48.py`**

Must cover: each of S1 / S2 / S3; S1 precedence over S2 (the Lauren Kyle case);
own-sub allowance fires for a collision surname; own-sub allowance does NOT
fire for a P1 surname; the existing 9 guarded players stay guarded; and
**`mcdavid` is NOT guarded** (the P2b `partner not in pool_first_names`
exemption must survive — this is the regression that matters).

- [ ] **Step 3: Re-run**

```bash
python fetch_reddit.py        # minutes; landing JSONs are cached
```

- [ ] **Step 4: Verify against the probe oracle**

```bash
python diagnostics/probe_firstname_guard_options.py
```

Assert pipeline `reddit_mentions_12mo` **equals the probe's C' column for all
13**. This makes the before/after step pass/fail rather than eyeballing a diff.
The probe is read-only, makes no network calls, and imports folding /
tokenizing / the A15 checker from `fetch_reddit` rather than reimplementing
them. Committed at `3a96f8e`.

Then diff `raw/reddit_counts.csv` + `raw/reddit_detail.csv` across **all 771
rows**, not just the 13, and produce a before/after table.

- [ ] **Step 5: Pre-registration amendment A48**

A48 must document, not bury: the 3-state rule; P1-strict scoping; that it
**overrides A42 rule 2** (*"team context never suffices for guarded
surnames"*); that it **overrides P2** for collision surnames (`connor` is
P2-guarded today and C' is strictly more permissive for it — defensible
because per-post bigram evidence beats a token-level aggregate, but it is a
real prereg change); and the tight-vs-loose bigram sensitivity. Fold **Defect 5**
(reddit null-vs-zero for the two Petterssons) into the same amendment.

#### Two open implementation risks

1. **Bucket split.** S1 ("proven not him") and S3-in-r/hockey ("unknown") are
   different disclosures — `guard_filtered` vs `ambiguous`. A third column may
   be needed to keep them clean (+20 min).
2. **Movement outside the 13.** The positional-token switch should change no
   other player's count. If the 771-row diff shows movement elsewhere, explain
   it before proceeding.

#### Known limits — carry to the poster, do not quietly drop

- **The own-sub allowance (605 mentions) rests on a base-rate judgment, not on
  labelled data.** The owner declined the ~20–30 min hand-label validation on
  2026-08-02 for time: *"surname and/or team name mention is enough to make it
  accurate enough most of the time."* Deliberate call, recorded as an
  honest-limits (criterion 6) item. Re-offer if the schedule loosens.
- **Defect 6 — A15 checker false positives.** The checker fires on the first
  name appearing ANYWHERE in the post, so "Lauren Kyle" credits Kyle Connor.
  Under C' these land in **S2**, the keep-bucket, so every option carries a
  small residual over-count. C' is less wrong, not right. Quantified only for
  `connor` (14 posts). Not worth fixing before the poster; note it in limits.

---

### Task 1: Venue mapping — subreddit to team code

Builds the two lookups every later task needs: which subreddit belongs to which team, and which subreddits are neutral. Two edge cases make this worth its own task: Utah has **two** subreddits in the corpus (`utahmammoth` and `UtahHockey`, from the franchise rename) but only one row in `market_proxy.csv`, and three corpus subs (`hockey`, `nhl`, `fantasyhockey`) belong to no team at all.

**Files:**
- Create: `affiliation.py`
- Test: `tests/test_affiliation_a45.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `NEUTRAL_SUBS: frozenset[str]`
  - `EXTRA_SUB_ALIASES: dict[str, str]`
  - `build_venue_map(market_proxy: pd.DataFrame) -> dict[str, str]` — lowercased subreddit name to team code
  - `venue_team(subreddit: str, venue_map: dict[str, str]) -> str | None` — team code, or `None` for neutral/unknown

- [ ] **Step 1: Write the failing test**

Create `tests/test_affiliation_a45.py`:

```python
"""A45 — Phase A reddit attention affiliation split."""
from __future__ import annotations

import pandas as pd
import pytest

import affiliation as aff


def _market_proxy() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "team_code": ["BOS", "MON", "UTA", "VEG"],
            "team_sub": ["BostonBruins", "Habs", "utahmammoth", "goldenknights"],
        }
    )


def test_build_venue_map_lowercases_keys():
    vm = aff.build_venue_map(_market_proxy())
    assert vm["bostonbruins"] == "BOS"
    assert vm["habs"] == "MON"


def test_build_venue_map_includes_utah_rename_alias():
    vm = aff.build_venue_map(_market_proxy())
    assert vm["utahmammoth"] == "UTA"
    assert vm["utahhockey"] == "UTA"


def test_venue_team_returns_none_for_neutral_subs():
    vm = aff.build_venue_map(_market_proxy())
    assert aff.venue_team("hockey", vm) is None
    assert aff.venue_team("nhl", vm) is None
    assert aff.venue_team("fantasyhockey", vm) is None


def test_venue_team_is_case_insensitive():
    vm = aff.build_venue_map(_market_proxy())
    assert aff.venue_team("BostonBruins", vm) == "BOS"
    assert aff.venue_team("bostonbruins", vm) == "BOS"


def test_venue_team_returns_none_for_unknown_sub():
    vm = aff.build_venue_map(_market_proxy())
    assert aff.venue_team("soccer", vm) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'affiliation'`

- [ ] **Step 3: Write minimal implementation**

Create `affiliation.py`:

```python
"""A45 — Phase A: reddit attention affiliation split (own / other / neutral).

Pure functions only. No file I/O, no network. The driver is
`compute_affiliation.py`.

Terminology
-----------
venue      the subreddit a mention appeared in
own        venue belongs to a team the player was on at mention time
other      venue belongs to some other team
neutral    venue belongs to no team (r/hockey, r/nhl, r/fantasyhockey)
rate       mentions in a venue divided by that venue's submission count
"""
from __future__ import annotations

import pandas as pd

# Subreddits in the corpus that belong to no single team. r/hockey alone is
# ~37% of all mention pairs, so this bucket is large and must be reported.
NEUTRAL_SUBS = frozenset({"hockey", "nhl", "fantasyhockey"})

# The corpus holds both Utah subreddits because the franchise was renamed
# mid-window (Utah Hockey Club -> Utah Mammoth). `market_proxy.csv` lists only
# the current one, so the old name is added by hand.
EXTRA_SUB_ALIASES = {"utahhockey": "UTA"}


def build_venue_map(market_proxy: pd.DataFrame) -> dict[str, str]:
    """Map lowercased subreddit name -> team code.

    `market_proxy` must have `team_code` and `team_sub` columns.
    """
    venue_map = {
        str(sub).lower(): str(code)
        for sub, code in zip(market_proxy["team_sub"], market_proxy["team_code"])
    }
    venue_map.update(EXTRA_SUB_ALIASES)
    return venue_map


def venue_team(subreddit: str, venue_map: dict[str, str]) -> str | None:
    """Team code owning `subreddit`, or None if neutral or unrecognised."""
    key = str(subreddit).lower()
    if key in NEUTRAL_SUBS:
        return None
    return venue_map.get(key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Commit**

```bash
git add affiliation.py tests/test_affiliation_a45.py
git commit -m "feat(a45): venue map for reddit affiliation split"
```

---

### Task 2: Player team timeline

`players.csv` records only a player's team at the **end** of the window. 101 trades, 76 free-agent signings, and 15 waiver claims happened during or before it, so a mention in r/leafs can be "own" in November and "other" in March for the same player. This task reconstructs which team a player was on at any timestamp.

Two data quirks: `mover_dates.csv` names teams by **nickname** (`Bruins`, `Golden Knights`) while everything else uses team codes, and 19 rows carry `status == "excluded_rename_artifact"` — the Utah franchise rename showing up as fake moves. Those rows must be dropped.

**Files:**
- Modify: `affiliation.py`
- Test: `tests/test_affiliation_a45.py`

**Interfaces:**
- Consumes: nothing from Task 1
- Produces:
  - `NICKNAME_TO_CODE: dict[str, str]`
  - `build_move_timeline(movers: pd.DataFrame) -> dict[int, list[tuple[pd.Timestamp, str]]]` — `player_id` to a chronological list of `(event_date, old_team_code)`
  - `team_at(player_id: int, when: pd.Timestamp, end_team: str, timeline: dict) -> str` — team code the player was on at `when`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_affiliation_a45.py`:

```python
def _movers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_id": [25, 25, 99, 7],
            "old_team": ["Oilers", "Bruins", "Maple Leafs", "Utah Hockey Club"],
            "new_team": ["Bruins", "Canadiens", "Wild", "Mammoth"],
            "event_date": ["2025-07-01", "2026-01-15", "2025-11-20", "2025-06-01"],
            "status": ["dated", "dated", "dated", "excluded_rename_artifact"],
        }
    )


def test_nickname_map_covers_every_mover_team():
    movers = pd.read_csv("mover_dates.csv")
    movers = movers[movers["status"] == "dated"]
    names = set(movers["old_team"].dropna()) | set(movers["new_team"].dropna())
    missing = sorted(n for n in names if n not in aff.NICKNAME_TO_CODE)
    assert missing == [], f"nicknames absent from NICKNAME_TO_CODE: {missing}"


def test_build_move_timeline_drops_rename_artifacts():
    tl = aff.build_move_timeline(_movers())
    assert 7 not in tl


def test_build_move_timeline_is_chronological():
    tl = aff.build_move_timeline(_movers())
    dates = [d for d, _ in tl[25]]
    assert dates == sorted(dates)


def test_team_at_returns_end_team_after_last_move():
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(25, pd.Timestamp("2026-03-01"), "MON", tl)
    assert got == "MON"


def test_team_at_reverts_one_move():
    # Between the two moves: joined BOS 2025-07-01, left for MON 2026-01-15.
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(25, pd.Timestamp("2025-10-01"), "MON", tl)
    assert got == "BOS"


def test_team_at_reverts_all_moves():
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(25, pd.Timestamp("2025-05-01"), "MON", tl)
    assert got == "EDM"


def test_team_at_for_player_with_no_moves():
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(1234, pd.Timestamp("2025-10-01"), "VAN", tl)
    assert got == "VAN"


def test_team_at_on_exact_move_date_uses_new_team():
    # A move dated 2026-01-15 means the player is on the new team that day.
    tl = aff.build_move_timeline(_movers())
    got = aff.team_at(25, pd.Timestamp("2026-01-15"), "MON", tl)
    assert got == "MON"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: FAIL — `AttributeError: module 'affiliation' has no attribute 'NICKNAME_TO_CODE'`

- [ ] **Step 3: Write minimal implementation**

Append to `affiliation.py`:

```python
# `mover_dates.csv` names teams by nickname; everything else uses the project's
# own team codes (LA not LAK, NAS not NSH, MON not MTL, VEG not VGK). Both Utah
# names map to UTA because the franchise was renamed mid-window.
NICKNAME_TO_CODE = {
    "Ducks": "ANA",
    "Bruins": "BOS",
    "Sabres": "BUF",
    "Hurricanes": "CAR",
    "Blue Jackets": "CBJ",
    "Flames": "CGY",
    "Blackhawks": "CHI",
    "Avalanche": "COL",
    "Stars": "DAL",
    "Red Wings": "DET",
    "Oilers": "EDM",
    "Panthers": "FLA",
    "Kings": "LA",
    "Wild": "MIN",
    "Canadiens": "MON",
    "Predators": "NAS",
    "Devils": "NJ",
    "Islanders": "NYI",
    "Rangers": "NYR",
    "Senators": "OTT",
    "Flyers": "PHI",
    "Penguins": "PIT",
    "Kraken": "SEA",
    "Sharks": "SJ",
    "Blues": "STL",
    "Lightning": "TB",
    "Maple Leafs": "TOR",
    "Mammoth": "UTA",
    "Utah Hockey Club": "UTA",
    "Canucks": "VAN",
    "Golden Knights": "VEG",
    "Capitals": "WAS",
    "Jets": "WPG",
}


def build_move_timeline(
    movers: pd.DataFrame,
) -> dict[int, list[tuple[pd.Timestamp, str]]]:
    """Map player_id -> chronological [(event_date, old_team_code), ...].

    Rows whose `status` is not `"dated"` are dropped: 19 of them are Utah
    rename artifacts, not real transactions. Rows naming a team absent from
    NICKNAME_TO_CODE are dropped too; `test_nickname_map_covers_every_mover_team`
    guards against that silently hiding a real gap.
    """
    dated = movers[movers["status"] == "dated"]
    timeline: dict[int, list[tuple[pd.Timestamp, str]]] = {}
    for row in dated.itertuples(index=False):
        code = NICKNAME_TO_CODE.get(row.old_team)
        if code is None:
            continue
        timeline.setdefault(int(row.player_id), []).append(
            (pd.Timestamp(row.event_date), code)
        )
    for moves in timeline.values():
        moves.sort(key=lambda pair: pair[0])
    return timeline


def team_at(
    player_id: int,
    when: pd.Timestamp,
    end_team: str,
    timeline: dict[int, list[tuple[pd.Timestamp, str]]],
) -> str:
    """Team code the player was on at `when`.

    `end_team` is their team in `players.csv` (end of window). Walk the moves
    newest-first; every move dated strictly after `when` is undone by reverting
    to that move's `old_team`. The oldest such move wins, which is why the
    loop runs in reverse. A move dated exactly `when` has already happened.
    """
    team = end_team
    for event_date, old_team in reversed(timeline.get(int(player_id), [])):
        if event_date > when:
            team = old_team
    return team
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: PASS, 13 tests

- [ ] **Step 5: Commit**

```bash
git add affiliation.py tests/test_affiliation_a45.py
git commit -m "feat(a45): player team timeline from mover_dates"
```

---

### Task 3: Label every mention own / other / neutral

Joins the pieces: for each `(player_id, submission_id)` row in `reddit_detail.csv`, look up the submission's subreddit and timestamp, resolve the venue's team and the player's team at that moment, and emit a bucket.

**Files:**
- Modify: `affiliation.py`
- Test: `tests/test_affiliation_a45.py`

**Interfaces:**
- Consumes: `venue_team` (Task 1), `team_at` (Task 2)
- Produces:
  - `WINDOW_START: pd.Timestamp`, `WINDOW_END: pd.Timestamp`
  - `label_mentions(detail, submissions, players, venue_map, timeline) -> pd.DataFrame` with columns `player_id, subreddit, bucket, score`. `bucket` is one of `"own"`, `"other"`, `"neutral"`. Rows outside the window, or whose submission is missing from the index, are dropped.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_affiliation_a45.py`:

```python
def _submissions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "submission_id": ["s1", "s2", "s3", "s4", "s5"],
            "subreddit": ["BostonBruins", "Habs", "hockey", "BostonBruins", "Habs"],
            "created_at": pd.to_datetime(
                [
                    "2025-10-01",
                    "2025-10-01",
                    "2025-10-01",
                    "2026-03-01",
                    "2020-01-01",  # before the window
                ]
            ),
        }
    )


def _players() -> pd.DataFrame:
    return pd.DataFrame({"player_id": [25], "team_code": ["MON"]})


def _labelled() -> pd.DataFrame:
    detail = pd.DataFrame(
        {
            "player_id": [25, 25, 25, 25, 25],
            "submission_id": ["s1", "s2", "s3", "s4", "s5"],
            "score": [10, 20, 30, 40, 50],
        }
    )
    return aff.label_mentions(
        detail,
        _submissions(),
        _players(),
        aff.build_venue_map(_market_proxy()),
        aff.build_move_timeline(_movers()),
    )


def test_label_mentions_own_before_trade():
    # Player 25 was on BOS on 2025-10-01, so r/BostonBruins is own.
    out = _labelled()
    assert out.loc[out.subreddit == "BostonBruins"].iloc[0]["bucket"] == "own"


def test_label_mentions_other_before_trade():
    out = _labelled()
    row = out[(out.subreddit == "Habs")].iloc[0]
    assert row["bucket"] == "other"


def test_label_mentions_flips_after_trade():
    # Traded to MON on 2026-01-15, so r/BostonBruins on 2026-03-01 is other.
    out = _labelled()
    late = out[out.subreddit == "BostonBruins"].iloc[1]
    assert late["bucket"] == "other"


def test_label_mentions_neutral_venue():
    out = _labelled()
    assert (out[out.subreddit == "hockey"]["bucket"] == "neutral").all()


def test_label_mentions_drops_out_of_window_rows():
    out = _labelled()
    assert 50 not in set(out["score"])


def test_label_mentions_drops_unknown_submissions():
    detail = pd.DataFrame(
        {"player_id": [25], "submission_id": ["nope"], "score": [1]}
    )
    out = aff.label_mentions(
        detail,
        _submissions(),
        _players(),
        aff.build_venue_map(_market_proxy()),
        aff.build_move_timeline(_movers()),
    )
    assert len(out) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: FAIL — `AttributeError: module 'affiliation' has no attribute 'label_mentions'`

- [ ] **Step 3: Write minimal implementation**

Append to `affiliation.py`:

```python
# Measurement window, matching the rest of the project (SESSION.md
# CARRY-FORWARD). Both bounds inclusive.
WINDOW_START = pd.Timestamp("2025-04-18")
WINDOW_END = pd.Timestamp("2026-04-17")


def label_mentions(
    detail: pd.DataFrame,
    submissions: pd.DataFrame,
    players: pd.DataFrame,
    venue_map: dict[str, str],
    timeline: dict[int, list[tuple[pd.Timestamp, str]]],
) -> pd.DataFrame:
    """Attach a own/other/neutral bucket to every mention pair.

    `detail`      : player_id, submission_id, score
    `submissions` : submission_id, subreddit, created_at
    `players`     : player_id, team_code (team at end of window)

    Returns player_id, subreddit, bucket, score. Mentions whose submission is
    absent from the index, or which fall outside the window, are dropped.
    """
    df = detail.merge(submissions, on="submission_id", how="inner")
    df = df[
        (df["created_at"] >= WINDOW_START) & (df["created_at"] <= WINDOW_END)
    ].copy()

    end_team = dict(
        zip(players["player_id"].astype(int), players["team_code"].astype(str))
    )

    buckets = []
    for row in df.itertuples(index=False):
        owner = venue_team(row.subreddit, venue_map)
        if owner is None:
            buckets.append("neutral")
            continue
        player_team = team_at(
            int(row.player_id),
            row.created_at,
            end_team.get(int(row.player_id), ""),
            timeline,
        )
        buckets.append("own" if owner == player_team else "other")

    df["bucket"] = buckets
    return df[["player_id", "subreddit", "bucket", "score"]].reset_index(drop=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: PASS, 19 tests

- [ ] **Step 5: Commit**

```bash
git add affiliation.py tests/test_affiliation_a45.py
git commit -m "feat(a45): label mentions own/other/neutral by venue and date"
```

---

### Task 4: Volume normalization and per-player aggregation

The step that makes cross-team comparison valid. `r/Habs` holds 14,532 submissions and `r/BostonBruins` 3,071 — despite Boston having **more** subscribers (119,306 vs 101,589). Raw counts would make every Bruin look ignored by their own fanbase. Dividing by each subreddit's submission count converts counts to "mentions per posting opportunity," which cancels the venue-volume artifact.

Score-weighted variants are computed alongside as a robustness check: a 2-upvote post and a 900-upvote post are not equal attention.

**Files:**
- Modify: `affiliation.py`
- Test: `tests/test_affiliation_a45.py`

**Interfaces:**
- Consumes: output of `label_mentions` (Task 3)
- Produces:
  - `LOW_N_MIN: int` (= 30)
  - `aggregate_players(labelled: pd.DataFrame, sub_volume: dict[str, int], players: pd.DataFrame) -> pd.DataFrame` — one row per player in `players`, columns: `player_id, full_name, team_code, own_mentions, other_mentions, neutral_mentions, attributed_mentions, own_intensity, other_intensity, neutral_intensity, own_share, own_share_scored, rival_reach, top_rival, low_n`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_affiliation_a45.py`:

```python
def _agg_players() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_id": [1, 2],
            "full_name": ["Own Heavy", "Road Show"],
            "team_code": ["BOS", "MON"],
        }
    )


def _agg_labelled() -> pd.DataFrame:
    rows = []
    # Player 1: 6 own mentions in a small sub, 2 other in a big sub.
    rows += [(1, "BostonBruins", "own", 10)] * 6
    rows += [(1, "Habs", "other", 10)] * 2
    # Player 2: 2 own in a big sub, 6 other spread over two rival subs.
    rows += [(2, "Habs", "own", 10)] * 2
    rows += [(2, "BostonBruins", "other", 10)] * 4
    rows += [(2, "leafs", "other", 10)] * 2
    rows += [(2, "hockey", "neutral", 10)] * 5
    return pd.DataFrame(rows, columns=["player_id", "subreddit", "bucket", "score"])


_SUB_VOLUME = {"BostonBruins": 3000, "Habs": 15000, "leafs": 10000, "hockey": 50000}


def test_aggregate_counts_each_bucket():
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    p1 = out.set_index("player_id").loc[1]
    assert p1["own_mentions"] == 6
    assert p1["other_mentions"] == 2
    assert p1["neutral_mentions"] == 0


def test_aggregate_normalizes_by_submission_volume():
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    p1 = out.set_index("player_id").loc[1]
    assert p1["own_intensity"] == pytest.approx(6 / 3000)
    assert p1["other_intensity"] == pytest.approx(2 / 15000)


def test_normalization_changes_the_ranking():
    """Raw counts and normalized rates disagree — that is the whole point.

    Player 2 has more raw other-mentions than player 1 has own-mentions, but
    after dividing by venue volume player 1 is far more own-concentrated.
    """
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    idx = out.set_index("player_id")
    assert idx.loc[1, "own_share"] > idx.loc[2, "own_share"]


def test_own_share_is_a_proportion_of_attributed_only():
    # Neutral mentions must not enter own_share's denominator.
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    p2 = out.set_index("player_id").loc[2]
    expected = (2 / 15000) / ((2 / 15000) + (4 / 3000) + (2 / 10000))
    assert p2["own_share"] == pytest.approx(expected)


def test_rival_reach_counts_distinct_rival_subs():
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    idx = out.set_index("player_id")
    assert idx.loc[1, "rival_reach"] == 1
    assert idx.loc[2, "rival_reach"] == 2


def test_top_rival_is_the_highest_rate_rival_sub():
    # Player 2: BostonBruins 4/3000 beats leafs 2/10000 despite both being
    # rivals, and beats it on rate even though the raw counts are closer.
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    assert out.set_index("player_id").loc[2, "top_rival"] == "BostonBruins"


def test_low_n_flag_set_below_threshold():
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, _agg_players())
    # Both fixture players are far below LOW_N_MIN=30 attributed mentions.
    assert out["low_n"].all()


def test_player_with_no_mentions_gets_a_row():
    players = pd.DataFrame(
        {"player_id": [1, 2, 3], "full_name": ["a", "b", "c"],
         "team_code": ["BOS", "MON", "VAN"]}
    )
    out = aff.aggregate_players(_agg_labelled(), _SUB_VOLUME, players)
    p3 = out.set_index("player_id").loc[3]
    assert p3["attributed_mentions"] == 0
    assert pd.isna(p3["own_share"])
    assert bool(p3["low_n"]) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: FAIL — `AttributeError: module 'affiliation' has no attribute 'aggregate_players'`

- [ ] **Step 3: Write minimal implementation**

Append to `affiliation.py`:

```python
import numpy as np

# Minimum attributed (own + other) mentions before own_share is trustworthy.
# Median pool player has 165 total mentions and ~63% are attributable, so this
# keeps roughly the top three quartiles. Pre-registered in A45; do not tune it
# after seeing results.
LOW_N_MIN = 30


def _rates(group: pd.DataFrame, sub_volume: dict[str, int], weight: str) -> pd.Series:
    """Per-subreddit rate for one player: weight summed, divided by volume."""
    summed = group.groupby("subreddit")[weight].sum()
    volumes = pd.Series(
        {sub: sub_volume.get(sub, 0) for sub in summed.index}, dtype=float
    )
    return (summed / volumes.replace(0, np.nan)).dropna()


def aggregate_players(
    labelled: pd.DataFrame,
    sub_volume: dict[str, int],
    players: pd.DataFrame,
) -> pd.DataFrame:
    """One row per player in `players`, with volume-normalized shares.

    `sub_volume` maps subreddit name -> number of submissions collected for it.
    Dividing by it is what makes a Bruin comparable to a Hab: r/Habs carries
    ~5x r/BostonBruins' submissions despite a smaller subscriber base, so raw
    mention counts encode venue activity rather than player attention.
    """
    work = labelled.copy()
    work["unit"] = 1.0
    work["weight"] = work["score"].clip(lower=0).astype(float) + 1.0

    records = []
    by_player = dict(tuple(work.groupby("player_id")))

    for row in players.itertuples(index=False):
        pid = int(row.player_id)
        group = by_player.get(pid)
        if group is None:
            group = work.iloc[0:0]

        counts = group["bucket"].value_counts()
        own_n = int(counts.get("own", 0))
        other_n = int(counts.get("other", 0))
        neutral_n = int(counts.get("neutral", 0))
        attributed = own_n + other_n

        intensity = {}
        scored = {}
        for bucket in ("own", "other", "neutral"):
            sub = group[group["bucket"] == bucket]
            intensity[bucket] = float(_rates(sub, sub_volume, "unit").sum())
            scored[bucket] = float(_rates(sub, sub_volume, "weight").sum())

        denom = intensity["own"] + intensity["other"]
        own_share = intensity["own"] / denom if denom > 0 else np.nan

        denom_s = scored["own"] + scored["other"]
        own_share_scored = scored["own"] / denom_s if denom_s > 0 else np.nan

        rivals = group[group["bucket"] == "other"]
        rival_rates = _rates(rivals, sub_volume, "unit")
        top_rival = str(rival_rates.idxmax()) if len(rival_rates) else ""

        records.append(
            {
                "player_id": pid,
                "full_name": row.full_name,
                "team_code": row.team_code,
                "own_mentions": own_n,
                "other_mentions": other_n,
                "neutral_mentions": neutral_n,
                "attributed_mentions": attributed,
                "own_intensity": intensity["own"],
                "other_intensity": intensity["other"],
                "neutral_intensity": intensity["neutral"],
                "own_share": own_share,
                "own_share_scored": own_share_scored,
                "rival_reach": int(len(rival_rates)),
                "top_rival": top_rival,
                "low_n": attributed < LOW_N_MIN,
            }
        )

    return pd.DataFrame.from_records(records)
```

Move the `import numpy as np` line up to sit beside `import pandas as pd` at the top of the file.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: PASS, 27 tests

- [ ] **Step 5: Commit**

```bash
git add affiliation.py tests/test_affiliation_a45.py
git commit -m "feat(a45): volume-normalized per-player affiliation aggregation"
```

---

### Task 5: Driver script and output CSV

Reads the real inputs, runs the pipeline, writes `attention_affiliation.csv`. The corpus is 125MB across 38 JSONL files; it is scanned once into a compact submission index rather than re-read per lookup.

**Files:**
- Create: `compute_affiliation.py`
- Test: `tests/test_affiliation_a45.py`

**Interfaces:**
- Consumes: everything from `affiliation.py`
- Produces:
  - `build_submission_index(corpus_dir: Path) -> tuple[pd.DataFrame, dict[str, int]]` — the `submission_id / subreddit / created_at` frame plus `sub_volume`
  - `main() -> None` — writes `attention_affiliation.csv`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_affiliation_a45.py`:

```python
import json
from pathlib import Path

import compute_affiliation as ca


def test_build_submission_index_parses_corpus(tmp_path: Path):
    corpus = tmp_path / "reddit_corpus"
    corpus.mkdir()
    recs = [
        {"id": "a1", "subreddit": "canucks", "created_utc": "1744934436"},
        {"id": "a2", "subreddit": "canucks", "created_utc": "1744934500"},
    ]
    with (corpus / "canucks.jsonl").open("w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")

    index, volume = ca.build_submission_index(corpus)
    assert set(index["submission_id"]) == {"a1", "a2"}
    assert volume["canucks"] == 2
    assert str(index["created_at"].dtype).startswith("datetime64")


def test_build_submission_index_skips_malformed_lines(tmp_path: Path):
    corpus = tmp_path / "reddit_corpus"
    corpus.mkdir()
    with (corpus / "leafs.jsonl").open("w", encoding="utf-8") as fh:
        fh.write('{"id": "b1", "subreddit": "leafs", "created_utc": "1744934436"}\n')
        fh.write("not json at all\n")
    index, volume = ca.build_submission_index(corpus)
    assert len(index) == 1
    assert volume["leafs"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compute_affiliation'`

- [ ] **Step 3: Write minimal implementation**

Create `compute_affiliation.py`:

```python
"""A45 — Phase A driver: write attention_affiliation.csv.

Reads the existing reddit corpus and project CSVs, labels every mention pair
as own / other / neutral relative to the player's team at that moment,
normalizes by each subreddit's submission volume, and writes one row per pool
player. No network calls, no LLM, no sentiment.

Run from inside `marchand_index/`:

    python compute_affiliation.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

import affiliation as aff

PILOT_DIR = Path(__file__).parent
RAW_DIR = PILOT_DIR / "raw"
CORPUS_DIR = PILOT_DIR / "cache" / "reddit_corpus"
OUT_PATH = PILOT_DIR / "attention_affiliation.csv"


def build_submission_index(corpus_dir: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    """Scan the JSONL corpus once into (submission frame, sub_volume).

    The corpus is ~125MB over 38 files, so this runs once and everything
    downstream works off the returned frame. Malformed lines are skipped
    rather than aborting the run.
    """
    ids: list[str] = []
    subs: list[str] = []
    times: list[int] = []
    volume: dict[str, int] = {}

    for path in sorted(corpus_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sub = str(rec["subreddit"])
                ids.append(str(rec["id"]))
                subs.append(sub)
                times.append(int(rec["created_utc"]))
                volume[sub] = volume.get(sub, 0) + 1

    index = pd.DataFrame(
        {
            "submission_id": ids,
            "subreddit": subs,
            "created_at": pd.to_datetime(times, unit="s"),
        }
    )
    return index, volume


def main() -> None:
    players = pd.read_csv(PILOT_DIR / "players.csv")
    movers = pd.read_csv(PILOT_DIR / "mover_dates.csv")
    market = pd.read_csv(PILOT_DIR / "market_proxy.csv")
    detail = pd.read_csv(RAW_DIR / "reddit_detail.csv")

    print(f"corpus scan: {CORPUS_DIR}")
    index, sub_volume = build_submission_index(CORPUS_DIR)
    print(f"  {len(index):,} submissions across {len(sub_volume)} subreddits")

    venue_map = aff.build_venue_map(market)
    timeline = aff.build_move_timeline(movers)
    print(f"  {len(timeline)} players carry at least one dated move")

    labelled = aff.label_mentions(detail, index, players, venue_map, timeline)
    counts = labelled["bucket"].value_counts()
    total = len(labelled)
    print(f"  {total:,} in-window mention pairs")
    for bucket in ("own", "other", "neutral"):
        n = int(counts.get(bucket, 0))
        print(f"    {bucket:8} {n:>8,}  ({n / total:.1%})")

    out = aff.aggregate_players(labelled, sub_volume, players)

    tmp = OUT_PATH.with_suffix(".csv.tmp")
    out.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, OUT_PATH)
    print(f"wrote {OUT_PATH} ({len(out)} rows, {int(out['low_n'].sum())} low_n)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: PASS, 29 tests

- [ ] **Step 5: Run the driver on real data**

Run: `python compute_affiliation.py`

Expected: prints ~63,898 submissions across 38 subreddits, roughly 160k in-window mention pairs split near 63% attributed / 37% neutral, and writes `attention_affiliation.csv` with 771 rows.

If the neutral share is far from ~37%, stop — the venue map is likely missing a subreddit. Check for corpus subreddits absent from both `venue_map` and `NEUTRAL_SUBS`.

- [ ] **Step 6: Commit**

```bash
git add compute_affiliation.py tests/test_affiliation_a45.py attention_affiliation.csv
git commit -m "feat(a45): compute_affiliation driver and attention_affiliation.csv"
```

---

### Task 6: Diagnostics — the Montreal question and the portable audit

Phase A exists to answer two open questions, so the answers get their own script rather than living in a console session. Open item #3B asks whether Montreal's 16-of-26 showing in the OAQ top-100 is real signal or a market-strip failure; the `own_share` distribution by team speaks to it directly. The second output tests whether `OAQ_portable` deserves its name — attention that never leaves a player's own subreddit is not portable.

**Files:**
- Create: `diagnostics/affiliation_report.py`
- Test: `tests/test_affiliation_a45.py`

**Interfaces:**
- Consumes: `attention_affiliation.csv` (Task 5)
- Produces:
  - `team_own_share(affil: pd.DataFrame) -> pd.DataFrame` — per-team median `own_share` and player count, excluding `low_n` rows
  - `main() -> None` — prints the team table and the `rival_reach` leaderboard

- [ ] **Step 1: Write the failing test**

Append to `tests/test_affiliation_a45.py`:

```python
from diagnostics import affiliation_report as ar


def test_team_own_share_excludes_low_n_rows():
    affil = pd.DataFrame(
        {
            "player_id": [1, 2, 3],
            "team_code": ["MON", "MON", "BOS"],
            "own_share": [0.9, 0.1, 0.5],
            "low_n": [False, True, False],
        }
    )
    out = ar.team_own_share(affil).set_index("team_code")
    assert out.loc["MON", "n_players"] == 1
    assert out.loc["MON", "median_own_share"] == pytest.approx(0.9)


def test_team_own_share_sorted_descending():
    affil = pd.DataFrame(
        {
            "player_id": [1, 2],
            "team_code": ["BOS", "MON"],
            "own_share": [0.2, 0.8],
            "low_n": [False, False],
        }
    )
    out = ar.team_own_share(affil)
    assert list(out["team_code"]) == ["MON", "BOS"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: FAIL — `ImportError: cannot import name 'affiliation_report' from 'diagnostics'`

- [ ] **Step 3: Write minimal implementation**

Create `diagnostics/affiliation_report.py`:

```python
"""A45 — Phase A diagnostics.

Two questions this answers:

1. Open item #3B — Montreal holds 16 of the OAQ_portable top-100. If MON
   players also show unusually high `own_share`, their attention is
   fanbase-captive and `market_z` is under-correcting for fanbase intensity
   rather than MON genuinely over-indexing.

2. Whether `OAQ_portable` earns the name "portable". Attention concentrated
   in a player's own subreddit does not travel with him.

Run from inside `marchand_index/`:

    python -m diagnostics.affiliation_report
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

AFFIL_PATH = Path(__file__).parent.parent / "attention_affiliation.csv"


def team_own_share(affil: pd.DataFrame) -> pd.DataFrame:
    """Median own_share per team, `low_n` players excluded, highest first."""
    usable = affil[~affil["low_n"].astype(bool)]
    grouped = (
        usable.groupby("team_code")["own_share"]
        .agg(median_own_share="median", n_players="count")
        .reset_index()
    )
    return grouped.sort_values(
        "median_own_share", ascending=False
    ).reset_index(drop=True)


def main() -> None:
    affil = pd.read_csv(AFFIL_PATH)

    print("=== median own_share by team (low_n excluded) ===")
    print(team_own_share(affil).to_string(index=False))

    usable = affil[~affil["low_n"].astype(bool)]
    print()
    print("=== most road-followed players (lowest own_share) ===")
    cols = ["full_name", "team_code", "own_share", "rival_reach", "top_rival"]
    print(usable.nsmallest(20, "own_share")[cols].to_string(index=False))

    print()
    print("=== widest rival reach ===")
    print(usable.nlargest(20, "rival_reach")[cols].to_string(index=False))

    print()
    print(f"league median own_share: {usable['own_share'].median():.3f}")
    print(f"league median rival_reach: {usable['rival_reach'].median():.1f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_affiliation_a45.py -v`
Expected: PASS, 31 tests

- [ ] **Step 5: Run the report and record the finding**

Run: `python -m diagnostics.affiliation_report`

Read the team table. If MON's median `own_share` sits near the top, that is evidence for interpretation (a) in open item #3B — the market strip under-corrects and "portable" carries fanbase intensity. If MON sits mid-pack, that is evidence for (b) — Habs players genuinely over-index.

Record the result in SESSION.md under open item #3B. Do not change `compute_oaq.py` either way; this is a finding, not a fix.

- [ ] **Step 6: Commit**

```bash
git add diagnostics/affiliation_report.py tests/test_affiliation_a45.py
git commit -m "feat(a45): affiliation diagnostics for open item 3B"
```

---

### Task 7: Pre-registration amendment A45

The measure will appear on the poster, so its definition and thresholds get locked before anyone looks at the ranked output. `LOW_N_MIN` in particular must not be tuned after seeing which players it excludes.

**Files:**
- Modify: `preregistration.md`

**Interfaces:**
- Consumes: the constants defined in Tasks 1–4
- Produces: nothing consumed by code

- [ ] **Step 1: Append the amendment**

Append to `preregistration.md`:

```markdown
## A45 — Reddit attention affiliation split (Phase A)

**Status:** locked 2026-07-31, before any ranked `attention_affiliation.csv`
output was inspected.

**What it measures.** For each pool player, the share of their Reddit
attention originating from their own fanbase versus rival fanbases.
Descriptive only. No sentiment, no LLM, no causal claim.

**Buckets.** Each `(player_id, submission_id)` mention pair is assigned
exactly one bucket by the subreddit it appeared in:

- `own` — subreddit belongs to a team the player was on at that submission's
  timestamp
- `other` — subreddit belongs to any other team
- `neutral` — `r/hockey`, `r/nhl`, `r/fantasyhockey` (no team affiliation)

Team membership at a point in time is reconstructed from `players.csv`
(end-of-window team) walked backwards through `mover_dates.csv` rows with
`status == "dated"`. Rows flagged `excluded_rename_artifact` are dropped.

**Normalizer — submissions, not subscribers.** Every count is divided by the
collected submission count of the subreddit it came from. Subscriber count is
explicitly rejected as a denominator: r/BostonBruins has more subscribers than
r/Habs (119,306 vs 101,589) but ~1/5 the submissions (3,071 vs 14,532), so a
subscriber-normalized figure would encode posting culture as player attention.

```
own_share = own_intensity / (own_intensity + other_intensity)
```

where each intensity is the sum over subreddits of
`mentions_in_sub / submissions_in_sub`. Neutral mentions are reported but are
**not** in `own_share`'s denominator.

**Score-weighted variant.** `own_share_scored` repeats the calculation with
`score + 1` in place of a unit count. Reported as a robustness check; the
count-based `own_share` is primary.

**Publish gate.** `low_n = attributed_mentions < 30`. Rows with `low_n` are
excluded from every published ranking and from the diagnostics tables. The
threshold is fixed here and will not be adjusted after inspecting results.

**Relationship to OAQ.** A45 is a companion output. It does not enter
`compute_oaq.py`, does not change any CES weight, and does not alter
`OAQ_portable`. Any use of `own_share` to interpret `OAQ_portable` (open item
#3B) is reported as an observed association, not a correction.

**Limits of claim.**
- Subreddit is a proxy for fanbase allegiance, not proof of it. A rival fan can
  post in any subreddit.
- ~37% of mention pairs land in neutral venues and cannot be attributed. All
  shares are computed on the attributed remainder and reported as such.
- The corpus covers submissions only, not comments.
- Collection volume differs across subreddits by up to 12x. Normalization
  addresses the arithmetic, not any sampling bias in what was collected.
```

- [ ] **Step 2: Verify the constants match the code**

Run:

```bash
grep -n "LOW_N_MIN\|NEUTRAL_SUBS\|WINDOW_START\|WINDOW_END" affiliation.py
```

Expected: `LOW_N_MIN = 30`, `NEUTRAL_SUBS` containing exactly `hockey`, `nhl`, `fantasyhockey`, and the window bounds `2025-04-18` / `2026-04-17` — all matching the amendment text. Fix whichever side is wrong.

- [ ] **Step 3: Run the full suite**

Run: `pytest -q`

Expected: PASS. The suite was at 240 tests before this work; expect 271.

- [ ] **Step 4: Commit**

```bash
git add preregistration.md
git commit -m "docs(a45): pre-register reddit affiliation split"
```

---

## Verification

**Task 0 first** — it has its own oracle and gates everything below:

```bash
python fetch_reddit.py                                  # re-run after the C' change
python diagnostics/probe_firstname_guard_options.py     # must match C' for all 13
```

After all tasks:

```bash
pytest -q                                  # see note
python compute_affiliation.py              # regenerates the CSV
python -m diagnostics.affiliation_report   # prints the #3B evidence
```

Test count: this plan was written when the suite was 240 and predicted 271. The
suite is now **302** (A47 landed since), and Task 0 adds ~10–12 more. Treat 271
as stale — assert "no regressions against the count at the start of the
session", not a fixed number.

`attention_affiliation.csv` should hold 771 rows. The `own`/`other`/`neutral`
split printed by the driver should be close to 63% attributed / 37% neutral —
**but that ratio, and the 61,163 / 163,937 figures behind it, are PRE-Task-0.**
Task 0 removes ~1,970 contaminated attributions and moves ~1,449 into the
ambiguous bucket, so re-derive the expected split from the regenerated
`reddit_detail.csv` before treating any mismatch as a venue-map bug.
