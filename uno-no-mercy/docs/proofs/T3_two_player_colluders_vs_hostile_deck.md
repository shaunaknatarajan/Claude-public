# T3-two-player-adversarial: colluding robots against a hostile deck (official rules, Mercy rule on)

**Status: partial result.** Two independent referees judged it *correct_with_minor_fixes, correct_with_minor_fixes*; their minor notes are listed at the end.
Scope: the official rules of RULES.md sections 1-6, not the house rule of section 7.

## Statement

PARTIAL result for T3 (exactly 2 players; colluding, fully informed players against a nature that picks every drawn card from the current draw-pile multiset). Rules and deck are the RULES.md defaults with the D-FW deck.

(1) Dichotomy (Lemma 3). Let C be the largest set of non-terminal states from which the players can keep every successor inside C. If C is empty, then under every strategy profile P(T > nK) <= (1-eps)^n, with K <= |S| and eps >= 167^(-|S|), so E[T] < infinity. If C is non-empty and reachable with positive probability, some profile has P(T = infinity) > 0.

(2) Budget-doom theorem (Theorem A). Nature uses strategy sigma: in a penalty draw, deal a coloured non-draw card of the colour c that maximises N_c among colours with n_c > 0; in a flood or Roulette reveal, knock the player out whenever it can. Take any state s with D(s) >= 33 and V(s) < j(s). Here:
- D is the sum of N_c minus the largest N_c, where N_c counts all coloured cards of colour c in the pile.
- V is the total draw value in both hands plus the pending stack.
- j(s) is the number of sigma-penalty deals needed to bring D down to 32 or less.
From such a state, every player strategy (even history-dependent and randomised) ends the game within 2(H(s)+V(s))+1 turns, where H(s) is the number of cards in both hands.

(3) Initial deals (Corollary B, computer-assisted exact bound). For all initial deals outside a set of probability < 1.7e-11, nature forces termination before the first reshuffle, within at most 205 turns.

(4) Reshuffle cycles (Lemma 6 and Proposition 7). Every reshuffle leaves D >= 59 and j >= 25. Any play that survives against sigma must satisfy V(S_k) + R_k >= j(P_k) at every reshuffle k, and then V(S_{k+1}) <= 152 - j(P_k) + R_k, with 0 <= R_k <= 23. Here S_k is the set of draw cards held at the k-th reshuffle, P_k the new pile and R_k the undrawn penalty carried across the reshuffle.

(5) The budget cannot decide the question (Proposition 8). These necessary budget conditions can be met within the 48-card hand capacity. An explicit alternating schedule exists: in one cycle the hands hold 31 red non-draw cards plus 17 coloured draw cards (j = 46 <= V = 50); in the next they hold 31 red, 1 other, and all 16 wild draws (j = 65 <= V = 96). So no argument based only on draw-value budgets can prove that C is empty.

Not decided: whether C is empty, i.e. whether nature forces termination from every 2-player state.

## Gaps (not proven)

- MAIN GAP: T3 is not decided. C = empty (nature forces termination from every 2-player state) is not proved, and no colluder fortress (C non-empty) is constructed.
- Proposition 8 shows every draw-value-budget argument fails: capacity-feasible rotating schedules exist. A proof that nature wins would need tactical arguments about the post-lethal-phase drain and the collection of the next draw set, which I could not formalize.
- J(x), the capacity search (feas.c) and the 1.65e-11 bound are computer-assisted (exhaustive enumeration and exact hypergeometric sums in scratchpad t3/jcalc.c, feas.c, py/initbound.py). They are rigorous only modulo code correctness. feas.c ignores the top card, which moves j by at most 1.
- The dichotomy constants (K <= |S|, eps >= 167^-|S|) are astronomically weak. They only show finiteness if C = empty.
- Reachability of C from the real initial distribution is not addressed, since C's emptiness is open.
- Numerical colluder searches (greedy lookahead, beam search up to width 4000) are heuristic. Their failure to survive 2 cycles against sigma0 is evidence, not proof. sigma0 differs slightly from sigma (it uses max n_c rather than max N_c in penalties).
- Results depend on the D-FW deck and the RULES.md defaults. Other decks or rule flags (e.g. voluntary draw, stack colour rule, Roulette chooser) were not analysed.

## Proof

