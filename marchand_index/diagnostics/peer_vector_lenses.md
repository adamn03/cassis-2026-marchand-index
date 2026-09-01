# A53 peer-vector lenses - Lens A vs Lens B

Pool 771 (`oaq_pilot.csv`, build of 2026-08-31). K=10, shrinkage delta=0.1, lambda=0.0. Primary = STORED `peer_player_ids`; every quantity except the peer sets is held at its build value.

| lens | p | peer overlap | lost >=half | identical | Pearson OAQ | Spearman OAQ | top-25 | bottom-25 | max move (top-25) |
|---|---|---|---|---|---|---|---|---|---|
| primary_pinv (fidelity check) | 6 | 100.0% | 0.0% | 100.0% | 1.0000 | 1.0000 | 100% | 100% | 0 |
| primary_shrunk (estimator effect) | 6 | 88.8% | 0.0% | 22.7% | 0.9882 | 0.9785 | 96% | 96% | 9 |
| lensA_production_detail | 12 | 43.0% | 54.7% | 0.1% | 0.9127 | 0.8368 | 68% | 76% | 559 |
| lensB_attention_stock | 10 | 52.8% | 30.9% | 0.1% | 0.8936 | 0.8392 | 76% | 60% | 123 |

## Largest headline rank moves, by lens

### lensA_production_detail

| player | pos | primary rank | lens rank | move |
|---|---|---|---|---|
| Kevin Korchinski | D | 711 | 56 | -655 |
| Adam Engstrom | D | 660 | 31 | -629 |
| Vincent Iorio | D | 655 | 50 | -605 |
| Zach Metsa | D | 12 | 571 | +559 |
| Ivan Miroshnichenko | L | 700 | 145 | -555 |
| Alex Turcotte | C | 53 | 585 | +532 |
| Jake Christiansen | D | 124 | 655 | +531 |
| Jacob Bernard-Docker | D | 585 | 63 | -522 |
| Ian Moore | D | 130 | 650 | +520 |
| Nils Hoglander | L | 673 | 158 | -515 |

### lensB_attention_stock

| player | pos | primary rank | lens rank | move |
|---|---|---|---|---|
| Cameron Crotty | D | 727 | 59 | -668 |
| Alex Turcotte | C | 53 | 693 | +640 |
| Jake Christiansen | D | 124 | 757 | +633 |
| Nikita Chibrikov | R | 720 | 105 | -615 |
| Hunter Haight | C | 704 | 120 | -584 |
| Kurtis MacDermid | L | 94 | 669 | +575 |
| Helge Grans | D | 659 | 87 | -572 |
| Jeff Malott | L | 599 | 36 | -563 |
| Nathan Bastian | R | 65 | 591 | +526 |
| Alex Bump | L | 624 | 102 | -522 |
