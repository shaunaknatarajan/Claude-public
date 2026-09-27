# UNO Show 'Em No Mercy: rules as simulated

This is the rules spec that `sim/nomercy.c` implements. Every choice is sourced. Where the
official sheet is silent or ambiguous, the default is marked and a command-line flag selects
the alternative.

**Primary source.** Mattel instruction sheet HWV18 (doc code `HWV18-4B70_4LB`, ©2023, marked
"7+ 2-6"), <https://service.mattel.com/instruction_sheets/HVW18-Eng.pdf>. The URL really is
spelled HVW18. Its text was read from a verbatim `pdftotext` dump, because mattel.com blocks
automated fetches:
<https://raw.githubusercontent.com/Aether-123/YouKnow-1/HEAD/pdf_rules_extracted.txt>
(section `--- HVW18-Eng.pdf ---`). A second clean transcription agrees:
<https://raw.githubusercontent.com/timothy0509/uno-cli/HEAD/rules.md>.

**Secondary sources.** Official @realUNOgame posts on X: 1863976235203764712 (2-player Wild
Reverse Draw 4), 1850939942953701796 (Roulette), 1887556543098286580 (Feb 2025: last-card swap
card wins), 1728096146231554184 (7-swap target). The deck breakdown comes from the
cardgameuno fan wiki, as unit-tested in `ayushrudani/no-mercy-uno`.

## 1. Deck (168 cards)

The official sheet says only "Contents 168 Cards", so the breakdown below is secondary-sourced,
but it is the most-cited one:

| Card | Per color | Total |
|---|---|---|
| Numbers 0-9 (two of each, including two 0s) | 20 | 80 |
| Draw 2 | 3 | 12 |
| Draw 4 (colored) | 2 | 8 |
| Skip | 3 | 12 |
| Skip Everyone | 2 | 8 |
| Reverse | 3 | 12 |
| Discard All | 3 | 12 |
| **Colored subtotal** | **36** | **144** |
| Wild Reverse Draw 4 | - | 8 |
| Wild Draw 6 | - | 4 |
| Wild Draw 10 | - | 4 |
| Wild Color Roulette | - | 8 |
| **Total** | | **168** |

There is no plain Wild and no plain Wild Draw 4. The official scoring section's list of "Wild
Action Card[s]" names only the four wild types above. Two other 168-card breakdowns circulate
and are simulated as sensitivity variants (`-deck`):

| `-deck` | Source | Per color | Wilds |
|---|---|---|---|
| `0` (default) | fan wiki; unit-tested by ayushrudani/no-mercy-uno | 36: as in the table above | 8 WRD4, 4 WD6, 4 WD10, 8 Roulette |
| `1` | rajatghate5/no-mercy | 38: 3 colored Draw 4 and 3 Skip Everyone | 4 of each wild type |
| `2` | open-mercy.com | 37: one 0; 3 of every colored action | 4 of each wild type, plus 4 plain Wilds |

Draw values used for stacking: Draw 2 = 2, Draw 4 = 4, Wild Reverse Draw 4 = 4, Wild Draw 6 =
6, Wild Draw 10 = 10. Wild Color Roulette is **not** a Draw Card.

## 2. Setup

- 2 to 6 players, 7 cards each.
- Flip the top card to start the discard pile. "If this card is an Action Card, ignore it and
  flip over the next card." Wilds count as action cards. The ignored cards stay in the discard
  pile. No effect is applied on the opening flip.
- The player to the dealer's left starts, and play goes clockwise. The dealer is uniformly
  random.

## 3. A turn

1. **A draw penalty is pending (a stack):** you may stack any Draw Card whose value is **at
   least the value of the last Draw Card played**. Color is irrelevant (flag `-stack_rule 1`
   also requires a color or symbol match). Otherwise you draw the whole accumulated total and
   lose your turn. Stacking is optional (flag `-stack_mandatory 1`).
2. **Otherwise:** you may play one card that matches the top card by color, number or symbol,
   or any wild. Official: "If you HAVE a matching card in your hand, you may PLAY IT."
   - Default (strict): you must play if you can. Flag `-voluntary_draw 1` lets you decline; you
     then draw until playable and must play that card, exactly as if you had had no playable
     card.
   - If you have no playable card: "you MUST draw cards from the Draw Pile UNTIL YOU DRAW A
     CARD YOU CAN PLAY. Then, play that card." This is `-after_draw 0`. Flags `1` (may keep
     it) and `2` (keep it, turn ends) are alternatives.
3. When you play a wild, you name the color in play.
4. "When a player plays their final card, they win." The win is immediate, and the last card's
   effect (0/7/draw/etc.) is not applied.

## 4. Card effects