# T3 (2 players, adversarial nature): what is proven and what is not

**Verdict.** I could not decide T3.
- I did not prove that the sure-safe core C is empty, i.e. that nature wins everywhere.
- I did not find a colluder fortress, i.e. that C is non-empty.

What is proven:
- the dichotomy (§2);
- a rigorous "budget-doom" theorem that kills a large, explicit class of states (§4);
- an exact bound showing that all but under 1.7·10⁻¹¹ of initial deals are doomed against adversarial nature (§5);
- a proof that the draw-value budget, even with reshuffle rotation and hand capacity included, **cannot** by itself prove C = ∅ (§6).

The open core is tactical (§7). The numerics (§8) lean towards nature, but they are heuristic.

Rule citations refer to `/home/user/Claude-public/uno-no-mercy/RULES.md` sections (§1 deck, §3 turn, §4 effects, §5 Mercy/end).

## 0. Deck facts (RULES §1)

| Class | Count | Draw value |
|---|---|---|
| Coloured non-draw (CND): per colour 20 numbers + 3 Skip + 2 Skip Everyone + 3 Reverse + 3 Discard All | 31 per colour, **124** total | 0 |
| Coloured draw (CD): per colour 3 D2 + 2 D4 | 5 per colour, **20** total | 2 or 4 |
| Wild draws (WD): 8 WRD4, 4 WD6, 4 WD10 | **16** | 4, 6, 10 |
| Roulettes | **8** | 0 (not a draw card) |

- The total draw value is 12·2 + 8·4 + 8·4 + 4·6 + 4·10 = **152**.
- CND action cards (Skip, Skip Everyone, Reverse, Discard All) number 11 per colour, 44 in total.
- The most copies of one kind in one colour is **3**: D2, Skip, Reverse and Discard All.

## 1. Model

**Lemma 1 (Markov).**
- A reshuffle produces a uniformly random order that nobody observes (§5). Conditional on the cards revealed so far, the rest of the pile is still uniformly ordered.
- Decisions cannot depend on the hidden order. So every draw is uniform over the current pile multiset.
- The state s consists of: both hands, the pile multiset, the discard multiset, the top card, the active colour, the player to move, the pending stack total and last value, and the phase inside a turn (penalty draws left, a draw-until-playable in progress, a Roulette in progress with its named colour).
- This state space S is finite. Nodes are either player nodes (a play, stack/absorb, colour, or Roulette-colour choice) or chance nodes (one card drawn).

**Lemma 2 (no deadlock).**
- A live hand holds at most 24 cards (§5, immediate Mercy).
- So pile plus the discard below the top always holds at least 168 − 1 − 24 − 24 = 119 cards.
- Every draw-until-playable, penalty or reveal therefore ends within 25 − h draws, where h is the drawer's hand size. It ends in a knockout or at a stopping card.
- With 2 players a knockout ends the game (§5).

## 2. The dichotomy

**Lemma 3.** Build the attractor of the terminal set:
- A₀ is the set of terminal states.
- A_{i+1} adds every player node all of whose successors lie in A_i, and every chance node with some successor in A_i.
- Let Z = S∖⋃A_i.

**Z = C.**
- In Z, every player node has a successor in Z, and every chance node has all its successors in Z. So Z has the defining property of C, and Z ⊆ C.
- Conversely, C ∩ A_i = ∅ for every i, by induction on i.

**If C = ∅.** Define the rank r(s) = min{i : s ∈ A_i} ≤ |S|.
- Nature's positional strategy: at a chance node, choose a successor of smaller rank.
- Every player move also lowers the rank. So termination follows within |S| steps, against any player strategy.
- Under random draws, the designated card has probability at least 1/167 at each chance node, because it is present and the pile has at most 167 cards.
- Hence, whatever the history, P(terminate within |S| steps) ≥ ε := 167^{−|S|}.
- Therefore P(T > n|S|) ≤ (1−ε)ⁿ, and E[T] ≤ |S|/ε. This holds for every profile, including history-dependent, randomised and fully informed ones. Turns are counted as at most steps.

**If C ≠ ∅.** Suppose C is reached with positive probability. Choosing a successor inside C forever gives P(T = ∞) > 0, so E[T] = ∞. ∎

## 3. Nature's strategy σ and notation

