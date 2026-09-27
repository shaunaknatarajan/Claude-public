# UNO Show 'Em No Mercy: is it solved, and is the average game infinitely long?

## Short answer

1. **It is not solved.** Nobody has solved No Mercy, or even classic UNO, in any game-theoretic
   sense: there is no known optimal strategy, equilibrium or game value. Strategy clearly matters.
   In our tournaments a simple greedy bot beats random play 67–33 one-on-one, and a Monte Carlo
   search bot beats the greedy bot 74–26.
2. **The mean game length is finite** for any sensible robotic play. Under the official rules and
   with no turn cap we simulated 100 million games of random play (20 million for each of 2–6
   players). Every one ended: the average ran from 32 turns (2 players) to 135 turns (6 players),
   and the longest was 546 turns. The chance that a game is still going falls off exponentially,
   halving every 10 to 15 turns. We also proved that, for any fixed strategy, the only two
   possibilities are "finite mean with an exponential tail" and "a positive chance of never
   ending". There is no heavy-tailed middle ground.
3. **It can be genuinely infinite if you drop the Mercy rule** (a house rule, not the official
   game). Hands can then soak up nearly the whole deck, and we caught games in provable endless
   loops. Under the official rules, robots that collude to stall stretch games to about 12,000
   turns on average at 6 players, but every such game we simulated still ended. Their lengths
   look exponential, with no "safe forever" plateau. Whether *perfect* collusion could stall
   forever comes down to a precise, finite question that we could not settle.

<!--SECTIONS-->