| Card | Effect |
|---|---|
| Number (not 0 or 7) | None. |
| **0** | All active players pass their hands to the next active player in the current direction. |
| **7** | You must swap hands with another active player of your choice. |
| Skip | The next player loses their turn. |
| Skip Everyone | "Skip all the other players and take another turn." |
| Reverse | The direction reverses. With 2 players it acts as a Skip ("letting you take another turn"). |
| Discard All | You also discard every other card in your hand of this card's color, placed under it, so their effects do not trigger. It can win the game. |
| Draw 2 / Draw 4 / Wild Draw 6 / Wild Draw 10 | Adds 2/4/6/10 to the pending penalty for the next player. The victim either stacks or draws the total and loses their turn. |
| Wild Reverse Draw 4 | "Reverse the direction of play, then the next player in the new direction must draw 4 cards and lose their turn." **With 2 players, "this card skips the other player and makes YOU draw 4 cards! You may use the stacking rule to send the penalty back"** (flag `-wrd4_2p_self`). This applies when it is played into a stack as well. |
| Wild Color Roulette | "The next player chooses a color. After that, they must reveal cards one at a time from the Draw Pile until they get a card of that color (Wild Cards do NOT count). Then they add all the revealed cards to their hand and lose their turn." The color in play afterwards is the victim's chosen color. Flag `-roulette_chooser 1` has the player of the card name it instead. |

## 5. Mercy rule and the end of the game

- "If a player ever has 25 or more cards in their hand, they are out of the game." The check is
  immediate, including in the middle of a draw.
- "Set aside their hand of cards until the deck runs out and needs to be reshuffled." The
  set-aside cards join the discard pile at the next reshuffle (`-elim_cards 2`). The
  alternatives are `0` (shuffled straight into the draw pile) and `1` (bottom of the draw
  pile).
- Eliminated players are skipped. They are not 7-swap targets and are not part of the 0-pass
  chain.
- The game ends when a player empties their hand, or when only one player remains.
- When the draw pile is empty, the discard pile (minus its top card) is shuffled to form a new
  draw pile.

**Derived fact (no deadlock).** With at most 6 players, every active hand holds at most 24
cards. So at least 168 − 5·24 − h − 1 = 47 − h cards are in the draw pile, discard pile (below
its top card) and set-aside pile, which is more than the 25 − h a knockout needs. Any
draw-until-playable, penalty or roulette sequence therefore always reaches a playable card, the
target color or a knockout. The draw and discard piles can never both run dry mid-sequence.

## 6. What a "turn" is (for game-length statistics)

A turn is every time the turn marker lands on a player and that player acts: they play,
accept a penalty, draw until playable, or (as a Wild Color Roulette victim) name a color and
reveal cards. The extra turn from Skip Everyone, and the "go again" from Skip, Reverse or Wild
Reverse Draw 4 with 2 players, count as separate turns. Skipped players do not get a turn.

Note: the first cross-check (`crosscheck/`) was run before Roulette reveals were counted as
turns. Both implementations used that older definition, so their comparison is valid. Results
under the current definition are in `results/final/`; they are about 6% higher.

## 7. House variant: play until one player is left (`-end_rule 1`)

Many tables don't stop when the first player goes out. Players who empty their hand
**finish** and leave the game, and play continues until only one player still holds cards. That
player is the loser. The official Mercy rule can be kept (`-mercy 25`, variant A) or dropped
(`-mercy 1000`, variant B, where finishing is the only way out). Everything in §1–§6 is
unchanged except for the following.

- **Finishing.** A player who plays their last card (including by Discard All) finishes at
  once. Their seat is skipped from then on, like a knocked-out player's. They are not a 7-swap
  target and are not part of the 0-pass chain.
- **The game ends** when only one player is left in play. That can happen by finishing or by a
  Mercy knockout. The first player to finish is recorded as the winner; if nobody finished,
  the last player standing is.
- **The finishing card still takes effect** (`-finish_effect 1`, the default), applied to the
  players still in, starting from the finisher's seat:
  - Draw cards add to the pending penalty, which passes to the next player in the direction
    of play (after a Wild Reverse Draw 4, in the new direction). The two-player self-hit rule
    of the Wild Reverse Draw 4 does not apply, because its player is no longer in the game.
  - Skip skips the next player. Reverse reverses the direction; the turn passes to the next
    player in the new direction.
  - Skip Everyone would give the finisher another turn, so the turn passes to the next player.
  - A wild's colour is named by the finisher. Wild Color Roulette hits the next player, who
    names a colour and reveals cards as usual.
  - A 0 makes the remaining players pass their hands on. A 7 does nothing, because the finisher
    has no hand to swap.
- **Alternative** (`-finish_effect 0`): the finishing card has no effect beyond setting the
  colour. Any penalty that was already pending stays with the next player, unchanged. The turn
  passes to the next player.
- **Turns** are counted exactly as in §6.
- **Deadlock without the Mercy rule.** In variant B the hands can hold every card but the top
  one. Then a player who can neither play nor draw passes. If every remaining player passes
  twice in a row with nothing changing, the game is stuck forever and counts as never ending.
