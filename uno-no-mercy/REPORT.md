# UNO Show 'Em No Mercy: is it solved, and is the average game infinitely long?

*(draft — numbers marked TBD are still being computed)*

## Short answer

1. **Not solved.** Nobody has solved No Mercy, or even classic UNO, in any game-theoretic sense:
   there is no known optimal strategy, equilibrium or game value. Strategy clearly matters. In
   our tournaments a simple greedy bot beats random play 67–33 one-on-one, and a Monte Carlo
   search bot beats the greedy bot 74–26.
2. **The mean game length is finite** for any sensible robotic play. With the official rules and
   no turn cap, random robots average about 32 turns (2 players) to TBD turns (6 players). The
   chance that a game is still going falls off exponentially, halving every 10–15 turns. We
   proved that for any fixed strategy this is the *only* way it can go (finite mean with an
   exponential tail) unless the strategy can get stuck somewhere the game can never end.
3. **It becomes genuinely infinite if the Mercy rule is removed** (a house rule). The game can
   then fall into provable endless loops. Robots colluding to stall stretch games to thousands of
   turns under the real rules, but every one of the games we simulated still ended, and their
   lengths look exponential with no "safe forever" plateau. Whether *perfect* collusion could
   stall forever reduces to a precise finite question that we could not settle.

## 1. "Solved"?

TBD

## 2. Rules

TBD

## 3. How long is a game when robots just play?

TBD

## 4. Why the mean is finite: the math

TBD

## 5. Can robots make it last forever on purpose?

TBD

## 6. Take away the Mercy rule and it really can be infinite

TBD

## 7. Sensitivity to rule interpretations and deck composition

TBD

## 8. How the results were checked

TBD

## 9. Reproduce

TBD
