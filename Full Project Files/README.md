# Full Project Files — active Marchand Index build

Everything currently in use for the CASSIS 2026 poster. Created by the 2026-06-28 reorg
(split from `Pilot Files/`).

## Contents

| Path | What |
|---|---|
| `NHL_Marchand_Index.md` | The live project spec (method, scope, validation gates, build order). |
| `marchand_index/` | The active codebase. **Self-contained** — `cd` into it and run `python -m pytest -q` (61 tests) or the fetch/compute scripts. Relative paths (`raw/`, `fetch_*.py`, `diagnostics/`, `preregistration.md`) resolve from inside the folder. |
| `marchand_index/preregistration.md` | **Canonical implementation prereg** (amendments A1–A14). Code + tests read this file relatively — do not move it out of `marchand_index/`. |
| `marchand_index/value_propositions.md` | Downstream value-prop backlog (#1–#7). Build AFTER data + the 5 validation gates land. |
| `docs/preregistration.md` | Spec-level prereg: H1–H4 hypotheses + Gate-4 sampling/band rules (committed before the production run). |
| `docs/superpowers/{specs,plans}/` | Design history (whole-league pool, ingestion expansion, skill-vector expansion). |

## Accepted CASSIS submission

The accepted 2-page abstract + plain-language methods guide live in **`../Pilot Files/submission/`**
(they document the N=160 pilot the submission was built on). The poster must conform to that
accepted abstract — keep it open as the reference target when building poster content.

## Status

Active branch `marchand-index-full-build`. Only remaining data task: the Reddit track — now
credential-free per prereg A23 (Arctic Shift archive): `fetch_reddit_corpus.py` pulls the 36-sub
corpus, `fetch_reddit.py` matches locally, then re-run `compute_oaq.py` + diagnostics. No OAuth
creds needed. See root `SESSION.md`.
