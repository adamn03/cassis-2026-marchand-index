# Design Spec — Attention-Ingestion Expansion (Amendment A12)

**Project:** The Marchand Index (NHL off-ice fan-attention model)
**Date:** 2026-06-20
**Status:** Approved design, pre-implementation
**Pre-registration:** continues the chain in `preregistration.md` (A1–A11). This is **A12 (ingestion + composite weights)**. A sibling skill-vector amendment (**A13**) is specced separately; A12 commits first.
**Target home:** the real project tree `Marchand Index/` (method ported from `pilot2/`). Amendment IDs continue the existing pre-reg chain.

---

## 1. Purpose

The attention composite reached only English-language and engaged-fan-community demographics (en-Wikipedia, Reddit, Google Trends). For a whole-league (A10, 774-skater) claim against an overclaim-hostile audience, that is too narrow: the single heaviest source (Reddit, 0.417 of the old weight) is also the most demographically narrow. A judge can say "this is three views of the same young-anglophone-fan demographic."

This amendment broadens the **input** demographic with a free flow source — **multi-language Wikipedia** (non-anglophone hockey markets) — drops the Instagram/X follower stock from the composite, re-locks the composite weights by demographic reasoning, and adds two honesty diagnostics that *quantify* the breadth gain. YouTube is **not** an input — it is reserved as the Gate-4 held-out validation signal (see the skill/validation specs); a narrow-input composite validated against a broad-platform signal is the anti-circularity argument, so YouTube earns its keep on the validation side.

GDELT mainstream-news volume was considered and **rejected**: its DOC 2.0 API has a hard ~3-month rolling window that cannot honor the A11 12-month window, and the window mismatch is not worth the breadth gain (see §4). The mainstream/casual-reach demographic is therefore not captured on the input side; it is carried instead by the broad-demographic YouTube validation gate.

## 2. Locked decisions

| Decision | Value |
|---|---|
| Multi-language Wikipedia | Add as a **separate** component `wiki_intl_12mo`; en-Wiki unchanged |
| Language whitelist | Fixed: `sv, fi, cs, ru, de, sk, fr` (hockey markets; locked before fetch) |
| GDELT news | **Rejected** — A11 window mismatch (3-month API floor) not worth it |
| Instagram / X followers | **Dropped entirely** from the model (noisy lifetime stock, fights the A11 window) |
| Composite weights | Final vector in §5, summing to 1.00, derived by demographic reasoning |
| Diagnostics | Source-correlation matrix + Reddit-downweight robustness re-run |
| Window | A11 fixed 365-day window `[2025-04-18 00:00 UTC, 2026-04-18 00:00 UTC)` applies to multilang-Wiki |

## 3. Component — Multi-language Wikipedia pageviews

**Construct:** non-anglophone fan attention (Swedish/Finnish/Czech/Russian/German/Slovak/French markets) that the English composite is blind to.

**Verified:** Wikidata `wbgetentities&props=sitelinks` returns sitelinks keyed `enwiki/svwiki/...` as `{site, title, badges}`. Each player's `wikidata_qid` is already resolved and stored (A1 occupation-checked resolver) in `raw/wiki_pageviews.csv` — **no re-resolution needed**. Wikimedia REST per-article pageviews works identically for any language edition and honors the exact A11 dates (confirmed against `sv.wikipedia/Connor_McDavid`).

