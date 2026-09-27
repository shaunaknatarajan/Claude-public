# T4-multiplayer-adversarial: colluding robots against a hostile deck (official rules, Mercy rule on)

**Status: partial result.** The first version was refereed; one referee found fixable flaws; this is the repaired version, which a re-review judged *correct_with_minor_fixes*.
Scope: the official rules of RULES.md sections 1-6, not the house rule of section 7.

## Statement

UNO Show 'Em No Mercy under the RULES.md defaults, N = 3..6 seats (some items also cover N = 2), with fully informed, non-anticipating colluding robots playing against an adversarial deck ("nature"). The following are proven.

(0) Extended model.
- Let Ŝ_N be the set of all T1 tuples that satisfy the invariants (I1)–(I5), which are stated explicitly in §2. The stack invariant (I4') includes the value of a wild Draw Card that is still waiting for its colour choice (WCOL phase).
- Ŝ_N is closed under the T1 transitions. It has ε ≥ 1/165 and |Ŝ_N| < 10^132, and it contains the reachable set R_N.
- T1's sure-safe set satisfies C_N = Ĉ_N ∩ R_N, where Ĉ_N is the largest safe set of the extended model.
- Hence Ĉ_N = ∅ implies E[T] ≤ K·165^K (K < 10^132) for every non-anticipating profile, and some profile has E[T] = ∞ iff Ĉ_N ∩ R_N ≠ ∅.
- For N ≥ 3, the tuple "all N hands hold 24 cards, TURN, no pending stack" lies in Ŝ_N but not in R_N. So the converse of the first implication is not automatic.

(1) Reduction to knockout-free play.
- Ĉ_N ≠ ∅ iff S_k ≠ ∅ for some k ∈ {2,…,N}. Here S_k is the largest knockout-free safe set of the k-seat extended game.
- Consequences: S_2 = … = S_N = ∅ is a sufficient condition for finite E[T] under every profile, and non-emptiness of Ĉ_N is monotone in N.
- For any stationary or finite-memory profile, almost surely on {T = ∞} the play eventually stays inside a knockout-free safe set.

(2) Exact forced-knockout criteria (Lemma 4.2).
- Draw-until-playable: nature can force a knockout iff h + U(D°) ≥ 24, or h + |D°| + U(X°) ≥ 24 when the pile holds no playable card.
- Roulette: the same criterion, applied to the named colour κ.
- Penalty: accepting σ is fatal iff h + σ ≥ 25.

(3) Colour support. In an endless knockout-free play with k active players:
- cards that are never again played and never shed by Discard All end up in hands forever, so there are at most 24k − 1 of them;
- consequently at least 3 colours (k ≤ 3), or at least 2 colours (k = 4), are played infinitely often.

(4) Funding (starvation) theorem. Let nature play N*: deal a draw-value-0 card whenever the pile holds one.
- Main inequality: H_j + ρ_j + H_{j+1} + g_{j+1} + Z_j + Z1_{j+1} ≥ 182. Hypotheses: cycle j is complete and knockout-free; phase 1 of cycle j+1 is complete and knockout-free; N* is used in that phase 1.
- Explicit minimum: Z_j + Z1_{j+1} ≥ M_k, with M_2 = 55 and M_3 = 10. For k ≥ 4 the bound is trivial.
- Pure-penalty plays: if N ≤ 3, nature plays N* and no draw-until-playable or Roulette draw occurs from a reshuffle t_j on, the game ends before t_{j+4}, within at most 1,036 turns.
- Necessary conditions on any knockout-free safe set:
  - every draw-until-playable or Roulette reveal it contains is non-lethal;
  - for k ≤ 3, every N*-play inside it makes at least M_k unfunded draws in every two consecutive cycles;
  - lethal window: no draw-until-playable sequence starts while the pile holds more than 91 cards, and no Roulette is played while it holds more than 58.

NOT resolved: for N = 3,4,5,6, whether Ĉ_N ∩ R_N ≠ ∅ (so that some colluding profile has infinite mean length), and whether Ĉ_N ≠ ∅.

## Gaps (not proven)

- The main question is still open for N = 3,4,5,6. No knockout-free safe set S_k has been constructed, none has been shown empty, and Ĉ_N ∩ R_N ≠ ∅ is neither proven nor refuted.
- Lemma 2.4(b) and Cor 3.4(b) are sufficient conditions only. Ĉ_N = ∅ implies finite E[T], but C_N = ∅ does not imply Ĉ_N = ∅. Example 2.5 shows that the extended model has unreachable states. No steering or reachability lemma is proven (Remark 3.6, Conjecture B), not even for k = N.
- The funding theorem uses only one nature strategy, N*. It gives a trivial bound for k >= 4. For k = 3, cheap one-card draw-until-playable sequences at low-pressure moments late in a cycle can supply the unfunded draws it requires. Prop 6.7(ii) and (iv) restrict when such sequences can occur, but not how many there are.
- The colour-skew and Roulette-poison levers, the strongest ones in the experiments, are not formalized.
- Prop 3.5 covers stationary and finite-memory profiles only, and holds almost surely. There is no pathwise statement for history-dependent safe profiles, and the old pathwise claim was false.
- The numerical colluders are heuristic depth-3 searchers, and the traces show avoidable blunders: self-inflicted stack spirals, and Wild Draw 6/10 cards played onto full hands. The adversaries are heuristic, not worst-case. Survival and collapse times are therefore evidence about these particular agents, not about Ĉ_N.
- Conjecture A (S_2 = S_3 = ∅) and the weak lean towards Ĉ_N = ∅ for N = 4..6 are unproven.

## Proof

# T4 (revised): three to six colluding robots against an adversarial deck

**Revision note.** This version answers both referee reports on the previous attempt.

- **State space (fatal issue 1).** All safe-set statements now live on an *extended model* $\hat{\mathfrak G}_N$ (§2). Its states are all tuples that satisfy explicit invariants (I1)–(I5). It is closed under the T1 transitions (Lemma 2.2), and the reachable set $R_N$ sits inside it. The reduction theorem (Thm 3.3) is stated for the extended safe set $\hat C_N$. The link to the question actually asked is Lemma 2.4: $C_N=\hat C_N\cap R_N$. So $\hat C_N=\varnothing$ gives finite $E[T]$ for every profile, but not conversely. Example 2.5 shows that $\hat{\mathfrak G}_N$ really has unreachable states. Headline claim (1) and "monotone in $N$" are restated for $\hat C_N$. Remark 3.6 records that reachability is open even for $k=N$.
- **Old Cor 5.8 (fatal issue 2).** It was vacuous and is deleted. It is replaced by pathwise statements: Cor 6.6, and Prop 6.7, a necessary condition on any knockout-free safe set.
- **Old Cor 2.4(c).** Replaced by Prop 3.5, an almost-sure statement for stationary and finite-memory profiles, with proof.
- **New results.** Example 2.5 (an explicit unreachable tuple of the extended model) and Prop 6.7(iv) (the lethal window).
- **Minor fixes.**
  - Lemma 4.1: the hypothesis "the remaining penalty is knockout-free" now appears in its summary line.
  - Lemma 6.2: now assumes phase 1 is completed.
  - Theorem 6.4: now states its minimal hypotheses.
  - Cor 6.5: the bound for $k\ge4$ is called trivial rather than "$M_k=0$". The table says "hand cards plus owed draws", and the capacity step is proved in full.
  - Cor 6.6: cites Lemma 5.1(i) for the existence of later reshuffles, and has an explained turn bound.
  - §1 and §9 describe a trade-off, not "full hands and 10 draws".
  - The Roulette colour is written $\kappa$, not $k$. Nature strategies act on the effective pile $D^*$.
  - The summary of Prop 5.2 includes the Discard All clause.
  - The two-player convention is an explicit assumption (A2).
- **Numerics (§8).** All numerics were re-run with an engine that counts the Roulette victim's turn, so lengths are $T$ as defined in [R§6]. Every game is reported, including those that ended before the adversary was switched on. The row without an output file has been re-run and saved. Traces show that some colluder deaths were self-inflicted.

**Old → new numbering.**

| Old | New |
|---|---|
| Lemma 2.2 | Lemma 3.2 |
| Thm 2.3 | Thm 3.3 |
| Cor 2.4 | Cor 3.4 and Prop 3.5 |
| Lemma 3.1–3.2 | Lemma 4.1–4.2 |
| Lemma 4.1 / Prop 4.2 | Lemma 5.1 / Prop 5.2 |
| Lemma 5.2–5.4 | Lemma 6.1–6.3 |
| Thm 5.5 | Thm 6.4 |
| Cor 5.6–5.7 | Cor 6.5–6.6 |
| Cor 5.8 | deleted; replaced by Prop 6.7 |

**Conventions.**
- Rules are the RULES.md defaults, cited [R§k]: [R§3.1] is §3 item 1, and [R§4 Roulette] is the Roulette row of the §4 table.
- Tuples, phases, transitions, nx, "playable", the effective pile $D^*$ and the turn count $T$ are those of T1 (`docs/proofs/T1_foundations_dichotomy.md`) §2.
- $N\in\{2,\dots,6\}$ is the number of seats. $k=|A|$ is the number of active players.
- $dv$ is the draw value: D2 = 2, D4 = WRD4 = 4, WD6 = 6, WD10 = 10, and 0 for every other card, including the Roulette (WCR) [R§1].
- The 36 Draw Cards have total value 152; their values in decreasing order are $10^{\times4},6^{\times4},4^{\times16},2^{\times12}$.
- $\mathrm{maxdv}(b)$ is the sum of the $b$ largest values. For example $\mathrm{maxdv}(4)=40$, $\mathrm{maxdv}(7)=58$, $\mathrm{maxdv}(9)=68$ and $\mathrm{maxdv}(17)=100$.
- $dv(Y)$ is the total draw value of a multiset $Y$.

**Assumptions.**
- **(A1)** Colluders are *non-anticipating* (T1 §4). They see every hand and the composition of every pile, but not the order of the draw pile.
- **(A2)** "With 2 players" in [R§4] (Reverse acts as Skip; Wild Reverse Draw 4 hits its own player) means "with exactly two *active* players". This is how T1 §2.2 and `sim/nomercy.c` (`G->nalive == 2`) read it.

---

## 0. Status

| # | Statement | Status |
|---|---|---|
| Lemma 2.2 | The extended state space $\hat S_N$ is closed under transitions; T1's kernel, $\varepsilon\ge1/165$ and finiteness hold on it | **Proven** (also tested: 0 failures in $7.2\times10^6$ random transitions) |
| Lemma 2.4 | $C_N=\hat C_N\cap R_N$. $\hat C_N=\varnothing$ implies $E[T]\le K\,165^K$ for every non-anticipating profile. $E[T]=\infty$ for some profile iff $\hat C_N\cap R_N\ne\varnothing$. | **Proven** |
| Ex. 2.5 | $\hat S_N\ne R_N$: for $N\ge3$, the tuple "all hands 24, TURN, no stack" is in $\hat S_N$ but unreachable | **Proven** |
| Thm 3.3 | $\hat C_N\neq\varnothing\iff S_k\neq\varnothing$ for some $k\in\{2..N\}$, where $S_k$ is the knockout-free safe set of $\hat{\mathfrak G}_k$ | **Proven** |
| Cor 3.4 | Monotonicity in $N$ (extended model). The sufficient condition "$S_2=\dots=S_N=\varnothing\Rightarrow E[T]<\infty$ for all profiles". The attractor form of $S_k=\varnothing$. | **Proven** |
| Prop 3.5 | Stationary or finite-memory profiles: almost surely on $\{T=\infty\}$, play eventually stays in a knockout-free safe set | **Proven** |
| Lemma 4.1–4.2 | Capacity identities; exact "nature can force a knockout" criteria | **Proven** |
| Prop 5.2 | Colour support: at least 3 colours ($k\le3$), or at least 2 ($k=4$), must be played infinitely often in endless knockout-free play | **Proven** |
| Thm 6.4 | Funding (starvation) inequality against the nature strategy $N^*$ | **Proven** |
| Cor 6.5–6.6, Prop 6.7 | At least 55 ($k=2$) or 10 ($k=3$) unfunded draws per two cycles, pathwise; pure-penalty plays with $N\le3$ end within 4 cycles; necessary conditions on knockout-free safe sets, including a "lethal window" (no draw-until-playable starts while the pile has more than 91 cards, no Roulette while it has more than 58) | **Proven** |
| — | Is $\hat C_N\cap R_N\ne\varnothing$ (so $E[T]=\infty$ for some colluding profile) for $N=3,4,5,6$? Is $\hat C_N\ne\varnothing$? | **OPEN** |
| §8 | Colluders survive $10^{3.7}$–$10^{5}$ turns with the real deck, but collapse within tens to hundreds of turns against simple adversarial decks | Numerical evidence (heuristic colluders) |
| §9 | Conjectures | Conjecture |

## 1. The answer in plain words

**Open.** For 3 to 6 players it is still undecided whether a perfect colluding team with full information can keep the game going forever with positive probability (mean length infinite), or whether the deck always wins in the end (mean length finite for every strategy).

**Proven.**
- **Reduction.** The question reduces to one about knockout-free play. If, for every $k\le N$ and every $k$-player position satisfying the basic invariants, nature can force a knockout or the end, then every strategy profile has finite mean length.
  - This is a *sufficient* condition only. The invariant-satisfying positions include some that no real game reaches (Example 2.5).
  - Conversely, if a real $N$-player game can reach a position from which colluders avoid the end forever against every draw sequence, the mean is infinite.
- **Nature's simplest lever.** Nature can withhold Draw Cards until the pile holds nothing else. Against this:
  - Two or three active players need at least 55, respectively 10, "unfunded" draws per two reshuffle cycles. An unfunded draw is one made in a draw-until-playable sequence or a Roulette reveal, whose length nature controls.
  - There is a trade-off: every empty hand slot at two consecutive reshuffles costs one more unfunded draw. The minimum 10 for three players needs nearly full hands.
  - A 2- or 3-player game in which nobody ever draws that way ends within four reshuffle cycles, about 1,040 turns.
  - With 4 or more players this counting obstruction disappears.
- **Colours.** In any endless knockout-free play with 2 or 3 active players, cards of at least three colours must keep circulating.

**Numerically.** Every colluder we built dies within tens to a few hundred turns once the deck turns adversarial, but these colluders are heuristic and make visible mistakes. With the real, uniformly shuffled deck the same colluders routinely last $10^4$–$10^5$ turns.

## 2. The extended model

### 2.1 States

**Definition 2.1.** $\hat S_N$ is the set of all tuples $s=(A,H,D,X,\tau,c,p,d,\sigma,v,\varphi)$ of T1 §2.1 that satisfy the following.

- **(I1)** Card conservation: $\sum_{q\in A}H_q+D+X+\{\tau\}=$ the full deck.
- **(I2)** $|H_q|\le24$ for $q\in A$, and $H_q=\varnothing$ for $q\notin A$.
- **(I3)** If $\varphi\ne\mathsf{END}$: $|A|\ge2$, $p\in A$, and $|H_q|\ge1$ for all $q\in A$.
- **(I4′)** Stack consistency:
  - $v=0\iff\sigma=0$;
  - $\sigma=0$ whenever $\varphi\in\{\mathsf{DRAW},\mathsf{PEN}(\cdot),\mathsf{REV}(\cdot),\mathsf{RCOL},\mathsf{SWAP}\}$;
  - $\tilde\sigma:=\sigma+[\varphi=\mathsf{WCOL}]\,dv(\tau)\le dv(X)+dv(\tau)$.
- **(I5)** If $\varphi=\mathsf{WCOL}$ then $\tau\in\{\mathrm{WRD4},\mathrm{WD6},\mathrm{WD10}\}$. If $\varphi=\mathsf{PEN}(r)$ then $1\le r\le152$.

$\hat{\mathfrak G}_N$ is the MDP on $\hat S_N$ with T1's action sets and kernel (T1 §2.2). $F$ is the set of END states.

*Why $\tilde\sigma$.* At WCOL the wild Draw Card just played has not yet been added to $\sigma$ (T1: Eff is applied after the colour choice). A first version of (I4′) used $\sigma\le dv(X)+dv(\tau)$. The randomized closure test (§8.1) found a successor violating it, which is why the in-flight term is included.

**Lemma 2.2 (closure).**
- (a) $\operatorname{supp}\mu_0\subseteq\hat S_N$.
- (b) At every $s\in\hat S_N\setminus F$, T1's rules give a nonempty finite action set and a successor law. At chance states $23\le|D|+|X|\le165$, so $D^*\ne\varnothing$, and every positive transition probability is at least $1/165$.
- (c) Every successor of every $s\in\hat S_N\setminus F$ lies in $\hat S_N$.
- (d) Consequently $R_N\subseteq\hat S_N$, and $|\hat S_N|<10^{132}$.

*Proof.* (a) An initial state has 7-card hands, $A=[N]$, $\sigma=v=0$ and phase TURN.

(b)
- Chance states. By (I1)–(I3), $|D|+|X|=167-\sum_A|H_q|$. This lies between $167-24\cdot6=23$ and $167-2=165$. So $D^*\ne\varnothing$, and $D^*(t)/|D^*|\ge1/165$.
- Decision states.
  - TURN with $\sigma>0$: *accept* is always legal.
  - TURN with $\sigma=0$: either some card is playable, or the state is a chance state.
  - WCOL and RCOL each offer 4 colours.
  - SWAP has the targets $A\setminus\{p\}\ne\varnothing$.
- nx is defined because $|A|\ge2$.
- Eff at WCOL is defined because $\tau$ is a wild Draw Card, by (I5).
- PEN($r$) moves to PEN($r-1$) only when $r>1$.

(c)
- **(I1)** Every transition relocates cards.
- **(I2)** Hand sizes change only in these ways:
  - a draw adds one card, and at 25 the drawer is knocked out and the hand is emptied into $X$;
  - plays and Discard All remove cards;
  - rotation and swap permute hands within $A$.
  Inactive seats never receive cards: draws go to $p\in A$, and rotation and swap act inside $A$.
- **(I3)**
  - $A$ shrinks only by a knockout, and $|A|=1$ leads to END.
  - A hand becomes empty only by Play, which then leads to END.
  - $p$ is set by nx, kept, or set to the victim nx$(p,d)$. After a knockout of $q$, $p:=\mathrm{nx}(q,d)\in A$.
- **(I4′)**
  - *$v$ and $\sigma$.* Accept sets both to 0. The effect of a Draw Card sets $v:=dv(t)\ge2$ and raises $\sigma$ by $dv(t)\ge2$. Nothing else changes them; a knockout occurs only in a chance phase, where both are already 0.
  - *Phases with $\sigma=0$.*
    - DRAW is entered from a TURN chance state (where $\sigma=0$) or from DRAW.
    - PEN is entered from accept, which sets $\sigma:=0$, or from PEN.
    - REV is entered from RCOL or REV.
    - RCOL and SWAP are entered only by playing WCR or a 7. At $\sigma>0$ only cards with $dv\ge v\ge2$ are playable, and $dv(\mathrm{WCR})=dv(7)=0$. A forced play after draw-until-playable happens at $\sigma=0$.
  - *The bound on $\tilde\sigma$.* Let $\tau_0$ be the old top.
    - Playing a coloured Draw Card $t$ gives $X'=X+\tau_0$, $\tau'=t$ and $\sigma'=\sigma+dv(t)\le dv(X)+dv(\tau_0)+dv(t)=dv(X')+dv(\tau')$.
    - Playing a wild Draw Card $t$ leads to WCOL with $\tilde\sigma'=\sigma+dv(t)$, which is bounded the same way. The Eff at WCOL keeps $\tilde\sigma$ fixed.
    - Discard All and knockouts only enlarge $X$.
    - A reshuffle ($X\to D$) happens only at chance states, where $\sigma=0$.
    - A Play that ends the game leaves $\sigma$ unchanged and enlarges $X$.
    - Other plays happen at $\sigma=0$.
- **(I5)** WCOL is entered only by playing a wild Draw Card. Accept creates PEN($\sigma$) with $\sigma\le\tilde\sigma\le dv(X)+dv(\tau)\le152$.

(d) $R_N\subseteq\hat S_N$ follows from (a) and (c). The count of T1 Lemma 2 covers all tuples of T1 §2.1. $\square$

### 2.2 Safe sets and the link to the real question

**Definition 2.3.** A set $Z\subseteq\hat S_N\setminus F$ is *safe* if every $s\in Z$ has an action $a$ with $\mathrm{succ}(s,a)\subseteq Z$. For a chance state this means all its successors lie in $Z$. $\hat C_N$ is the largest safe set of $\hat{\mathfrak G}_N$. It exists because a union of safe sets is safe, and it equals $\hat S_N\setminus\mathrm{Attr}(F)$ (T1 Lemma B1). $C_N$ is T1's safe set of $\mathfrak G_N$, whose state space is $R_N$.

**Lemma 2.4.**
- (a) $C_N=\hat C_N\cap R_N$.
- (b) If $\hat C_N=\varnothing$, then every non-anticipating profile (history-dependent, randomised, correlated, fully informed) satisfies $P(T>t)\le(1-165^{-K})^{\lfloor t/K\rfloor}$ and $E[T]\le K\cdot165^{K}$, with $K\le|R_N\setminus F|<10^{132}$.
- (c) Some non-anticipating profile has $E[T]=\infty$ iff $\hat C_N\cap R_N\ne\varnothing$. In that case a stationary deterministic full-information profile has $P(T=\infty)>0$.

*Proof.* (a)
- $\mathfrak G_N$ is $\hat{\mathfrak G}_N$ restricted to $R_N$, with the same kernel.
- $\mathrm{succ}(R_N)\subseteq R_N$.
- By induction, $\mathrm{Attr}_i(\mathfrak G_N)=\mathrm{Attr}_i(\hat{\mathfrak G}_N)\cap R_N$, as in T1 Lemma B1(iv).

(b) By (a), $C_N=\varnothing$; then apply T1 Thm B(A). (c) is T1 Thm B together with (a). $\square$

The converse of (b) is **not** claimed. $\hat C_N$ might contain only unreachable states. The next example shows that $\hat S_N\setminus R_N$ is not empty.

**Example 2.5 (an unreachable tuple).** Let $N\ge3$. Take any $s^*\in\hat S_N$ with $A=[N]$, $|H_q|=24$ for all $q$, $\varphi=\mathsf{TURN}$ and $\sigma=0$. Such tuples exist: $168-24N-1\ge23$ cards remain for $D$ and $X$. Then $s^*\notin R_N$.

*Proof.* Suppose a legal chain $s_0\to\dots\to s_n=s^*$ exists, with $s_0\in\operatorname{supp}\mu_0$.

*Setup.*
- No knockout occurs on the chain, because $A(s^*)=[N]$ and $A$ never grows.
- Some Play step occurs. $s^*\ne s_0$ because initial hands have 7 cards. From $s_0$ (TURN, $\sigma=0$) the chain either plays at once or draws until playable. That sequence must end in a forced Play, because a knockout is excluded and $s^*$ is not in DRAW phase.
- Let $m$ be the last Play step, by player $r$. Just after it, the hand that $r$ played from holds at most 23 cards. If the card was a 0, that hand has moved to nx$(r)$; if a 7 is followed by SWAP, it may move to the swap target.
- After step $m$ there is no Play, so hands change only by draws.

*Possible continuations after the Play.*
- **TURN with $\sigma=0$.** Every continuation from such a state plays, or draws until playable and then plays, or is still in DRAW. So this state is $s^*$, and it contains a hand of at most 23 cards.
- **TURN with $\sigma>0$ (possibly via WCOL).** No stacking can follow, since a stack is a Play, so the player $q$ now facing the stack accepts. Here $q\ne r$: with $|A|=N\ge3$ active players, even a Wild Reverse Draw 4 passes the penalty to a neighbour. Then $q$ draws, and the chain reaches $s^*$. Only $q$'s hand grew, so $r$ still has at most 23 cards.
- **SWAP.** This leads to TURN with $\sigma=0$, which is $s^*$. The hand of at most 23 cards belongs to $r$ or to the swap target.
- **RCOL, then REV.** Only the victim nx$(r)\ne r$ draws, and then comes TURN with $\sigma=0$, which is $s^*$.
- **END.** Impossible.

In every case some hand of $s^*$ has at most 23 cards, a contradiction. $\square$

Whether $\hat C_N$ contains reachable states at all, or even non-trivially differs from $C_N$, is open (Remark 3.6).

## 3. Reduction to knockout-free safety

**Definition 3.1.** For $k\in\{2..6\}$, let $\hat S_k^{\circ}=\{s\in\hat S_k:A(s)=[k],\ \varphi\ne\mathsf{END}\}$. A set $Z\subseteq\hat S_k^\circ$ is *knockout-free safe* if every $s\in Z$ has an action $a$ with $\mathrm{succ}(s,a)\subseteq Z$. So no successor under $a$ is a knockout or END. $S_k$ is the largest such set; it is the union of all of them.

**Lemma 3.2 (embedding).** Fix $N\ge k$ and $A\subseteq[N]$ with $|A|=k$. Let $\iota:[k]\to A$ be the increasing bijection; it preserves cyclic order. Define
$$\Phi_A(s)=\big([k],(H_{\iota(i)})_i,D,X,\tau,c,\iota^{-1}(p),d,\sigma,v,\varphi\big).$$
Then:
- $\Phi_A$ is a bijection from $\{s\in\hat S_N\setminus F:A(s)=A\}$ onto $\hat S_k^\circ$.
- Actions correspond: cards and colours unchanged, swap targets mapped by $\iota^{-1}$.
- For every such $s$ and action $a$:
  - $s'$ is a knockout-free, non-END successor of $(s,a)$ iff $\Phi_A(s')$ is a knockout-free, non-END successor of $(\Phi_A(s),\Phi_A(a))$, with the same probability;
  - $(s,a)$ has a knockout or END successor iff $(\Phi_A(s),\Phi_A(a))$ does.

