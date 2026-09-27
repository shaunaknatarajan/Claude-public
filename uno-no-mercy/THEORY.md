# Theory: when can the average game be infinite?

This page states what is proven about game length, under the rules in [RULES.md](RULES.md). Full
proofs are in [docs/proofs/](docs/proofs/). Each was written by a proof agent and then checked by
independent referees whose only job was to break it; the status column records the outcome.

## 1. The game is a finite Markov decision process

Record, at every moment: who is still in; every hand, as a multiset of card types; the draw
pile and the discard + set-aside pile, as multisets; the top card and the color in play; whose
turn it is; the direction; the pending penalty (≤ 152) and the value of the last Draw Card;
and where we are inside a turn (drawing, choosing a color, and so on).

- **Finite.** There are fewer than 10^132 such states (about 10^85 for 2 players).
- **Markov.** Because shuffles are uniform and nobody sees the order of the draw pile, the next
  card drawn is always uniform over the pile's current contents, whatever anyone knows or
  remembers. This holds across reshuffles and knocked-out hands (T1, Thm A).
- **No deadlock.** With 2–6 players and the Mercy rule, every hand has at most 24 cards, so at
  least 23 cards are always drawable. Every draw sequence ends within 24 cards (T1, Thm D).
- **Probabilities are bounded below.** Every possible draw has probability at least 1/165.

## 2. The dichotomy (T1, Thm B)

Call a set of non-terminal states **safe** if from each of them the players have some move whose
every possible outcome (every card that could be drawn) stays inside the set. Let C be the
largest safe set. Exactly one of these holds:

- **C is unreachable.** Then for *every* way of playing that never sees the order of the draw
  pile — any mix of competition, collusion, memory, randomization or full knowledge of all
  hands — the game ends with probability 1, the probability that it lasts more than t turns
  decays geometrically, and E[T] ≤ K·165^K for a finite K. (The bound is astronomically loose;
  it only certifies finiteness.)
- **C is reachable.** Then some colluding strategy (all players sharing information) keeps the
  game going forever with positive probability, so its expected length is infinite.

So "can the mean be infinite?" is exactly the question "does a reachable safe set exist?" It is a
finite, in-principle decidable property of a huge graph. For the strategies described next, it
cannot be infinite because of a heavy tail: each has either a finite mean with an exponential
tail, or a positive chance of never ending.

A second consequence (T1, Thm C and Cor. C1): for any fixed strategy that uses only the current
state, coin flips and a finite memory (all of our robots do; the look-ahead robots `collude` and
`mcwin` carry a chosen color or 7-target from one step to the next),

> E[T] < ∞ ⟺ P(the game ends) = 1 ⟺ from every reachable state, the end is still reachable.

For uniformly random robots, which make every legal move with positive probability, this becomes
**"no trap"**: from every reachable position *some* sequence of legal moves and draws ends the
game.

## 3. Natural play: random robots (T2)

TBD — status of the no-trap theorem for uniformly random play.

## 4. Colluding robots (T3, T4)

TBD.

## 5. What breaks without the Mercy rule

Without the 25-card Mercy rule, hands can absorb almost the whole deck. The draw and discard piles
can then hold a single card between them, so a "reshuffle" is not random at all, and play can
become a deterministic cycle. The simulator's `-detect_cycles` option proves a game infinite when
the full state repeats with no random event and no free decision in between. See the report for
an example and how often it happens. With the Mercy rule, at least 23 cards are always in play
outside the hands, so every cycle of the game must pass through a genuinely random reshuffle.
