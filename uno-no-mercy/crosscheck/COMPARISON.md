# Cross-check: Python reference vs C simulator (random policy)

> **Version note.** This comparison was run against the first version of `sim/nomercy.c` (git commit `6ce905f`), which did not count a Roulette victim's reveal as a turn; the reference used the same definition, so the comparison is like-for-like. Its C results now live in `results/crosscheck_v1/`. The current simulator counts those reveals (RULES.md section 6); the re-check under the new definition is at the end of this file.


## Verdict

**No real discrepancy was found. Across 80 comparisons, the largest |z| is 2.53, and no |z| exceeds 4.**
The two implementations were written independently. They agree on every metric at every
player count from 2 to 6: mean, SD, quantiles and tail survival of game length, how the game
ends, eliminations, plays, draws and reshuffles.

- **The only group above 2σ is at 3 players** (mean turns, SD, plays and draws, z of about −2.5).
  These four metrics are strongly correlated, so they count as one event, not four. Fresh-seed
  reruns of both programs remove it: a new 1M-game reference run and a new 10M-game C run
  differ by **z = +0.06** on mean turns (see the follow-up section). It was sampling noise:
  the original reference run happened to be about 1.9σ high, and the original C run about 1.3σ low.
- **The other point above 2σ is 4-player P(T>300), z = +2.16.** That is 49 against 140 games out of
  millions. With about 80 tests, about 3.6 results above 2σ are expected by chance. We saw 5,
  and 4 of them are the one correlated 3-player group.
- **Reading the code agrees with the statistics.** I checked the two programs rule by rule
  against RULES.md and found no behavioural difference under the default rules (table below).
- **Both still pass their own checks.** The reference `--selftest` passes all 15 groups. The C
  build with `-debug 1` (invariant check after every turn) ran 20,000 games each at 2, 3 and 6
  players with no failure.

Mean game length under the random policy is finite in both implementations, with matching
exponential tails. The longest game in the 10M games of `results/crosscheck_v1/random_p*.json` is 456 turns, and in 5M reference
games it is 435 turns.

## Inputs

| | Reference (Python) | C simulator |
|---|---|---|
| Source | `crosscheck/ref_nomercy.py` | `sim/nomercy.c` (not modified) |
| Results | `crosscheck/ref_results.json` and `ref_results_extra.json` | `results/crosscheck_v1/random_p{2..6}.json` |
| Games per player count | 1,000,000 (seed 20260927) | 2,000,000 (seed 777) |
| Draw pile | unordered, uniform random draw | shuffled array, drawn from the top |
| Percentiles | numpy linear interpolation | nearest rank (ceil(qN)) |

**How the standard errors were computed.** The SE of each difference is sqrt(SE_ref² + SE_C²).

- **Mean turns:** both SEMs as reported.
- **SD of turns:** asymptotic SE of the sample SD, sqrt((μ₄ − σ⁴)/(4σ²n)), with μ₄ taken from
  the C histogram. The distribution is not normal, so sd/sqrt(2n) would be wrong here.
- **Fractions** (emptied hand, P(T>t)): pooled binomial SE.
- **Eliminations, plays, draws, reshuffles:** the reference SEM comes from its per-game sums of
  squares in `ref_results_extra.json`. The C output has no per-game SD for these, so the C SEM
  is **approximated** as the reference per-game SD divided by sqrt(2,000,000). That is exact in
  expectation if the two distributions are the same. It also adds the ±0.5e-4 rounding of the
  C's 4-decimal output.
- **C values for P(T>t):** computed from the full C turn histogram.
- **Quantiles:** SE = sqrt(q(1−q)/n)/f(x_q), with the density f taken from the C histogram
  (a 5-turn window). Quantiles are integers, so the difference can only be 0 or ±1.