For a pile P and each colour c:
- n_c = number of CND cards of colour c;
- F_c = number of CD cards of colour c ("filler");
- N_c = n_c + F_c;
- **D(P) = ΣN_c − max_c N_c**.

For a state s:
- V(s) = draw value in both hands + pending stack total;
- H(s) = number of cards in both hands.

Nature's strategy σ:
- **σ_pen:** in a penalty draw, deal a CND card of the colour c that maximises N_c among colours with n_c > 0 (ties go to the lowest index).
- **σ_flood / σ_roul:** if a draw-until-playable or a Roulette reveal can reach 25 cards, deal unplayable cards (respectively non-named-colour cards) until the knockout.

**j(s)** is the number of σ_pen deals that take the pile from P(s) down to D ≤ 32. Each deal lowers one n_c by 1, so j(s) is a deterministic function of (n, F).

## 4. The lethal zone and the budget-doom theorem

**Lemma 4.** If D(P) ≥ 33, every draw-until-playable and every Roulette reveal is lethal under σ.

*Draw-until-playable.* The drawer has h ≥ 1 cards (h = 0 means the game is already over). Let the top card be t, with active colour c.
- A pile card is playable iff it is wild, or has colour c, or shares the kind of a coloured t (§3.2).
- Pile cards of colour ≠ c with t's kind number at most 3 × 3 = 9.
- So the unplayable count is at least Σ_{c'≠c} N_{c'} − 9 ≥ D − 9 ≥ 24 ≥ 25 − h.
- Nature deals those unplayable cards until the drawer reaches 25 (§3.2 "draw until playable", §5 immediate Mercy).

*Roulette.* The victim names a colour C and reveals until a C card, and wilds do not count (§4). The non-C cards in the pile number at least Σ_{c'≠C} N_{c'} ≥ D ≥ 33 ≥ 25 − h. ∎

**Lemma 5.**
- σ_pen never deals a draw card or a wild. So while it is the only kind of deal, no draw value enters any hand.
- The pile changes only by draws (a reshuffle needs an empty pile, i.e. D = 0). So D stays ≥ 33 until j(s) deals have been made.

**Theorem A.** If D(s) ≥ 33 and V(s) < j(s), every player strategy ends the game within 2(H(s) + V(s)) + 1 turns.

*Proof.*
1. By Lemma 4, any draw-until-playable or Roulette reveal ends the game, so until the end every draw is a penalty draw.
2. A penalty's size is the total value of draw cards played into it, plus the pending stack at s.
3. By Lemma 5, no draw card enters a hand. So the total number of penalty draws is at most V(s) < j(s), and D ≥ 33 persists.
4. Strict must-play (§3.2) means every normal turn either plays a card or draws until playable, which is lethal. So cards leave the hands at least once per surviving normal turn.
5. At most H(s) + V(s) cards are ever in hands, so there are at most H(s) + V(s) plays.
6. Each absorbing turn is preceded by a draw-card play or by the initial pending stack, so there are at most H(s) + V(s) + 1 absorbing turns.
7. After at most H(s) + V(s) plays a hand is empty, which is a win (§3.4). ∎

Card swaps from 0 and 7 and Discard All sheds (§4) change neither V nor the pile, so they do not affect the argument.

## 5. Initial deals (computer-assisted, exact)

**Bounding j₀.**
- Let J(x) be the minimum of j over all piles missing exactly x CND cards, with any F ∈ {0..5}⁴. It was computed by exhaustive enumeration in `jcalc.c`.
- **J(x) = 81 − x for 0 ≤ x ≤ 20.** From there: J(20..30) = 61, 59, 58, 56, 55, 53, 52, 50, 49, 47, 46; J(40) = 35; J(48) = 25.
- J is strictly decreasing.
- At the start, x = x₀ + a₀ + 1. Here x₀ is the number of CND cards dealt, a₀ the number of CND action cards ignored in the opening flip (§2), and the 1 counts the number card on top. So j₀ ≥ J(x₀ + a₀ + 1). Also D₀ ≥ 33.

**Bounding a₀.**
- a₀ ≥ k requires the first k of the (CND action ∪ number) cards in the remaining deck to be actions.
- At most 44 such actions and at least 66 numbers remain, so P(a₀ ≥ k) ≤ ∏_{i<k} (44−i)/(110−i).

