> Produced by a proof agent and refereed (see THEORY.md for status). Rule citations [R§k] refer to ../../RULES.md.

# T1: Foundations. UNO Show 'Em No Mercy as a finite stochastic game

**Conventions.**
- $N\in\{2,\dots,6\}$ is the number of seats, fixed throughout.
- Rules are the defaults of `uno-no-mercy/RULES.md`, cited as [R§k]. For example, [R§3.2] is §3 item 2, and [R§4 Roulette] is the Roulette row of the §4 table.
- There is no turn cap. A *turn* is as defined in [R§6]. $T\in\{1,2,\dots\}\cup\{\infty\}$ is the number of turns until the game ends.
- A *profile* is a joint rule for all decision makers, possibly colluding.

## 0. Status at a glance

| Part | Claim | Status |
|---|---|---|
| (d) | No deadlock. At least 23 cards are always drawable. Every draw run is at most 24 cards. Every turn is at most 49 micro-steps. | **Proven** (Thm D) |
| (a) | Finite controlled Markov model. Hidden, uniformly random pile order implies each drawn card is uniform over the current effective pile, given everything the decision makers know. This holds across reshuffles and set-aside cards. | **Proven** (Thm A) |
| (b) | Attractor/safety dichotomy with explicit constants $E[T]\le K\cdot165^{K}$ | **Proven** (Thm B). *Which* alternative holds is **not** decided here. |
| (b) | The task's constant $E[T]\le K/\varepsilon$ (from $P(T>nK)\le(1-\varepsilon)^n$) | **False in general.** Corrected to $K/\varepsilon^K$ (§5.5). |
| (b) | Information structures covered. Clairvoyant (deck-order-aware) profiles are excluded, but they satisfy the dichotomy on an enlarged model, with $C'\supseteq\mathrm{lift}(C)$. | **Proven** (§5.6, Prop B3). "$C=\varnothing$ but $C'\neq\varnothing$" is **open**. |
| (c) | Stationary or finite-memory profiles: $E[T]<\infty\iff P(T<\infty)=1\iff$ termination is reachable from every reachable state. Geometric tails in that case. | **Proven** (Thm C) |
| (c) | Uniformly random play: $E[T]<\infty$ iff "no trap" | Equivalence **proven**. "No trap" (Conj. E) is **open**, with strong numerical support. |

---

## 1. Cards

$\mathcal T$ has 68 types:
- **64 coloured types**: colour in $\{R,Y,G,B\}$ times kind in $\{0,\dots,9,\mathrm{D2},\mathrm{D4},\mathrm{Sk},\mathrm{SkE},\mathrm{Rev},\mathrm{DA}\}$.
- **4 wild types**: $\mathrm{WRD4},\mathrm{WD6},\mathrm{WD10},\mathrm{WCR}$ (Wild Colour Roulette).

Multiplicities $m(t)$ [R§1]:
- 2 for each number (0 included);
- 3 each of D2, Sk, Rev, DA per colour;
- 2 each of D4, SkE per colour;
- 8 WRD4, 4 WD6, 4 WD10, 8 WCR.

This gives $\sum_t m(t)=168$.

Draw values $dv$ [R§1]: D2 = 2, D4 = 4, WRD4 = 4, WD6 = 6, WD10 = 10, and 0 for every other type (WCR is not a Draw Card). The total over the deck is

$$\sum_t m(t)\,dv(t)=12\cdot2+8\cdot4+8\cdot4+4\cdot6+4\cdot10=152.$$

$\mathrm{col}(t)$ is the colour of a coloured card and $W$ for a wild.

## 2. The micro-state model $\mathfrak G_N$

### 2.1 States

A micro-state is $s=(A,H,D,X,\tau,c,p,d,\sigma,v,\varphi)$, where:

- $A\subseteq[N]$ is the set of active seats.
- $H=(H_q)_{q\in[N]}$ are the hands, as multisets over $\mathcal T$, with $H_q=\varnothing$ for $q\notin A$.
- $D$ is the draw-pile multiset.
- $X$ is the multiset of the discard pile *below the top card* plus all set-aside (knocked-out) hands (Remark 2.1).
- $\tau\in\mathcal T$ is the top card, and $c\in\{R,Y,G,B\}$ is the colour in play.
- $p\in A$ is the seat to act, and $d\in\{\pm1\}$ is the direction.
- $\sigma\in\{0,\dots,152\}$ is the pending penalty, and $v\in\{0,2,4,6,10\}$ is the value of the last Draw Card in the pending stack.
- $\varphi$ is the phase, one of $\mathsf{TURN}$, $\mathsf{DRAW}$, $\mathsf{PEN}(r)$ with $1\le r\le152$, $\mathsf{WCOL}$, $\mathsf{SWAP}$, $\mathsf{RCOL}$, $\mathsf{REV}(k)$ with $k$ a colour, or $\mathsf{END}$.

**Remark 2.1 (set-aside cards).** A knocked-out hand is "set aside ... until the deck runs out and needs to be reshuffled", when it joins the discard pile [R§5]. The rules use the discard pile below the top only at a reshuffle [R§5, last bullet]. So every transition depends on the pair (discard below the top, set-aside) only through their multiset sum.

