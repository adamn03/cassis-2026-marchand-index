# A53 peer-vector lenses - Lens A vs Lens B

Pool 771 (`oaq_pilot.csv`, build of 2026-08-31). K=10, shrinkage delta=0.1, lambda=0.0. Primary = STORED `peer_player_ids`; every quantity except the peer sets is held at its build value.

| lens | p | peer overlap | lost >=half | identical | Pearson OAQ | Spearman OAQ | top-25 | bottom-25 | max move (top-25) |
|---|---|---|---|---|---|---|---|---|---|
| primary_pinv (fidelity check) | 6 | 100.0% | 0.0% | 100.0% | 1.0000 | 1.0000 | 100% | 100% | 0 |
| primary_shrunk (estimator effect) | 6 | 88.8% | 0.0% | 22.7% | 0.9885 | 0.9788 | 96% | 92% | 9 |
| lensA_production_detail | 12 | 43.0% | 54.7% | 0.1% | 0.9225 | 0.8547 | 76% | 76% | 584 |
| lensB_attention_stock | 10 | 52.8% | 30.9% | 0.1% | 0.8782 | 0.8039 | 60% | 64% | 409 |

## Largest headline rank moves, by lens

### lensA_production_detail

| player | pos | primary rank | lens rank | move |
|---|---|---|---|---|
| Jaycob Megna | D | 740 | 139 | -601 |
| Jake Christiansen | D | 47 | 643 | +596 |
| Jacob Bryson | D | 9 | 593 | +584 |
| Zack MacEwen | R | 44 | 594 | +550 |
| Nils Aman | C | 593 | 51 | -542 |
| Justin Danforth | R | 703 | 165 | -538 |
| Lars Eller | C | 132 | 645 | +513 |
| Kevin Korchinski | D | 519 | 11 | -508 |
| Fedor Svechkov | C | 56 | 558 | +502 |
| Zach Metsa | D | 259 | 751 | +492 |

### lensB_attention_stock

| player | pos | primary rank | lens rank | move |
|---|---|---|---|---|
| Jake Christiansen | D | 47 | 759 | +712 |
| Scott Sabourin | R | 716 | 13 | -703 |
| Zack MacEwen | R | 44 | 719 | +675 |
| Nikita Chibrikov | R | 728 | 62 | -666 |
| Alex Turcotte | C | 31 | 695 | +664 |
| Cameron Crotty | D | 742 | 90 | -652 |
| Max Jones | L | 51 | 693 | +642 |
| Helge Grans | D | 691 | 109 | -582 |
| Carson Lambos | D | 612 | 35 | -577 |
| Kurtis MacDermid | L | 30 | 604 | +574 |
