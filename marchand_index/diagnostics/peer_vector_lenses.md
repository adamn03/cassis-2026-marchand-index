# A53 peer-vector lenses - Lens A vs Lens B

Pool 771 (`oaq_pilot.csv`, build of 2026-08-31). K=10, shrinkage delta=0.1, lambda=0.0. Primary = STORED `peer_player_ids`; every quantity except the peer sets is held at its build value.

| lens | p | peer overlap | lost >=half | identical | Pearson OAQ | Spearman OAQ | top-25 | bottom-25 | max move (top-25) |
|---|---|---|---|---|---|---|---|---|---|
| primary_pinv (fidelity check) | 6 | 100.0% | 0.0% | 100.0% | 1.0000 | 1.0000 | 100% | 100% | 0 |
| primary_shrunk (estimator effect) | 6 | 88.8% | 0.0% | 22.7% | 0.9882 | 0.9784 | 92% | 96% | 11 |
| lensA_production_detail | 12 | 43.0% | 54.7% | 0.1% | 0.9117 | 0.8349 | 68% | 76% | 552 |
| lensB_attention_stock | 10 | 52.8% | 30.9% | 0.1% | 0.8931 | 0.8403 | 72% | 60% | 141 |

## Largest headline rank moves, by lens

### lensA_production_detail

| player | pos | primary rank | lens rank | move |
|---|---|---|---|---|
| Kevin Korchinski | D | 711 | 62 | -649 |
| Adam Engstrom | D | 663 | 31 | -632 |
| Vincent Iorio | D | 656 | 52 | -604 |
| Zach Metsa | D | 12 | 564 | +552 |
| Ivan Miroshnichenko | L | 704 | 159 | -545 |
| Alex Turcotte | C | 54 | 587 | +533 |
| Jake Christiansen | D | 123 | 655 | +532 |
| Jacob Bernard-Docker | D | 587 | 64 | -523 |
| Ian Moore | D | 131 | 649 | +518 |
| Nils Hoglander | L | 675 | 178 | -497 |

### lensB_attention_stock

| player | pos | primary rank | lens rank | move |
|---|---|---|---|---|
| Cameron Crotty | D | 727 | 61 | -666 |
| Alex Turcotte | C | 54 | 693 | +639 |
| Jake Christiansen | D | 123 | 757 | +634 |
| Nikita Chibrikov | R | 720 | 114 | -606 |
| Hunter Haight | C | 699 | 119 | -580 |
| Kurtis MacDermid | L | 93 | 668 | +575 |
| Helge Grans | D | 659 | 92 | -567 |
| Jeff Malott | L | 593 | 37 | -556 |
| Nathan Bastian | R | 67 | 594 | +527 |
| Alex Bump | L | 618 | 101 | -517 |