The finer model that keeps them separate is also finite and Markov, by the same proofs. Merging is an exact lumping: the coarse kernel is a function of the coarse state. Strategies may still use the finer information, since it is part of the history (§4). The simulator does exactly this merge (`eliminate`, `elim_cards=2`).

**Notation.**
- $\mathrm{nx}(q,d)$ is the first seat $q+jd \bmod N$ ($j\ge1$) that lies in $A$. It is defined whenever $A\setminus\{q\}\neq\varnothing$. Eliminated players are skipped [R§5].
- **Playable** [R§3.2, R§3.3]: $\mathrm{pl}(t)$ holds iff $t$ is wild, or $\mathrm{col}(t)=c$, or ($\tau$ is coloured and $\mathrm{kind}(t)=\mathrm{kind}(\tau)$). Write $P(s)=\{t\in\operatorname{supp}H_p:\mathrm{pl}(t)\}$.
- **Stackable** [R§3.1]: $dv(t)\ge v$. Since $v\ge2$ whenever $\sigma>0$, only Draw Cards qualify. Colour is irrelevant.
- **Effective pile**: $D^*=D$ if $D\neq\varnothing$. Otherwise $D^*=X$; this is the reshuffle of the discard pile minus its top, together with the set-aside cards [R§5].

### 2.2 Actions and transitions

Every state has a finite action set $A(s)$ and a kernel $p(\cdot\mid s,a)$. At decision states the successor is deterministic. Chance states have $A(s)=\{*\}$.

**Play $t$ by $p$.**
1. Remove one $t$ from $H_p$, put the old $\tau$ into $X$, and set $\tau:=t$.
2. If $\mathrm{kind}(t)=\mathrm{DA}$, move every other card of colour $\mathrm{col}(t)$ from $H_p$ to $X$ [R§4 DA].
3. If $H_p=\varnothing$, go to END; the win is immediate and no effect is applied [R§3.4, R§4 DA].
4. Otherwise:
   - if $t$ is coloured, set $c:=\mathrm{col}(t)$ and apply $\mathrm{Eff}(t)$;
   - if $t\in\{\mathrm{WRD4},\mathrm{WD6},\mathrm{WD10}\}$, go to WCOL;
   - if $t=\mathrm{WCR}$, go to RCOL.

**$\mathrm{Eff}(t)$** for the card $t=\tau$ played by $p$. "TURN($q$)" means set $p:=q$ and $\varphi:=\mathsf{TURN}$.

| $t$ | effect | source |
|---|---|---|
| 1–6, 8, 9 | TURN(nx$(p,d)$) | [R§4] |
| 0 | $H'_{\mathrm{nx}(q,d)}:=H_q$ for all $q\in A$; TURN(nx$(p,d)$) | [R§4 0], [R§5] |
| 7 | go to SWAP | [R§4 7] |
| Skip | TURN(nx(nx$(p,d),d$)) | [R§4] |
| Skip Everyone | TURN($p$) | [R§4] |
| Reverse | $d:=-d$; TURN($p$) if $\lvert A\rvert=2$, else TURN(nx$(p,d)$) | [R§4] |
| Discard All | TURN(nx$(p,d)$) | [R§4] |
| D2, D4, WD6, WD10 | $\sigma\mathrel{+}=dv(t)$, $v:=dv(t)$; TURN(nx$(p,d)$) | [R§4], [R§3.1] |
| WRD4 | $\sigma\mathrel{+}=4$, $v:=4$, $d:=-d$; TURN($p$) if $\lvert A\rvert=2$ (also when played into a stack), else TURN(nx$(p,d)$) | [R§4 WRD4] |

**Draw for $q$** (chance).
1. If $D=\varnothing$, reshuffle: $D:=X$, $X:=\varnothing$ [R§5].
2. Draw type $t$ with probability $D(t)/|D|$. Remove it from $D$ and add it to $H_q$.
3. If now $|H_q|=25$, $q$ is knocked out immediately [R§5 Mercy, checked mid-draw]:
   - $A:=A\setminus\{q\}$, $X:=X+H_q$, $H_q:=\varnothing$;
   - if $|A|=1$, go to END [R§5];
   - otherwise go to TURN(nx$(q,d)$).
4. Otherwise continue as the phase prescribes.

**Phase table.**

| state | type | moves |
|---|---|---|
| TURN, $\sigma>0$ | decision | *accept*: $r:=\sigma$, $\sigma:=v:=0$, go to PEN($r$). Or *stack* any $t\in\operatorname{supp}H_p$ with $dv(t)\ge v$, then Play $t$. Stacking is optional [R§3.1]. |
| TURN, $\sigma=0$, $P(s)\ne\varnothing$ | decision | play any $t\in P(s)$ (strict must-play) [R§3.2] |
| TURN, $\sigma=0$, $P(s)=\varnothing$ | chance | Draw for $p$. If the drawn $t$ is playable, Play $t$ (forced: "Then, play that card" [R§3.2]); else go to DRAW. |
| DRAW | chance | same as the previous row |
| PEN($r$) | chance | Draw for $p$; then PEN($r-1$) if $r>1$, else TURN(nx$(p,d)$) [R§3.1] |
| WCOL | decision | choose colour $k$: $c:=k$, then apply Eff($\tau$) [R§3.3] |
| SWAP | decision | choose $r\in A\setminus\{p\}$: swap $H_p$ and $H_r$; TURN(nx$(p,d)$) [R§4 7] |
| RCOL | decision, made by the victim nx$(p,d)$ | choose $k$: $c:=k$, $p:=\mathrm{nx}(p,d)$, go to REV($k$) [R§4 Roulette] |
| REV($k$) | chance | Draw for $p$ (the victim). If $\mathrm{col}(t)=k$, go to TURN(nx$(p,d)$); else stay. Wilds never count [R§4 Roulette]. |
| END | absorbing | $F:=\{\varphi=\mathsf{END}\}$ |

