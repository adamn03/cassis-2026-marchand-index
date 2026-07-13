# Supplement — Reddit Source Switch to Arctic Shift (2026-07-13)

**Status:** owner-approved 2026-07-13 (plan-mode approval). Supplements `airtight_execution_plan.md` v1.1 — does not edit it; supersessions recorded in §3 below. Amendment text lives in `2026-07-12-amendment-proposals.md` (A23, rewritten) and commits to the impl prereg §14 before any fetch.

## 1. Decision

Replace the A9 authenticated Reddit OAuth transport with the **Arctic Shift archive** (`arctic-shift.photon-reddit.com`, free, no auth) for the 774-set production Reddit fetch. Architecture is **corpus-first**: download every in-window submission for 36 fixed subreddits into a local cache once; all per-player matching runs locally against that corpus. The local corpus — not the API — is the source of record for the production run.

Drivers: kills the months-old owner creds blocker; removes the 1,000-result cap (original A23's entire reason to exist); native date-windowed complete enumeration replaces the A11 newest-first paging hack; fetch estimate drops from days (Task 1.8) to hours.

## 2. Verification evidence (live probes, 2026-07-13)

| Check | Result |
|---|---|
| Window coverage [2025-04-18, 2026-04-17] | 13/13 months r/hockey; 32/32 team subs have posts through window end. Two transient HTTP 422s cleared on retry — rate-limit noise, not gaps |
| Fields | `id, title, selftext, score, created_utc, subreddit, num_comments, author` all present; `limit=100` works |
| Score semantics | `_meta.retrieved_2nd_on` ≈ 2.5 days post-creation; realistic distribution (probe: med 10, max 2551) |
| Completeness | Cross-check vs PullPush (independent archive) on r/hockey "McDavid" [2025-04-18, 2025-05-17]: **67/67 unique ids present in Arctic Shift**; Arctic-Shift-only misses vs PullPush: 0 |
| Archive `query` search recall | 63/67 on the slice — misses = curly-apostrophe possessives ("McDavid's") + posts whose mention was bot-edited in after creation. Local fold-token matching recovers 65/67; residual 2 = creation-time-text semantics (pre-declared, A23 rule 4a). **Production never uses the archive's search endpoint** |
| PullPush (the alternative) | NOT viable — its ingestion died 2025-05-19; covers ~1 of 12 window months. Also returns duplicate rows (77 raw = 67 unique on the test slice) |
| UTA sub rename | `r/UtahHockey` (pre-rebrand) active from ≥2025-04-19; `r/utahmammoth` earliest in-window post 2025-04-30 → UTA sub set = both (A22 sub-rename rule) |
| Extra-sub candidates (Jan-2026 volume) | ADD to corpus, descriptive-only: r/nhl (500+/mo), r/fantasyhockey (500+/mo — densest depth-player mention source). REJECTED: r/hockeyanalytics (0 — dead), r/hockeycirclejerk (62/mo + nickname-dominant, surname matching structurally misses), r/NHLHUT (game-card economy, not fan salience) |

## 3. Supersessions of `airtight_execution_plan.md` v1.1

| v1.1 item | Status |
|---|---|
| §B A23 spec (top-sort second pass, lower-bound semantics) | **Superseded.** Cap does not exist under complete enumeration; A23 slot repurposed for the source-switch amendment (proposals doc, 2026-07-13 revision) |
| Task 1.8 "Reddit fetch readiness" (OAuth, days-long pagination) | **Obsolete.** No creds; corpus pull ≈ 3–5 h at 1 req/s, resumable |
| §E Phase-2 trigger "after creds" | **Obsolete.** Reddit fetch has no owner prerequisite. §E's ORDER (purge → fetch → wiki_intl → one compute) is unchanged |
| Owner action "fill Reddit creds in `.env`" (decision sheet, README, whole-league spec) | **Void.** Removed from the owner task list |

Unchanged: A21 identity rules; A22 roster-derivation rule (extended with the UTA rename clause); all weights, floors, window, λ, denominators; the decision sheet's D-1/D-2/D-3 and U-items.

## 4. Construct boundaries (what did NOT change)

- **Submissions-only stands.** Reddit COMMENTS remain rejected per the 2026-07-07 free-data supplement (construct change on 0.44 locked A12 weight). The corpus architecture makes a comments pull cheap later (H1/H4/Gate-5 are post-poster future work) — but it is not part of this switch.
- **Composite counting subs unchanged:** r/hockey + the player's A22 team-sub set. r/nhl + r/fantasyhockey enter only `reddit_mentions_allsubs` / `reddit_mentions_fantasy` (descriptive, never composite — A12 weights locked).

## 4b. Finding — pool duplicate rows (OWNER DECISION NEEDED, pre-existing)

The A21 acceptance dry-run (`diagnostics/reddit_identity_dryrun.py`, output
`raw/reddit_identity_pairs.md`) confirmed the MID-dupe suspicion SESSION.md had
queued: the locked 774 pool contains **3 duplicate persons** — identical
`nhl_player_id` under two snapshot teams (mid-move rows): Emil Andrae (pids
499/637, PHI+TOR), Simon Benoit (500/638, PHI+TOR), Ross Colton (152/368,
COL+NAS). The two Elias Petterssons are NOT dupes (distinct ids — real pair).

Effect on Reddit: A21 rule 3 mechanically flags each dupe pair fully
non-discriminable → all their mentions land in `ambiguous_mentions`, zeroing
both rows. Honest per the rules, but it zeroes 3 real players because of a
pool defect, not true ambiguity. Fix is a POOL amendment (774 → 771 dedup) —
touches N everywhere, so it is an owner decision, not made here. The matcher
is deterministic from the corpus: re-run after the pool decision costs ~2 min.

## 5. Open item — A30 transport

A30 (market-proxy rebuild, pending owner decision D-2) specified team-sub subscriber counts via the A9 OAuth transport (`oauth.reddit.com/r/<sub>/about`). A9 is now superseded. If D-2 = rebuild: source subscriber counts from Arctic Shift's subreddits endpoint or unauthenticated `www.reddit.com/r/<sub>/about.json` — probe at A30 implementation time, record in A30's text. Not blocking anything today.

## 6. Risk register

- **Archive longevity:** PullPush died mid-2025 with zero warning. Mitigation: pull the corpus NOW; after the pull the run is fully reproducible offline.
- **Rate limiting:** transient 422s observed; puller uses the house backoff ladder. Worst case the pull just takes longer.
- **Completeness unprovable vs ground truth:** two-archive 67/67 id agreement is the strongest available evidence; recorded in A23 rule 6 and disclosed as a residual.
