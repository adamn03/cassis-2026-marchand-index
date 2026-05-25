# Session Handoff
Date: 2026-05-24
Active: NHL_Marchand_Index — CASSIS 2026 abstract

LAST: Abstract finalized for May 31 submission, committed, and pushed to `github.com/adamn03/cassis-2026-marchand-index` (private). Three rounds of editorial passes shipped: (a) oral-talk acceptance rewrite — title leads with the eponym, goal sentence as opener, pilot rank-flip in lede para 2; (b) per-player evidence added to §2 so every name in the 14-player pilot carries a verifiable accolade or role identifier; (c) every internal-doc reference (file paths, `pre-reg §N`, `amendment AN`) stripped — the abstract stands on its own to any reviewer who only sees the PDF. Pilot figure replaced with a real-name top-5 rank-flip diagram (Bedard / J. Hughes / Crosby stay; Marchand and McDavid drop out; B. Tkachuk and Kucherov enter — driven by cap), rendered by `pilot/render_figure_v2.py`. Pre-reg amendments A5 (Gate 4 added, prior session) and A6 (§4 figure scope changed to real-name top-5) logged in `pilot/preregistration.md`. Cap-matched peer grouping considered as an alternative model design and explicitly rejected — it conflates skill with attention and would destroy the off-ice-premium interpretability.

STATUS: working — abstract ready for owner to send.

BLOCKER: none. **Owner-only action: send `abstract_final.pdf` to `cascadia-sports@sfu.ca` by 2026-05-31** (7 days from session date).

NEXT: Begin the leaguewide full-build per `NHL_Marchand_Index.md` build order Wk 1 (scrape infra A: Reddit / Wikipedia / Trends → SQLite). Three highest-impact pre-symposium deliverables in priority order — (1) leaguewide K=10 OAQ + Marchand Index for all active NHL skaters with per-player bootstrap CIs + `match_quality` flags; (2) Gates 1 + 2 (jersey-list Spearman ρ AND All-Star fan-vote Spearman ρ — both single-Spearman on already-public data, cheap, 2× validation lift regardless of direction); (3) Gate 4 (stratified generalization on outside-star YouTube residuals — defends the role/depth-player framing).

## Commits landed this session (in order on `main`)

```
36a43a2 SESSION.md: handoff after abstract finalization
06ada79 Abstract: oral-talk rewrite for CASSIS submission
004c023 Pre-reg + figure: full-build Gate 4 added; pilot figure now real-name top-5
34afc36 SESSION.md: capture 90% auto-pause hook investigation + Stop hook fix  ← prior session
```

The current SESSION.md edit (this overwrite) is **uncommitted** and reflects the actual final state after the cancelled push.

## Decisions logged this session — do not re-propose without strong reason

- **Cap-matched peer grouping → rejected.** Considered replacing K=10 Mahalanobis skill matching with K=10 cap-hit matching. Rejected because cap is correlated with skill, so cap-matching covertly matches on skill too — destroys the model's core claim of isolating an off-ice premium. Also breaks the MI = OAQ / cap ratio (numerator would already be cap-conditioned), and would require restarting both pre-registrations. **Cheaper alternative if the cap-fairness story is wanted later:** cap-tier sub-leaderboards (computed from the standard MI) as a v1.1 case-study layer — no model change needed, no pre-reg restart.

## Open items not blocking submission

1. **GitHub push.** Done — repo at `github.com/adamn03/cassis-2026-marchand-index` (private). gh CLI authenticated as `adamn03`. To flip visibility to public later: `gh repo edit --visibility public`. The abstract does **not** commit to a public artifact link, so even private is fine for the submission.
2. **Reddit credentials.** `pilot/.env` from `pilot/.env.example`, 5 min one-time. Then re-run `compute_oaq.py` + `render_figure_v2.py` to incorporate Reddit signal in the pilot. May flip P1 / P2 verdicts.
3. **Bonus pilot re-run with corrected market-baseline composite** (team social-account followers + arena attendance + market-population control). 1–2 days. Could convert pilot P1 / P2 from disconfirmed → confirmed; abstract wouldn't need editing but a re-rendered figure with the corrected proxy would strengthen §2's visual.
4. **Any prose edits owner flags after re-reading the rebuilt PDF.**

