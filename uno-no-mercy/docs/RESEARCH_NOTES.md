# UNO Show 'Em No Mercy: Rules Specification and Prior-Work Summary for Simulation (v1)

**Scope.** This spec covers one hand of the base game: Mattel HWV18, ©2023, 2–6 players. Players are treated as robots:
- UNO is always called, so the missed-call penalty never applies.
- There are no physical limits such as how many cards a hand can hold.
- There is no turn cap.

The Expansion Pack JJB29 is out of scope.

**Evidence grades used throughout:**
- **P**: primary text, quoted verbatim.
- **O**: official social-media reply.
- **S**: secondary text the researchers actually read.
- **U**: search-engine snippet or summary only; wording is not verbatim.
- **I**: inference made here.

| Key | Source | Grade |
|---|---|---|
| MS | Mattel instruction sheet HWV18, https://service.mattel.com/instruction_sheets/HVW18-Eng.pdf (the URL really is spelled "HVW18"). The proxy blocked it, so the text was read from a byte copy of the PDF and from two transcriptions that match it word for word: https://raw.githubusercontent.com/Aether-123/YouKnow-1/HEAD/pdf_rules_extracted.txt and https://raw.githubusercontent.com/timothy0509/uno-cli/HEAD/rules.md. Local copies: `/tmp/claude-0/-home-user-Claude-public/453ed49c-5fba-5de9-980c-3a67163eb5fe/scratchpad/src/timothy0509_uno-cli_HEAD_rules.md` and `.../scratchpad/src/youknow_pdf_rules.txt` | P |
| X-1887 | @realUNOgame, https://x.com/realUNOgame/status/1887556543098286580 (Feb 2025, a No Mercy question) | O |
| X-1863 | @realUNOgame, https://x.com/realUNOgame/status/1863976235203764712 (two-player Wild Reverse Draw 4) | O |
| X-1850 | @realUNOgame, https://x.com/realUNOgame/status/1850939942953701796 (Wild Color Roulette) | O |
| X-1728 | @realUNOgame, https://x.com/realUNOgame/status/1728096146231554184 (7 swap: any other player) | O |
| X-2019 | @realUNOgame, https://twitter.com/realUNOgame/status/1092455045227077640 (classic UNO Wild Swap Hands, not No Mercy) | O |
| MSTORE | https://shop.mattel.com/products/uno-show-em-no-mercy-hwv18 | U |
| FW | cardgameuno fan wiki, https://cardgameuno.fandom.com/wiki/UNO_Show_'Em_No_Mercy | U |
| MF | matteluno fan wiki card pages (Wild Reverse Draw 4, Wild Color Roulette, main page) | U |
| WB | Wikibooks, https://en.wikibooks.org/wiki/UNO/UNO_Show_Em'_No_Mercy | U |
| OM | alii13/open-mercy (RULES-REFERENCE.md, rules pages, deck.ts) | S |
| RG | rajatghate5/no-mercy (config/deck.yml, packages/engine/src/*.ts) | S |
| AY | ayushrudani/no-mercy-uno (docs/PLAN.md, packages/engine/test/deck.test.ts) | S |
| CH | cheanus/uno-no-mercy (house-rules guide) | S |
| UR | unorules.com write-up, via https://raw.githubusercontent.com/timothy0509/uno/HEAD/rules.md | S |
| BGG-nnnnnnn | BoardGameGeek threads; only titles and summaries were seen | U |
| UBI | Ubisoft No Mercy DLC news and butwhytho.net coverage | U |

---

## 1. Deck composition

### 1.1 What the primary source says
- MS says only "Contents 168 Cards". It gives **no per-card breakdown**.
- MSTORE (U) says 168 cards, "56 more cards" than classic UNO, 2–6 players.
- The MS scoring section fixes the set of card *types*:
  - Colored actions: "Skip, Reverse, Draw 2, Draw 4, Discard All, Skip Everyone".
  - Wilds: "Wild Reverse Draw 4, Wild Draw 6, Wild Draw 10, Wild Color Roulette".
- **MS lists no plain Wild and no colorless Wild Draw 4.**
- The Draw 4 is a colored card: it is scored among the "Any Color Action Card" types.

### 1.2 Default deck (D-FW)
D-FW comes from the FW snippet. The AY repo unit-tests the same deck, and AY's PLAN.md calls it "confirmed official". No primary source confirms it.

| Card | Match symbol | Color | Per color | Total | Draw value | Points (MS) |
|---|---|---|---|---|---|---|
| Number 0 | 0 | R/Y/G/B | 2 | 8 | 0 | 0 |
| Numbers 1–9 | n | R/Y/G/B | 2 each (18) | 72 (8 of each rank) | 0 | face |
| Draw 2 | D2 | colored | 3 | 12 | 2 | 20 |
| Draw 4 (colored) | D4 | colored | 2 | 8 | 4 | 20 |
| Skip | SKIP | colored | 3 | 12 | 0 | 20 |
| Skip Everyone | SKIP_ALL | colored | 2 | 8 | 0 | 20 |
| Reverse | REV | colored | 3 | 12 | 0 | 20 |
| Discard All | DISCARD_ALL | colored | 3 | 12 | 0 | 20 |
| **Colored subtotal** | | | **36** | **144** | | |
| Wild Reverse Draw 4 | (wild) | none | – | 8 | 4 | 50 |
| Wild Draw 6 | (wild) | none | – | 4 | 6 | 50 |
| Wild Draw 10 | (wild) | none | – | 4 | 10 | 50 |
| Wild Color Roulette | (wild) | none | – | 8 | 0 (not a Draw Card) | 50 |
| **Wild subtotal** | | | | **24** | | |
| **Total** | | | | **168** | | |

### 1.3 Conflicting breakdowns
All four breakdowns total 168.

| Card type | **D-FW (default)** | D-RG (RG deck.yml) | D-OM (open-mercy deck.ts) | D-WB (literal reading of the WB snippet) |
|---|---|---|---|---|
| 0s (total) | 8 | 8 | 4 | 8 |
| 1–9 (total) | 72 | 72 | 72 | 108 (3 per rank per color) |
| 7s (total) | 8 | 8 | 8 | 12 |
| Draw 2 | 12 | 12 | 12 | 8 |
| Draw 4 (colored) | 8 | 12 | 12 | 4 |
| Skip | 12 | 12 | 12 | 8 |
| Skip Everyone | 8 | 12 | 12 | 4 |
| Reverse | 12 | 12 | 12 | 8 |
| Discard All | 12 | 12 | 12 | 4 |
| Plain Wild | 0 | 0 | **4** | 0 |
| Wild Reverse Draw 4 | 8 | 4 | 4 | 4 |
| Wild Draw 6 | 4 | 4 | 4 | 4 |
| Wild Draw 10 | 4 | 4 | 4 | 4 |
| Wild Color Roulette | 8 | 4 | 4 | 4 |
| Cards per color | 36 | 38 | 37 | 38 |
| Wilds | 24 | 16 | 20 | 16 |

Notes on the alternatives:
- **D-RG.** RG's deck.yml says its source is "Mattel's own instruction sheet". The sheet has no breakdown, so that claim is unsupported. This is the "38 per colour + 16 wilds" deck that one prior-work note described as "checked against Mattel's sheet".
- **D-OM.** Its plain Wilds contradict MS, which lists no plain Wild.
- **D-WB.** WB says "an extra number card for each number/colour combination and four each of" the seven new card types. Read literally, that is 116 numbers + 24 classic actions + 28 new cards. It gives only one Skip Everyone, one Discard All and one Draw 4 per color, which is implausible.
- **Other decks, not used.** lalit2406 has 4 plain Wilds and 4 Roulettes. nfemmanuel and Akshat-1290 carry clearly wrong counts. One unoreverse.com snippet was nonsensical.

**Recommendation:**
- Default to D-FW.
- Run sensitivity checks on D-RG and D-OM, and optionally D-WB.
- Settling the deck needs a physical count of a retail deck.

### 1.4 Derived deck constants
These are computed here (grade I). "Full deck" means a fresh shuffle of all 168 cards.

| Constant | D-FW | D-RG | D-OM | D-WB |
|---|---|---|---|---|
| Number of Draw Cards | 36 | 36 | 36 | 24 |
| Total draw value (sum of +n) | 152 | 152 | 152 | 112 |
| Cards at the +4 level (D4 + WRD4) | 16 | 16 | 16 | 8 |
| E[Roulette reveals, full deck] = (N+1)/(K+1) | 169/37 ≈ **4.57** | 169/39 ≈ 4.33 | 169/38 ≈ 4.45 | 169/39 ≈ 4.33 |
| P(a random card is playable on a number top, rank 1–9), pool of 167 | 65/167 ≈ 0.39 | 59/167 ≈ 0.35 | 62/167 ≈ 0.37 | 62/167 ≈ 0.37 |

Two figures in the research inputs are corrected by this table:
- Item 11 gave the D-FW Roulette mean as "≈4.7". It is 4.57.
- Item 18 gave "about 12 sevens and zeros". D-FW has 16: 8 zeros and 8 sevens.

---

## 2. Canonical rules (default interpretation)

### 2.0 State and notation
- **Seats and turn order.** Seats are 0..n−1, and clockwise is +1. The active set A holds the players not knocked out. Direction d ∈ {+1, −1}.
- **next(s)** is the first seat s + k·d (mod n), for k ≥ 1, that is in A. It is computed in the *current* direction at the moment of resolution.
- **Piles.**
  - The draw pile is an ordered, face-down stack.
  - The discard pile is ordered, with its top card t.
  - The set-aside pile holds the hands of knocked-out players.
- **Active color a.**
  - If t is colored, a is t's color.
  - If t is a WRD4, WD6 or WD10, a is the color its player named.
  - If t is a Roulette, a is the color the victim named (R10).
- **Pending stack.** `pending = None | {total, last, target}`.
- **Draw value dv(c).** D2 = 2, D4 = 4, WRD4 = 4, WD6 = 6, WD10 = 10, and 0 for every other card.
- **Draw Cards** are the cards with dv > 0 [MS: "Draw Card (+2, +4, +6, +10)"].
- **Policy vs rules.** Every choice written *(policy)* below is a decision for the player's policy, not a rule.

### R1. Players, deal and first card
1. There are 2–6 players [P: MS header "2-6"; U: MSTORE]. Shuffle all 168 cards uniformly and deal 7 to each player [P: MS Setup 2].
2. The dealer sits at seat n−1. Seat 0 ("the player to the left of the dealer") moves first, and d = +1 [P: MS Setup 5].
3. **Opening flip.**
   - Flip the top card of the draw pile onto the discard pile.
   - While t is not a number card, flip the next card on top of it. Ignored cards stay buried in the discard pile.
   - The loop ends on a number card, and a becomes its color.
   - No effect applies, so an opening 0 or 7 does nothing.
   - Basis: MS Setup 4 says "If this card is an Action Card, ignore it and flip over the next card" [P]. Wilds count as action cards because MS scores them as "Any Wild Action Card" [P]; that they are ignored too is inference [I]. Leaving the ignored cards buried is the literal reading [I].
   - Flag: `opening_card`.

### R2. The turn
When it is player p's turn:
1. **Stack pending against p.** Resolve it with R6. Nothing else is legal.
2. **Otherwise, p holds a legal card** (R3). p **must** play exactly one legal card *(policy: which one)*.
   - Basis: MS says "If you HAVE a matching card in your hand, you may PLAY IT" and "If you DO NOT HAVE a matching card, you MUST draw" [P]. MS gives no draw option to a player who has a match [P]; the classic sheet's "You may also choose NOT to play a playable card" sentence is absent.
   - This strict reading is moderately supported. Flag: `voluntary_draw`.
3. **Otherwise, p draws until playable** (R4).
4. Only one card is played per turn [P: MS "playing ONE CARD"]. Discard All's shedding is the only exception (R7.5). There are no jump-ins.

### R3. Matching and legality (no stack pending)
- **When a card is playable.** Card c is playable on (t, a) if at least one of these holds [P: MS "matches at least one attribute ... its color, number, or symbol"]:
  - c is a wild; or
  - c's color = a; or
  - c and t are number cards of the same rank; or
  - c and t are colored action cards with the same symbol. The symbols are D2, D4, SKIP, SKIP_ALL, REV and DISCARD_ALL.
- **A colored D4 and a WRD4 are different symbols.** So outside a stack, a D4 on a WRD4 needs the declared color. There is no source either way [I]. Flag: `plus4_symbols_shared`.
- **Naming the color.** The player of a WRD4, WD6 or WD10 names a *(policy)*. MS never says this directly; it comes from "It plays just like classic UNO" [P]+[I]. Roulette is different: see R10.
- **No restrictions on wild draws.** A wild draw card may be played at any time. There is no classic "no matching color" restriction and no challenge rule [I: MS contains neither]. Flag: `wild_draw_restriction`.

### R4. Draw until playable
Repeat the following [P: MS: "you MUST draw cards from the Draw Pile UNTIL YOU DRAW A CARD YOU CAN PLAY. Then, play that card."]:
1. If the draw pile is empty, reshuffle (R14).
2. Draw one card into p's hand. **Check Mercy (R12).** If p is knocked out, the sequence ends.
3. If the drawn card is playable (R3), p **must play that card now**, and it resolves normally. Otherwise, repeat.

Notes:
- No other hand card can have become playable, because t and a have not changed.
- Drawn cards are private.
- Flags: `no_playable_action` and `drawn_card_play`.

### R5. Resolving a play
1. Move c from p's hand to the top of the discard pile.
2. If c is a Discard All, apply R7.5's shedding first.
3. **If p's hand is now empty, p wins and the game ends immediately. The card's effect is not resolved.**
   - Basis: MS: "When a player plays their final card, they win" [P]. Official reply X-1887 on last-card swap cards [O]. BGG-3211870 [U].
   - Flag: `last_card_effect`.
4. Otherwise, resolve the effect (R6–R10). Then play passes to the player the effect specifies. The default is next(p).

### R6. Stacking and pending draw penalties
Basis: MS Stacking paragraph [P], quoted in §1 of the inputs.

1. **Opening a stack.** When a Draw Card c is played and does not end the game:
   - `pending.total += dv(c)` (starting from 0);
   - `pending.last = dv(c)`;
   - `pending.target` is set by the card's rule: next(p) for D2, D4, WD6 and WD10, and R8.3 for WRD4.
2. **The target's options.** On the target's turn the legal responses are the Draw Cards c′ in hand with **dv(c′) ≥ pending.last**.
   - The comparison is with the last card, not the running total [P: MS example: "+4 ... +6 ... forced to draw 10 cards (unless they can play a Draw +6 or higher" and "equals or exceeds the value of the last card played"]. Flag: `stack_threshold`.
   - **Color and symbol are ignored** [I: the clause states only a value; BGG-3169658 (U) reports that the official video stacks a green +4 on a yellow +2]. Flag: `stack_matching`.
   - Order of values: +2 < +4 (D4 or WRD4) < +6 < +10.
3. **Stacking is optional** [P: "you can 'Stack'"]. The target either:
   - (a) plays one legal response *(policy)*. It adds its value, sets the new `last`, and sets the new target by its own rule; or
   - (b) **absorbs**: draws `pending.total` cards one at a time, with a Mercy check after each (R12).
   - Flag: `stack_optional`.
4. **After absorbing,** `pending` is cleared and the absorber has **lost their turn**. Play passes to next(absorber) [P: every Draw card says "must draw N cards and lose their turn"; "That player then takes the full penalty"]. The absorber does not also draw until playable.
5. **Knockout mid-absorb.** If the absorber is knocked out, the undrawn rest of the penalty is cancelled and the stack cleared [I: the sheet is silent]. Play passes to the next active seat after the knocked-out seat.
6. **Nothing but a Draw Card may be played while a stack is pending.** That includes Skip, Reverse, Skip Everyone, Discard All, Roulette and numbers [P: only "Draw Card" answers are described; S: OM and UR agree]. Flag: `stack_deflection`.
7. **After the stack resolves,** t stays the last Draw Card played. a is its color, or the color named for it.
8. **A winning stack card ends the game.** A response that is the responder's last card wins immediately (R5.3).

### R7. Colored action cards
1. **Skip.** next(p) loses their turn, and play passes to next(next(p)) [P]. With 2 active players, p goes again.
2. **Reverse.**
   - Set d = −d, and play passes to next(p) in the new direction.
   - With 2 active players, a Reverse acts as a Skip, so p goes again [P: "With just two players a Reverse skips the other player, letting you take another turn."].
   - Flags: `reverse_2p` and `two_player_basis`.
3. **Draw 2 and Draw 4 (colored).** They open or extend a stack targeting next(p) (R6) [P].
4. **Skip Everyone.** p immediately takes another turn, and d does not change [P: "Skip all the other players and take another turn."]. The extra turn is a complete R2 turn: p must play if able, and otherwise draws until playable.
5. **Discard All.**
   - When it is played, **every other card of the Discard All's color** in p's hand goes to the discard pile, **underneath** the Discard All [P: "Discard all the cards in your hand that match the color of the Discard All Card. Place the extra cards under the Discard All Card."].
   - The shedding is mandatory, and wilds are excluded.
   - The effects of buried cards do not trigger. The Discard All stays on top, and a is its color.
   - If this empties p's hand, p wins (R5.3).
   - Like any colored card, it is playable on its color or on another Discard All.
   - Flag: `discard_all_mode`.

### R8. Wild draw cards
1. **Wild Draw 6 and Wild Draw 10.** p names a. The card opens or extends a +6 or +10 stack targeting next(p) [P].
2. **Wild Reverse Draw 4 with 3 or more active players.** p names a, then sets d = −d. The stack gains +4 and targets next(p) **in the new direction**, which is the player who was previous in turn order [P: "Reverse the direction of play, then the next player in the new direction must draw 4 cards and lose their turn."]. Inside a stack, this sends the whole running total back toward the player who stacked on p [I+S: BGG-3322195 (U); open-mercy rules page]. A WRD4 is legal on a pending +2 or +4, and illegal on +6 or +10.
3. **Wild Reverse Draw 4 with exactly 2 active players.**
   - p names a. The stack gains +4 (added to any running total), and **the target is p**.
   - p may immediately answer with a Draw Card of value ≥ 4 *(policy)*. That card targets the opponent, as normal R6 play. Otherwise p absorbs, and play passes to the opponent.
   - Basis: MS: "With just two players this card skips the other player and makes YOU draw 4 cards! You may use the stacking rule to send the penalty back to the other player." [P]; X-1863 repeats it [O]. Applying this to a running total is inference [I].
   - Flags: `two_player_wrd4` and `two_player_basis`. The default basis for "two players" is the *active* count [I].

### R9. 7s and 0s
Both apply only when the card is played and does not end the game.
1. **7.** p **must** swap their whole hand with any other active player of p's choice *(policy)*. Play then passes to next(p) [P: "you MUST swap your hand with another player of your choice. Play then continues in current order."; O: X-1728]. With 2 players, the target is forced. Flag: `seven_swap_optional`.
2. **0.** Every active player's hand moves at the same moment to the next active player in the current direction. Knocked-out seats are skipped. Play then passes to next(p) [P: "ALL players must pass their hand to the next player in the current direction of play."]. With 2 players, this is a hand exchange.
3. **No knockouts from swaps or passes.** Under the immediate Mercy check (R12), every hand is at most 24 cards, and swaps and passes only permute hands. So neither can cause a knockout [I].

### R10. Wild Color Roulette
1. It is playable on anything, as a wild. It **cannot** be played while a stack is pending, and it neither starts nor joins a stack. It has no draw value [P: absent from "(+2, +4, +6, +10)"; U: BGG-3363721].
2. **The victim** v = next(p) names a color c *(policy)* [P: "The next player chooses a color."; O: X-1850]. **The active color becomes c** [U: MF; RG and AY implement this; BGG-3240961 and BGG-3597907 are unresolved]. The Roulette's player names nothing. Flag: `roulette_active_color`.
3. **The reveal.**
   - v reveals cards from the draw pile one at a time, reshuffling as needed (R14).
   - **Each revealed card enters v's hand immediately, with a Mercy check** [I from the Mercy wording "ever has"]. Flag: `roulette_add_timing`.
   - The reveal stops at the first card whose color is c. Wilds never count as hits but are kept [P: "(Wild Cards do NOT count). Then they add all the revealed cards to their hand and lose their turn."].
   - A knockout stops the reveal.
4. v loses their turn, and play passes to next(v). With 2 players, p goes again.
5. **No answer is possible.** Neither another Roulette nor a Draw Card can answer it. Flag: `roulette_in_stack`.

### R11. Calling UNO
UNO is always called, and the 2-card penalty [P] never applies. Flag: `uno_miss_prob` = 0.

### R12. Mercy rule (knockout)
1. **Check after every card that enters any hand.** If the hand has **25 or more cards**, that player is **knocked out immediately** [P: "If a player ever has 25 or more cards in their hand, they are out of the game."; U: UBI "immediately knocked out"]. Flags: `mercy_enabled`, `mercy_threshold` and `mercy_timing`.
2. **What happens to the hand.** It goes to the set-aside pile. It is neither discarded nor shuffled in yet [P: "Set aside their hand of cards until the deck runs out and needs to be reshuffled."]. Flag: `knocked_out_cards`.
3. **Interrupted actions.** Any draw sequence in progress ends: draw until playable, a penalty absorb, or a Roulette reveal. Any pending stack is cleared. Play passes to the next active seat after the knocked-out seat, in the current direction.
4. **Last player standing.** If |A| becomes 1, that player wins [P: "if all other players are knocked out of the game ... you win"].
5. **Invariant:** every active hand holds at most 24 cards at all times.

### R13. Knocked-out players
Knocked-out players take no turns. They are skipped by next(), are not valid 7-swap targets, and are excluded from the 0-pass [I: they "are out of the game"].

### R14. Empty draw pile and reshuffle
1. **When it happens.** A card must be drawn or revealed and the draw pile is empty. This trigger is lazy, following "until the deck runs out and needs to be reshuffled".
2. **What happens.**
   - The new draw pile is every discard card except the top card, plus all set-aside cards, shuffled uniformly.
   - The top card stays as the only card in the discard pile.
   - Basis: MS: "if there are no cards left in the Draw Pile, reshuffle the Discard Pile to form a new Draw Pile" [P]. Keeping the top card is standard practice [I].
   - Flags: `reshuffle_keep_top` and `reshuffle_timing`.
3. **Exhaustion cannot happen under the defaults with n ≤ 6** (proof in R17). If it ever does, the simulator should **raise an assertion**; it signals a bug. Flag: `exhaustion_fallback`, for variants that allow exhaustion.

### R15. Winning and scoring
1. **How a hand ends.**
   - (a) A player's hand becomes empty as a result of their play, including by Discard All shedding. They win at once, and pending effects are moot.
   - (b) Only one active player remains.
   - Basis [P]: MS Object and Winning sections.
2. **The unit of simulation is one hand.** Optional scoring [P]:
   - The winner scores the cards left in opponents' hands: number cards at face value, colored action cards 20, wilds 50.
   - Add 250 for each opponent knocked out during the hand, ignoring their cards.
   - The match is to 1000 points or more.
   - Flag: `match_unit`.

### R16. Two-player summary
The special cases are Reverse and WRD4. Every other two-player result follows from the general rules.

| Card | 2-player result |
|---|---|
| Skip, Skip Everyone, Reverse | p goes again |
| D2, D4, WD6, WD10 | The opponent absorbs or stacks. After an absorb, p goes again. |
| Roulette | The opponent reveals, then p goes again |
| WRD4 | p faces +4 (plus any running total) and may stack it back, or absorbs (R8.3) |
| 0 | Hands are exchanged |
| 7 | p must swap with the opponent |
| Knockout | The opponent wins |

"Two players" means 2 **active** players, including a larger game reduced to two by knockouts [I].

### R17. Termination facts under the defaults
These are derived here (grade I) and should be asserted in code.
1. **No hand exceeds 24.** Every active hand h satisfies 1 ≤ h ≤ 24. A hand at 0 means that player has already won.
2. **Drawable cards always suffice.** Drawable cards (the draw pile, the discard pile except its top, and set-aside cards) number at least 168 − 1 − h − 24(n−1). For n ≤ 6, that is at least 47 − h, which is at least 25 − h: enough to reach either a playable card, the Roulette color, or a knockout. So **every draw sequence ends within 24 cards, and the pool is never exhausted.** This bound is tight at the official maximum: with n = 7, the worst case leaves 23 − h cards, fewer than the 25 − h needed.
3. **Draw-free stretches are bounded.** A turn without a draw removes at least one card from the hands in total, and 0s and 7s only permute hands. So there are at most 24n consecutive draw-free turns.
4. **All length units are comparable.** Cards drawn per turn are at most 24, and stack totals are at most 152 on D-FW. So turns, actions and card movements are all within constant factors of each other. A finite mean in one unit implies a finite mean in all of them.

### R18. Length metrics the simulator should record
- **`turns` (primary).** Count one each time a seat acts. Acting means playing a card, drawing until playable, answering or absorbing a stack, or doing a Roulette reveal. Skipped seats do not count. A Skip Everyone extra turn and a two-player WRD4 self-response each count as a new turn.
- **Secondary:** `plays`, `cards_drawn`, `reshuffles`, `knockouts`, `rounds` (= turns / n), and `end_reason` (a player went out, or last player standing).
- **`rg_actions`.** For comparison with RG. RG's unit counts one per play, one per whole draw-until-playable, one per stack take and one per color choice.

### Compact resolution pseudocode
```
turn(p):
  if pending and pending.target == p:
      R = {c in hand[p]: dv(c) >= pending.last}                # F08/F09
      if R and policy.stack(p, R): play(p, policy.pick(R)); return
      absorb(p, pending.total)       # 1 card at a time, Mercy check after each; stops on knockout
      pending = None; cur = next_from(p); return
  L = {c in hand[p]: playable(c, top, color)}
  if L: play(p, policy.pick(L)); return                      # F07: strict must-play
  loop: c = draw(p)                  # reshuffle if needed; Mercy check → knockout ends turn
        if playable(c): play(p, c); return

play(p, c):
  discard_top(c); if c is DISCARD_ALL: bury all other hand cards of color(c)
  if hand[p] empty: WIN(p)                                   # effect not resolved (F28)
  effect(c)   # R6–R10; wild naming; next seat computed in current direction
```

---

## 3. Variant flags

The default is in **bold**. "Length" is the expected direction of the effect on mean game length; these are hypotheses to test. "Term." is the effect on the termination guarantee.

| # | Flag | Values (default first) | Basis for default | Expected effect on length / termination |
|---|---|---|---|---|
| F01 | `deck` | **D-FW** \| D-RG \| D-OM \| D-WB \| custom | §1 | D-OM's plain wilds raise playability and so reduce draws. D-WB has less total draw value (112 vs 152), so fewer knockouts and probably longer games. D-RG has fewer wilds, so a lower playable fraction and more draws. |
| F02 | `n_players` | **2–6** \| 7+ (stress only) | P | Term.: n ≥ 7 breaks R17.2 (the pool can run out) and needs F26. |
| F03 | `hand_size` | **7** | P | — |
| F04 | `opening_card` | **bury_until_number** \| wild_ok_first_player_names \| apply_effect_classic | P + I | Negligible. |
| F05 | `no_playable_action` | **draw_until_playable** \| draw_one_play_if_playable \| draw_one_pass | P | Draw-one (the Keshav-Madhav simulator) slows hand growth: fewer knockouts, and the length effect is ambiguous. |
| F06 | `drawn_card_play` | **forced** \| optional_keep | P ("Then, play that card.") | Optional keeping lets hands balloon: more knockouts, fewer wins by going out. |
| F07 | `voluntary_draw` | **forbidden** \| allowed_draw_until_playable \| allowed_draw_one_may_pass | P (strict reading, moderate confidence); X-1887 is noncommittal | Allowing it adds stalling. With pass allowed, colluding or adversarial stalling becomes possible; Mercy still caps hands, but see G3. Likely the largest effect on the mean. |
| F08 | `stack_threshold` | **ge_last_card** \| ge_running_total (UR) \| gt_last_card \| any (RG option, not a real rule) | P (sheet example) | Running-total or strictly-greater thresholds make chains shorter: fewer knockouts, longer games. "any" makes stacks survivable and sharply cuts knockouts (RG comment). |
| F09 | `stack_matching` | **value_only** \| value_and_normal_match (CH) \| value_and_same_color | P (value only) + U (official video) | Stricter matching means shorter stacks and longer games. |
| F10 | `stack_optional` | **true** \| false (must stack if able) | P ("you can") | Mandatory stacking means bigger stacks, more knockouts, shorter games. Under the default, this is a policy lever. |
| F11 | `wrd4_is_draw_card` | **true** \| false | P (WRD4 text invokes "the stacking rule") | false: fewer +4-level answers, shorter stacks. |
| F12 | `wrd4_stack_redirect` (3+ players) | **reverse_and_target_new_next** \| add_only_keep_target \| not_playable_on_stack | P (literal) + S (OM) | Redirect produces "ping-pong" between neighbors: larger stacks, more knockouts. |
| F13 | `two_player_wrd4` | **self_target_may_restack** \| opponent_draws ("misprint" reading) | P, O (X-1863) | Under the default, naive bots hurt themselves, lengthening duels. opponent_draws shortens duels. |
| F14 | `two_player_basis` | **active_count** \| starting_count | I | Affects endgames after knockouts. |
| F15 | `stack_deflection` | **none** \| skip_or_reverse_deflects (house rule) | P + S | Deflection means fewer absorbed penalties: longer games. |
| F16 | `victim_after_penalty` | **lose_turn** \| normal_turn_after_draw | P | normal_turn lets victims shed a card at once: slightly longer games. |
| F17 | `roulette_active_color` | **victim_choice** \| roulette_player_names | U (MF), S (RG/AY); officially unresolved | Small. |
| F18 | `roulette_add_timing` | **immediate_each_card** \| at_end | I (from "ever has") | Term.: with at_end, a reveal can loop forever when every card of the named color sits in hands. Needs F26. |
| F19 | `roulette_in_stack` | **none** \| roulette_passes_roulette \| draw_answers_roulette | P (list of +values) + U | Either alternative makes Roulette less lethal: longer games. |
| F20 | `mercy_enabled` | **true** \| false | P | false: hands unbounded and the pool can run out, so the R17 guarantees are lost. Needs F26. The one anecdote is a 2.5-hour game without the rule (ShopSavvy, U). Key stress test for the question "is the mean infinite?". |
| F21 | `mercy_threshold` | **25 (≥)** \| integer | P | A higher threshold means fewer knockouts; R17.2 must be recomputed. |
| F22 | `mercy_timing` | **immediate** \| after_draw_action (RG's actual code for penalty and Roulette) \| end_of_turn (secondary sites) | P ("ever"), U (UBI) | Later timing lets hands exceed 24 temporarily. Term.: the pool can run dry mid-penalty, and a swap or pass of a 25+ hand becomes possible. Needs F26. |
| F23 | `knocked_out_cards` | **set_aside_until_reshuffle** \| under_discard_now (RG; MF "bottom of discard") \| shuffle_in_now \| remove | P | remove shrinks the deck: exhaustion risk and shallower draws. The others barely differ. |
| F24 | `reshuffle_keep_top` | **true** \| false | I (standard practice) | Negligible. |
| F25 | `reshuffle_timing` | **lazy** \| eager | P ("needs to be reshuffled") | Negligible. |
| F26 | `exhaustion_fallback` | **assert_unreachable** \| stop_draw_turn_ends \| fewest_cards_wins (RG `settleIfDeadlocked`) | I | Only reachable under F02/F18/F20/F22/F23 variants. Without a fallback, a code deadlock would appear as an "infinite" game: an artifact, not a property of the game. |
| F27 | `discard_all_mode` | **all_same_color_under_no_effects** \| optional_subset (CH) \| choose_top_and_fire (OM) | P ("under") | choose_top_and_fire shortens games (buried Draw or Skip Everyone cards fire). optional_subset has a small effect. |
| F28 | `last_card_effect` | **win_immediately** \| resolve_then_empty_hand_wins | P (Winning) + O (X-1887) + U (BGG-3211870); the alternative follows X-2019 (classic Wild Swap Hands) | Under the alternative, a last 7 or 0 hands cards back and a last two-player WRD4 forces a self-draw. That removes outs and lengthens games; it is a possible stalling mechanism. |
| F29 | `discard_all_empty_hand_wins` | **true** \| false (fringe "must *play* final card") | P (Object) | false removes a major instant-win route: much longer games. |
| F30 | `seven_swap_optional` | **false** \| true (RG default `sevenMayDecline`) | P ("MUST") | true allows keeping good hands: slightly shorter games. |
| F31 | `zero_pass_scope` | **active_only** \| include_empty_seats | I | Negligible in practice. |
| F32 | `plus4_symbols_shared` | **false** \| true (CH) | I (no source) | true: marginally more playability. |
| F33 | `wild_draw_restriction` | **none** \| classic_wd4_rule_with_challenge | P (absent) | A restriction reduces stacks slightly. |
| F34 | `skip_everyone_extra_turn` | **full_turn** \| optional_pass | P | Small. |
| F35 | `reverse_2p` | **acts_as_skip** \| direction_only | P | direction_only means fewer extra turns in duels. |
| F36 | `uno_miss_prob` | **0** \| p ∈ (0,1] | User request (robotic players) | p > 0 adds 2 cards to near-winners: slightly longer games. |
| F37 | `match_unit` | **single_hand** \| to_1000_points | P (scoring is optional) | Scoring changes the measured unit, not the dynamics of a hand. |

**Policy decision points** are not flags; the simulator must model them as policy:
- which legal card to play;
- the color named for a WRD4, WD6 or WD10;
- the 7-swap target;
- the Roulette color (chosen by the victim);
- whether to stack or absorb.

Depending on flags, also:
- whether to draw instead of play (F07);
- which Discard All subset to shed (F27).

The mean length is a property of rules × policy, and must be reported per policy class.

---

## 4. Prior work

### 4.1 Is No Mercy (or UNO) solved?
**No.** No source claims a game-theoretic solution of any strength (ultra-weak, weak or strong), a computed equilibrium, or an optimal strategy for No Mercy or for real UNO.
- **Complexity of abstract models.** Demaine, Demaine, Harvey, Uehara, T. Uno and Y. Uno, "The Complexity of UNO" (arXiv:1003.2851; FUN 2010; TCS 521 (2014) 51–61), known here only from search summaries (U).
  - The model has perfect information, colors and numbers only, no action cards and no draw pile.
  - Solitaire UNO is NP-complete, with some special cases in P.
  - Uncooperative two-player UNO is in P. The FUN 2010 PSPACE claim was withdrawn in the journal version.
  - Dey, Goyal and Misra (FUN 2014) give tractable special cases of the solitaire model (U).
  - None of this transfers to the real game, which has hidden information, chance, multiple players and action cards. None of it models No Mercy's features.
- **State-space size.** The RLCard README (fetched, S) puts classic two-player UNO at about 10^163 information sets, with an average size of about 10^10. Exact solution is infeasible. No Mercy has more cards and more rules; that it is harder still is inference [I].
- **Best strategy study.** Orsini's replication package (github.com/fredorsi/uno; Zenodo 10.5281/zenodo.22110130; S) finds an empirical equilibrium over 13 heuristics for classic UNO only. It states: "It does not prove a Nash equilibrium over the full space of all possible UNO policies."
- **No Mercy code.** About 90 GitHub repos were searched. They are playable engines with heuristic bots, with no solver, CFR run, equilibrium computation or "solved" claim.
- **Nothing else found.** No No Mercy academic paper was found. The requested "Mishiba & Takenaga, UNO is hard" was not found either; their known joint paper is "QUIXO is EXPTIME-complete", so the citation is probably misattributed.

### 4.2 Claims that the game is infinite or has infinite expected length
- **No rigorous claim exists either way.** Nobody has shown or seriously argued that the expected length is infinite, and nobody has published a proof that it is finite.
- **"Forever" claims are only marketing or anecdote:**
  - Official @uno TikTok: "Happiness is temporary. UNO Show 'Em No Mercy is forever." (U; marketing).
  - ShopSavvy (U): "regularly stretches to 45-60 minutes", and a 2.5-hour game *played without the Mercy rule*.
  - X post by @_cherishme_ (U): a 2-hour game.
  - steveharveyfm SEO page (U): says there is no documented record, and contains factual errors such as a "108-card" deck.
- **Simulators cap turns only as bug guards:**
  - RG: `maxTurns: 5000`, with the comment "Safety valve for the simulation harness; not a real UNO rule".
  - Orsini: max_turns 10,000, with 0 aborts.
  - Keshav-Madhav: k = 100,000.
- **Known stall hazard: RG's deadlock.** RG adds `settleIfDeadlocked`, under which the fewest cards win when the draw pile and recyclable discard are both empty and the player to act cannot play. Its author says that before this fix "the game simply stopped: no winner". RG also recycles knocked-out hands at once, citing possible starvation. By R17, with n ≤ 6, immediate Mercy and set-aside hands, **starvation is impossible**. RG's hazard comes from its support for 8–10 players and its non-immediate Mercy timing (§4.3 caveats).
- **Known stall hazard: runouts in classic UNO.** The flazz classic-UNO simulator (rerun, S) aborts 0.02–0.09% of five-player games as "runouts" (every card in hands, draw required). Those rules differ: classic deck, stacking house rule, no Mercy cap.
- **Theory from other card games** (U, from summaries):
  - Deterministic games can cycle forever. War can cycle (Spivey, INTEGERS 10 (2010) G02). A non-terminating Beggar-my-neighbour deal was found (Casella et al., arXiv:2403.13855).
  - Adding randomness gives a finite expected length: Lakshtanov & Roshchina (Amer. Math. Monthly 119 (2012), War) and Lakshtanov & Aleksenko (Probl. Inf. Transm. 49 (2013), BMN).
  - Random War variants end in about n² steps on average (Bhatia, Chin, Mani, Mossel, arXiv:2302.03535; AMM 2026).
  - Beggar-my-neighbour lengths are roughly exponential (arXiv:2602.23406).
  - No Mercy's reshuffles supply this kind of randomness, but nobody has applied the argument to it.

### 4.3 Simulation numbers

**Table A: No Mercy.** Every figure comes from reruns of third-party code by our own research agents. The authors published none of them. Status: *verified by rerun* (reproducible). The rerun scripts include `/tmp/claude-0/-home-user-Claude-public/453ed49c-5fba-5de9-980c-3a67163eb5fe/scratchpad/sweep2/rg/packages/engine/test/mydist.ts` and `mytail.ts`.

| Source | Players | Policy | Unit | Mean | Median | Spread / tail | n games | Knockouts |
|---|---|---|---|---|---|---|---|---|
| RG, rerun 1 | 2 | medium bots | RG actions | 39.9 | 32 | p99 141, p99.9 188, max 285 | 20,000 | 0.54/game |
| RG, rerun 1 | 3 | medium | actions | 65.1 | 53 | p99 209, p99.9 267, max 388 | 20,000 | 0.86 |
| RG, rerun 1 | 4 | medium | actions | 81.9 | 63 | p99 267, p99.9 335, max 423 | 20,000 | 1.09 |
| RG, rerun 1 | 4 | medium | actions | 81.4 | 64 | p99 262, p99.9 346, max 498; none hit a 2,000,000 cap | 100,000 | ≈15% of games end by last player standing |
| RG, rerun 1 | 6 | medium | actions | 103.5 | 72 | p99 352, p99.9 448, max 673 | 20,000 | 1.43 |
| RG, rerun 2 (commit 44ab7b6) | 2 | medium | actions | 39.8 | 32 | sd 30.2, p99 142, max 285 | 10,000 | 0.55; 54% of games have ≥1 knockout |
| RG, rerun 2 | 3 | medium | actions | 65.7 | – | max 365 | not stated | – |
| RG, rerun 2 | 4 | medium | actions | 82.1 | 64 | sd 60.2, p99 263, max 423 | 10,000 | 1.09; 62% of games have ≥1 knockout |
| RG, rerun 2 | 6 | medium | actions | 102.8 | – | max 523 | not stated | – |
| RG, rerun 2 | 8 / 10 (beyond the official 2–6) | medium | actions | 111.7 / 121.1 | – | – | 5,000 each | 1.70 at 10 players |
| RG, rerun 2 | 4 | easy | actions | 107.3 | – | max 358 | 20,000 | 89–92% of easy-bot games have ≥1 knockout |
| RG, rerun 2 | 4 | hard | actions | 115.5 | – | max 612; P(T>100)=0.518, P(T>200)=0.143, P(T>300)=0.0203, P(T>400)=0.0019 | 20,000 | – |
| RG, rerun 2 | 2 | hard | actions | 47.7 | – | max 328 | 20,000 | – |
| RG test suite (author's code) | 4; and 2, 3, 5, 8, 10 | bots | actions | – | – | all games end below maxTurns = 5000 | 500; 100 each | – |
| Keshav-Madhav/Uno_Sim | 6 | greedy | turns | *no published results* | | | (100,000 configured) | |
| yaboikoi/Simulated-Uno-No-Mercy-Experiment | ? | ? | ? | *repo deleted (404)* | | | | |

**Caveats on the RG numbers.** These were verified from RG source (`types.ts`, `reduce.ts`, `config/deck.yml`). RG deviates from this spec's defaults in these ways:
- Its deck is D-RG, not D-FW.
- `sevenMayDecline: true` is on by default. RG's own comment says this is not Mattel's rule.
- **Mercy timing is mixed.** Draw until playable stops at 25, but stack penalties (`takeStack`) and Roulette reveals are drawn in full *before* `applyMercy`, so hands can temporarily exceed 24.
- Knocked-out hands go **under the discard pile immediately**, not set aside.
- It has code guards: 200 cards for draw until playable, 500 for a Roulette. It also has the deadlock settlement described in §4.2.
- UNO calls and catches are enabled.
- Its unit counts actions, including color choices, not seat-turns.
- In both reruns the tails decay geometrically or faster: in hard 4-player, each extra 100 actions multiplies survival by about 0.1–0.28. **That is consistent with a finite mean for these stochastic bots.** It says nothing about adversarial policies.

**Table B: classic UNO baselines.** These are not No Mercy.

| Source | Players | Policy | Unit | Mean | Median / mode | Spread | n | Status |
|---|---|---|---|---|---|---|---|---|
| Pfann (TDS article + bernhard-pfann/uno-card-game-rl) | 2 | Q-learning vs Q-learning | turns (not incremented on Skip or Reverse replays) | 41.5 | median 34 | sd 28.2, min 5, p99 144, max 200 | 3,000 | **Verified by rerun** |
| Pfann (article claim) | 2 | – | turns | 41 | mode 13 | min 3, max 327 | 100,000 | Unverified (U); the mean matches our rerun |
| Orsini (fredorsi/uno) | 2 / 3 / 4 / 5 / 6 / 8 / 10 | uniform random | turns | 46.8 / 47.4 / 49.6 / 55.2 / 60.7 / 72.4 / 82.9 | – | 2-player max 311 | 4,000 per cell | **Verified by rerun** |
| Orsini | same | majority_color | turns | 31.3 / 36.6 / 43.6 / 50.4 / 57.1 / 67.7 / 79.2 | – | 0 aborts at cap 10,000 | 4,000 per cell | **Verified by rerun**. The published package (up to 2,000,000 paired worlds, 0 aborts) is S. |
| flazz/monte-carlo-uno-simulation | 5 | several tactics | rounds of 5 seats | 24.0–24.8 (≈120 seat-turns) | – | runouts 0.02–0.09% | 10,000 per tactic | **Verified by rerun** |
| Divij Garg (Medium) | 4 | ? | turns | ≈63–64 | – | min ≈16, max ≈188, roughly log-normal | ? | Unverified (U) |
| Table Games Hub | 4 | ? | turns | 63–64 | – | – | ? | Unverified (U), no source given |
| Corrigan (LinkedIn) | ? | ? | – | first player wins ≈10% more often | – | – | 10k–50k | Unverified (U) |
| Ramadhan, Iida et al. (game refinement) | varies | several AIs | – | not found | – | – | ≈1.4M | Unverified (U) |
| "Emergence of Fluctuation Relations in UNO" (PRR 7, 023054, 2025; arXiv:2406.09348) | varies | – | steps between hand sizes | not retrieved | – | – | ? | Abstract only (U) |
| "150–200 moves per game" (unattributed) | ? | ? | moves | 150–200 | – | – | ? | Unverified, source unknown |

---

## 5. Open questions and gaps our analysis must fill

1. **Deck composition (G1).** No primary source has a breakdown. Run the main results on D-FW and repeat the key ones on D-RG and D-OM. Report how sensitive the mean length and knockout rate are to the deck.
2. **Termination proof under the defaults (G2).**
   - Model the game as a finite-state chain whose full state includes the draw-pile order. Randomness enters only at reshuffles.
   - Prove, or refute, that under any stationary randomized policy with full support over legal moves, termination is reachable with positive probability from every reachable state. That gives absorption with probability 1, a geometric tail and a finite mean.
   - Building blocks: R17.1–R17.4 (hands at most 24; pool at least 47 − h for n ≤ 6; draw-free stretches at most 24n turns; draws per sub-procedure at most 24).
   - Still missing: a uniform lower bound on the probability of termination within a bounded number of reshuffles.
3. **Adversarial or colluding policies (G3).** Is there any policy profile under which P(termination) < 1 or E[T] = ∞? Examples: all players colluding to stall, or n−1 players protecting one. Tactics include avoiding a single playable last card, and using 7s, 0s and wild colors to deny outs.
   - Under strict must-play (F07 default), a player whose only card is playable must play it and win. Does that force termination?
   - Under F07 = allowed_draw_one_may_pass, or F28 = resolve_then_empty_hand_wins, stalling looks more plausible.
   - Compute or bound the minimum over policies of P(game ends within K turns).
4. **Policy dependence (G4).** The mean is a property of rules × policy. Report it by policy class: uniform-random legal, greedy heuristics, stack-maximizing, stack-avoiding and "stalling" heuristics, and ideally search-based or RL agents.
5. **Units and comparability (G5).** Report `turns` (R18) as the primary unit, and also `rg_actions` so the results line up with the RG reruns in Table A.
6. **Tail analysis (G6).** Use at least 10^6–10^7 games per core configuration and no turn cap, with an assertion instead of a fallback. Check whether log-survival is linear, and estimate the tail index. Report the maximum observed and any hangs, which should be none.
7. **Flag sensitivity (G7).** Rank the effect on the mean of F07, F08, F09, F13, F22, F27, F28 and F29, plus F01. Run the termination stress variants F20 (Mercy off), F22 (late Mercy), F18 (Roulette cards added at the end), F23 (remove) and F02 (7+ players). These need F26 fallbacks, and any "infinite" outcome must be classified as either a code artifact (a deadlock with no rule to resolve it) or a genuine game property.
8. **The user's "no cap" (G8).** "No cap" most plausibly means no turn or time cap in the simulation. It could also be read as "no hand-size cap", which would mean Mercy is off. Present the official result (Mercy on, no turn cap) as the headline and the Mercy-off variant as a separate labelled result, and state which reading each answers.
9. **What "solved" means here (G9).** Define it: a zero-sum two-player equilibrium or value, and a general-sum equilibrium concept for 3–6 players. Exact solution is infeasible (RLCard's classic figure alone is about 10^163 information sets). At most, approximate: Monte Carlo or MCTS agents, abstraction plus CFR, or exploitability estimates on small variants. The expected length *under equilibrium play* is also unknown.
10. **Unread sources (G10).** BGG thread bodies (3260915, 3597907, 3240961, 3363721, 3404487, 3289357, 3322195, 3452604, 3331079, 3211870, 3169658), the official Mattel video (youtube RxpKRuk1pIg), Stack Exchange questions 59382 and 61301, and Reddit were not read directly because of proxy blocks. Several defaults (F09, F17, the Roulette color rule, F28) rest partly on snippets.
11. **Unverified prior numbers (G11).** Pfann's 100k figures (the mean matches our rerun), Garg, Corrigan, Table Games Hub, Ramadhan/Iida and the PRR 2025 statistics all remain unverified. Cite them only as such.
12. **Mercy edge cases under non-default timing (G12).** Under F22 ≠ immediate, define what happens when a 25+ hand is swapped or passed before the check, and how a penalty that exceeds the drawable pool is handled.