### 2.3 Initial law, terminal set, turn count

The initial law $\mu_0$ [R§2]:
1. Shuffle the 168 cards uniformly and deal 7 to each seat.
2. Flip cards from the pile until the first number card. Flipped action or wild cards go to $X$ with no effect. The number card becomes $\tau$, and $c:=\mathrm{col}(\tau)$.
3. The dealer $\delta$ is uniform on the seats. Set $p:=\delta+1 \bmod N$, $d:=+1$, $A:=[N]$, $\sigma=v=0$, $\varphi=\mathsf{TURN}$.

The flip always succeeds: at most $7N\le42$ number cards are dealt, so at least $80-42=38$ number cards remain in the pile.

Define $M:=\tau_F=\inf\{n:s_n\in F\}$, the number of micro-steps. Define $T:=\#\{n<\tau_F:\varphi(s_n)=\mathsf{TURN}\}$. This is exactly [R§6]: Skip Everyone and 2-player go-agains are separate turns, and skipped players get none. It is also what `sim/nomercy.c` counts in `take_turn`.

### 2.4 Invariants, finiteness, short turns

**Lemma 1 (invariants).** Every reachable state satisfies:
- **(I1)** $\sum_{q\in A}H_q+D+X+\{\tau\}=m$ (card conservation).
- **(I2)** $|H_q|\le24$ for $q\in A$, and $H_q=\varnothing$ for $q\notin A$.
- **(I3)** If $\varphi\ne\mathsf{END}$, then $|A|\ge2$, $p\in A$, and $|H_q|\ge1$ for all $q\in A$.
- **(I4)** $\sigma\le152$, and $v=0\iff\sigma=0$. In every chance phase $\sigma=0$.

*Proof.* Induction over transitions.

(I1): every move relocates cards.

(I2): hand sizes change only by
- drawing, which adds 1 and knocks out at exactly 25;
- playing or Discard All, which subtract;
- the 0-rotation and the 7-swap, which permute sizes among active players.

Initially every hand has 7 cards.

(I3):
- $A$ shrinks only by knockouts, and $|A|=1$ leads to END.
- A hand becomes empty only through Play, which then leads to END.
- Rotation and swap permute nonempty hands.
- Every next-player assignment uses nx, whose value lies in $A$, or keeps the current $p\in A$. In REV, $p$ is the victim, who is in $A$.

(I4):
- $\sigma>0$ arises only from Draw-Card plays. While $\sigma>0$, the only moves are stack plays, colour choices, or *accept*, and accept resets $\sigma$ to 0. So no card enters any hand between the moment $\sigma$ becomes positive and its reset.
- Hence the Draw Cards that build one stack are distinct physical cards, and $\sigma\le152$.
- Chance phases arise only from TURN with $\sigma=0$, from accept (which sets $\sigma=0$), or from a Roulette. A Roulette is playable only at $\sigma=0$, because $dv(\mathrm{WCR})=0$. $\square$

**Lemma 2 (finiteness).** Count as follows:
- The copies of each type are placed among $N+2$ locations ($N$ hands, $D$, $X$).
- Multiply by 68 top types, $2^N$ active sets, 4 colours, $N$ seats, 2 directions, 153 values of $\sigma$, 5 values of $v$, and 162 phases.

This gives

$$|S|\le 68\cdot2^N\cdot4N\cdot2\cdot153\cdot5\cdot162\prod_t\binom{m(t)+N+1}{N+1}.$$

The bound is $10^{85.1}$, $10^{99.4}$, $10^{111.5}$, $10^{121.9}$, $10^{131.0}$ for $N=2,\dots,6$ (computed exactly), so $|S|<10^{132}$.

**Lemma 3 (short runs and turns).**
- (a) Any maximal run of consecutive draws by one player (a DRAW sequence, a penalty, or a Roulette reveal) has at most 24 draws.
- (b) Every turn (the micro-steps from a TURN state up to the next TURN state or END) has at most 49 micro-steps.
- (c) Hence $T\le M\le49T$, and $M=\infty\iff T=\infty$.

*Proof.* (a) By (I3) the drawer holds at least 1 card when the run starts. Each draw adds one card, and reaching 25 knocks the drawer out, which ends the run.

(b) Enumerate the cases from TURN:
- stack a coloured card: 1 step;
- stack a wild: 2 steps (TURN, WCOL);
- accept: $1+\le24$ steps;
- play: 1, plus at most 1 for WCOL, SWAP or RCOL, plus at most 24 REV draws;
- nothing playable: at most 24 draws (the first is the TURN step), then at most 1 decision, then at most 24 REV draws.

