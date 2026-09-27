# T2: no trap with 2 or 3 active players (official rules, Mercy rule on)

**Status: partial result, refereed.** Two independent referees returned *correct with minor fixes* and found no fatal issue; their notes are listed at the end and have not yet been folded into the text below. Scope: the official rules of RULES.md sections 1–6 (with the 25-card Mercy rule), not the house rule of section 7.

## Statement

Conjecture E (no trap) holds for 2 and 3 active players. Take any non-terminal micro-state of the T1 model G_N (any seat count N) that satisfies invariants (I1)-(I4) and has |A| = m in {2,3} active players. Then some finite path of legal decisions, with every drawn card of positive probability (any card in the current draw pile, or in the reshuffled pile when the draw pile is empty), reaches END. Consequences: Conjecture E holds for N = 2 and N = 3. So by T1 Theorem C and Corollary C2, uniformly random play, and any full-support stationary policy, has E[T] < infinity with geometric tails in 2- and 3-player games. For N in {4,5,6}, every state with at most 3 active players can still reach END; the open part is the knockout step from 4, 5 or 6 active players. A general kill toolkit valid up to m = 6 is also proven.

## Gaps (what is not proven)

- Knockout step for m = 4 active players is not proven. Property (P) fails with exactly one holder hand, because a penalty on the seat opposite the holder hand grows the non-holder hands. The (alpha) draw budget of 23*4 + 10 = 102 also exceeds the guaranteed fresh pile of 71. It needs a single-holder routing argument, or a potential that works across cycles.
- Knockout step for m = 5 is not proven. The feeding lemma F fails (slack -23), so reshuffles triggered by draw-until-playable are no longer kills, and the fresh pile is only at least 47. Lemmas KA, KB and KM and the perfect-drain window still hold.
- Knockout step for m = 6 is not proven. KB fails and the fresh pile can be as small as 23. Only KC (empty draw pile), KD (draw pile lacks two colours) and KM (monochromatic after an earlier non-killing Roulette in the same cycle) are available.
- So Conjecture E remains open for N = 4, 5 and 6. What is proven is that any trap must have at least 4 active players.
- The m=2/3 strategy was verified by hand-checked case analysis and the arithmetic script only. It was not tested in an instrumented simulator with an adversarial-nature controller.

## Proof

# Conjecture E for 2 and 3 active players, and a kill toolkit up to 6

## Status

**Proven:**
- The "knockout-or-end" step for m = 2 and m = 3 active players. So Conjecture E holds for N = 2 and N = 3.
- The toolkit lemmas KA, KC, KD, KM for all m ≤ 6.
- Lemma KB for m ≤ 5.
- Lemmas F and T for m ≤ 4.

**Not proven:** the knockout step for m = 4, 5, 6. See §7 for the exact obstacles.

**What the result covers.** The proof uses only (I1)–(I4) of [T1 Lemma 1] and the transition table of [T1 §2.2]. So it covers every invariant-satisfying state, not only reachable ones. [R§k] cites RULES.md (default rules).

## 0. Setting and notation

**Model.** This is the T1 micro-state model. A path may use any legal decision, and nature may draw any card type present in D*. D* is the draw pile D, or X if D is empty ([T1 §2.2 "Draw for q"], [R§5 last bullet]).

**Progress** means reaching END or a knockout. When m = 2, a knockout means END [R§5]. It suffices to reach progress from every state with m ∈ {2,3}. After a knockout from m = 3 we are at m = 2, and (I1)–(I4) still hold [T1 Thm D]. So the two steps concatenate.

**Notation.**
- U = D + X is everything outside the active hands and the top card. By (I1), |U| = 167 − Σ_A |H_q|.
- h_q = |H_q|.
- For a colour k, non_k(Y) is the number of cards in Y that are not of colour k, wilds included.
- d_k(Y) is the number of colour-k cards in Y.
- A **Roulette** is WCR. A **holder hand** is a hand (a card multiset, followed as it moves under 0 and 7) that contains a Roulette. A **holder turn** is a TURN state with σ = 0 whose current player holds a holder hand.
- **DUP** is draw-until-playable: TURN with σ = 0 and no playable card [R§3.2]. In a DUP the colour in play c and top card τ do not change until the playable card is played.

