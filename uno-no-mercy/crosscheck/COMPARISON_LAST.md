# Cross-check: play until one player is left (RULES.md section 7)

Two independent implementations of the house rule are compared. One is the C simulator (`sim/nomercy.c -end_rule 1`). The other is the Python reference (`crosscheck/ref_nomercy.py --end-rule last`), written from the RULES.md text alone without reading the C code. Random play is used **only as a test harness**: the same players under the same rules must give the same game-length distribution. The C runs are in `c_last/`, and the Python runs in `ref_results_last.json`. Both implementations resolve the ambiguous cases the same way: a penalty or Roulette reveal that runs out of cards stops early.

| Rule set | Players | Python games | Python mean ± SE | C games | C mean ± SE | z |
|---|---:|---:|---:|---:|---:|---:|
| A: Mercy rule on, finish effect 1 | 3 | 300,000 | 66.14 ± 0.06 | 20,000,000 | 66.14 ± 0.01 | -0.02 |
| A: Mercy rule on, finish effect 1 | 4 | 300,000 | 100.06 ± 0.07 | 1,000,000 | 100.12 ± 0.04 | -0.71 |
| A: Mercy rule on, finish effect 1 | 5 | 300,000 | 130.56 ± 0.08 | 1,000,000 | 130.52 ± 0.04 | +0.48 |
| A: Mercy rule on, finish effect 1 | 6 | 300,000 | 155.29 ± 0.08 | 1,000,000 | 155.31 ± 0.04 | -0.19 |
| A: Mercy rule on, finish effect 0 | 4 | 100,000 | 100.28 ± 0.13 | 1,000,000 | 100.19 ± 0.04 | +0.69 |
| A: Mercy rule on, finish effect 0 | 6 | 100,000 | 155.73 ± 0.14 | 1,000,000 | 155.50 ± 0.04 | +1.59 |
| B: no Mercy rule (your table) | 2 | 3,000 | 15,968.59 ± 340.61 | 100,000 | 16,091.41 ± 60.88 | -0.35 |
| B: no Mercy rule (your table) | 3 | 1,500 | 32,595.73 ± 622.63 | 100,000 | 32,377.21 ± 78.87 | +0.35 |

largest |z| = 1.59 over 8 comparisons

No discrepancy. The Python reference also passes 29 selftest groups (`--selftest`), and its official-rule output is byte-identical to the version used in COMPARISON.md.
