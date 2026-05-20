# Session Handoff
Date: 2026-05-20
Active: NHL_Marchand_Index — CASSIS 2026 abstract

## LAST SESSION
- **Built:** Complete CASSIS abstract package. 2-page PDF rendered. Pre-registered pilot ran end-to-end. Pre-reg fallback rule fired (2/3 expected patterns disconfirmed) and produced a methodologically informative sensitivity finding rather than a forced-pretty figure.
- **Status:** working — `abstract_final.pdf` is ready for the owner to email by 2026-05-31.
- **Next:** Owner sends the PDF to `cascadia-sports@sfu.ca` on or before 2026-05-31, with a brief cover note (title + author + oral preferred). Attach `abstract_final.pdf`. Optionally also attach `pilot/` as zip for the rigor signal.

## How to send (May 31 owner action)

1. Compose new email to `cascadia-sports@sfu.ca`
2. Subject: `CASSIS 2026 abstract submission — The Marchand Index`
3. Body (suggested):
   > Hello,
   >
   > Please find attached my CASSIS 2026 abstract submission, "The Marchand Index: A Cap-Adjusted Off-Ice Attention Quotient for NHL Players." I am requesting consideration for an oral presentation.
   >
   > The pilot pre-registration document, pipeline scripts, and pilot CSV are available at [project repository URL — push to GitHub before sending if you want this link to resolve].
   >
   > Best,
   > Adam Noakes (ana178@sfu.ca)
4. Attach: `abstract_final.pdf`
5. Send.

## Optional pre-send polish

- Push the project repo to GitHub (`adamn03/marchand-index-cassis-2026` or similar) and add the URL to the cover note.
- Re-verify the PDF still says "Adam Noakes · ana178@sfu.ca" at the foot of page 2.
- If you want Reddit signal included in the pilot composite, set up `pilot/.env` per `pilot/.env.example` (5 min, one-time) and re-run `python compute_oaq.py && python render_figure.py`. Doing so will change the §4 pilot result and may flip pattern verdicts.

## Repo state (commits)

```
cce3037  Abstract: 2-page PDF rendered for CASSIS submission
747f398  Pilot run: results + schematic figure (P1/P2 disconfirmed, P3 confirmed)
702b30f  Pilot pipeline: fetch + compute + render scripts
b89656e  abstract: pin pilot pre-reg reference to commit 9774a68
91f4bdc  Pilot scaffold: requirements, env template, 14-player roster, README
9774a68  Pilot pre-registration locked; no fetch code in this commit
7e08355  Project setup: CASSIS conference specs and initial abstract draft
```

## Key file inventory

| Path | What |
|---|---|
| `abstract_final.pdf` | 2-page submission PDF — the artifact |
| `abstract_v1.md` | Markdown source of the abstract |
| `abstract.css` | Print stylesheet (Letter, 8.6pt Charter, justified) |
| `abstract_v1.html` | Pandoc-rendered HTML (intermediate) |
| `pilot/preregistration.md` | Pre-registered pilot scope + 4 amendments (A1–A4) |
| `pilot/oaq_pilot.csv` | Per-player OAQ, Marchand Index, bootstrap CIs |
| `pilot/results.md` / `results.json` | Pattern verdicts (P3 confirmed; P1, P2 disconfirmed) |
| `pilot/figure.png` | Schematic side-by-side rank diagram (fallback rule) |
| `pilot/raw/*.csv` | Fetched raw data |
| `pilot/fetch_*.py`, `compute_oaq.py`, `render_figure.py` | Pipeline scripts |
| `NHL_Marchand_Index.md` | Locked spec (full 14-week build) |
| `CLAUDE.md` | Project rules + 7 evaluation criteria |