The maximum is $24+1+24=49$.

(c) Each turn contains at least 1 and at most 49 micro-steps, and every micro-step before absorption belongs to a turn. $\square$

## 3. (d) No deadlock

**Theorem D.** Let $s$ be a reachable non-terminal state. Then:
- **(i)** $A(s)\neq\varnothing$.
- **(ii)** If $s$ is a chance state, then $D^*\neq\varnothing$. In fact $|D|+|X|=167-\sum_{q\in A}|H_q|\ge167-24|A|\ge23$, and $|D^*|\le165$.
- **(iii)** nx, the victim, and the set of swap targets are well defined.
- **(iv)** Every draw run ends within 24 draws, and every turn within 49 micro-steps.

Hence the rules define a unique successor distribution at every reachable non-terminal state. All its successors again satisfy (I1)–(I4).

*Proof.*

(i):
- At TURN with $\sigma>0$, *accept* is always legal, since stacking is optional [R§3.1].
- At TURN with $\sigma=0$, either $P(s)\ne\varnothing$ or the state is a chance state.
- WCOL and RCOL each have 4 colours.
- SWAP has $A\setminus\{p\}\neq\varnothing$ by (I3).

(ii) (I1) gives $|D|+|X|=167-\sum_A|H_q|$. By (I2) this is at least $167-24\cdot6=23$. By (I3), $\sum_A|H_q|\ge2$, so $|D^*|\le|D|+|X|\le165$. The count holds at every single draw, including mid-sequence, because (I2) holds before each draw.

(iii) $|A|\ge2$ by (I3). After a knockout, either $|A|=1$ (END) or nx is defined.

(iv) Lemma 3.

This is the "derived fact" of [R§5], made precise. The draw and discard piles can never run dry together, because some player must reach 25 cards first. $\square$

## 4. (a) Markov property with a hidden, uniformly random pile order

**Physical model.** Label the cards $1,\dots,168$, with type map $\mathrm{ty}$.

A *configuration* $\hat s$ records the location of every labelled card (a hand, the pile set, $X$, or the top), together with $(c,p,d,\sigma,v,\varphi)$. It does **not** record the internal order $\omega$ of the pile. $\omega$ is a bijection $\{1..|D|\}\to D$, with $\omega(1)$ the top card of the pile.

The dynamics are those of §2, except that a draw removes $\omega(1)$. If $D=\varnothing$ at a draw, $\omega$ is first replaced by a fresh ordering of $X$.

Randomness is carried by the following objects, all mutually independent:
- $\Pi_0$, uniform over orderings of all 168 cards;
- for each $j\ge1$ and each nonempty $Z\subseteq[168]$, $\Pi_{j,Z}$, uniform over orderings of $Z$;
- the dealer $\delta$;
- i.i.d. $\xi_0,\xi_1,\dots$, which carry all strategy randomisation, including an initial mixed-strategy draw in $\xi_0$ and correlated coalition coins.

The $j$-th reshuffle, if it shuffles the set $Z$, uses $\Pi_{j,Z}$.

Let $\mathcal G_n:=\sigma(\delta,\hat s_0,\dots,\hat s_n,\xi_0,\dots,\xi_n)$. This is the entire past of the game at card level: every hand of every player, the discard and set-aside contents, physical identities, all past actions (functions of these) and all coins. A profile is **non-anticipating** if each action $a_n$ (a labelled card, a colour, or a target) is $\mathcal G_n$-measurable. This dominates every coalition's information that does not include looking at undrawn cards.

**Lemma A0.** Let $\omega$ be a uniform ordering of a finite set $Z$ with $|Z|=k$. Then $\omega(1)$ is uniform on $Z$. Given $\omega(1)=x$, the rest $(\omega(2),\dots,\omega(k))$ is uniform over orderings of $Z\setminus\{x\}$.

*Proof.* $P(\omega(1)=x,\text{rest}=\rho)=1/k!=\frac1k\cdot\frac1{(k-1)!}$. $\square$

**Lemma A0′.** Suppose $\omega$ is conditionally uniform given $\mathcal G$, and $\xi$ is independent of $\sigma(\mathcal G,\omega)$. Then $\omega$ is conditionally uniform given $\mathcal G\vee\sigma(\xi)$.

*Proof.* For $B\in\mathcal G$ and $E\in\sigma(\xi)$:

$$P(\{\omega=\rho\}\cap B\cap E)=P(\{\omega=\rho\}\cap B)P(E)=E[1_BP(\omega=\rho|\mathcal G)]P(E)=E[1_B1_EP(\omega=\rho|\mathcal G)].$$

A $\pi$–$\lambda$ argument extends this to all of $\mathcal G\vee\sigma(\xi)$. $\square$

**Theorem A.** Under any non-anticipating profile, for every $n$, $P(\omega_n=\rho\mid\mathcal G_n)=1/|D_n|!$ for every ordering $\rho$ of $D_n$. Consequently:

1. At a chance step, the drawn card is uniform on $D^*_n$ given $\mathcal G_n$, and its type is $t$ with probability $D^*_n(t)/|D^*_n|$. This holds with or without a reshuffle, and whatever cards have been set aside.
2. With $s_n$ the type-level projection of $\hat s_n$ and $\bar a_n$ the type-level action,
$$P(s_{n+1}=s'\mid\mathcal G_n)=p(s'\mid s_n,\bar a_n).$$
So $(s_n,\bar a_n)$ is an *admissible play* of $\mathfrak G_N$ in the sense of §5.

