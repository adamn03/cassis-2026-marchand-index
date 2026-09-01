# Market pass-through on the log scale

Movers pooled over both transitions: **n = 170**. Every outcome is a change in log attention, so each coefficient is a proportional pass-through per 1 SD of market size. Controls: change in PPG, TOI/G, destination points percentage, transition.

## Per component

| source | A12 weight | b | 95% CI | t | % per SD |
|---|---|---|---|---|---|
| en-Wikipedia | 0.29 | +0.1470 | [+0.082, +0.211] | +4.65 | +15.8% |
| intl-Wikipedia | 0.11 | +0.0360 | [-0.012, +0.083] | +1.42 | +3.7% |
| Reddit mentions | 0.27 | -0.0824 | [-0.161, -0.007] | -2.25 | -7.9% |
| Reddit upvotes | 0.17 | +0.0714 | [-0.033, +0.180] | +1.37 | +7.4% |

## Averaged across sources (A12 weights, log scale)

| outcome | b | 95% CI | t | % per SD |
|---|---|---|---|---|
| weighted composite | +0.0434 | [-0.021, +0.108] | +1.40 | +4.4% |

## Free club effects (no market index assumed)

24 clubs, identified off 170 moves (~7.1 per club -- thin, so these are noisy).

- correlation with the market index: Spearman **+0.322** (p=0.125), Pearson +0.325

| club | est. attention effect | market index |
|---|---|---|
| VAN | +0.949 | +0.47 |
| TOR | +0.925 | +1.32 |
| PIT | +0.771 | +0.44 |
| DAL | +0.755 | +0.31 |
| WPG | +0.705 | -0.95 |
| MIN | +0.678 | +0.79 |
| … | | |
| STL | +0.274 | +0.07 |
| PHI | +0.207 | +0.04 |
| UTA | +0.027 | -2.37 |
| ANA | +0.000 | -0.62 |

## Read

- Component estimates span -0.082 to +0.147 (spread 0.229).
- Averaged estimate: **+0.0434** [-0.021, +0.108] = **+4.4% per SD of market**.
- Averaged CI excludes zero: **False**.