**Result.**
- An exact multivariate-hypergeometric sum over the 14 dealt cards (`py/initbound.py`) gives P(V₀ ≥ J(x₀ + a₀ + 1)) < 1.65·10⁻¹¹.
- On every other deal, Theorem A applies: termination comes within 2(14 + V₀) + 1 ≤ 205 turns, before any reshuffle.
- Monte Carlo cross-check over 2·10⁷ deals: max V₀ = 62, min j₀ = 68, and no deal had V₀ ≥ j₀.

## 6. Reshuffle cycles, rotation, and why the budget cannot decide

**Setup.** Let r_k be the k-th reshuffle, P_k the new pile, S_k the set of draw cards in hands, and R_k the undrawn remainder of a penalty that straddles the reshuffle. The absorber must stay at 24 cards or fewer, so R_k ≤ 23.

**At every reshuffle.**
- ΣN ≥ 144 − 48 − 1 and max N ≤ 36, so D(P_k) ≥ 59 and j(P_k) ≥ J(48) = 25.
- Every flood and every Roulette right after a reshuffle is therefore lethal. This is the "post-reshuffle danger zone", made exact.

**Lemma 6 (rotation).**
- Every draw card is, at r_{k+1}, either in hand, the top card, or in P_{k+1}. The last means it was played or shed by Discard All during cycle k.
- By Theorem A, surviving cycle k needs V(S_k) + R_k ≥ j(P_k).
- The value played in the lethal phase of cycle k, from r_k until D ≤ 32, is at least j(P_k) − R_k. It all comes from S_k (Lemma 5) and lies in the discard at r_{k+1}.
- Hence V(S_k∖S_{k+1}) ≥ j(P_k) − R_k and V(S_{k+1}) ≤ 152 − j(P_k) + R_k.

**Proposition 7 (necessary shape of any surviving play).** At every reshuffle, the hands (at most 48 cards) must satisfy value ≥ j − R. An exhaustive search over hand compositions (`feas.c`, top card ignored) gives:
- the minimum feasible j is **47** if no Roulettes are held;
- it is **60** if all 8 Roulettes are held.

Both minima need about 25–31 non-draw cards of a single colour in hand, together with most of the coloured draw cards.

**Proposition 8 (the budget alone cannot prove C = ∅).** Alternate two reshuffle hands, with the top card a blue number:
- **Hand A:** all 31 red CND cards plus 17 coloured draw cards (d = 5, 5, 5, 2). This gives j = 46 ≤ V = 50.
- **Hand B:** 31 red CND cards, 1 more CND card, and all 16 wild draws. This gives j = 65 ≤ V = 96.

The draw sets of A and B are disjoint. So every condition of Lemma 6 holds forever, with R = 0.

The worry raised in the task is confirmed: colluders can rotate which draw cards they use between cycles. No draw-value-only argument can close the gap.

## 7. Tactical levers and the precise obstruction

**Lemma 9 (rigorous small facts).**
- (a) A player with one card, on a normal turn, whose card is playable must play it and wins (§3.2, §3.4).
- (b) A Roulette in hand is always playable. If it is the holder's only playable card it must be played, and while D ≥ 33 that is lethal for the opponent (Lemma 4).
- (c) In a non-lethal draw-until-playable, nature chooses the stopping card, and it must be played (§3.2, after_draw 0). In a non-lethal Roulette, nature chooses which card of the named colour ends the reveal.
- (d) A draw-until-playable whose pile holds no playable card is always lethal, because the reshuffled pile has at least 99 − 48 unplayable cards.

**The obstruction.** To survive, colluders must carry out Proposition 8's schedule while doing all of the following:
- (i) Reach every reshuffle with hands almost full (about 48 cards), holding roughly one whole colour plus a draw set.
- (ii) Never face a flood or a forced Roulette while D ≥ 33.
- (iii) Drain the rest of each cycle's pile (about 45 CND cards of three colours plus the pile's draw cards, which σ deals last) mostly through non-penalty draws. Nature picks the stopping card of each one, which can force a finish, a Roulette, a Discard All finish or a hand-shrinking play.
- (iv) Collect the next draw set at the very end of the cycle.