**Card counts [R§1].**
- Each colour has 36 cards.
- There are 24 wilds.
- For a fixed coloured kind κ, the other three colours hold at most 3·3 = 9 cards of kind κ.
- So the cards playable on (c, τ) number at most 24 + 36 + 9 = 69.

**L0.** From any non-TURN phase, any choices reach a TURN state or END within 49 micro-steps [T1 Lemma 3]. So we may start at a TURN state, with σ ≥ 0.

**L1 (draw-free turns end the game).** Consider a turn in which no card is drawn. It is a play: a stack, a normal play, or a Roulette that is the player's last card, which gives END [R§3.4]. The reasons:
- Accepting a penalty draws σ ≥ 2 cards.
- A DUP draws.
- A Roulette with cards left in hand makes its victim reveal at least 1 card [R§4].

A play lowers Σ_A h_q by at least 1: 0 and 7 only permute hands, and Discard All lowers it further. By (I3), Σ_A h_q ≥ 2. So along any path that never reaches END, draws happen infinitely often. Between reshuffles D only shrinks. Hence a reshuffle (a draw from an empty D) happens after finitely many steps.

## 1. Kill lemmas (a Roulette played by r; victim v = nx(r,d), with v ≠ r by (I3))

**Setup.** The victim names a colour k, then reveals cards until one of colour k. Wilds never count, and every revealed card enters the hand at once, with the Mercy check [R§4 Roulette, R§5]. No card is played during the reveal. So if D runs out, the reshuffled pile is exactly the X of the moment the Roulette was played.

**Hand bounds.** After playing, h_r ≤ 23, and every other hand is ≤ 24 by (I2). Hence |U| ≥ 167 − 23 − 24(m−2) − h_v. This is ≥ 48 − h_v for m ≤ 6, and ≥ 120 − h_v for m ≤ 3.

**Lemma KA (all m).** If some colour k has non_k(D) ≥ 25 − h_v, then v can be knocked out.
- *Proof.* v names k. Nature reveals non-k cards of D. After 25 − h_v of them, v has 25 cards and is out.
- *Special case.* This applies whenever |D| ≥ 31. The reason: Σ_k non_k(D) = 3|D| + w(D) ≥ 93, so some non_k(D) ≥ 24 ≥ 25 − h_v, using h_v ≥ 1.
- *Correction.* This is the task's (K2) with the threshold 32 improved to 31.

**Lemma KB (m ≤ 5).** If D has no card of colour j, then v can be knocked out.
- *Proof.* v names j. The reveal takes all of D, then the reshuffle, then the non-j cards of X. That is non_j(U) ≥ |U| − 36 ≥ 108 − 24(m−2) − h_v ≥ 36 − h_v ≥ 25 − h_v.
- *Correction.* This is the task's (K3). The slack is 11 at m = 5. The bound fails at m = 6.