*Proof.*
- (I1)–(I5) hold for $s$ iff they hold for $\Phi_A(s)$. Seats outside $A$ hold nothing, by (I2).
- $\mathrm{nx}_N(\iota(i),\pm1)=\iota(\mathrm{nx}_k(i,\pm1))$, since $\iota$ preserves cyclic order and nx skips inactive seats [R§5].
- The 0-rotation acts along nx on $A$, and the 7-targets are $A\setminus\{p\}$ [R§4, R§5].
- The two-player rules depend on $|A|=k$ (assumption A2).
- Draw laws depend only on $D$ and $X$, and Mercy and END depend only on hand sizes and $|A|$. $\square$

**Theorem 3.3.** $\hat C_N\ne\varnothing\iff S_k\ne\varnothing$ for some $k\in\{2,\dots,N\}$.

*Proof.* (⇐) Fix any $A\subseteq[N]$ with $|A|=k$. By Lemma 3.2, $\Phi_A^{-1}(S_k)$ is a safe set of $\hat{\mathfrak G}_N$: each state keeps the action corresponding to its safe action, whose successors map into $S_k$. So it is contained in $\hat C_N$.

(⇒)
- Let $k^*=\min\{|A(s)|:s\in\hat C_N\}\ge2$ and $C^*=\{s\in\hat C_N:|A(s)|=k^*\}$.
- For $s\in C^*$ and a safe action, every successor lies in $\hat C_N$, is non-END, and has at least $k^*$ active players. The active set never grows, so each successor has the same active set as $s$. So no knockout occurs.
- Pick $A$ with $C^*_A=\{s\in C^*:A(s)=A\}\ne\varnothing$. By Lemma 3.2, $\Phi_A(C^*_A)$ is knockout-free safe in $\hat{\mathfrak G}_{k^*}$. $\square$

