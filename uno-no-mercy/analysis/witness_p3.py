#!/usr/bin/env python3
"""Build the 3-player endless-game witness results/no_mercy/witness_p3.json.

Seats: 0 = "E", 1 = "N", 2 = "F". Dealer = seat 2, so seat 0 starts; direction +1 (0->1->2->0).
Loop cards: L1 = a Red Reverse (E's), L2 = a Blue Reverse (F's).

Plan (all choices are legal, so each has positive probability under the random policy, and each
deck / reshuffle order has positive probability under a uniform shuffle):
  T1  E plays Wild Color Roulette on the opening G3; N (victim) names Yellow and reveals the 115
      non-yellow cards left in the pile (all remaining wilds and non-yellow Reverses among them),
      stopping on a Yellow Reverse. The 30 cards left in the pile are 29 yellow non-6 non-Reverse
      cards and, at the bottom, the second Y6.
  T2  F plays Y6.   T3 E plays R6.   T4 N plays G6.
  T5  F cannot play on G6, draws the 29 yellow cards (none playable on G6) and then Y6: plays it.
      The draw pile is now empty.
  T6  E plays YD2 (forced).   T7 N accepts the +2: the discard pile is reshuffled and N draws the
      Roulette (the only wild outside N's hand) and G3.
  T8  F plays Y5.   T9 E plays R5 (forced).   T10 N plays R3.   T11 F plays R8.
  T12 E plays L1 = Red Reverse (forced): direction -1, turn to F.
  T13 F plays L2 = Blue Reverse (forced; F holds no red, no Reverse, no wild): direction +1, turn to E.
  T14 E holds no blue, no Reverse, no wild: draws the 4 pile cards and the reshuffled discard
      (YD2 Y5 R5 R3 R8, none playable on a Blue Reverse) and finally L1, which E must play.
  Now only L2 is outside the hands (top L1, discard = {L2}, draw pile empty). F cannot play on
  L1 and E cannot play on L2, so they alternately draw the lone reshuffled card and must play it,
  forever. N (holding all 24 wilds and the 10 other Reverses) never moves again. Nobody ever
  empties their hand, so this never ends under the official ending (end_rule 0) nor under
  "play until one player is left" (end_rule 1).
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import witness_p3_replay as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "no_mercy", "witness_p3.json")


def minus(a, b):
    c = Counter(a)
    c.subtract(Counter(b))
    assert all(v >= 0 for v in c.values()), c
    return c


def build_deck():
    E = ["WRoulette", "RRev", "R6", "YD2", "R5", "G1", "G2"]
    N = ["YRev", "YRev", "G6", "R3", "WWD10", "WWD10", "WWD10"]
    F = ["Y6", "Y5", "BRev", "R8", "B1", "B2", "B3"]
    flip = ["G3"]
    deal = []
    for r in range(7):
        deal += [E[r], N[r], F[r]]
    rest = minus(R.full_deck(), deal + flip)
    canon = R.full_deck()
    nonyellow = []
    for c in canon:                                # canonical order, each type once per copy left
        if R.color(c) != "Y" and rest[c] > 0:
            nonyellow.append(c)
            rest[c] -= 1
    assert len(nonyellow) == 115
    yellow_left = []
    for c in canon:
        if R.color(c) == "Y" and rest[c] > 0:
            yellow_left.append(c)
            rest[c] -= 1
    assert sum(rest.values()) == 0 and len(yellow_left) == 31
    yellow_left.remove("YRev")                     # the Roulette's stopping card
    yellow_left.remove("Y6")                       # the card that ends F's big draw
    assert all(R.kind(c) not in ("6", "Rev") for c in yellow_left) and len(yellow_left) == 29
    pile = nonyellow + ["YRev"] + yellow_left + ["Y6"]
    deck = deal + flip + pile
    assert len(deck) == 168
    return deck, {"0": E, "1": N, "2": F}


PLAN = [  # (what, player, choice) in the order the decisions arise
    ("play", 0, "WRoulette"), ("roulette_color", 1, "Y"),
    ("play", 2, "Y6"), ("play", 0, "R6"), ("play", 1, "G6"),
    ("play", 0, "YD2"), ("stack_or_accept", 1, "accept"),
    ("play", 2, "Y5"), ("play", 0, "R5"), ("play", 1, "R3"), ("play", 2, "R8"),
    ("play", 0, "RRev"), ("play", 2, "BRev"),
]
RESHUFFLE_FIRST = [["WRoulette", "G3"], ["YD2", "Y5", "R5", "R3", "R8"]]   # drawn first, in order; RRev last
N_TURNS = 14


# ---------------------------------------------------------------------------------------------
# Scripted random stream for sim/nomercy.c (random policy): the exact sequence of rng_below(n)
# results that makes the C simulator play this very game (see witness_p3_csim_check.sh).
# ---------------------------------------------------------------------------------------------
TYPE_ORDER = [c + k for c in R.COLORS for k in R.KINDS] + list(R.WILDS)   # sim type index order


def fy_stream(start, target):
    """rng_below results for sim's shuffle_u8 turning array `start` into `target`."""
    a = list(start)
    out = []
    for i in range(len(a) - 1, 0, -1):
        j = next(j for j in range(i + 1) if a[j] == target[i])
        a[i], a[j] = a[j], a[i]
        out.append((j, i + 1))
    assert a == list(target)
    return out


