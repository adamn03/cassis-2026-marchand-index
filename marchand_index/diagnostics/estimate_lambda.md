# A55 - lambda estimated from club changes

Movers pooled over both transitions: **n = 170** (87 + 83). Outcome is the A12 composite in within-season standard deviations.

| term | b | se | t |
|---|---|---|---|
| intercept | +0.1497 | 0.0599 | +2.50 |
| D market_z | -0.0080 | 0.0324 | -0.25 |
| D ppg | +0.0313 | 0.3114 | +0.10 |
| D toi/g | +0.0578 | 0.0243 | +2.38 |
| D points% | +1.9216 | 0.6803 | +2.82 |
| transition | -0.0457 | 0.0861 | -0.53 |

**lambda-hat = -0.0080**, 95% bootstrap interval [-0.0559, 0.0361] (2000 draws, seed 20260526).

Interval excludes zero: **False**.

A55 adoption rule -> primary lambda = **0.5000** (estimate not distinguishable from zero; pre-registered 0.5 retained).

Pre-registered comparison lambda = 0.5 is retained and reported either way, with the {0, 0.25, 0.5, 0.75, 1.0} ladder unchanged.