**Lemma KC (all m ≤ 6; this is the task's (K)).** If D = ∅, v names the colour j that is rarest in U. Then non_j(U) ≥ ⌈3|U|/4⌉ ≥ ⌈3(48 − h_v)/4⌉ ≥ 25 − h_v.

**Lemma KD (all m ≤ 6; the fix for m = 6).** Suppose D lacks two colours j1 and j2. v names whichever of them is rarer in U.
- Then non_j(U) ≥ ⌈|U|/2⌉ ≥ ⌈(48 − h_v)/2⌉.
- This is ≥ 25 − h_v for every 1 ≤ h_v ≤ 24. At h_v = 1, integrality gives 24; at h_v ≥ 2 the real bound suffices.
- With three colours missing, the bound is ⌈2|U|/3⌉.

**Lemma KM (monochromatisation).** Suppose v names k and nature uses the rule "draw a non-k card whenever the current pile has one". Then either v is knocked out, or the reveal ends with D ⊆ colour-k cards.
- *Proof.* A k card is drawn only when the pile holds nothing but k cards.
- *Consequence.* D only shrinks until the next reshuffle, so D stays inside colour k until then. D then lacks 3 colours. By KD, a later Roulette played before the next reshuffle knocks out its victim, for every m ≤ 6.

**Lemma F (feeding kill; m ≤ 4).** In a DUP by p, suppose D contains no card playable for p (D = ∅ included). Then p can be knocked out.
- *Proof.* Nature draws all of D. Every card is unplayable, so the draw continues. Then comes the reshuffle, then unplayable cards of X.
- There are at least |U| − 69 unplayable cards in U, and |U| ≥ 167 − 24(m−1) − h_p ≥ 95 − h_p.
- So at least 26 − h_p ≥ 25 − h_p unplayable cards are available [R§3.2, R§5].

**Lemma T (reshuffle triggers; m ≤ 4).** Suppose the controller obeys two rules:
- (T1) In a DUP, it draws a playable card from D if D has one; otherwise it feeds as in F.
- (T2) A Roulette victim who faces a D lacking some colour names that colour and reveals as in KB; otherwise it names a colour present in D, and the reveal stays inside D. The reveal can take one k card first, or all non-k cards and then a k card.

Then every reshuffle is either part of a knockout (F or KB) or happens while a player draws an accepted penalty.

## 2. Fresh cycles

**Definition.** A **fresh cycle** starts at a reshuffle that happens while q draws an accepted penalty. Its properties:
- D0 := X at that moment, with |D0| ≥ 167 − 24m. That is ≥ 119 for m = 2 and ≥ 95 for m = 3.
- q still owes at least 1 card. Unless knocked out, q draws at most 24 − h_q ≤ 23 of them (the "remainder").
- Afterwards the game is at TURN(nx(q,d)) with σ = 0 [T1 PEN row].
- The top card is the draw card that created the penalty, so it is not a Roulette.
- r := number of Roulettes in D0. c1 := a colour of minimal count in D0. Then non_c1(D0) ≥ ⌈3|D0|/4⌉, which is ≥ 90 for m = 2 and ≥ 72 for m = 3.

**Controller Γ0.**
- Every penalty is accepted [R§3.1: accepting is always legal].
- Normal turns play any playable card by a fixed rule.
- DUP and Roulette-colour choices follow (T1) and (T2).
- Wild colours and 7-targets are arbitrary.

**Stage 1.** From any TURN state, follow Γ0. By L1 a reshuffle occurs. By Lemma T it is either progress or the start of a fresh cycle.

## 3. Property (P) and the Routing Lemma (m ≤ 3)

**Property (P).** Assume holder hands exist, holders never play Draw Cards, and nobody stacks. Suppose a non-holder hand accepts a penalty and survives. Then the next TURN is a holder turn.

*Proof of (P).* Only non-holders create penalties, and each accepted σ is the value of a single card.
- **m = 2, one holder hand H.** A D2, D4, WD6 or WD10 by the non-holder Q hits H [T1 Eff]. So a non-holder penalty can only come from Q's own WRD4: σ = 4 at TURN(Q) [R§4 WRD4, 2-player]. After Q accepts, TURN(nx(Q)) = H. If both hands hold Roulettes, no non-holder exists.
- **m = 3, one holder hand.** The creator p and the victim v are the two non-holders, and v = nx(p, d′), where d′ is the direction after the effect. After v accepts, TURN(nx(v, d′)) is the third seat, which is the holder. Hands do not move during a penalty.
- **m = 3, two holder hands.** The single non-holder can only hit holders.

**Potentials.**
- Ψ := total size of non-holder hands.
- B := Σ over holder hands of (24 − size) ≥ 0.

**Routing Lemma.** Let m ≤ 3, and suppose all 8 Roulettes lie in active hands. Under the controller Γ_R:
- accept every penalty;
- at a holder turn, play a Roulette;
- at a non-holder turn with a playable card, play any playable card;
- handle DUPs by (T1).

Then either a holder plays a Roulette at a holder turn, or progress occurs.

*Proof.*
- Before the goal no Roulette is played, so D, X and the top stay Roulette-free. Holder hands never shrink, and non-holder hands never gain a Roulette.
- Every turn falls into one of these classes:
  - (i) A non-holder plays from hand: Ψ drops by at least 1. A non-holder that empties its hand wins, which is END.
  - (ii) A holder accepts a penalty: B drops by σ ≥ 2. If the holder's hand would exceed 24, that is a knockout.
  - (iii) A non-holder accepts a penalty: by (P), the next turn is the goal.
  - (iv) A DUP by a non-holder: exactly one playable card is drawn and played, so the hand size is unchanged. Otherwise Lemma F applies and gives progress.
  - A holder turn: this is the goal.
- So (i) and (ii) occur finitely often.
- After the last of them, every turn is a DUP turn with no Draw Card played, since a Draw Card would lead to (ii) or (iii). No reveal occurs.
- In that tail, a reshuffle would be a DUP draw from an empty D, which falls under F and gives progress. Each tail turn removes one card from D. So the tail has at most |D| + 1 turns. □

## 4. Main theorem (m ∈ {2,3})

Run Stage 1, which gives a fresh cycle F or progress. Then split on r(F).

### (α) r ≥ 1

**Controller Γ_α.**
- **Remainder.** If r ≥ 2, q's first remaining draw is a Roulette.
- **Other penalty draws.** Every other remainder draw and every later penalty draw is a c1 card while D has one, and otherwise a non-Roulette card.
- **Penalties** are accepted.
- **Holder turn:** play a Roulette.
- **Non-holder turn with a playable card:** play any playable card.
- **DUP:** draw a Roulette from D. It must be played [R§3.2 "Then, play that card"].
- **Victim:** names c1; nature reveals non-c1 cards first.

**(a) A holder hand exists.** If r ≥ 2, q gets a Roulette. If r = 1, at least 7 Roulettes lie in hands, because the top is a Draw Card.

**(b) Draw count.** Let η be the number of holder hands.
- If η = m, the first TURN is a holder turn, and at most 23 cards have been drawn.
- Otherwise, the draws before the first Roulette play are at most:
  - 23 for the remainder;
  - 23(m−1) for holder penalties, since each holder hand has at most 23 cards of room;
  - 10 for one class-(iii) penalty.
- That totals at most 23m + 10: 56 for m = 2 and 79 for m = 3. This is below |D0| − 8 (111 and 87).
- Hence no penalty ever needs a Roulette, D keeps a Roulette, and there is no reshuffle.

**(c) Window.** While c1 ∈ D, the only non-c1 draws are the Roulette given to q and the Roulette drawn in the goal DUP. So non_c1(D) ≥ 70 ≥ 24, and KA applies. Once c1 ∉ D, KB applies (m ≤ 5).

**(d) Termination.** The classes are as in §3, except that every DUP now reaches the goal immediately. So after at most Ψ + B/2 + 2 turns a Roulette is played, either at a holder turn or out of a DUP. By (c) its victim is knocked out, unless it was the player's last card, which gives END.

### (β) r = 0

**All Roulettes are in hands.** The top is a Draw Card and D0 has no Roulette, so all 8 Roulettes are in active hands.

**Routing.** Apply the Routing Lemma. Any reshuffles along the way are penalty-triggered by Lemma T, or they are progress. This yields a Roulette played at a holder turn.
- If KA or KB applies, the victim is out.
- Otherwise D contains all 4 colours. The victim names some k, and nature reveals as in KM. The reveal stays inside D, so there is no reshuffle. Now D ⊆ colour k.

**After a non-killing reveal.** Continue with Γ0.
- Any Roulette played before the next reshuffle faces a D that lacks a colour. By (T2) and KB, that kills.
- By L1 and Lemma T, the next reshuffle is progress, or the start of a fresh cycle F′.
- At F′, the Roulette from (β) is in D0. It was covered by the Draw Card whose penalty triggered F′, and X is drawn from only at reshuffles.
- So r(F′) ≥ 1, and (α) applies.

**Conclusion.** Every state with m ∈ {2,3} reaches progress. Two steps (m = 3, then m = 2) reach END. □

## 5. Consequences

**Conjecture E for N ∈ {2,3}.** It holds for N = 2 and N = 3. By [T1 Thm C and Cor C2], uniformly random play (and every full-support stationary policy) has P(T > t) ≤ (1 − ε^k)^⌊t/k⌋, so E[T] < ∞.

**Constraint on traps for N ≥ 4.** A trap must have at least 4 active players.

## 6. Checks on the suggested tools

**(K), (K2), (K3).** Correct, as KC, KA and KB. For (K2), 31 suffices.

**(Drain).** The claim "|D| ≥ 71 at a reshuffle for m ≤ 5" is **false for m = 5**: the bound is only 47. The "39 draws exceed 36" step therefore works only for m ≤ 4.
- *Repaired version.* While nature draws only c1 cards, non_c1(D) = non_c1(D0) stays constant: at least 36 for m = 5 and at least 54 for m = 4. So KA holds until c1 is exhausted, and KB holds afterwards.
- *Limitation.* This is exact only if every draw is nature's free choice. DUP draws are not free.

**(Holder).** As stated, it is incomplete. A holder can be avoided indefinitely by Skip, Reverse, Skip Everyone, 0 and 7. The fix is the (Ψ, B) potential together with (P), and (P) is valid only for m ≤ 3.

## 7. What is open (m = 4, 5, 6)

**m = 4.**
- F, T, KA, KB and KM all hold.
- (P) holds when there are at least 2 holder hands, in both the adjacent and the alternating seating.
- (P) **fails** with exactly one holder hand. A penalty on the seat opposite the holder hand is followed by a non-holder's turn, so Ψ can grow.
- The count in (α)(b), 23·4 + 10 = 102, exceeds |D0| ≥ 71.
- Missing: a routing argument for the single-holder case, and a draw budget or a cross-cycle potential.

**m = 5.**
- F fails: the slack is −23. So DUP-triggered reshuffles are no longer kills.
- The fresh-pile margin is small: 47.

**m = 6.**
- KB fails, and |D0| can be as small as 23.
- Only KC, KD and KM are available: a Roulette is certain to kill when D is empty, lacks 2 colours, or has been made monochromatic by an earlier reveal in the same cycle.

## 8. Numerical checks (scratchpad `lemmas.py`)

The script confirmed all constants:
- at most 9 same-kind cards in the other colours, and the 69 bound;
- KA at |D| = 31;
- |D0| ≥ 119, 95, 71, 47, 23 for m = 2..6, with non_c1(D0) ≥ 90, 72, 54, 36, 18;
- KB slack 83, 59, 35, 11, −13;
- F slack 49, 25, 1, −23, −47;
- the inequalities for KC and KD (2 and 3 colours) for all h in 1..24.

No repository files were modified.

## Referee notes (minor; to be folded in)

### Referee 1: correct_with_minor_fixes

- The scope claim is too broad. The proof says it 'covers every invariant-satisfying state, not only reachable ones', but (I1)-(I4) say nothing about the top card while a penalty is pending. Take TURN with sigma=4, top = WCR, D empty. Gamma0 accepts, and the reshuffle during that penalty counts as a 'fresh cycle' whose top is not a Draw Card. Then '(beta): all 8 Roulettes are in active hands' and '(alpha)(a): r=1 => 7 in hands' fail. My checker (edge.py) hit the 'Roulette outside hands' assertion in 1347 of 3000 such states. Fix: in Stage 1, ignore a reshuffle that happens while a penalty pending at the start is being accepted. Every later penalty is created on the path, so its top is a Draw Card. Alternatively, restrict the claim to reachable states, which is all Conjecture E needs. The theorem itself is unaffected.
- The Routing Lemma is stated for any TURN state, but (P) only covers penalties that a non-holder created under Gamma_R. A penalty already pending at the start (for example one created by a holder) can be accepted by a non-holder, and the next TURN can then belong to a non-holder. The checker found 73 of 20000 routing-start states where this happens, all on the first turn. This does no harm to the main chain, because (beta) starts routing at sigma=0 after the remainder, and in general it adds only one bounded increase of Psi. Still, the lemma should either assume sigma=0 at the start or allow this one-off case.
- (alpha)(d) says 'the classes are as in §3', but §3's premise (all 8 Roulettes in hands, and D, X and the top free of Roulettes) is false in (alpha). The facts actually needed are that non-holders never gain a Roulette and holder hands never shrink. They follow from Gamma_alpha's draw rules together with the (b) budget, while (b) itself relies on that class structure (at most one class-(iii) penalty, and 23 cards of room per holder hand). This is a valid simultaneous induction up to the goal, but it is not written out.
- Routing Lemma (iv): 'the hand size is unchanged' should be 'the hand size does not increase'. A Discard All drawn and then forced into play in a DUP lowers the hand. Psi still never increases, so the argument stands.
- L0 cites 49 micro-steps, but T1 Lemma 3(b') gives 48. This is harmless.
- (alpha)(a): with r=1 there are exactly 7 Roulettes in hands, not 'at least 7'. The bound 'Psi + B/2 + 2 turns' in (alpha)(d) is informal but correct as a finiteness argument.

### Referee 2: correct_with_minor_fixes

- Scope overclaim. The proof says 'it covers every invariant-satisfying state, not only reachable ones', but it relies on facts that come from the dynamics, not from (I1)-(I4). The fresh-cycle claim 'the top card is the draw card that created the penalty' is used in (alpha)(a) for r=1 and in (beta) for 'all 8 Roulettes are in active hands'. It fails for an unreachable invariant state with sigma>0 and a non-Draw top card. Example: top = WCR, D empty, X Roulette-free, 7 WCR in hands. There the (beta) premise is false, as it was in 5000 of 5000 constructed starts. The path still reached END in every one, so the conclusion survives empirically, but the written argument does not cover these states. T1 also defines the kernel only on S := R; for example, WCOL with tau = WCR has no Eff. Fix: restrict the claim to reachable states, which is what 'micro-state of G_N' already means in T1.
- L0 cites '49 micro-steps [T1 Lemma 3]'. T1 Lemma 3(b') now gives 48; 49 is still valid but is not the cited figure.
- L1 is titled 'draw-free turns end the game', but it proves something else: a draw-free turn is a play that lowers the sum of h_q over A by at least 1, so draws, and hence a reshuffle, must recur. The title should say that.
- The (alpha)(b) budget of 23m+10 draws before the first Roulette play leaves out the DUP's own Roulette draw, which happens before that play (+1). The margins are unaffected: 57 < 111 and 80 < 87. The observed maximum over about 12,000 alpha cycles was 26 draws.
- In the m=3, one-holder case of (P), 'The creator p and the victim v are the two non-holders' should say 'in the case where the victim is a non-holder'. When the victim is the holder, it is class (ii).
- Section 6 (Drain) refers to a '39 draws exceed 36' step from the task text, which the proof never states. That remark cannot be checked from the proof alone. The repaired version (non_c1(D) >= 36 at m=5 and >= 54 at m=4) is correct.
