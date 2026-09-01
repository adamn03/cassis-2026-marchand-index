# The Marchand Index

**Alex Ovechkin and a fourth-line enforcer named Matt Rempe have something in common: both
draw far more public attention than anyone who plays like them.**

That gap is measurable. This project measures it for all 771 skaters in the NHL.

**Accepted for [CASSIS 2026](https://www.cascadiasports.com/) — the Cascadia Symposium on
Statistics in Sports.**

### ➜ **[Open the dashboard](https://adamn03.github.io/cassis-2026-marchand-index/)**

---

## What it does

Every player is matched against his ten closest comparables in the league — same position,
similar scoring rate, similar minutes, similar even-strength play. Then it asks a simple
question:

> **How much more public attention does he generate than those ten do?**

Attention is measured three ways over one fixed season: Wikipedia pageviews, Reddit
mentions and upvotes, and Google search interest. What's left after subtracting his peers
is the **Marchand Index** — the attention a player generates that his play doesn't explain.

It's named for Brad Marchand: a genuinely excellent player whose public profile runs well
ahead of what his production alone would produce.

A second version divides that figure by the player's salary, which asks a different
question — not *who is over-noticed*, but *who is over-noticed cheaply*. The two lists
barely overlap, and that turns out to be one of the more interesting results.

## What it found

**The NHL does not pay extra for attention.** A player who generates one standard deviation
more attention than his peers earns essentially nothing extra on his next contract —
**−0.4%**, with a confidence interval of [−6.5%, +6.5%]. The same model prices one standard
deviation of ice time at **+43.8%**.

Attention is a cost the market does not charge for. A club acquiring a high-profile player
gets the public interest thrown in free.

**Most of the league is unremarkable, and that is the point.** Only 26 players out of 595
are clearly above their peer group. Roughly 94% sit within the noise. The interesting
population is small.

**The index agrees with something it never saw.** It was built from Wikipedia, Reddit and
search data, and never shown a single follower count. Checked afterwards against players'
Instagram and X followings, it lines up at **ρ = 0.50** — an independent confirmation that
it's measuring real public interest rather than statistical residue.

## What it deliberately doesn't do

It doesn't publish a ranking. Rebuild the peer groups using a different but equally
defensible set of statistics and players move enough that "7th" and "8th" are not
distinguishable claims. So the dashboard reports **tiers**, sized so that a player in one
tier is genuinely separated from a player in the next, and it says outright that order
within a tier is not a claim.

It also doesn't correct for market size, despite market size mattering. The attempt is
documented on the dashboard: the data sources disagreed about the sign of the effect, so no
correction is applied rather than one that can't be defended.

## Reproduce it

```bash
cd marchand_index
python fetch_rosters_league.py    # roster pool
python fetch_nhl_api.py           # age, scoring, ice time
python fetch_moneypuck.py         # even-strength play-driving
python fetch_wikipedia.py         # pageviews
python fetch_reddit.py            # mentions and upvotes
python fetch_trends.py            # search interest
python fetch_cap_hits.py          # contracts
python compute_oaq.py             # the index
python build_dashboard_data.py    # dashboard payload
```

Every source is free or public. No paid APIs, no private data.

## Layout

| Path | What |
|---|---|
| **`marchand_index/`** | **Everything needed to reproduce this** — fetchers, the index, tests |
| `marchand_index/raw/` | Every input, as collected |
| `marchand_index/preregistration.md` | Every design decision, written down before the code that tests it ran |
| `marchand_index/value_propositions.md` | Every idea tried, including the ones that failed |
| `docs/` | The dashboard, served by GitHub Pages |
| `cassis_submission/` | The accepted CASSIS abstract |