**Method:**
1. Map `player_id → wikidata_qid` from the existing wiki CSV.
2. One sitelinks call per QID; intersect available sitelinks with the locked whitelist `{sv,fi,cs,ru,de,sk,fr}`.
3. For each whitelisted edition present, fetch per-article pageviews over the **fixed A11 window** (`20250418/20260417` hardcoded — this diverges from the en fetcher's run-time window).
4. Use the sitelink `title` **verbatim** (canonical by construction; non-Latin titles come straight from the sitelink). URL-encode with `quote(safe="")`.
5. Sum per edition and overall.

**Aggregation:** keep `wiki_en_12mo` (existing component, unchanged) and add a **separate** `wiki_intl_12mo = Σ` over the non-English whitelist editions. Not folded into en, not replacing en — separateness lets the source-correlation diagnostic prove intl adds breadth, and lets per-player sentinel renorm handle the common "en-only" player cleanly.

**Output — `raw/wiki_intl_pageviews.csv`:** `player_id, full_name, wikidata_qid, editions_available (pipe-list), editions_fetched (pipe-list), wiki_intl_12mo (int or NULL), per_edition_json, window_start, window_end, fetch_date, intl_match (ok|none)`.
Plus **`raw/wiki_intl_daily.csv`** (`player_id, edition, n_days, daily_views`) mirroring `wiki_daily.csv`, so the §10 bootstrap can resample international daily vectors.

**Fetcher — `fetch_wikipedia_intl.py`:** reuses `_common.session()`, `CONTACT_UA`, `atomic_write_csv`, UTF-8 forcing. `requests_cache` on; `sleep(0.2)` between article calls, `0.15` between sitelink calls. Budget ≈ 3–4k requests (~20–30 min), free on re-run via cache.

**Failure / NULL:** no whitelisted sitelink → `wiki_intl_12mo` NULL, `intl_match=none`, sentinel renorm drops the component for that player. A single edition 404 → skip that edition, keep the rest. No occupation re-check needed (QID already passed A1's P106 test); the A1 redirect-undercount bug cannot recur (sitelink titles are canonical).

## 4. Considered and rejected

**GDELT mainstream-news volume.** DOC 2.0 ArtList has a hard ~3-month rolling window + 250-record cap; `timelinevolraw` dodges the record cap but not the 3-month coverage floor. It **cannot** retrospectively cover the A11 12-month window. Backfilling from raw GDELT GKG/Events dumps is terabytes of download + multi-day local compute — disproportionate at $0. Including GDELT over a shorter, disclosed window was on the table but rejected: a single source on a different window than every other component is a standing target for a stats-literate reviewer, and the breadth gain does not justify the integrity cost. The mainstream-media demographic is instead carried by the broad-demographic YouTube validation gate.

**Instagram / X follower counts.** Publicly recoverable via search snippets/aggregators (no API needed), but they are a lifetime **stock** (career-accumulated fame), not an in-window flow — they fight the A11 window and leak age/career length. They are also noisy and inflatable (documented fake-follower rates; public sources disagree ~2×). Dropped from the model entirely.

## 5. Composite weights (final, locked)

IG/X and GDELT removed, multilang-Wiki inserted, derived by demographic-coverage balance (not fitted to any result), locked before fetch, original vector retained in the amendment.

| Component | Weight | Demographic |
|---|---|---|
| `wiki_en_12mo` | 0.29 | EN encyclopedic / casual lookup |
| `wiki_intl_12mo` | 0.11 | non-anglophone hockey markets |
| `reddit_mentions_12mo` | 0.27 | engaged fan community |
| `reddit_upvotes_12mo` | 0.17 | engaged fan community |
| `trends_12mo` | 0.16 | general search (passive) |
| **Sum** | **1.00** | |

Reddit family = 0.44 (still below the old 0.484 — the narrowest demographic no longer dominates, while passionate-fan attention, the core construct, keeps strong weight), with 0.11 of new non-anglophone breadth added. `engagement_raw = Σ_c weight_c × z(component_c)`, components z-scored across the 774.

**Sentinel renormalization (extends §4 unchanged):**
- `wiki_intl` NULL is common (anglophone-only players) → other flow weights renorm to 1.00 for that player; he is not penalized for lacking a Swedish article.
- The dropped IG/X stock never participates in flow renorm (out of the composite entirely).

## 6. Diagnostics (honesty / skew-defense)

**(a) Source-correlation matrix.** Across the 774, pairwise **Spearman** correlation among all z-scored components (`wiki_en, wiki_intl, reddit_mentions, reddit_upvotes, trends`), pairwise-complete with per-cell n reported. Pre-registered expectation (descriptive, not a gate, reported regardless of direction): `corr(wiki_intl, reddit_*)` is **lower** than `corr(wiki_en, reddit_*)` — the added non-anglophone source sits further from the Reddit cluster. Output: `diagnostics/source_correlation.csv` + `figure_source_correlation.png`. Poster line: "International Wikipedia correlates ρ≈X with Reddit vs ρ≈Y for English Wikipedia — it reaches fans the English-only signals miss." Never feeds back into weights.

**(b) Reddit-downweight robustness.** Re-run the full OAQ pipeline at a pre-declared ladder of Reddit weights — Reddit family scaled to {1.0, 0.5, 0.0}× its A12 weight, redistributing proportionally across non-Reddit flows. Compare each variant to the headline via Spearman of `OAQ_portable` across the 774 + top-20 overlap. Expectation (reported regardless): `ρ(full, half-reddit) ≥ ~0.9`, no-reddit still strongly positive → OAQ is not a Reddit artifact; a collapse is disclosed honestly. Output: `diagnostics/reddit_robustness.csv` + figure. The headline stays the locked A12 vector regardless — this is sensitivity analysis (like the A5 λ-ladder), not a weight search.

## 7. Amendment A12 text (to commit before any new-source fetch)

> **A12 (2026-06-XX) — Attention ingestion broadened: multi-language Wikipedia added as a flow component; Instagram/X follower count removed from the composite; GDELT news rejected on A11-window grounds. New §4 flow-weight vector logged BEFORE any new-source fetch. Anti-tuning: weights derived by demographic-coverage reasoning, prior vector retained.**
>
> Motivation: the §4 composite reached only English-language and engaged-fan-community demographics, leaving the whole-league (A10) coverage claim open to the "this just measures Anglophone Reddit fame" attack. A breadth flow is added — `wiki_intl_12mo` (pageviews summed over the fixed hockey-market edition set {sv, fi, cs, ru, de, sk, fr}, A11 window, Wikidata-QID reused from A1).
>
> The Instagram follower count — a lifetime STOCK that is noisy and inflatable (documented fake-follower rates; public sources disagree ~2×) and conceptually mismatched with the A11 flow window — is removed from the composite (prior weight 0.139 → dropped); X followers are not added. GDELT mainstream-news volume was considered and rejected: its DOC 2.0 API has a hard ~3-month rolling window that cannot honor the A11 12-month window, and a single source on a divergent window is not worth the integrity cost; the mainstream-reach demographic is carried instead by the broad-demographic YouTube validation gate.
>
> New §4 flow weights: wiki_en 0.29, wiki_intl 0.11, reddit_mentions 0.27, reddit_upvotes 0.17, trends 0.16 (sum 1.00). Prior vector (wiki 0.306, reddit_mentions 0.250, reddit_upvotes 0.167, trends 0.139, instagram 0.139) retained here for audit. Sentinel renorm (§4) applies unchanged to the new component; the dropped follower stock never participates. Peer features (§6), λ (§7/A5), denominators (A4/A8), OAuth transport (A9), the A10 774-pool + small_sample flag, the A11 window, and all validation floors (§9, A6/V3) are unchanged.
>
> **Letter reconciliation:** the sibling skill-vector amendment commits as the next free letter (A13).

## 8. Anti-tuning compliance

Weights assigned by demographic-coverage reasoning before any new component is fetched; prior vector retained verbatim; no weight adjusted after seeing OAQ, ρ, or any player's rank. The language whitelist is external/objective, not rank-driven. Diagnostics are descriptive and never feed back into weights.

## 9. Open items / risks

1. **multilang whitelist** — locked `{sv,fi,cs,ru,de,sk,fr}`; revisit only as a logged amendment.
2. **Breadth now rests on one new source** (multilang-Wiki). With GDELT rejected and IG/X dropped, the input-side demographic broadening is non-anglophone markets only; mainstream-media reach is validated, not ingested. Disclose this honestly — the source-correlation diagnostic shows exactly how much breadth multilang-Wiki adds.
3. **Coverage skew** — `wiki_intl` is NULL for anglophone-only players (most North-American-born skaters); reported in `results.md`, and is the *point* (it lights up for European players the en signal under-counts).
4. **Re-confirmation** — adding a composite component re-rolls every gate; V1/V2/V3 re-reported regardless of direction against unchanged floors (shared with A13).