def main():
    deck, hands = build_deck()
    stream = []
    # initial shuffle: sim fills the pile in type order and deals from the END of the array
    canon = [t for t in TYPE_ORDER for _ in range(R.COUNT[t[1:]] if t[0] != "W" else R.WILDS[t])]
    stream += fy_stream(canon, list(reversed(deck)))
    stream.append((2, 3))                                    # dealer = seat 2

    decisions, reshuffles = [], []
    plan = list(PLAN)
    rs_plan = [list(x) for x in RESHUFFLE_FIRST]

    def dcb(what, player, options):
        w, p, ch = plan.pop(0)
        assert (w, p) == (what, player), (w, p, what, player)
        assert ch in options, (ch, options)
        d = {"what": what, "player": player, "choice": ch, "options": options}
        if len(options) == 1:
            d["forced"] = True
        decisions.append(d)
        # C-sim stream: options in sim order
        if what == "play":
            so = [t for t in TYPE_ORDER if t in options]
            stream.append((so.index(ch), len(so)))
        elif what == "stack_or_accept":
            so = [t for t in TYPE_ORDER if t in options]
            if so:                                             # sim draws nothing when n == 0
                stream.append((len(so) if ch == "accept" else so.index(ch), len(so) + 1))
        elif what in ("roulette_color", "wild_color"):
            stream.append(("RYGB".index(ch), 4))
        else:
            raise AssertionError(what)
        return ch

    def rcb(cards):
        first = rs_plan.pop(0)
        order = list(first) + sorted(minus(cards, first).elements(), key=lambda c: (c == "RRev", c))
        reshuffles.append({"cards": sorted(cards), "draw_order": order})
        start = [t for t in TYPE_ORDER for _ in range(Counter(cards)[t])]   # sim appends by type
        stream.extend(fy_stream(start, list(reversed(order))))
        return order

    g = R.Game(3, 0, deck, 2)
    g.decide_cb, g.reshuffle_cb = dcb, rcb
    first_player = g.cur
    opening = {"top": g.top, "ignored_action_cards": list(g.disc)}
    events = []
    for _ in range(N_TURNS):
        ev = g.take_turn()
        ev["after"] = g.summary()
        events.append(ev)
    assert not plan and not rs_plan and not g.over
    entry = g.full_state()
    entry_turn = g.turns
    # one full period of the loop, all forced
    g.forced_only = True
    period = []
    for _ in range(2):
        ev = g.take_turn()
        ev["after"] = g.summary()
        period.append(ev)
    assert g.full_state() == entry

    W = {
        "title": "Explicit endless 3-player UNO Show 'Em No Mercy game without the Mercy rule",
        "players": 3,
        "found": True,
        "end_rules_claimed": [0, 1],
        "end_rule": "both",
        "rules": {"deck": 0, "mercy": "off (-mercy 1000)", "voluntary_draw": 0, "after_draw": 0, "stack_rule": 0,
                  "stack_mandatory": 0, "roulette_chooser": 0, "zero_seven": 1, "reverse2p_skip": 1,
                  "wrd4_2p_self": 1, "finish_effect": 1, "note": "RULES.md sections 1-4 and 7 (defaults); "
                  "nobody ever empties a hand, so end_rule 0 and end_rule 1 give the same history"},
        "card_notation": "colour letter R/Y/G/B + kind (0-9, D2, D4, Skip, SkipAll, Rev, DiscardAll); wilds "
                         "WWRD4 (Wild Reverse Draw 4), WWD6, WWD10, WRoulette (Wild Color Roulette) -- the names "
                         "printed by sim/nomercy.c",
        "deal_procedure": "deck_top_first[0] is the top card of the shuffled face-down deck. Dealer = seat 2, so "
                          "dealing starts at seat 0 (dealer's left): 7 rounds, one card to seats 0,1,2 in turn "
                          "(cards 0..20). Card 21 is flipped: it is a number card, so it starts the discard pile "
                          "(no action cards ignored). Cards 22..167 are the draw pile, top first. Seat 0 (the "
                          "dealer's left) moves first, direction +1 (0->1->2->0).",
        "deck_top_first": deck,
        "dealer": 2,
        "first_player": first_player,
        "opening_flip": opening,
        "initial_hands": hands,
        "roles": {"0": "E: loop player facing the Blue Reverse (holds no blue, Reverse or wild at the loop)",
                  "1": "N: never moves once the loop starts; holds all 24 wilds and the 10 other Reverses",
                  "2": "F: loop player facing the Red Reverse (holds no red, Reverse or wild at the loop)"},
        "decisions": decisions,
        "decisions_note": "every decision in the order it arises (play = card played from hand, stack_or_accept, "
                          "roulette_color named by the victim, wild_color, seven_target). 'options' lists the "
                          "legal distinct options; 'forced' marks a single legal option. Plays of the card that "
                          "ends a draw-until-playable are forced by the rules and are not decisions.",
        "reshuffles": reshuffles,
        "reshuffles_note": "each reshuffle of the discard pile (minus its top card) as the order in which the new "
                           "draw pile is drawn (first = drawn first). One-card reshuffles are trivially forced "
                           "and are not listed.",
        "turns": events,
        "turns_note": "one entry per turn (RULES.md section 6); 'after' is the state after the turn: cur = player "
                      "to move, dir, top, colour, pending stack, hand sizes, draw-pile and discard-pile sizes. A "
                      "Roulette victim's reveal is its own (lost) turn; it is recorded inside the Roulette play "
                      "(roulette.victim_turn) and the turn counter jumps by 2 there.",
        "loop": {
            "entry_state": entry,
            "entry_after_turn": entry_turn,
            "period": 2,
            "period_turns": period,
            "why_forced": "Only L2 = BRev is outside the hands (top RRev, discard {BRev}, draw pile empty). "
                          "Seat 2 holds no red card, no Reverse and no wild, so nothing in hand is playable on the "
                          "Red Reverse: it must draw; the one-card reshuffle gives BRev, which is playable and must "
                          "be played (after_draw 0). Reverse flips the direction to +1, so seat 0 moves. Seat 0 "
                          "holds no blue, no Reverse and no wild: it draws the lone RRev and must play it; the "
                          "direction flips back to -1 and seat 2 moves. The state (all hands, piles, top, colour, "
                          "direction, player to move) is then identical. No decision with two or more options "
                          "and no shuffle of two or more cards ever occurs, and no hand ever becomes empty.",
        },
        "c_sim_rng_stream": [v for v, n in stream],
        "c_sim_rng_bounds": [n for v, n in stream],
        "c_sim_note": "the exact sequence of rng_below(n) results (with the bound n) that makes sim/nomercy.c "
                      "(-p 3 -policy random -mercy 1000 -threads 1 -n 1) play this game; replayed by "
                      "analysis/witness_p3_csim_check.sh, where the simulator's own -detect_cycles proves the "
                      "cycle and the stream is never read again after the loop is entered.",
        "narrative": __doc__.split("Plan (")[1].split('"""')[0].strip(),
    }
    with open(OUT, "w") as f:
        json.dump(W, f, indent=1)
    print("wrote", OUT, "turns:", len(events), "stream:", len(stream))


if __name__ == "__main__":
    main()