*Proof.* Induction on $n$.

**Base case.** The deal and the flip consume a prefix of $\Pi_0$. Its length $k$ is determined by the prefix itself, because the flip stops at the first number card. For a complete deal-and-flip record $x=(x_1..x_k)$ and any ordering $\rho$ of the complement, $P(\Pi_0=(x,\rho))=1/168!$. So given the prefix, $\omega_0$ is uniform. $\hat s_0$ is a function of (prefix, $\delta$), and $\delta$ and $\xi_0$ are independent. The complement set $D_0$ is $\hat s_0$-measurable. So conditioning on the coarser $\mathcal G_0$ mixes identical uniform laws, and $\omega_0$ stays uniform.

**Step, decision move or deterministic update.** $\omega_{n+1}=\omega_n$. $\hat s_{n+1}$ is a function of $(\hat s_n,a_n)$, which is $\mathcal G_n$-measurable. $\xi_{n+1}$ is independent of $\sigma(\mathcal G_n,\omega_n)$. Apply Lemma A0′.

**Step, draw with $D_n\ne\varnothing$.** The new information is $x=\omega_n(1)$, plus $\xi_{n+1}$. By Lemma A0 applied conditionally on $\mathcal G_n$, $x$ is uniform on $D_n$. Given $(\mathcal G_n,x)$, the rest of the pile is uniform over orderings of $D_n\setminus\{x\}$. Then apply Lemma A0′ for $\xi_{n+1}$. A knockout only moves hand cards into $X$ and does not touch $\omega$.

**Step, draw with $D_n=\varnothing$.** The index $j$ of this reshuffle and the set $Z=X_n$ are $\mathcal G_n$-measurable. $\Pi_{j,Z}$ is independent of $\mathcal G_n\subseteq\sigma(\Pi_0,(\Pi_{i,\cdot})_{i<j},\delta,\xi_{0..n})$. So given $\mathcal G_n$, the new order is uniform on orderings of $Z$. This covers the set-aside cards, which are in $Z$. Then proceed as in the previous case.

**Consequence 2.** The type-level successor is a deterministic function of $(s_n,\bar a_n)$ at decision states, and of $(s_n,\mathrm{ty}(\text{drawn card}))$ at chance states. Which physical copy of a type is played does not affect the type-level successor. $\square$

**Corollaries.**
- **(A1)** For a stationary type-level policy $\pi$, $(s_n)$ is a time-homogeneous Markov chain on $S$ with kernel $P_\pi(s,s')=\sum_a\pi(a|s)p(s'|s,a)$.
- **(A2) Implementation equivalence.** The pre-shuffled pile read from the top (`sim/nomercy.c`) and on-demand sampling without replacement (`crosscheck/ref_nomercy.py`) produce the same law of the type-level trajectory, provided no policy reads the pile order. In `nomercy.c`, `G->pile` is accessed only in `reshuffle`, `eliminate`, `draw_one`, `game_init` and `check_invariants`, and never in any `choose_*` or score function. So all simulator policies are non-anticipating.
- **(A3)** Everything that must be in the state is listed in §2.1. Dropping $\sigma$, $v$, the phase or the pile/discard split would break the Markov property. The order of $X$ is irrelevant, because reshuffles are uniform.
- A variant with an *eager* reshuffle (at the moment the pile empties) gives another finite model of the same kind. Lemma A0/A0′ apply unchanged because the reshuffle time is $\mathcal G$-measurable.

## 5. (b) The attractor/safety dichotomy

### 5.1 Abstract setting

A finite MDP is $\mathfrak M=(S,F,A(\cdot),p,\mu_0)$, with terminal states absorbing and $\mathrm{succ}(s,a)=\{s':p(s'|s,a)>0\}$.

An **admissible play** consists of:
- a filtered probability space $(\Omega,(\mathcal G_n),P)$;
- adapted processes $s_n$ and $a_n\in A(s_n)$, with $s_0\sim\mu_0$;
- the property $P(s_{n+1}=s'|\mathcal G_n)=p(s'|s_n,a_n)$.

By Theorem A, every non-anticipating profile of the physical game yields an admissible play of $\mathfrak G_N$. This covers history-dependent, randomised, correlated and full-information profiles, and the intra-turn decisions (WCOL, SWAP, RCOL) are separate micro-states.

$R$ is the set of states reachable by a chain $s_0\in\operatorname{supp}\mu_0$, $s_{i+1}\in\mathrm{succ}(s_i,a_i)$.