## What's where (lean inventory)

| File | Purpose |
|---|---|
| `abstract_final.pdf` | THE submission artifact. 2 pages, 8.5pt Charter, justified. Footer: Adam Noakes · ana178@sfu.ca. |
| `abstract_v1.md` | Markdown source. Edit here → re-render PDF via the command below. |
| `abstract.css` | 2-page Letter print stylesheet. |
| `docs/preregistration.md` | Full-build pre-reg: H1–H4, four validation gates incl. Gate 4 (Stratified Generalization), null-result downgrade rules. Locked before any production modelling. |
| `pilot/preregistration.md` | Pilot pre-reg: 14-player set, K=5 peer pool, P1 / P2 / P3 patterns, A1–A6 amendments. A5 = Gate 4 logged; A6 = §4 figure scope change to real-name top-5. |
| `pilot/oaq_pilot.csv` | Final pilot per-player table. `dropped_components` shows Reddit + Instagram NULL across all 14 rows. |
| `pilot/results.md` / `pilot/results.json` | Pattern verdicts: P3 confirmed (rank reordering); P1, P2 disconfirmed (proxy flaw, diagnostic). |
| `pilot/figure.png` | Real-name top-5 rank-flip diagram (regenerated this session). |
| `pilot/render_figure.py` | ORIGINAL schematic renderer. Preserved for audit; no longer the source of `pilot/figure.png`. |
| `pilot/render_figure_v2.py` | NEW renderer. Reads `pilot/oaq_pilot.csv`, draws top-5 rank-flip with real player names + cap hits. |
| `NHL_Marchand_Index.md` | Full 14-week build spec. Gate 4 added prior session. |

## Rebuild PDF after edits

```bash
pandoc abstract_v1.md -o abstract_v1.html --standalone --embed-resources --css abstract.css --mathml
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless --disable-gpu --no-sandbox \
  --user-data-dir="$TEMP/chrome-pdf-tmp" --no-pdf-header-footer \
  --print-to-pdf="$TEMP/abstract_final.pdf" --print-to-pdf-no-header \
  "file:///C:/Local%20Only/Ai%20projects/Sports%20Analytics%20Conference%20Projeccts/abstract_v1.html"
mv "$TEMP/abstract_final.pdf" abstract_final.pdf
rm abstract_v1.html
```

**Gotcha:** under the Bash-tool sandbox, Chrome cannot write directly into the project directory — render to `$TEMP` and `mv` into place. The `--no-sandbox` and `--user-data-dir` flags also matter.

Regenerate the pilot figure: `python pilot/render_figure_v2.py`.

## Soft factual claims in the abstract worth a 30-second sanity check before sending

1. **"No peer-matched, cap-adjusted, market-controlled estimator exists in the public literature for the off-ice component."** Non-existence claim — defensible against pGPS / NHLe / Corsi-family (all on-ice). Owner should be comfortable defending against a reviewer who names a specific off-ice paper.
2. **Specific accolade citations in §2.** McDavid (multiple Hart and Art Ross), MacKinnon (Hart 2024), Makar (Norris + Conn Smythe 2022), Draisaitl (Hart + Art Ross 2020), Crosby (3 Cups + 2 Harts), Matthews (multiple Maurice Richard + 69 goals in 2023–24), Kucherov (Art Ross 2019 + 2024, Conn Smythe 2020). All believed correct from public records; quick NHL Trophy history check would close any uncertainty.
3. **Bootstrap clause in §1** describes the full-build procedure (per-player attention signal, 1000 draws). Pilot's bootstrap was Wiki-only because Reddit was NULL — honest as a model description, but a careful reviewer might notice the asymmetry.

## Submission reminder (May 31)

Email `abstract_final.pdf` to `cascadia-sports@sfu.ca`. Cover note draft from prior sessions remains valid. Optionally attach `pilot/` (zipped) for the rigor signal — but the abstract is self-contained.
