# Pilot Files — decided / non-active artifacts

Earlier-stage and superseded work, boxed up by the 2026-06-28 reorg so it stays accessible without
cluttering the active build in `../Full Project Files/`. Nothing here is on the live build path.

## Contents

| Path | What | Why it's here |
|---|---|---|
| `pilot/` | The N=160-skater pilot codebase + raw data + figure + results (`compute_oaq.py`, `fetch_*.py`, `oaq_pilot.csv`). | Illustrative worked example for the abstract; superseded by the 774-skater full build. Its `preregistration.md` is the pilot prereg, NOT the active one. |
| `submission/` | The **accepted CASSIS abstract** (`abstract_v1.md` + `abstract_final.pdf` + `abstract.css`) and the plain-language **methods guide** (`methods.md` + `methods_final.pdf` + `methods.css`). | The conference submission, built on the pilot. Filed here because it documents pilot-scope work — but it is the **reference target the full-build poster must match** (the active build cross-links to it from `../Full Project Files/README.md`). |
| `archive/NHL_Draft_Model.md` | The on-ice prospect-evaluation candidate idea. | Lost selection to the Marchand Index; kept for reference, never built. |

## Notes

- Re-running the pilot needs its own venv: `cd "Pilot Files/pilot"` then `python -m venv .venv` (see `pilot/README.md`). The pilot venv was moved with the folder and its absolute paths may be stale — recreate if needed.
- `*.pdf` finals are committed; `*.html`/`*.css` are pandoc build intermediates.
