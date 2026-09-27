# Endless-loop witnesses without the Mercy rule

Under random play every legal choice has positive probability, and so does every order of a
uniform shuffle. A single explicit, legal game history that ends in a forced endless loop therefore
proves that P(the game never ends) > 0, and hence that the expected length is infinite.

| Players | Witness | Status |
|---:|---|---|
| 3 | [witness_p3.json](witness_p3.json): a 15-turn legal history from a legal deal into a period-2 loop. Two Reverses (Red and Blue) alternate between seats 0 and 2, and seat 1 (123 cards) never moves again. Nobody empties a hand, so it holds under the official ending and under play-until-one-left. | **Verified** by two independent checkers. One wrote their own replay from RULES.md and checked legality of every step, the deal and flip, the reshuffle permutations and the after-states. The other attacked the loop rule by rule and confirmed every move is forced and the state repeats. Replay: `python3 analysis/witness_p3_replay.py` |
| 4–6 | Found directly by the simulator (`-detect_cycles 1`): 3, 5 and 17 per 100,000 random games at 4, 5 and 6 players ([cycle_example.txt](cycle_example.txt)) | Proven loops (a repeated full state with no choice and no random event in between) |
| 2 | None. [witness_p2.json](witness_p2.json) argues that **no forced loop is reachable with 2 players**: all wilds would have to sit in one hand that never acts, and the other hand's last change can't be completed. | **Accepted** by two independent referees (logic lens, and rules/counterexample lens): verdict *correct with minor fixes*, no counterexample found ([referee reports](witness_p2_referees.json)). The fixes are wording: double periods for 0/7 swaps, the Discard All exit, and the case where W draws through every card and passes. |

Scope: default rules, deck 0, no Mercy rule. The 3-player loop needs the default "play the card
you drew" rule (`-after_draw 0`). The 2-player argument rules out *forced* loops only. It does not
rule out endless play that keeps depending on chance or choices.