**Corollary 3.4.**
- (a) **Monotonicity (extended model).** If $\hat C_N\ne\varnothing$, then $\hat C_{N'}\ne\varnothing$ for all $N'\ge N$.
- (b) **Sufficient condition for finite mean length.** If $S_2=\dots=S_N=\varnothing$, then $\hat C_N=\varnothing$, and Lemma 2.4(b) applies: $E[T]\le K\,165^K$ for every non-anticipating profile.
- (c) **Attractor form.** In the MDP on $\hat S_k^\circ\cup\{\mathfrak b\}$, all knockout and END successors are merged into one absorbing state $\mathfrak b$. Its largest safe set is $S_k$. So $S_k=\varnothing$ iff there is $L_k\le|\hat S^\circ_k|$ such that, from every $s\in\hat S_k^\circ$ and against every colluder behaviour, a knockout or END occurs within $L_k$ micro-steps with probability at least $165^{-L_k}$ (T1 Lemmas B1, B2).

**Proposition 3.5 (where endless plays live).** Let $\pi$ be a stationary, possibly randomised, profile on $\hat{\mathfrak G}_N$ (or on $\mathfrak G_N$). Almost surely on $\{T=\infty\}$, there are a random time $n_0$ and an active set $A_\infty$ with $|A_\infty|\ge2$ such that $s_n\in Z_\pi\cap\{A(s)=A_\infty\}$ for all $n\ge n_0$. Here $Z_\pi$ is the set of non-terminal states from which, under $P_\pi$, no knockout and no END is reachable.

$Z_\pi\cap\{A=A_\infty\}$ is knockout-free safe, so its image under $\Phi_{A_\infty}$ lies in $S_{|A_\infty|}$. The same holds for finite-memory profiles, on $\hat S_N\times\mathcal M$ (T1 Cor C1).

*Proof.*
- Let $Y$ be the set of non-terminal states from which a knockout or END is reachable under $P_\pi$. Let $L=|\hat S_N|$ (or $|\hat S_N\times\mathcal M|$ for finite memory) and $\delta=\varepsilon_\pi^{L}>0$, where $\varepsilon_\pi$ is the smallest positive entry of $P_\pi$. From every $s\in Y$, a knockout or END occurs within $L$ steps with probability at least $\delta$.
- Define stopping times: $\nu_1$ is the first visit to $Y$, and $\nu_{i+1}$ is the first visit to $Y$ at or after $\nu_i+L$.
- Let $E_i=\{\nu_i<\infty$, and a knockout or END occurs in $[\nu_i,\nu_i+L)\}$. Then $E_i\in\mathcal G_{\nu_{i+1}}$. By the strong Markov property (T1 Cor A1), $P(E_i\mid\mathcal G_{\nu_i})\ge\delta\,1\{\nu_i<\infty\}$.
- By Lévy's conditional Borel–Cantelli lemma (for the filtration $(\mathcal G_{\nu_{i+1}})_i$), almost surely on $\{\nu_i<\infty\ \forall i\}$ infinitely many $E_i$ occur.
- The windows are disjoint. On $\{T=\infty\}$ there are at most $N-2$ knockouts and no END, so almost surely on $\{T=\infty\}$ the set $Y$ is visited only finitely often.
- After the last visit the play is in $Z_\pi$. $Z_\pi$ is closed under $P_\pi$: a successor in $Y$, or a knockout successor, would put the state itself in $Y$. So no knockout occurs after that point, and the active set is constant.
- For each $s$ in $Z_\pi\cap\{A=A_\infty\}$, any action in the support of $\pi(\cdot|s)$ has all its successors in that set, so the set is knockout-free safe. $\square$

This replaces the old pathwise Cor 2.4(c). The pathwise version was false: a safe action may have an unrealised knockout branch.

**Remark 3.6 (reachability).**
- $E[T]=\infty$ needs $\hat C_N\cap R_N\ne\varnothing$ (Lemma 2.4(c)). This is open even for $k=N$: no steering lemma is known that shows some state of $S_N$ (or of a lower-$k$ copy, with $N-k$ knocked-out hands in $X$) is reachable from the deal.
- Example 2.5 shows that $\hat S_N\setminus R_N\ne\varnothing$. What is not known is whether $\hat C_N\setminus R_N$ can be non-empty while $C_N=\varnothing$.
- By Theorem 3.3, if T3 proved $S_2=\varnothing$, the 3–6 player question on the extended model would become exactly whether $S_3,\dots,S_N$ are empty.

## 4. Capacity and forced knockouts

**Lemma 4.1 (capacity).** Every $s\in\hat S_N\setminus F$ with $k$ active players satisfies:
- $\sum_{q\in A}|H_q|\le24k$.
- The *pool* satisfies $|D|+|X|+1=168-\sum|H_q|\ge168-24k$. That is 96, 72, 48 and 24 for $k=3,4,5,6$.
- $\sum_q(24-|H_q|)=\text{pool}-(168-24k)$.

At a draw by $q$:
- If this draw does not knock $q$ out, then $|H_q|\le23$ before it.
- At a penalty draw with $\rho$ draws still owed (this one included), if **all remaining penalty draws are knockout-free**, then $|H_q|+\rho\le24$.
- Hence, at every draw moment whose remaining draw run is knockout-free (for draw-until-playable and reveal draws, just the current draw, and $\rho:=0$): $\sum|H_q|+\max(\rho,1)\le24k$.

*Proof.* (I1), (I2), and the fact that Mercy is checked after every single card [R§5]. $\square$

**Lemma 4.2 (forced knockouts).** Let $q$ hold $h$ cards when a draw sequence starts.
- If $D=\varnothing$ at that moment, the reshuffle comes first. Let $(D^\circ,X^\circ)=(X,\varnothing)$ in that case, and $(D,X)$ otherwise.
- Nothing is played during the sequence. So $\tau$, $c$ and $X^\circ$ stay fixed, and $X^\circ$ becomes the pile if $D^\circ$ runs out.

The criteria are:
- **(a) Draw-until-playable** [R§3.2]. Let $U(Y)$ be the number of cards of $Y$ not playable on $(\tau,c)$.
  - If $D^\circ$ contains a playable card, nature can knock $q$ out iff $h+U(D^\circ)\ge24$.
  - Otherwise, nature can knock $q$ out iff $h+|D^\circ|+U(X^\circ)\ge24$. This always holds if $X^\circ$ has no playable card, because $|D^\circ|+|X^\circ|\ge23$ (Lemma 2.2(b)).
- **(b) Roulette** [R§4 Roulette]. The victim names a colour $\kappa$. The stop cards are the coloured cards of colour $\kappa$; wilds never stop the reveal. Let $U_\kappa(Y)$ be the number of non-stop cards in $Y$. The criteria are those of (a) with $U_\kappa$ in place of $U$ and "stop card" in place of "playable card". The victim is surely safe iff some $\kappa$ makes the relevant quantity at most 23.
- **(c) Penalty** [R§3.1]. Accepting $\sigma$ knocks $q$ out iff $h+\sigma\ge25$, whatever the draws.

*Proof.* By T1 Thm A, the positive-probability draw orders are all orders of $D^\circ$, followed by all orders of $X^\circ$. The sequence stops at the first playable card (in (b), the first stop card). That card enters the hand before it is played or kept, and Mercy is checked on every card [R§5]. Nature's best order puts the non-stopping cards first. This gives a peak hand of $h+U(D^\circ)+1$, or $h+|D^\circ|+U(X^\circ)+1$. A knockout occurs iff this reaches 25. $\square$

## 5. Dead cards and colour support

**Lemma 5.1.** Take a play of $\hat{\mathfrak G}_N$ that never reaches END and whose active set is constant, of size $k$.
- (i) It contains infinitely many draws, infinitely many plays and infinitely many reshuffles.
- (ii) Suppose that after some time $t_0$ no card of a set $P$ of types is ever played or shed by Discard All. Then from some time on every copy of those types lies in a hand forever. Hence $\sum_{t\in P}m(t)\le24k-1$.

*Proof.* (i)
- *Draws.* Suppose there were only finitely many draws.
  - After the last draw no accept can occur, since an accept is immediately followed by a PEN draw with $\sigma\ge2$.
  - No RCOL can occur, since it is followed by REV draws.
  - No draw-until-playable can occur.
  - So every TURN state is a Play, and WCOL/SWAP steps only follow plays.
  - Each play removes at least one card from the finite hands, and none enter. So there are finitely many steps, a contradiction.
- *Reshuffles.* A pile has at most 165 cards, so infinitely many draws force infinitely many reshuffles.
- *Plays.* Each maximal draw run (at most 23 draws, knockout-free, Lemma 4.1) is tied to a distinct play: a DUP run to its forced play, a reveal to the Roulette play, and a penalty to the last Draw-Card play before its accept (all but possibly the first penalty). So there are infinitely many plays.

(ii)
- After $t_0$, a card of type in $P$ leaves the hands only by a knockout, and there are none.
- A copy in $X$ enters $D$ at the next reshuffle. Every copy in $D$ is drawn into a hand before the following reshuffle. The top card moves to $X$ at the next play.
- By (i), after finitely many reshuffles every copy is in a hand, and stays there. At the infinitely many knockout-free draw moments, $\sum|H_q|\le24k-1$ (Lemma 4.1). $\square$

**Proposition 5.2 (colour support).** In such a play, let $S$ be the set of colours some card of which is played infinitely often. Then $36(4-|S|)\le24k-1$. So:
- $|S|\ge3$ for $k\in\{2,3\}$;
- $|S|\ge2$ for $k=4$.

*Proof.* For a colour outside $S$, its 36 cards are, after some $t_0$, neither played nor shed. A card can be shed only by a Discard All *of its own colour*, and that is itself a play of that colour [R§4 DA]. Apply Lemma 5.1(ii): $72>71$ and $108>95$. $\square$

In particular, for $k\le4$ there is no "single-colour fortress" in which, from some time on, only one colour is played. For $k=5,6$, such a fortress would have to hold all 108 off-colour cards in hands forever, leaving at most 11, respectively 35, slots at draw moments.

## 6. The funding (starvation) theorem

**Definitions.** Fix a play of $\hat{\mathfrak G}_N$.

- **Nature strategy.** A *nature strategy* is a rule that picks, at every draw, a type present in $D^*$. Every finite prefix of a play that follows it has positive probability (T1 Thm A).
- **$N^*$.** Whenever $D^*$ contains a value-0 card, draw one; the choice among value-0 types is free.
- **Owed draws $\rho(t)$.** $\rho(t)=r$ in phase PEN($r$). Otherwise $\rho(t)=\sigma+[\varphi=\mathsf{WCOL}]\,dv(\tau)$: the pending stack, including a wild Draw Card whose colour is being chosen.
- **Funding potential.** $F(t)=\sum_{q\in A}dv(H_q)+\rho(t)$.
- **Reshuffle times.** $t_1<t_2<\dots$ are the draws made with $D=\varnothing$.
- **Cycle data.** $D_j$ is the pile formed at $t_j$, and $H_j=\sum|H_q|$ at $t_j$ (before the draw). $\rho_j=\rho(t_j)$; it is 0 unless the draw at $t_j$ is a penalty draw. $n_j$ and $g_j$ are the numbers of value-0 cards and of Draw Cards in $D_j$.
- **Cycles.** *Cycle $j$* is the $|D_j|$ draws from $D_j$. It is *complete* if $t_{j+1}$ exists. *Phase 1* of cycle $j$ is its first $n_j$ draws.
- **Unfunded draws.** A draw is *unfunded* if it is made in a draw-until-playable sequence or in a Roulette reveal; the other draws are *penalty draws*. $Z_j$ counts the unfunded draws of cycle $j$, and $Z1_j$ those of phase 1.
- **Value played.** $u_j$ is the total draw value of Draw Cards played in $[t_j,t_{j+1})$, whether played normally, stacked, or forced after a draw.

**Lemma 6.1 (bookkeeping).** $F$ changes only as follows:
- $-1$ per penalty draw;
- $+dv(\text{card})$ whenever a drawn card enters a hand;
- $-dv$ of Draw Cards shed by Discard All;
- $-(\text{hand value}+\text{remaining owed draws})$ at a knockout.

Playing a Draw Card (normally, stacked, or forced; coloured, or wild through WCOL), accepting, and 0/7 hand moves leave $F$ unchanged.

*Proof.*
- A coloured Draw Card moves its value from the hand to $\sigma$ in one step.
- A wild one moves it into the WCOL term of $\rho$, then into $\sigma$.
- Accept turns $\sigma$ into PEN($\sigma$). Each penalty draw lowers $r$ by 1. At PEN(1) the next state has $\rho=0$.
- 0 and 7 permute hands [R§4]. $\square$

**Lemma 6.2 (phase-1 bound).** Suppose nature follows $N^*$ during phase 1 of cycle $j$, and all $n_j$ phase-1 draws take place with no knockout among them. Then $n_j\le F(t_j)+Z1_j$.

*Proof.*
- At the $i$-th draw of the cycle ($i\le n_j$), $D$ still contains $n_j-i+1\ge1$ value-0 cards. So $N^*$ draws a value-0 card, and no Draw Card enters a hand during phase 1.
- By Lemma 6.1, during phase 1 $F$ never increases and drops by exactly 1 per penalty draw. Since $F\ge0$, phase 1 contains at most $F(t_j)$ penalty draws.
- Every other phase-1 draw is unfunded. $\square$

**Lemma 6.3 (cycle accounting; any nature).** Suppose cycle $j$ is complete and knockout-free. Then:
- (a) $|D_j|=167-H_j$.
- (b) The number of penalty draws in cycle $j$ is $\rho_j+u_j-\rho_{j+1}$. Hence $u_j=|D_j|-Z_j-\rho_j+\rho_{j+1}$.
- (c) $F(t_{j+1})\le152-u_j+\rho_{j+1}$.

*Proof.* (a) At $t_j$, $D=\varnothing$ and $D_j=X$. By (I1), $\sum|H|+|X|+1=168$.

(b)
- At $t_j$ and $t_{j+1}$ a draw is in progress, so $\sigma=0$ by (I4′), and the owed draws are $\rho_j$ and $\rho_{j+1}$.
- In between, by Lemma 6.1, the owed draws rise by exactly $u_j$ and fall by one per penalty draw. There is no knockout and no END.
- Every draw of the cycle is either a penalty draw or unfunded.

(c)
- A card played after $t_j$ stays in $X\cup\{\tau\}$ until the reshuffle at $t_{j+1}$. So the Draw Cards played in cycle $j$ are distinct physical cards, none of them in a hand at $t_{j+1}$.
- Hence the Draw Cards in hands at $t_{j+1}$ are worth at most $152-u_j$. $\square$

**Theorem 6.4 (funding / starvation).** Assume:
- (H1) cycle $j$ is complete and knockout-free;
- (H2) phase 1 of cycle $j+1$ takes place entirely, without knockout;
- (H3) nature follows $N^*$ during phase 1 of cycle $j+1$.

Then
$$|D_j|+|D_{j+1}|\le152+g_{j+1}+\rho_j+Z_j+Z1_{j+1},$$
or equivalently
$$H_j+\rho_j+H_{j+1}+g_{j+1}+Z_j+Z1_{j+1}\ \ge\ 182.$$

*Proof.* By Lemma 6.2 at $j+1$, then Lemma 6.3(c), then Lemma 6.3(b):
$$n_{j+1}\le F(t_{j+1})+Z1_{j+1}\le152-u_j+\rho_{j+1}+Z1_{j+1}=152-|D_j|+Z_j+\rho_j+Z1_{j+1}.$$
Insert $n_{j+1}=|D_{j+1}|-g_{j+1}$ and Lemma 6.3(a). $\square$

*Meaning.* Nature shows every Draw Card of a pile only after all its non-Draw cards. The colluders must therefore pull each pile's non-Draw part with value they already hold. The value they spend in one cycle is exactly the value nature then hides at the end of the next pile.

**Corollary 6.5 (explicit constants).** Assume:
- cycles $j$ and $j+1$ are complete and knockout-free;
- nature follows $N^*$ in phase 1 of cycle $j+1$;
- $k$ players are active.

Let $b$ be the number of Draw Cards in hands at $t_{j+1}$, and $Z:=Z_j+Z1_{j+1}$. Then
$$Z\ \ge\ 182-g_{j+1}-(H_j+\rho_j+H_{j+1})\quad\text{and}\quad Z\ \ge\ \max\big(147-48k+b,\ 131-24k+b-\mathrm{maxdv}(b)\big)\ \ge\ M_k,$$
where $M_k:=\min_b$ of the right-hand side. Enumerating $b=0..36$ gives:
- **$M_2=55$**, attained at $b=4$;
- **$M_3=10$**, attained at $b=7$; for $b=0..9$ the values are 59, 50, 41, 32, 23, 18, 13, 10, 11, 12;
- for $k\ge4$ the minimum is negative ($-33$, $-75$, $-117$), so **the bound is trivial** ($Z\ge0$).

Setting $Z=0$ gives the necessary conditions in the table. The middle column is the total $H_j+\rho_j+H_{j+1}$ of *hand cards plus owed draws* at the two reshuffle moments.

| $k$ | Hand cards plus owed draws needed | Capacity $48k-1$ | Draw Cards needed in hands at $t_{j+1}$ |
|---|---|---|---|
| 2 | $\ge163$ | 95 | $b\ge17$ |
| 3 | $\ge155$ | 143 | $b\ge9$ |
| 4 | $\ge150$ (18.75 per player per moment) | 191 | $b\ge4$ |
| 5 | $\ge148$ (14.8) | 239 | $b\ge2$ |
| 6 | $\ge146$ (12.2) | 287 | none |

So $Z=0$ is impossible for $k=2,3$.

*Proof.*
- **Capacity at $t_j$.** If $\rho_j\ge1$, the draw at $t_j$ is a penalty draw by some $q$, and the penalty's remaining $\rho_j$ draws are the first draws of cycle $j$. Now $|D_j|=167-H_j\ge167-24(k-1)-|H_q(t_j)|\ge47-|H_q(t_j)|$. So if $|H_q(t_j)|+\rho_j\ge25$, then $q$ would reach 25 cards inside cycle $j$, contradicting knockout-freeness. Hence $H_j+\rho_j\le24k$ (Lemma 4.1). If $\rho_j=0$, then $H_j\le24k-1$.
- **Capacity at $t_{j+1}$.** The same argument with cycle $j+1$ gives $H_{j+1}\le24k-\max(\rho_{j+1},1)$.
- **Draw Cards.** $g_{j+1}+b\le36$.
- **First bound.** Theorem 6.4 gives the first displayed inequality. Inserting the three bounds gives $Z\ge182-(36-b)-24k-(24k-1)=147-48k+b$.
- **Second bound.** $n_{j+1}=167-H_{j+1}-g_{j+1}\ge131-24k+b+\max(\rho_{j+1},1)$. Lemma 6.2 gives $n_{j+1}\le\mathrm{maxdv}(b)+\rho_{j+1}+Z1_{j+1}$. Hence $Z\ge Z1_{j+1}\ge131-24k+b-\mathrm{maxdv}(b)$. $\square$

*Reading.* This is a **trade-off**: every missing hand slot at the two reshuffles costs one more unfunded draw. The minimum $M_3=10$ is reached only with nearly full hands at both reshuffle moments.

**Corollary 6.6 (pure-penalty plays, $N\le3$).** Consider any play of $\hat{\mathfrak G}_N$, $N\in\{2,3\}$, with any colluder behaviour. Suppose that from a reshuffle $t_j$ on nature follows $N^*$ and no unfunded draw occurs. Then the play reaches END before $t_{j+4}$ (before $t_{j+2}$ if only 2 players are active at $t_j$). Here "before $t_i$" includes the case that $t_i$ never occurs. From $t_j$, this takes at most $4\cdot258+4=1{,}036$ turns.

*Proof.*
- **Two active players at $t_j$.** If the play has not ended before $t_{j+2}$, then cycles $j$ and $j+1$ are complete. A knockout with $k=2$ ends the game [R§5], so they are also knockout-free. With $Z=0$ this contradicts Cor 6.5 ($M_2=55$).
- **Three active players at $t_j$.** The same contradiction ($M_3=10$) shows that a knockout or END occurs before $t_{j+2}$, say in cycle $i\le j+1$.
- **After the first knockout.** If the game continues, two players remain. If no further knockout occurs, Lemma 5.1(i), applied to the rest of the play, shows that $t_{i+1},t_{i+2},\dots$ exist. Cor 6.5 for cycles $i+1$ and $i+2$ then gives END before $t_{i+3}\le t_{j+4}$.
- **Turn count.** A knockout-free cycle has:
  - at most $H_j+|D_j|=167$ plays;
  - at most $\lfloor165/2\rfloor+1=83$ accepts, since every completed penalty draws at least 2 cards and at most one penalty straddles $t_{j+1}$;
  - at most 8 RCOL turns, since each Roulette is played at most once per cycle.

  That is at most 258 turns. Each of the at most two knockouts adds at most 2 turns (a TURN state without a play). $\square$

**Proposition 6.7 (necessary conditions on knockout-free safe sets).** Let $Z$ be a knockout-free safe set of $\hat{\mathfrak G}_k$, with a safe selector $a(\cdot)$, and let $s\in Z$.
- (i) Every play from $s$ that uses $a(\cdot)$ stays in $Z$. It is endless and knockout-free, and it has infinitely many reshuffles (Lemma 5.1(i)).
- (ii) **Any $k$.** At every state of $Z$ that starts a draw-until-playable sequence, the non-knockout criterion of Lemma 4.2(a) holds: $h+U(D^\circ)\le23$ (respectively $h+|D^\circ|+U(X^\circ)\le23$). At every RCOL state of $Z$, the selected colour $\kappa$ satisfies the corresponding criterion of Lemma 4.2(b). At every accept, $h+\sigma\le24$.
- (iii) **$k\in\{2,3\}$.** Along every such play in which nature follows $N^*$ from some reshuffle $t_j$ on, and for every $i\ge j$:
$$Z_i+Z1_{i+1}\ \ge\ \max\big(M_k,\ 182-g_{i+1}-(H_i+\rho_i+H_{i+1})\big),\qquad M_2=55,\ M_3=10.$$
  In particular, unfunded draws occur in every pair of consecutive cycles, and each of them happens at a state where (ii) holds.
- (iv) **Lethal window (any $k$).** In $Z$:
  - A draw-until-playable sequence can start only when $|D^\circ|\le92-h\le91$, or $|D^\circ|\le23-h$ if $D^\circ$ holds no playable card.
  - A Roulette can be played only when $|D^\circ|\le59-h_v\le58$, or $|D^\circ|\le23-h_v$ if $D^\circ$ holds no card of the named colour. Here $h_v$ is the victim's hand size.
  - A cycle starts with $|D_j|=167-H_j\ge167-24k$ cards, and the pile only shrinks within a cycle. So in every cycle:
    - no draw-until-playable sequence *starts* during the first $167-24k-91$ draws ($\ge28$ for $k=2$, $\ge4$ for $k=3$);
    - no Roulette is played during the first $167-24k-58$ draws ($\ge61$, 37 and 13 for $k=2,3,4$).
  - So unfunded sequences start only once the pile is down to 91 cards (draw-until-playable) or 58 cards (Roulette). Among the first $167-24k-91$ draws of a cycle, the only unfunded ones continue a sequence already under way at $t_j$, and there are at most 22 of them (Lemma 4.1).

*Proof.* (i) $Z$ is closed under $a$, has no END states, and admits no knockout successors. (ii) Otherwise some successor would be a knockout, by Lemma 4.2. (iii) By (i), for each $i\ge j$ cycles $i$ and $i+1$ are complete and knockout-free, and $N^*$ holds in phase 1 of cycle $i+1$. Apply Cor 6.5.

(iv)
- **Playable cards.** At most 69 cards are playable on $(\tau,c)$: the 24 wilds, the 36 cards of colour $c$, and at most $3\cdot3=9$ cards of $\tau$'s kind in other colours. If $\tau$ is coloured then $c=\mathrm{col}(\tau)$; if $\tau$ is wild there is no kind match.
- **Draw-until-playable.** By (ii), if $D^\circ$ holds a playable card then $|D^\circ|=U(D^\circ)+\#\{\text{playable in }D^\circ\}\le(23-h)+69$. Otherwise $h+|D^\circ|\le23$.
- **Roulette.** For the named colour $\kappa$, there are at most 36 stop cards, so $|D^\circ|\le(23-h_v)+36$.
- **Cycle openings.** Before the $i$-th draw of cycle $j$ the pile holds $|D_j|-i+1$ cards, and a sequence starting at that moment has $D^\circ=D$. For $i\le|D_j|-91$ the pile holds more than 91 cards, so no draw-until-playable sequence starts there. The same computation with 58 gives the Roulette statement.
- **Continuation.** A sequence that straddles $t_j$ is knockout-free, so it has at most 23 draws in all (Lemma 4.1), and at least one of them was made before $t_j$. $\square$

This replaces the old Cor 5.8. Its hypothesis class was provably empty: every $R_\pi$ contains an opening deal that forces a draw-until-playable at turn 1. Prop 6.7 is a necessary condition on knockout-free safe sets. Its hypothesis ($S_k\ne\varnothing$) is open rather than known to fail, and if some $S_k\ne\varnothing$ it constrains every such set.

## 7. What the obstructions do not exclude

- **$k\ge4$.** Theorem 6.4 can be satisfied with $Z=0$. Colluders can keep a buffer of Draw Cards and fairly large hands at reshuffles, so there is no counting contradiction.
- **$k=3$.** The required unfunded draws may be cheap. A draw-until-playable in which nature is forced to stop at once costs one draw and changes no hand size. Prop 6.7(ii) and (iv) restrict *when* unfunded draws are possible: only at low-pressure moments, and only late in a cycle. Nothing bounds how many such moments occur. So §6 does not settle $N=3$.
- **Not formalized.** The colour-skew lever (dealing penalty cards that make hands monochromatic, so that colluders run out of playable colours) and the Roulette-poison lever (feeding Roulettes into hands until one becomes a player's only playable card) are the strongest levers in the experiments. Neither is formalized.
- **Reachability** (Remark 3.6) is untouched.

## 8. Numerical experiments (evidence, not proof)

### 8.1 Checks of the proven statements

- **Lemma 2.2 (closure).**
  - Test: `t4v2/closure_test.py`. Random tuples of $\hat S_N$ were generated for $N=2..6$ in all phases, including pending stacks and PEN($r$) with $r$ up to 152. Every successor of each visited state was expanded, followed by a random walk of 30 steps.
  - Result: 245,029 states expanded, 7,180,503 successors, **0 violations** of (I1)–(I5) and 0 empty effective piles.
  - The first version of (I4′), without the WCOL term, failed this test (see §2.1).
- **Cor 6.5 constants.** Recomputed by script: $\mathrm{maxdv}(4,7,9,17)=40,58,68,100$. $M_2=55$ at $b=4$; $M_3=10$ at $b=7$; the minima for $k=4,5,6$ are $-33$, $-75$ and $-117$. The $Z=0$ thresholds are $b\ge17,9,4,2,0$, with totals 163, 155, 150, 148 and 146.
- **Theorem 6.4 and Lemma 6.2 on simulated $N^*$ cycles.**
  - Engine: `t4v2/t4e2`, option `-scheck 1`. Only knockout-free cycles within one game are used, with the next reshuffle present, after the switch to $N^*$.
  - Theorem 6.4: 731 cycle pairs (2, 7 and 32 at $N=4,5,6$, plus 690 for the retuned $N=6$ colluder; none at $N=3$, where every game died first). **0 violations**, minimum slack 2.
  - Lemma 6.2: 758 cycles, 0 violations, minimum slack **0**, so the bound is attained.

### 8.2 Colluders against uniform and adversarial decks

**Setup.**
- **Engine.** `t4v2/t4eng2.c` is the previous engine `t4/t4eng.c` with one change: the Roulette victim's colour-naming and reveal now counts as a turn, as in [R§6] and T1 §2.3. The previous tables used $T^\circ\le T\le2T^\circ$. Piles are multisets and nature picks each drawn type. Card conservation and hands of at most 24 cards are asserted after every turn.
- **Colluder.** Full-information depth-3 search with a quiescence extension for forced lines and stacks. Its evaluation combines a hand-size band, colour coverage, penalties for forced wild or Roulette plays, the knockout tests of Lemma 4.2, and a total-hand flow term.
- **Natures.** The uniform deck; $N^*$ (non-Draw cards first, otherwise uniform); and a heuristic adversary. The adversary knocks out whenever Lemma 4.2 allows it, and otherwise forces the worst playable card. In penalty draws it starves, poisons with Roulettes, and skews colours.
- **Runs.** 8 games per row, target hand 18. The adversarial deck starts at turn 2000. **All games are reported**, including those that ended before the switch.

| Deck | $N$ | Outcome |
|---|---|---|
| uniform, cap $10^5$ | 3 | 8/8 ended; mean 5,686, max 19,969 |
| uniform, cap $10^5$ | 4 | 8/8 ended; mean 13,936, max 27,782 |
| uniform, cap $10^5$ | 5 | 8/8 ended; mean 44,573, max 87,457 |
| uniform, cap $10^5$ | 6 | 7/8 ended; 1 reached the cap with 0 knockouts, 0 draw-until-playable and 0 Roulettes in $10^5$ turns (1,165 reshuffles) |
| uniform, cap $3\cdot10^4$, target 15 | 6 | 5/6 reached the cap; 1 ended at turn 90 |
| uniform, cap $3\cdot10^4$, target 18 | 6 | 4/6 reached the cap; 2 ended (7,120 and 25,754) |
| $N^*$ | 3 | 4 ended before the switch (654–1,611). The 4 alive at the switch died on average 88 turns later (max 140). |
| $N^*$ | 4 | 2 ended before the switch (35, 94). 6 died on average 174 turns after it (max 534). |
| $N^*$ | 5 | 8 died on average 398 turns after the switch (max 890) |
| $N^*$ | 6 | 8 died on average 709 turns after the switch (max 1,149); all by a forced last card |
| heuristic adversary | 3 | 2 ended before the switch (1,185, 1,634). 6 died on average 62 turns after it (max 84). |
| heuristic adversary | 4 | 1 ended before the switch (181). 7 died on average 138 turns after it (max 185). |
| heuristic adversary | 5 | 8 died on average 183 turns after the switch (max 250) |
| heuristic adversary | 6 | 8 died on average 361 turns after the switch (max 481) |
| $N^*$, retuned colluder (flow weight 60, target 20) | 6 | 1/8 reached the cap of $2\cdot10^4$, pure-penalty (0 knockouts, 0 draw-until-playable, 0 Roulettes). 7 died on average 4,592 turns after the switch (median 2,072, max 10,037). |
| heuristic adversary, retuned colluder | 6 | 8 died on average 715 turns after the switch (max 1,205) |

**How deaths happen.**
- Under $N^*$, deaths are mostly forced last cards. Of the games alive at the switch: 3 of 4 at $N=3$, and all at $N=4,5,6$. Without Draw Cards, hands shrink.
- Under the heuristic adversary, deaths are mostly Mercy knockouts.

**Traces** (`t4v2/trace_skew.txt`, `t4v2/trace_fix.txt`).
- **Skew-only adversary**, $N=6$, seed 506.
  - The first knockout (turn 2172) was **self-inflicted**. A 4-card penalty was escalated by consecutive stacks, including three Wild Draw 10s, to 58 cards, and a player with 16 cards had to accept it.
  - All four later knockouts in that game were likewise penalties that the victim could neither absorb nor pass on. Some were created by an ordinary Wild Draw 6 or Wild Draw 10 played onto a player with 20 or more cards.
- **Exact stack check.** A variant `t4v2/t4e3` scores a pending stack as lost iff no safe resolution exists (checked by exhaustive deterministic search). It did not improve survival: 0/4 at each of three settings.
  - In its trace (seed 306), the first knockout came from a forced Roulette.
  - A player held only red cards and two Roulettes while the colour was blue, so the Roulette was their only playable card.
  - Its victim (11 cards) had to reveal into a 29-card pile (10 non-Draw cards and 19 Draw Cards, many of them wild). Whatever colour the victim named, at least 13 non-stop cards remained, which is lethal by Lemma 4.2(b), since $11+13\ge24$.
  - The adversary's penalty rule prefers to deal Roulettes. The colluders' own previous move set the colour to blue.

**Interpretation.**
- With the real deck, collusion makes games last $10^4$–$10^5$ turns.
- Against adversarial decks these colluders die within hundreds of turns. The one exception is a single pure-penalty 6-player run that survived $1.8\cdot10^4$ turns of $N^*$.
- The colluders are myopic and make avoidable mistakes. So the deaths are evidence about these colluders, not about $\hat C_N$.

## 9. Conjectures (not proven)

- **Conjecture A ($N=3$; moderate confidence).** $S_2=S_3=\varnothing$, hence $\hat C_3=\varnothing$, and every 3-player profile has $E[T]\le K\,165^K$. Support:
  - Cor 6.5 and Prop 6.7: at least 10 nature-controlled unfunded draws per two cycles, and more whenever hands are not nearly full. Each must occur at a low-pressure moment in the sense of Prop 6.7(ii).
  - Prop 5.2: at least 3 colours must circulate.
  - §8: the best colluder found lasts about $6\times10^3$ turns even with the real deck.
- **$N=4,5,6$: open.** There is no counting obstruction. The adversarial levers destroy every search-based colluder we built, but those colluders demonstrably blunder. We lean weakly towards $\hat C_N=\varnothing$ for every $N$, and hence finite $E[T]$ for every profile.
- **Conjecture B (reachability).** $\hat C_N\ne\varnothing\Rightarrow\hat C_N\cap R_N\ne\varnothing$. Safe play from a state of $\hat C_N$ quickly produces "generic" positions that a real game can plausibly reach with lucky draws. We have no proof.
- **Even if $\hat C_N=\varnothing$**, the uniform-deck numbers show that collusion makes typical games last $10^4$–$10^5$ turns.


## Referee notes

### Referee 1: flawed_fixable

- Theorem 2.3 / Lemma 2.2 / Cor 2.4 use a state space that is not the one they cite. T4 says C_N and R_N 'come from T1'. But T1 sets S := R ('For G_N, S=R, so C∩R=C'), so under T1's definitions C_N ⊆ R_N and S_k ⊆ R_k. Two steps then fail. (⇐): 'Take a copy of S_k inside G_N ... so it is contained in C_N (T1 Lemma B1(ii))' needs the embedded states to lie in R_N, which is exactly the unproven steering/reachability. T4's own Remark 2.5 concedes this ('reachable only through N−k knockouts, and no general steering lemma is proven'). (⇒): the image of C* must lie in R_{k*}; this is also unproven. The document also treats 'C_N ≠ ∅' and 'C_N ∩ R_N ≠ ∅' as different statements, which is inconsistent with T1. FIX: define an extended model Ĝ_N on all tuples satisfying (I1)–(I4). This set is closed under successors, and T1 Thm D's kernel is well defined there. Take Ĉ_N and Ŝ_k as the maximal (knockout-free) safe sets of Ĝ_N and Ĝ_k. Lemma 2.2 and Thm 2.3 then hold verbatim for Ĉ_N and Ŝ_k, and C_N = Ĉ_N ∩ R_N, since R_N is closed under successors. Consequences must be restated: Ĉ_N = ∅ ⟹ E[T] < ∞ for every profile, but not conversely. Headline claim (1) must be reworded: 'nature wins iff nature can force a knockout or the end from EVERY state with ≤ N active players' holds only for Ĉ_N. 'Monotone in N' likewise holds for Ĉ_N, not for C_N ∩ R_N. Remark 2.5 also understates the gap: even for k = N, reachability of Ŝ_N from the deal is needed, not only for k < N.
- Corollary 5.8 (listed as Proven, and restated in the claimed theorem as 'Every stationary pure-penalty 3-player profile has finite E[T]') is vacuously true: no profile satisfies the hypothesis. 'Pure-penalty at every reachable state' requires that no draw-until-playable ever occurs on any reachable path. But the initial law of T1 §2.3 gives positive probability to deals where the starting player holds no card playable on the flipped number, for example seven off-colour, off-number non-wilds. So a DRAW chance state is reachable at turn 1 under every profile. The corollary must be deleted or reformulated. The only non-vacuous content available is local: from a state s from which every π-path is pure-penalty, termination is reachable. Even that does not give E[T] < ∞ unless it covers all of R_π.
- Cor 2.4(c) overclaims. Under a history-dependent safe profile, the set of states visited after the last knockout need not be a knockout-free safe set: a safe action may have knockout successors that happen not to be realised. For a STATIONARY safe policy on a finite space, a Lévy/Borel–Cantelli argument shows that almost surely the play eventually enters a knockout-free π-closed set. That is an almost-sure statement, not a pathwise one, and it is not proven in the text. Restate it that way, or drop it.
- Lemma 3.1's final line 'at every knockout-free draw moment Σ|H_q| + max(ρ,1) ≤ 24k' needs the hypothesis that the REMAINING penalty is knockout-free, not just the current draw. That hypothesis is stated in the bullet above it but dropped in the summary line. The uses in Cor 5.6 at t_j and t_{j+1} are fine, because cycles j and j+1 are assumed knockout-free.
- Lemma 5.3 should also assume that phase 1 completes, i.e. the game does not end during the first n_j draws. Theorem 5.5 needs only phase 1 of cycle j+1 to be knockout-free, not the whole cycle. Harmless over- and under-statements.
- Cor 5.7's proof silently assumes that t_{j+2}, t_{j+3}, ... exist whenever the game is still running. This needs Lemma 4.1(i), applied after the last knockout: an infinite play with a constant active set has infinitely many reshuffles. Cite it.
- The turn estimate after Cor 5.7 ('at most 167 card-removing turns plus about 96 accept turns') has an unexplained 96. Accept turns per cycle are at most about ⌊165/2⌋+1 = 83. The '~10^3 turns' conclusion still holds, but it counts only from t_j, and the time until t_j is not bounded.
- M_4 = M_5 = M_6 = 0 is really max(min_b RHS, 0). The minimum over b of the right-hand side is negative (e.g. −24 at b=9 for k=4, and more negative with larger b). Say 'the bound is trivial (Z ≥ 0)'.
- In the Cor 5.6 table, the column 'Hands needed at t_j and t_{j+1} combined' is actually H_j + ρ_j + H_{j+1}; it includes owed draws ρ_j. The 'average per player' figures inherit this.
- The plain-language §1 and the §8 support bullet say colluders 'need essentially full hands AND ≥10 unfunded draws'. The theorem gives a trade-off, Z ≥ 182 − g_{j+1} − (H_j+ρ_j+H_{j+1}): fuller hands mean fewer unfunded draws. 10 is the minimum, and only near-full hands attain it.
- Notation: k denotes both the number of active players and the Roulette colour in Lemma 3.2(b). 'A nature strategy picks one type present in D' should say D* (the effective pile), because at a reshuffle draw D = ∅.
- §7 reporting: the N* and heuristic-adversary rows report averages 'after the switch' over only the games that survived to turn 2000. In R_starve_p4, 3 of 8 games ended before the switch (turns 90, 105, 1759); in R_adv_p4, 1 of 8 did (turn 179). This is not disclosed. I recomputed the reported means from the scratch files: 156.8/329, 381.4/703, 699.25/1141, 118.4/182, 178.1/245 and 296.4/401. All match. The '574 pairs, min slack 2' and '101 cycles, min slack 0' figures match chk*.txt. I found no output file for the row 'Uniform, 6 games per target, cap 3×10^4, all survived'.

### Referee 2: correct_with_minor_fixes

- State-space convention clash in Thm 2.3 and claim (1). T4 says all notation comes from T1, but T1 fixes the state space as S := R (T1 §2.3, §5.1: 'C ∩ R = C'). Under that convention, C_N ⊆ R_N, so 'C_N ≠ ∅' and 'C_N ∩ R_N ≠ ∅' are the same statement, which contradicts Remark 2.5 and the 'NOT resolved' line. Both directions of Thm 2.3 then have a gap. (⇐) needs the embedded copy of S_k to be reachable in the N-seat game, which is exactly the steering lemma that Remark 2.5 says is missing. (⇒) needs the relabelled C* to lie in R_{k*}. Fix: define an extended model on all tuples satisfying T1 (I1)–(I4). T1 Lemma 1 shows this set is closed under transitions, and Thm D and ε ≥ 1/165 use only (I1)–(I3). Define S_k and C_N on that model. Theorem 2.3 and Cor 2.4(a,b) are then correct. Claim (1) must be restated: 'nature wins' (C_N ∩ R_N = ∅) is implied by S_2 = … = S_N = ∅ on the extended model; the converse is not proven. So 'nature wins (C_N empty) iff …' should read 'if'. Monotonicity in N holds only for the extended C_N.
- Cor 5.8 (claim (4), 'every stationary pure-penalty 3-player profile has finite E[T]') is vacuous. Every R_π contains initial deals in which the first player has no playable card. Example: top card Red 5 and a hand of 7 non-red, non-5, non-wild cards (positive probability [R§2]). That player's first turn is a draw-until-playable [R§3.2], which is an unfunded draw. So no profile is pure-penalty at every reachable state. Replace it with a pathwise statement: for k ≤ 3, along any N*-path that stays knockout-free, every pair of consecutive cycles has Z_j + Z1_{j+1} ≥ M_k. Equivalently, no closed class of a stationary or finite-memory profile, and no knockout-free safe set with its safe policy, can avoid unfunded draws along N*-paths.
- Cor 2.4(c), second sentence, overclaims. Along a single play, the tail after the last knockout stays in C_N ∩ {A = A_final}, and that set need not be knockout-free safe: a safe action may have a positive-probability knockout successor that this particular path avoids. The statement holds only almost surely. It needs an argument, e.g. outside the largest knockout-free safe subset the safe profile knocks someone out with probability at least ε^K within K steps, then Borel–Cantelli.
- The 'hands needed' column of Cor 5.6 and the per-player averages in claim (4) (18.75, 14.8, 12.2) bound H_j + ρ_j + H_{j+1}, which includes the owed draws ρ_j (up to 23). The hands themselves can be smaller by ρ_j. The text should say 'hand cards plus owed draws'.
- §1 plain words overstate the result: 'they would need to keep essentially full hands AND still take at least 10 cards'. What is proven is a trade-off, Z ≥ 182 − g_{j+1} − (H_j + ρ_j + H_{j+1}). Full hands are forced only when Z is near M_3 = 10; smaller hands are allowed with more unfunded draws.
- Lemma 5.3 should state that phase 1 of cycle j is completed, i.e. all n_j phase-1 draws take place. Thm 5.5 supplies this through 'the game has not ended before t_{j+2}', but the lemma's own statement omits it.
- The turn estimate after Cor 5.7 ('about 96 accept turns') is unexplained. A clean bound per cycle is at most 167 plays (hand cards plus draws) plus at most 82 accepts (each accept draws at least 2 cards), so about 10^3 turns over 4 cycles, as stated.
- §7 averages silently drop games. The heading says 8 games per row. N* at N = 4: the figure '157 after the switch (max 329)' averages only 5 of 8 games; three ended before the switch at turn 2000 (at 90, 105 and 1759). Heuristic adversary at N = 4: '118 (max 182)' averages 7 of 8 games; one ended at 179. I recomputed all other rows from R_*.txt and they match.
- Claim (3)'s summary drops the Discard All clause of Lemma 4.1(ii). The dead cards are those never played and never shed by Discard All. Prop 4.2 handles this correctly.
- Lemma 2.2 assumes that the two-player rules (Reverse acts as Skip; Wild Reverse Draw 4 hits its own player) follow the active count |A|. This matches T1, the simulator (G->nalive == 2) and the task statement. RULES.md only says 'With 2 players', so the assumption should be stated explicitly.

### Re-review of the repaired version: correct_with_minor_fixes

- Both earlier fatal issues are fixed. (1) Safe-set statements now live on the extended model Ŝ_N. Lemma 2.2 (closure) holds, including the WCOL in-flight term. Lemma 2.4(a) C_N = Ĉ_N ∩ R_N holds by induction on Attr_i, using succ(R_N) ⊆ R_N. Thm 3.3 is correct in both directions for Ĉ_N and S_k. The headline claims and monotonicity are stated for Ĉ_N and presented as sufficient only. Remark 3.6 notes that reachability is open even for k = N. (2) The vacuous Cor 5.8 is gone; Cor 6.6 and Prop 6.7 are pathwise or conditional statements and are not vacuous.
- Prop 6.7(iv) says 'If τ is coloured then c = col(τ)'. None of (I1)–(I5) links c to τ, so this is false on Ŝ_N. The bound of 69 playable types still holds: the kind-matches outside colour c number at most 3·3 = 9 in any case. Reword the sentence.
- Cor 6.6, 2- and 3-player steps. 'If the play has not ended before t_{j+2}, then cycles j and j+1 are complete' (and the matching 3-player step) silently uses Lemma 5.1(i). That lemma is needed to rule out an endless, knockout-free play with only finitely many reshuffles. It is cited only in the post-knockout step.
- Cor 6.6 turn bound. The bound of 258 turns per cycle is derived for knockout-free cycles. For a cycle that contains a knockout, the '+2 turns per knockout' is asserted, not derived: a penalty cut short by a knockout can consist of a single draw. The final bound of 1,036 still holds and is loose. The '8 RCOL turns' term is really 0: every Roulette forces at least one reveal draw, which is unfunded, and there are none in pure-penalty play.
- Headline item (4) 'Explicit minimum Z_j + Z1_{j+1} ≥ M_k' is listed under the main inequality's hypotheses (H1)–(H3). Cor 6.5 actually assumes the stronger hypothesis that cycle j+1 is complete and knockout-free, which it uses for the capacity bound at t_{j+1} with ρ_{j+1} owed draws. The summary should say so.
- The headline 'lethal window' is phrased in terms of 'the pile'. It is proved for the effective pile D°, which equals X when D = ∅. Make the wording match.
- Prop 3.5 cites T1 Cor A1 for the strong Markov property. Cor A1 gives only the time-homogeneous Markov property. Strong Markov at the stopping times ν_i is standard for discrete chains, but should be cited as such. For finite-memory profiles, 'the same holds' needs one more sentence: the projection of Z_π ∩ {A = A_∞} from Ŝ_N × M to Ŝ_N is knockout-free safe.
- Prop 5.2 checks only 72 > 71 (k = 3) and 108 > 95 (k = 4). The k = 2 case (capacity 47) follows a fortiori but is not stated.
- Lemma 5.1(i) cites Lemma 4.1 for 'at most 23 draws per knockout-free run'. The direct source is T1 Lemma 3(a). The closure_test.py header still says 'Lemma 1.1', the old numbering.