- **Maximum turns:** with an exponential tail of rate λ (the reference's p99–p99.9 rate), the
  maximum of n games is roughly Gumbel. So E[max over 2M] − E[max over 1M] = ln2/λ, and the SD
  of the difference is π/(λ√6)·√2. This is an **approximation**.

## z-score summary (C − reference)

| n | mean turns | sd turns | emptied-hand frac | eliminations | plays | draws | reshuffles | worst P(T>t) | worst quantile | max turns (Gumbel) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | +1.41 | +0.17 | +1.12 | -1.11 | +1.39 | +0.95 | +0.66 | +1.80 (P(T>50)) | +0.00 (p50) | -0.34 |
| 3 | -2.46 | -2.24 | +0.85 | -0.60 | -2.49 | -2.53 | -1.91 | -1.56 (P(T>100)) | +0.00 (p50) | -0.41 |
| 4 | -0.24 | +0.55 | -0.59 | +0.00 | -0.27 | +0.12 | -0.45 | +2.16 (P(T>300)) | -1.39 (p999) | +1.16 |
| 5 | -0.93 | -0.42 | +0.88 | -0.62 | -0.91 | -0.84 | -0.48 | -1.08 (P(T>50)) | +1.30 (p999) | -0.04 |
| 6 | +0.40 | +0.59 | +1.44 | -0.99 | +0.44 | -0.04 | +0.65 | +1.01 (P(T>300)) | +1.06 (p999) | +0.15 |

Flag rule: |z| > 4 counts as a real discrepancy. **None of the 80 results reaches it.**

## 3-player follow-up (fresh seeds)

I ran both programs again at 3 players with new seeds:
`python3 ref_nomercy.py --games 1000000 --players 3 --seed 31337 --check 0` and
`/tmp/nm -p 3 -n 10000000 -policy random -seed 4242`.

| run | games | mean turns | SEM | mean plays | mean draws | SD turns |
|---|---:|---:|---:|---:|---:|---:|
| ref, seed 20260927 (original) | 1,000,000 | 60.9520 | 0.0323 | 50.1896 | 92.9942 | 32.321 |
| ref, seed 31337 (new) | 1,000,000 | 60.8857 | 0.0322 | 50.1303 | 92.9246 | 32.246 |
| C, seed 777 (original) | 2,000,000 | 60.8548 | 0.0228 | 50.1055 | 92.8762 | 32.242 |
| C, seed 4242 (new) | 10,000,000 | 60.8879 | 0.0102 | 50.1353 | 92.9145 | 32.253 |

| comparison | z (turns) | z (plays) | z (draws) |
|---|---:|---:|---:|
| original ref vs new ref (same code) | −1.45 | −1.52 | −1.29 |
| original C vs new C (same code) | +1.32 | +1.40 | +1.30 |
| **new ref vs new C** | **+0.06** | **+0.17** | **−0.25** |
| pooled ref (2M) vs pooled C (12M) | −1.48 | −1.40 | −1.76 |

Each program differs from its own rerun about as much as the original cross-program gap. So
the −2.5σ result came from seed variation, not from the rules. A separate 2M-game run of the
reference at seed 777, found in the scratch directory and not produced by me, gave
60.905 ± 0.023. That is also consistent with the new C run (|z| = 0.7).

## Code reading: rule-by-rule check (default rules)

| Rule (RULES.md) | Reference (`ref_nomercy.py`) | C (`nomercy.c`) | Same? |
|---|---|---|---|
| Deck: 36 per colour, 8 WRD4, 4 WD6, 4 WD10, 8 Roulette | `build_deck` | `COLORED_COUNT`, `WILD_COUNT` | yes |
| Opening flip until a number card; ignored cards stay in discard | `Game.__init__` | `game_init` with `start_rule` 0 | yes |
| Dealer uniform, dealer+1 starts, direction +1 | yes | `next_alive(dealer, 1)` | yes |
| Playable: any wild, colour in play, or same kind (coloured only) | `_playable` | `playable` | yes |
| Stack: any draw card with value ≥ last value, colour ignored, optional | `STACK_TAB[last_dv]` | `stackable`, `stack_rule` 0 | yes |
| Random policy: uniform over distinct playable types; facing a stack, uniform over distinct stackable types plus "accept" | `step` | `choose_play` / `choose_stack` | yes |
| Draw until playable, then must play that card | yes | `after_draw` 0 | yes |
| Mercy at 25 after every card; the rest of the draw is lost; next active player moves | `_receive` | `draw_one`, `mercy_immediate` 1 | yes |
| Knocked-out cards join the discard pile and are reshuffled only when a draw hits an empty pile | `set_aside`, then `_reshuffle` | added to `disc` at once, `reshuffle` in `draw_one` | yes (same multiset at every reshuffle) |
| Last card wins with no effect; Discard All can win | `_play` | `play_card`, `last_card_wins` 1 | yes |
| Discard All sheds only coloured cards of its own colour | yes | yes | yes |
| Skip = next of next; Skip Everyone = same player; Reverse with 2 active players = same player | yes | yes | yes |
| WRD4: flip direction; with 2 active players its own player faces the stack (also inside a stack) | yes | `wrd4_2p_self` 1 | yes |
| Roulette: victim names a colour uniformly and reveals until that colour (wilds do not count); a knockout stops it; play resumes after the victim; **the victim's reveal is not a turn** | yes | yes (the extra RNG draw for a provisional colour has no effect on the distribution) | yes |
| 0: every active hand passes to the next active player; 7: swap with a uniform other active player | `_pass_hands`, `_swap7` | `rotate_hands`, `choose_swap` | yes |
| Counters: a turn is each `step`/`take_turn`; draws exclude the deal and the opening flip; stacks count as plays | yes | yes | yes |

I found no behavioural difference. The reference's nine "interpretation decisions" match what
the C code does under its default flags.

## Notes and caveats

- **Turn definition.** RULES.md §6 now counts a Roulette victim's reveal as a turn. Neither
  `sim/nomercy.c` as checked in nor `ref_nomercy.py` does that: `turns++` appears only in
  `take_turn`. This comparison therefore uses the older definition on both sides, as the
  RULES.md note says. `results/final/*.json` were produced by a **different C build**: their
  JSON has a `"deck"` field that `sim/nomercy.c` never prints, and their means are about 6%
  higher. This cross-check validates `sim/nomercy.c` and `results/crosscheck_v1/random_p*.json`. It does
  **not** directly validate the build behind `results/final/`. One consistency check: at 3
  players, final 64.507 minus 3.61 Roulettes per game ≈ 60.89, which matches.
- **Quantile methods differ** (numpy linear vs nearest rank). For integer data at these sample
  sizes they coincide, except for a ±1 at p99.9, which is within the SE.
- **The C SEs for eliminations, plays, draws and reshuffles are approximated** as described
  above. The z-scores in those columns are a little less exact than those for turns.

## Detailed tables

### 2 players (reference n = 1,000,000; C n = 2,000,000)

| metric | reference | C | C − ref | SE of diff | z | verdict |
|---|---:|---:|---:|---:|---:|---|
| mean turns | 30.068 | 30.106 | +0.038 | 0.0271 | +1.41 | ok |
| sd turns | 22.133 | 22.138 | +0.005 | 0.0295 | +0.17 | ok |
| emptied-hand frac | 0.0836 | 0.0840 | +0.0004 | 0.00034 | +1.12 | ok |
| eliminations | 0.9164 | 0.9160 | -0.0004 | 0.00034 | -1.11 | ok |
| plays | 24.588 | 24.620 | +0.032 | 0.0233 | +1.39 | ok |
| draws | 47.926 | 47.955 | +0.029 | 0.0307 | +0.95 | ok |
| reshuffles | 0.0023 | 0.0023 | +0.0000 | 6.5e-05 | +0.66 | ok |
| P(T>50) | 0.156966 | 0.157768 | +0.000802 | 0.00045 | +1.80 | ok |
| P(T>100) | 0.012961 | 0.012987 | +0.000026 | 0.00014 | +0.19 | ok |
| P(T>200) | 0.000013 | 0.000008 | -0.000004 | 3.9e-06 | -1.16 | ok |
| p50 | 24 | 24 | +0 | 0.0283 | +0.00 | ok |
| p90 | 61 | 61 | +0 | 0.0814 | +0.00 | ok |
| p99 | 105 | 105 | +0 | 0.197 | +0.00 | ok |
| p999 | 135 | 135 | +0 | 0.392 | +0.00 | ok |
| max turns | 234 | 235 | +1 | 24 | -0.34 | ok (Gumbel; +9 expected for 2M vs 1M) |

### 3 players (reference n = 1,000,000; C n = 2,000,000)

| metric | reference | C | C − ref | SE of diff | z | verdict |
|---|---:|---:|---:|---:|---:|---|
| mean turns | 60.952 | 60.855 | -0.097 | 0.0396 | -2.46 | check |
| sd turns | 32.321 | 32.242 | -0.078 | 0.0349 | -2.24 | check |
| emptied-hand frac | 0.1726 | 0.1730 | +0.0004 | 0.00046 | +0.85 | ok |
| eliminations | 1.7569 | 1.7565 | -0.0004 | 0.0007 | -0.60 | ok |
| plays | 50.190 | 50.105 | -0.084 | 0.0337 | -2.49 | check |
| draws | 92.994 | 92.876 | -0.118 | 0.0466 | -2.53 | check |
| reshuffles | 0.0931 | 0.0924 | -0.0007 | 0.00036 | -1.91 | ok |
| P(T>50) | 0.557545 | 0.556895 | -0.000650 | 0.00061 | -1.07 | ok |
| P(T>100) | 0.121523 | 0.120901 | -0.000622 | 0.0004 | -1.56 | ok |
| P(T>200) | 0.001230 | 0.001187 | -0.000043 | 4.2e-05 | -1.03 | ok |
| P(T>300) | 0.000002 | 0.000002 | +0.000000 | 1.7e-06 | +0.00 | ok |
| p50 | 55 | 55 | +0 | 0.05 | +0.00 | ok |
| p90 | 105 | 105 | +0 | 0.089 | +0.00 | ok |
| p99 | 156 | 156 | +0 | 0.27 | +0.00 | ok |
| p999 | 204 | 204 | +0 | 0.703 | +0.00 | ok |
| max turns | 350 | 349 | -1 | 38 | -0.41 | ok (Gumbel; +14 expected for 2M vs 1M) |

### 4 players (reference n = 1,000,000; C n = 2,000,000)

| metric | reference | C | C − ref | SE of diff | z | verdict |
|---|---:|---:|---:|---:|---:|---|
| mean turns | 89.060 | 89.048 | -0.012 | 0.0505 | -0.24 | ok |
| sd turns | 41.266 | 41.287 | +0.020 | 0.0372 | +0.55 | ok |
| emptied-hand frac | 0.2613 | 0.2610 | -0.0003 | 0.00054 | -0.59 | ok |
| eliminations | 2.5070 | 2.5070 | +0.0000 | 0.00113 | +0.00 | ok |
| plays | 73.567 | 73.555 | -0.012 | 0.0427 | -0.27 | ok |
| draws | 133.573 | 133.581 | +0.008 | 0.0637 | +0.12 | ok |
| reshuffles | 0.4732 | 0.4729 | -0.0003 | 0.00063 | -0.45 | ok |
| P(T>50) | 0.812420 | 0.812149 | -0.000271 | 0.00048 | -0.57 | ok |
| P(T>100) | 0.368463 | 0.368100 | -0.000363 | 0.00059 | -0.61 | ok |
| P(T>200) | 0.009238 | 0.009119 | -0.000119 | 0.00012 | -1.02 | ok |
| P(T>300) | 0.000049 | 0.000070 | +0.000021 | 9.7e-06 | +2.16 | check |
| p50 | 86 | 86 | +0 | 0.0663 | +0.00 | ok |
| p90 | 144 | 144 | +0 | 0.104 | +0.00 | ok |
| p99 | 199 | 199 | +0 | 0.25 | +0.00 | ok |
| p999 | 242 | 241 | -1 | 0.721 | -1.39 | ok |
| max turns | 341 | 393 | +52 | 34 | +1.16 | ok (Gumbel; +13 expected for 2M vs 1M) |

### 5 players (reference n = 1,000,000; C n = 2,000,000)

| metric | reference | C | C − ref | SE of diff | z | verdict |
|---|---:|---:|---:|---:|---:|---|
| mean turns | 111.499 | 111.445 | -0.054 | 0.0587 | -0.93 | ok |
| sd turns | 47.920 | 47.903 | -0.017 | 0.0411 | -0.42 | ok |
| emptied-hand frac | 0.3180 | 0.3185 | +0.0005 | 0.00057 | +0.88 | ok |
| eliminations | 3.2140 | 3.2130 | -0.0010 | 0.00159 | -0.62 | ok |
| plays | 91.971 | 91.927 | -0.045 | 0.0492 | -0.91 | ok |
| draws | 168.120 | 168.054 | -0.066 | 0.0789 | -0.84 | ok |
| reshuffles | 0.8252 | 0.8249 | -0.0003 | 0.00066 | -0.48 | ok |
| P(T>50) | 0.875896 | 0.875458 | -0.000438 | 0.0004 | -1.08 | ok |
| P(T>100) | 0.595317 | 0.595082 | -0.000235 | 0.0006 | -0.39 | ok |
| P(T>200) | 0.034046 | 0.033813 | -0.000233 | 0.00022 | -1.05 | ok |
| P(T>300) | 0.000411 | 0.000408 | -0.000003 | 2.5e-05 | -0.12 | ok |
| p50 | 112 | 112 | +0 | 0.0707 | +0.00 | ok |
| p90 | 172 | 172 | +0 | 0.103 | +0.00 | ok |
| p99 | 230 | 230 | +0 | 0.302 | +0.00 | ok |
| p999 | 282 | 283 | +1 | 0.768 | +1.30 | ok |
| max turns | 379 | 393 | +14 | 41 | -0.04 | ok (Gumbel; +16 expected for 2M vs 1M) |

### 6 players (reference n = 1,000,000; C n = 2,000,000)

| metric | reference | C | C − ref | SE of diff | z | verdict |
|---|---:|---:|---:|---:|---:|---|
| mean turns | 127.708 | 127.734 | +0.027 | 0.0671 | +0.40 | ok |
| sd turns | 54.787 | 54.814 | +0.027 | 0.0452 | +0.59 | ok |
| emptied-hand frac | 0.3498 | 0.3507 | +0.0008 | 0.00058 | +1.44 | ok |
| eliminations | 3.8990 | 3.8969 | -0.0021 | 0.00207 | -0.99 | ok |
| plays | 104.962 | 104.987 | +0.025 | 0.0559 | +0.44 | ok |
| draws | 196.054 | 196.050 | -0.004 | 0.0936 | -0.04 | ok |
| reshuffles | 1.1346 | 1.1352 | +0.0006 | 0.00091 | +0.65 | ok |
| P(T>50) | 0.887958 | 0.887764 | -0.000194 | 0.00039 | -0.50 | ok |
| P(T>100) | 0.702350 | 0.702116 | -0.000235 | 0.00056 | -0.42 | ok |
| P(T>200) | 0.087875 | 0.087907 | +0.000033 | 0.00035 | +0.09 | ok |
| P(T>300) | 0.001566 | 0.001615 | +0.000050 | 4.9e-05 | +1.01 | ok |
| P(T>400) | 0.000008 | 0.000011 | +0.000003 | 3.9e-06 | +0.77 | ok |
| p50 | 130 | 130 | +0 | 0.0778 | +0.00 | ok |
| p90 | 196 | 196 | +0 | 0.119 | +0.00 | ok |
| p99 | 260 | 260 | +0 | 0.289 | +0.00 | ok |
| p999 | 310 | 311 | +1 | 0.944 | +1.06 | ok |
| max turns | 435 | 456 | +21 | 39 | +0.15 | ok (Gumbel; +15 expected for 2M vs 1M) |