I could not turn (iii) and (iv) into either a potential function (which would show nature wins) or an invariant (which would show a fortress exists). A plain counting potential fails: with 48 slots, colluders' free drains can in principle absorb the slack left by §6.

## 8. Numerical evidence (not proof)

**Setup.**
- I wrote a 2-player engine with a deterministic adversarial nature (scratchpad `t3/*.h`, `main.c`). Its strategy σ₀ is σ with a max-n_c tie rule, plus "stingy" non-lethal endings that give priority to forced finishes, forced Roulettes and Roulette snipes.
- Against σ₀, colluders searched with two methods:
  - greedy play with exhaustive 2–3-decision lookahead;
  - beam search (width up to 4000) with a budget-shortfall evaluation and a lookahead filter.

**Results.**
- From random deals, every game died, with a mean of about 16 turns. This is consistent with §5.
- From hand-built post-reshuffle "rich" states (all wild draws, all Roulettes, coloured draws), about 40 runs lasted 2 to 213 turns. The best runs completed at most one reshuffle cycle, and none completed two.
- The observed causes of death were:
  - reaching the next reshuffle with V of about 2–30, against a need of about 60 or more;
  - the Roulette holder being squeezed into a forced Roulette;
  - forced finishes.

This is evidence that σ₀ is strong. It is not evidence about C, because the colluder search is heuristic.

## 9. Consequence for the user's question

If C = ∅, the mean game length is finite under every collusion (Lemma 3). If C ≠ ∅ and it is reachable, some collusion gives E[T] = ∞. Theorems A and B show that, against worst-case draws, almost every game ends in the first cycle whatever the players do. Whether perfect collusion plus lucky draws can reach a state from which the game never has to end is still open.

## Referee notes

### Referee 1: correct_with_minor_fixes

- Theorem A turn bound. Counted literally, steps 4-7 give at most (H+V) plays, (H+V+1) absorbing turns and 1 final lethal flood or Roulette turn. That totals 2(H+V)+2, not 2(H+V)+1, because the proof never counts the last lethal non-play turn. The stated bound is still true with a sharper count. No draw card enters a hand, so absorbing turns are at most (number of draw cards held at s) + 1, which is at most V_h/2 + 1. The total is then at most H + V + V_h/2 + 2, which is at most 2(H+V)+1 because H >= 2. The proof text should be fixed to this count.
- Claim (4) says 'every reshuffle leaves j >= J(48) = 25', but that is misderived. Under the proof's own accounting (hands <= 48 plus a coloured non-draw top card), up to 49 coloured non-draw cards can be missing from the pile, and J(49) = 23. I verified this: the minimum is reached at n=(6,7,31,31), F=0. So the cited inequality does not give 25. The conclusion is true, and much stronger, once one uses the fact that at a 2-player reshuffle the pile is the exact complement of hands plus top. With at most 49 coloured cards missing IN TOTAL (non-draw plus draw), exhaustive search gives min j = 46. It gives 47 for at most 48 missing and 48 for at most 47. Replace J(48) by this constrained minimum.
- Reshuffle timing is never fixed in the model (Lemma 1), yet Prop 8 depends on it. The simulator reshuffles lazily: in draw_one, when the pile is empty and a card is needed. So at a reshuffle someone is about to draw, and a drawer who survives holds at most 23 cards, which leaves both hands at most 47. Prop 8's hands A and B hold exactly 48 cards, so under lazy semantics they only occur at a reshuffle that is immediately lethal. The conclusion survives with 47-card versions, which I checked. 30 red non-draw cards + 17 coloured draw cards gives j <= 48 <= V = 50. 31 red non-draw cards + 16 wild draws gives j <= 66 <= V = 96. The two draw sets are disjoint, so both Lemma 6 conditions hold. State the timing convention and use 47-card hands.
- Prop 7 is imprecise and does not match Prop 8. 'Feasible' is never defined. feas.c sets R = 0, ignores the top card and allows 48 cards. It reports min j = 47 with no Roulettes, yet Prop 8's hand A has j = 46 once the blue-number top card is included. The stated gap 'the top card moves j by at most 1' is not a general fact: J drops by 2 per card in its tail, e.g. J(48)=25 to J(49)=23. Also, with R > 0, necessity requires V + R >= j with capacity reduced by R, and this was not searched. Prop 7 carries no weight in the logic, but it should be stated precisely or downgraded to a remark.
- Prop 8's headline, 'no argument based only on draw-value budgets can prove C = empty', is a meta-claim and not a theorem. What is actually proven is narrower: the particular necessary conditions derived here (Lemma 6 plus hand capacity) can be met together by an alternating schedule. It should be reworded as exactly that.
- Lemma 3 says 'turns are counted as at most steps'. That needs every turn to contain at least one node of the game graph, so forced single-option moves and deterministic effect resolution must be modelled as nodes. It is true under the stated model, but it should be said.
- Lemma 3's uniform-draw step (probability >= 1/167 conditional on the history) needs the players NOT to know the pile order. 'Fully informed' has to mean all hands plus the full history, and not the hidden order. Lemma 1 says this, and the task stipulates a hidden order, but the claimed theorem's wording 'fully informed' should be qualified. With knowledge of the order, the conditional-probability step fails.
- Cosmetic points. The 205-turn bound is loose: on the good event V0 < J(x) <= J(1) = 80, which gives at most 2(14+79)+1 = 187. Lemma 5 writes 'reshuffle needs an empty pile, i.e. D = 0', but D = 0 does not imply an empty pile. The hypothesis D(s) >= 33 in Theorem A is redundant, since V(s) < j(s) already forces j >= 1 and hence D >= 33.

