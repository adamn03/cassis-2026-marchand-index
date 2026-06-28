# Roster Validation — 2025-26 NHL club-stats (A7 TOI position-split set)

Source of record: `https://api-web.nhle.com/v1/club-stats/{TRICODE}/20252026/2`
plus `/v1/player/{id}/landing` (TOI/GP aggregation) and `search.d3.nhle.com` (id resolution).
Players in file: 160

**Summary: 160/160 confirmed** | 0 mismatch | 0 fetch-failed | 0 id-missing | 0 match_quality=low

## Provenance (A7)

The set is **NHL-API-native**: each row's `full_name`, `position`, `nhl_team_code`, and
`nhl_player_id` are selected directly from the NHL club-stats roster + landing endpoints
by the A7 builder (`fetch_rosters_toi.py`). Per-team selection = top-3 forwards + top-2
defensemen by GP-weighted 2025-26 regular-season TOI/G among skaters with ≥ 41 GP. Identity
is therefore consistent with the NHL API by construction; this file confirms structural
completeness and downstream identifier resolution.

## Structure

- 160 rows = 32 teams × 5 skaters (3 F + 2 D); no team off-count.
- 96 forwards (`group=f1`) / 64 defensemen (`group=d1`).
- 160 unique `nhl_player_id` (no duplicates).
- `roster_source`: 160 `nhl_toi_position`, 0 `nhl_toi_relaxed` (no team needed the
  GP-floor relaxation).

## Identifier resolution

- `nhl_player_id`: 160/160 present (the DailyFaceoff-set's lone id-missing row,
  Michael Benning, is not in the A7 set).
- `wikipedia_slug`: 160/160 resolved; all 160 confirmed via Wikidata occupation =
  ice-hockey player (A1), `wiki_match = occupation` for every row.
- `capwages_slug`: 160/160 resolved; `cap_quality = ok` for all 160 (no `low`-quality
  cap rows excluded from the MI leaderboard).

## Mismatches
- 0 real mismatches

## Fetch failures
- none

## ID-missing
- none (the A7 TOI set fully resolves all 160 against the NHL API)
