# Owner Decision Sheet — §D + U1–U8 slotting

**Date:** 2026-07-11. **Status:** ADVISORY — synthesized from `airtight_execution_plan.md` §D, the idea-maximization review, and the application plan (both 2026-07-11). Owner marks each box; decisions get recorded in prereg per §I. Nothing below is committed until marked.

---

## Part 1 — The 3 §D blockers (in order)

### D-1: Gate-4 GO/NO-GO
**Recommend: GO.** Panel verdict says mandatory — without it the ≥3-pathways criterion fails (J3-F2) and criterion 2 collapses. ~8 fetch-days of free quota, long-lead, independent of Reddit.
**Rider:** approve U1 with it (fail-fast 10-player dry-run, 3–5h, no amendment needed, ~1.5k quota units). If depth-band yield is thin you learn in July, not the last fetch-week; §6.2.2 escalation rule already pre-registers the response.
- [ ] GO + U1 rider (recommended)
- [ ] GO without U1
- [ ] NO-GO (accept 2-pathway cap — fails criterion 2; not viable for best-in-show)

### D-2: A30 market-proxy rebuild
**Recommend: REBUILD PRIMARY.** Canada confound is first-order on 0.44 of composite weight; no results exist yet so the rebuild is free of tuning suspicion; sensitivity-only fallback stays documented in A30.
- [ ] Rebuild primary (recommended)
- [ ] Sensitivity-only

### D-3: A31 headline structure sign-off
**Recommend: SIGN OFF, with U2 folded in before A31 is committed.** Validation-finding headline, MI demoted to panel — unchanged from plan. U2 adds (a) Hanley–McNeil pre-computed power statement (kills "test you can't fail" attack), (b) paired bootstrap ΔAUC vs baselines (same 1,000 draws, same seed — two-line code change). Free ONLY while A31 is unwritten; after commit it costs an A40 clause.
- [ ] Sign off + U2 folded in (recommended)
- [ ] Sign off without U2
- [ ] Rework headline structure (specify)

---

## Part 2 — U1–U8 slotting

| U | What | Effort | Amendment? | Recommend | When |
|---|---|---|---|---|---|
| U1 | Gate-4 10-player dry-run | 3–5h | none | **YES** (rider on D-1) | right after G4-A1..3 commit + YouTube key |
| U2 | Power statement + paired ΔAUC | 2–3h | none if inside A31 | **YES** (rider on D-3) | at A31 write time — window closes at commit |
| U3 | A40 descriptive batch (reliability, permutation-null, market-share, drop-one-peer, survivorship line) | ~1 day | YES — draft §4 of idea-max review | **YES** | Phase-0 tail, after A39, before compute |
| U4 | Amendment-timeline audit-trail figure | 3–4h | none | **YES** | poster phase |
| U5 | Criterion-7 package: repo snapshot + `reproduce.ps1` + booth lookup CLI | ~1 day | none | **YES** — criterion 7 currently has ZERO deliverable; poster footer promises repo URL nothing produces | poster phase; repo scaffold any idle moment |
| U6 | Booth attack-FAQ card | 2–3h | none | **YES** | poster phase |
| U7 | Elevate A38 λ̂ to titled second finding ("fame is X% portable") | ~2h layout | none | **YES** — the single highest-leverage counter to the identified loss mode (rigor without memorable discovery) | poster phase |
| U8 | Merch/usage outcome sweep | 3–4h | YES (A41-class) | **DEFAULT SKIP** — only if U1 dry-run comes back worrying | conditional |

- [ ] Accept recommended slate (U1–U7 yes, U8 conditional)
- [ ] Modifications: ______________

**Budget check:** pre-compute adds U1+U2+U3 ≈ 2 working days; U4–U7 land in poster phase where plans are thinnest. Nothing touches weights, window, λ, K, seed, pool, floors, or headline definition.

## Part 3 — Interaction with application plan (no decision needed, FYI)
`marchand_explorer.html` (judge-touch artifact) and U5 (repo + reproduce + CLI) are complementary, not duplicative — together they fully fund criterion 7. Explorer builds post-gates (≤2 days); U5 scaffold can start any idle moment. Post-conf ranking (#2 Superstar Whistle → #6 Sticky Minutes) needs no decision until the A31 matrix row is known.

## Part 4 — After boxes are checked (execution order, no further input needed)
1. Record §D decisions in prereg (§I item).
2. Write + commit A21–A29 amendment texts, then A30 (per D-2), then A31 (with U2 per D-3), A32–A35, G4-A1..3.
3. U1 dry-run (needs YouTube API key — USER ACTION alongside Reddit creds).
4. Supplement tail A36→A39, then U3's A40 batch.
5. Gate-4 launch; Phase 2 on Reddit creds.