Define $\varepsilon:=\min\{p(s'|s,a)>0:s\in R\setminus F\}$. For $\mathfrak G_N$, decision transitions have probability 1 and draws have probability $D^*(t)/|D^*|\ge1/165$ by Thm D(ii). So $\varepsilon\ge1/165$.

**Lemma B0.** In every admissible play, $s_n\in R$ for all $n$, almost surely.

*Proof.* Induction on $n$: a positive-probability successor lies in $\mathrm{succ}$. $\square$

### 5.2 Attractor and safe set

Let $\mathrm{Attr}_0=F$ and

$$\mathrm{Attr}_{i+1}=\mathrm{Attr}_i\cup\{s\notin F:\forall a\in A(s),\ \mathrm{succ}(s,a)\cap\mathrm{Attr}_i\ne\varnothing\}.$$

Let $\mathrm{Attr}=\bigcup_i\mathrm{Attr}_i$, $\mathrm{rank}(s)=\min\{i:s\in\mathrm{Attr}_i\}$, and $C:=S\setminus\mathrm{Attr}$.

A set $Z\subseteq S\setminus F$ is **safe** if every $s\in Z$ has some $a$ with $\mathrm{succ}(s,a)\subseteq Z$. For a chance state this means *all* its successors lie in $Z$.

**Lemma B1.**
- (i) $C$ is safe.
- (ii) Every safe set is contained in $C$, so $C$ is the largest safe set.
- (iii) $C\cap R$ is the largest safe subset of $R$.
- (iv) Every $s\in R\cap\mathrm{Attr}$ has $\mathrm{rank}(s)\le|R\setminus F|$.

*Proof.*

(i) The sequence $\mathrm{Attr}_i$ increases in a finite set, so it stabilises at some $i^*$. For $s\in C$ we have $s\notin\mathrm{Attr}_{i^*+1}$, so some $a$ has $\mathrm{succ}(s,a)\cap\mathrm{Attr}=\varnothing$, that is, $\mathrm{succ}(s,a)\subseteq C$.

(ii) Show $Z\cap\mathrm{Attr}_i=\varnothing$ by induction. It holds at $i=0$ because $Z\cap F=\varnothing$. If $s\in Z\cap\mathrm{Attr}_{i+1}$, the safe action's successors lie in $Z$, which is disjoint from $\mathrm{Attr}_i$ by induction. This contradicts the definition of $\mathrm{Attr}_{i+1}$.

(iii) $\mathrm{succ}$ maps $R$ into $R$. So $C\cap R$ is safe, and any safe subset of $R$ lies in $C$ by (ii).

(iv) Because $\mathrm{succ}(R)\subseteq R$, the sets $\mathrm{Attr}_i\cap R$ satisfy the same recursion inside $R$. Each strict increase adds a state of $R\setminus F$. $\square$

### 5.3 The forcing lemma

**Lemma B2.** In every admissible play, for all $n$ and $r\ge0$: on $\{\mathrm{rank}(s_n)\le r\}$,

$$P(\tau_F\le n+r\mid\mathcal G_n)\ge\varepsilon^{r}.$$

*Proof.* Induction on $r$. The case $r=0$ is trivial.

Suppose $\mathrm{rank}(s_n)=r\ge1$ ($s_n\in R$ by B0). For the realised $a_n$, and whatever randomisation produced it, pick measurably $s'\in\mathrm{succ}(s_n,a_n)\cap\mathrm{Attr}_{r-1}$. Then $P(s_{n+1}\in\mathrm{Attr}_{r-1}|\mathcal G_n)\ge p(s'|s_n,a_n)\ge\varepsilon$. By the tower property and the induction hypothesis at time $n+1$:

$$P(\tau_F\le n+r|\mathcal G_n)\ge E\big[1\{s_{n+1}\in\mathrm{Attr}_{r-1}\}\,\varepsilon^{r-1}\mid\mathcal G_n\big]\ge\varepsilon^r.$$

If the rank is less than $r$, use the induction hypothesis together with $\varepsilon^{r-1}\ge\varepsilon^r$. $\square$

At decision states every action descends, so they contribute a factor of 1. Only chance steps cost a factor of at least $1/165$.

### 5.4 The dichotomy

**Theorem B.** Exactly one of the following holds.

**(A) $C\cap R=\varnothing$.** Let $K:=\max_{s\in R}\mathrm{rank}(s)\le|R\setminus F|<10^{132}$. Then every admissible play (every non-anticipating profile) satisfies

$$P(\tau_F>jK)\le(1-\varepsilon^K)^j,\qquad E[T]\le E[\tau_F]\le K\varepsilon^{-K}\le K\cdot165^{K}.$$

Also $P(T>t)\le(1-165^{-K})^{\lfloor t/K\rfloor}$. From every reachable state, against every profile, nature ends the game within $K$ micro-steps with probability at least $165^{-K}$.

**(B) $C\cap R\ne\varnothing$.** There is a stationary deterministic policy under which $P(T=\infty)>0$, and hence $E[T]=\infty$. This is a pure profile in which each decision maker's choice is a function of the full current state, which requires knowing all hands.

*Proof.*

(A) By B0 and B1, every visited state has rank at most $K$. Apply B2 at time $jK$ on $\{\tau_F>jK\}$:

$$P(\tau_F>(j+1)K)=E\big[1\{\tau_F>jK\}P(\tau_F>(j+1)K|\mathcal G_{jK})\big]\le(1-\varepsilon^K)P(\tau_F>jK).$$

Then $E[\tau_F]=\sum_{m\ge0}P(\tau_F>m)\le K\sum_j(1-\varepsilon^K)^j=K\varepsilon^{-K}$. Finally $T\le\tau_F$ by Lemma 3.

(B) Take a shortest chain $s_0\to\dots\to s_k$ from $\operatorname{supp}\mu_0$ into $C\cap R$, with actions $a_i$. Its states are distinct and $s_0,\dots,s_{k-1}\notin C$. Define $\pi(s_i)=a_i$ for $i<k$, let $\pi(s)$ be a safe action on $C$, and choose $\pi$ arbitrarily elsewhere.

With probability at least $\mu_0(s_0)\prod_ip(s_{i+1}|s_i,a_i)>0$ the chain is followed. After that, every step stays in $C\subseteq S\setminus F$ surely. So $\tau_F=\infty$, and $T=\infty$ by Lemma 3.

Exclusivity is immediate. $\square$

**Remark.** In case (A), $\sup E[T]$ over all non-anticipating profiles is finite, at most $K\,165^K$. By standard transient/stochastic-shortest-path MDP theory, it is attained by a stationary deterministic full-information profile solving the Bellman equation $V(s)=1\{\varphi(s)=\mathsf{TURN}\}+\max_a\sum_{s'}p(s'|s,a)V(s')$ with $V|_F=0$ (Bertsekas–Tsitsiklis 1991; Puterman ch. 7). This is cited, not re-proved here.

### 5.5 Correction to the constant in the task statement

The claim "$P(T>nK)\le(1-\varepsilon)^n$, $E[T]\le K/\varepsilon$" is false in general.

**Counterexample.** Take states $1..K$ plus terminal state 0. From state $i$, move to $i-1$ with probability $\varepsilon$ and to $K$ with probability $1-\varepsilon$. Then:
- $C=\varnothing$, and $\mathrm{rank}(i)=i$;
- but $E_K[\tau]=(1-\varepsilon^K)/((1-\varepsilon)\varepsilon^K)$.

For $\varepsilon=1/2$ and $K=10$, $E_K[\tau]=2046>K/\varepsilon=20$; this was checked by an exact linear solve. It is at most $K/\varepsilon^K=10240$, as Theorem B says. Forcing needs up to $K$ consecutive favourable chance outcomes, which costs $\varepsilon^K$, not $\varepsilon$.

### 5.6 Which information structures are covered

1. **Covered by (A)**: every profile whose decisions are measurable with respect to the past of the game plus randomness independent of the shuffles. This includes:
   - collusion and communication;
   - full knowledge of every hand, and of the discard and set-aside contents;
   - physical card identities;
   - unbounded memory;
   - correlated or mixed randomisation.

   It also covers the real imperfect-information game, which is a special case.

   **Generalisation.** Lemma B2 uses only two facts: successors stay in $\mathrm{succ}$, and each $s'\in\mathrm{succ}(s_n,a_n)$ has conditional probability at least $\varepsilon_0$. So (A) also holds, with $\varepsilon$ replaced by $\varepsilon_0$, for any imperfect shuffle or partially informed play in which every card type present in $D^*$ has conditional probability at least $\varepsilon_0$ of being drawn next.

2. **Not covered**: *anticipating* information, meaning any knowledge of the order of undrawn cards. Examples are peeking, marked or stacked decks, and a bot reading a simulator's RNG state. Then conditional draw probabilities can be 0 or 1, and Lemma B2 fails.

**Proposition B3 (clairvoyant model).** Let $S'=\{(s,w)\}$, where $w$ is the type sequence of the pile, top first. Then:
- $S'$ is finite, and nature moves only at reshuffles. Each type sequence has probability $\prod_tX(t)!/|X|!\ge1/165!$.
- Clairvoyant non-anticipating profiles are admissible plays of this model, so Theorem B holds there with $\varepsilon'\ge1/165!$ and a safe set $C'$.
- $\mathrm{lift}(C):=\{(s,w):s\in C\}$ is safe. At a decision the order is unchanged. The drawn top type, or any reshuffled order, projects to a positive-probability successor of $s$, which lies in $C$.
- Every $s\in R$ has a reachable lift: choose orders consistent with the draws along a witnessing path.

Hence $C\cap R\ne\varnothing$ implies $C'\cap R'\ne\varnothing$. The converse is not claimed. $C\cap R=\varnothing$ does **not** by itself give finite $E[T]$ against clairvoyant coalitions; that would need the separate computation on $S'$.

## 6. (c) Stationary and finite-memory policies

**Theorem C.** Let $\pi$ be stationary and possibly randomised: $\pi(\cdot|s)$ is a distribution on $A(s)$. Let $R_\pi$ be the set of states reachable from $\operatorname{supp}\mu_0$ under $P_\pi$. The following are equivalent:
1. $E[T]<\infty$;
2. $P(T<\infty)=1$;
3. for every $s\in R_\pi$, $F$ is reachable from $s$ under $P_\pi$.

Under (3), with $k_\pi=|R_\pi\setminus F|$ and $\varepsilon_\pi=$ the minimum positive entry of $P_\pi$ on $R_\pi$ (which is at least $\min(1/165,\min_{\pi(a|s)>0}\pi(a|s))$):

$$P(T>t)\le P(\tau_F>t)\le(1-\varepsilon_\pi^{k_\pi})^{\lfloor t/k_\pi\rfloor}.$$

*Proof.*

(1)⇒(2) is trivial.

(2)⇒(3): if some $s\in R_\pi$ cannot reach $F$, the chain hits $s$ with positive probability and then never absorbs. So $P(\tau_F=\infty)>0$, and $P(T=\infty)>0$ by Lemma 3.

(3)⇒(1) with the tail bound: by Corollary A1, the chain is an admissible play of the single-action MDP with kernel $P_\pi$. Its attractor is exactly the set of states from which $F$ is reachable under $P_\pi$. (3) says $R_\pi\subseteq$ this attractor. Theorem B(A) then applies with $K\le k_\pi$ and $\varepsilon=\varepsilon_\pi$. $\square$

**Corollary C1 (finite memory).** A policy run by a finite automaton with memory $m\in\mathcal M$ gives a Markov chain on $S\times\mathcal M$. The same equivalence and geometric tail hold. So for stationary or finite-memory profiles, $E[T]=\infty$ happens only through a positive probability of a never-ending game, never through a heavy tail.

**Corollary C2 (full support, including uniformly random play).** Suppose $\pi(a|s)>0$ for every legal type-level action. The simulator's `random` policy qualifies:
- it plays uniformly over distinct playable types (at least 1/24);
- facing a stack, it chooses uniformly over the stackable types (at most 11) plus accept (at least 1/12);
- it chooses colours with probability 1/4, and swap targets with probability at least 1/5.

For such $\pi$, $R_\pi=R$, and condition (3) is equivalent to **no trap**: from every $s\in R$, some finite path of legal decisions and positive-probability draws ends the game. So under uniformly random play:
- if there is no trap, $E[T]<\infty$ with geometric tails;
- otherwise $P(T=\infty)>0$.

Case (A) of Theorem B implies no trap, but not conversely. The simulator's `greedy` and `prolong` policies are stationary and randomised, but not full-support. For them, condition (3) must be checked directly, or it follows from (A).

**Conjecture E (no trap, $N=2..6$).** From every reachable non-terminal micro-state, some finite legal path with positive-probability draws ends the game. This is **unproven**.

Partial observation: suppose a Roulette is played when $|D|\ge32$. Let the victim name the colour $k$ that is rarest in $D$. Then there are at least $3|D|/4\ge24$ non-$k$ cards, so nature can reveal $25-h$ of them first and knock the victim out. A full proof needs a case analysis that steers any configuration into such a situation, including 5- and 6-player worst cases in which other hands hold up to 120 cards.

## 7. Numerical sanity checks

These were run with an instrumented copy of `nomercy.c` in the scratchpad; `sim/` was not modified.

- **Invariants.** Card conservation, hand size at most 24, and the current player being active were checked after every turn in 1.5M games ($N\in\{2..6\}$ × policies {random, greedy, prolong} × 100k). There were 0 violations and 0 deadlocks.
- **Bounds of Thm D and Lemma 3.**
  - Maximum single draw run: 24 (bound 24, attained).
  - Maximum draws in one turn: 42 (bound 48).
  - Maximum $|D^*|$ at a draw: 165 (bound 165, attained).
  - Minimum $|D|+|X|$ at a draw: 119, 74 and 40 for $N=2,4,6$ (bounds 119, 71 and 23).
- **Theorem A (draw uniformity).** Martingale z-scores were computed for $\sum(1\{\text{drawn}\in\text{class}\}-D^*(\text{class})/|D^*|)$. The classes were wild, red, first draw after a reshuffle, and draw inside draw-until-playable. Over 9 runs of 100k games, all 36 z-values had $|z|<2.5$, with a mean near 0, consistent with N(0,1).
- **Corollary A2.** The deferred-sampling reference (40k games) gives mean $T$ = 29.99±0.11 (2p) and 127.74±0.27 (6p). The physical-pile C simulator (2M games) gives 30.106±0.016 and 127.734±0.039. These agree.
- **Theorem C.** Under random play the empirical survival functions are log-linear between the 99% and 99.99% quantiles. The per-turn decay rates are 0.920, 0.947, 0.951, 0.954 and 0.956 for $N=2..6$, stable across half-windows. The simulator has no cap, and all 10M games terminated (max 456 turns). So if a trap is reachable under random play, it is hit with probability below $1.5\times10^{-6}$ per $N$ (95% bound).
- **§5.5.** The counterexample gives 2046, versus 20 and 10240.

## 8. Summary of what is proven

**Proven:** (d), (a), (b) and (c) exactly as stated in Theorems D, A, B and C, including:
- the explicit constants: $\varepsilon\ge1/165$, $K\le|R\setminus F|<10^{132}$, $E[T]\le K\,165^K$ in case (A), and at most 49 micro-steps per turn;
- the correction of the task's $K/\varepsilon$;
- the precise information-structure boundary: non-anticipating profiles are covered and clairvoyant ones are not.

**Not proven, and outside T1:**
- which alternative of Theorem B holds, i.e. whether $C\cap R=\varnothing$;
- Conjecture E, which is exactly what finite expected length under uniformly random play needs;
- the clairvoyant case when $C=\varnothing$.

The dichotomy reduces the question "is the mean game length infinite for some colluding strategy?" to a finite, decidable graph property of a model with up to about $10^{131}$ states. Nothing here claims the game is "solved" in the game-theoretic sense.