### Referee 2: correct_with_minor_fixes

- The model never fixes when a reshuffle happens. The simulator (sim/nomercy.c, draw_one) reshuffles lazily, only when a draw is needed and the pile is empty. RULES §5's derived fact reads the same way. Under that convention a draw-until-playable or Roulette that runs into a reshuffle is always lethal, because D(P_k) >= 59. So every reshuffle the game survives happens in the middle of a penalty, which forces R_k >= 1 and at most 47 cards in hands (the absorber holds at most 23). Proposition 8 uses 48-card hands with R = 0, which is not reachable under this convention. The fix works: with R = 1, 30 red non-draw cards plus 17 coloured draws (5,5,5,2) give j = 48 <= V+R = 51, and 31 red plus 16 wild draws give j = 66 <= 97. The Lemma 6 transitions still hold (96 <= 152-48+1 = 105 and 50 <= 152-66+1 = 87). I checked these numbers in my own C.
- §6 contradicts itself on the j bound. It counts hands <= 48 plus the top card, so up to x = 49 non-draw cards can be missing from the pile. J(49) = 23, not J(48) = 25. So 'j(P_k) >= 25' is only true if hands hold at most 47, which is the lazy convention above. But the explicit Proposition 8 schedule uses 48. Pick one convention: either j >= 23 (eager) or a repaired Proposition 8 (lazy).
- Theorem A's turn count is loose as written. Steps 5-7 give at most H+V plays, at most H+V+1 absorbing turns, and one final lethal flood or Roulette turn, which adds up to 2(H+V)+2, not +1. The stated bound 2(H+V)+1 is still true with tighter counting: each absorb that does not end the game draws at least 2 cards, so there are at most V/2+1 absorbs, and turns <= H + 1.5V + 2 <= 2(H+V)+1 because H >= 2. So the 205-turn bound in Corollary B stands. Also, V(s) must include the draws still owed when s is in the middle of a penalty.
- Lemma 6 says a draw card in P_{k+1} 'was played or shed by Discard All during cycle k'. It could also be the top card at r_k. This does not change the conclusion.
- Proposition 7's search (feas.c) leaves out the carried penalty R, not only the top card, although the text states the condition as V >= j - R. I reran it with R from 0 to 23 and hand capacity 48-R. The minimum feasible j stays 47, or 60 with 8 Roulettes. Under the lazy convention (R >= 1) it is 48. So the numbers are essentially right, but the omission should be disclosed or the search fixed.
- Proposition 8 overclaims when it says 'no draw-value-only argument can close the gap'. What it actually shows is narrower: two fixed hand compositions satisfy the specific necessary conditions (Lemma 6 plus hand capacity) together. It does not show those compositions can be reached against sigma. It also does not cover budget arguments that combine value with other counts. It should be restated as 'the Lemma 6 plus capacity conditions do not by themselves exclude survival'.
- In Lemma 3, eps can be tightened: with 2 players the pile holds at most 165 cards. This does not affect correctness.
