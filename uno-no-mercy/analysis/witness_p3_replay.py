#!/usr/bin/env python3
"""Standalone replay checker for an explicit endless-game witness (UNO Show 'Em No Mercy).

Usage:  python3 analysis/witness_p3_replay.py [results/no_mercy/witness_p3.json]

It re-plays the witness move by move under RULES.md sections 1-4 and 7 (deck 0, no Mercy rule,
strict play, after_draw 0, stack_rule 0, roulette_chooser 0, 0/7 on, Reverse = Skip with two
players, finishing card takes effect under end_rule 1), and asserts that:

  * the deal deck is a permutation of the 168-card deck, and the deal / opening flip follow
    RULES.md section 2 (7 rounds of one card per seat starting at seat 0 = the dealer's left);
  * every decision is legal (a playable card, a stackable card or accept, a colour, a 7 target),
    and every reshuffle order is a permutation of the discard pile minus its top card;
  * the recorded state after every turn matches the replayed one;
  * from the final state the game is FORCED: every turn has exactly one legal option, every
    reshuffle has at most one card (so one possible order), no wild colour / Roulette colour /
    7-target / stack decision ever arises, nobody empties their hand, and the complete state
    recurs after the stated period.  Hence the game never ends.

It does this for each end rule the witness claims (end_rule 0 = official, 1 = play until one
player is left).  Only the Python standard library is used.
"""
import json
import sys

COLORS = "RYGB"
KINDS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "D2", "D4", "Skip", "SkipAll", "Rev", "DiscardAll"]
COUNT = {"0": 2, "1": 2, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2, "7": 2, "8": 2, "9": 2,
         "D2": 3, "D4": 2, "Skip": 3, "SkipAll": 2, "Rev": 3, "DiscardAll": 3}
WILDS = {"WWRD4": 8, "WWD6": 4, "WWD10": 4, "WRoulette": 8}   # names as printed by sim/nomercy.c
DRAWVAL = {"D2": 2, "D4": 4, "WRD4": 4, "WD6": 6, "WD10": 10}


def full_deck():
    d = []
    for c in COLORS:
        for k in KINDS:
            d += [c + k] * COUNT[k]
    for w, n in WILDS.items():
        d += [w] * n
    assert len(d) == 168
    return d


def color(card):
    return "W" if card[0] == "W" else card[0]


def kind(card):
    return card[1:]          # "Rev", "D2", "WRD4", "Roulette", ...


def is_wild(card):
    return card[0] == "W"


def drawval(card):
    return DRAWVAL.get(kind(card), 0)


class Rejected(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise Rejected(msg)


class Game:
    """State + rules. Nature (reshuffle orders) and decisions come from callbacks."""

    def __init__(self, np_, end_rule, deck_top_first, dealer):
        need(sorted(deck_top_first) == sorted(full_deck()), "deal deck is not the 168-card deck")
        need(0 <= dealer < np_, "bad dealer")
        self.np = np_
        self.end_rule = end_rule
        self.hands = [[] for _ in range(np_)]
        self.alive = [True] * np_
        pile = list(deck_top_first)            # index 0 = top of the face-down deck
        for _ in range(7):                     # RULES.md 2: 7 cards each, one at a time,
            for s in range(np_):               # starting with the dealer's left (= seat 0 here,
                self.hands[s].append(pile.pop(0))   # see first_player below)
        self.disc = []                         # discard pile below the top card
        while True:                            # opening flip: action cards are ignored
            t = pile.pop(0)
            if not is_wild(t) and kind(t) in KINDS[:10]:
                self.top, self.color = t, color(t)
                break
            self.disc.append(t)
        self.pile = pile
        self.dir = 1
        self.cur = (dealer + 1) % np_          # the player to the dealer's left starts
        self.stack = 0
        self.stackv = 0
        self.turns = 0
        self.over = False
        self.winner = None
        self.finished = []
        self.log = []                          # human-readable events of the current turn
        self.forced_only = False               # loop check: reject any genuine choice
        self.reshuffle_cb = None
        self.decide_cb = None

    # -- helpers --------------------------------------------------------------
    def nalive(self):
        return sum(self.alive)

    def next_alive(self, p, d):
        q = p
        while True:
            q = (q + d) % self.np
            if self.alive[q]:
                return q

    def playable(self, card):
        if is_wild(card) or color(card) == self.color:
            return True
        return (not is_wild(self.top)) and kind(card) == kind(self.top)

    def stackable(self, card):
        v = drawval(card)
        return v > 0 and v >= self.stackv

    def decide(self, what, player, options):
        """Ask for a decision among `options` (distinct values). Returns the chosen value."""
        options = list(dict.fromkeys(options))
        need(len(options) >= 1, f"no options for {what}")
        if self.forced_only:
            need(len(options) == 1, f"loop is not forced: {what} by p{player} has options {options}")
            return options[0]
        ch = self.decide_cb(what, player, options)
        need(ch in options, f"illegal {what} by p{player}: {ch!r} not in {options}")
        return ch

    def reshuffle(self):
        cards = list(self.disc)
        self.disc = []
        if len(cards) <= 1:
            order = cards
        else:
            need(not self.forced_only, f"loop is not forced: a reshuffle of {len(cards)} cards")
            order = self.reshuffle_cb(sorted(cards))
            need(sorted(order) == sorted(cards), "reshuffle order is not a permutation of the discard pile")
        self.pile = list(order)                # order[0] is drawn first
        self.log.append({"reshuffle": list(order)})

    def draw_one(self, p):
        if not self.pile:
            self.reshuffle()
        if not self.pile:
            return None
        c = self.pile.pop(0)
        self.hands[p].append(c)
        return c

    # -- a turn ---------------------------------------------------------------
    def take_turn(self):
        self.log = []
        p = self.cur
        self.turns += 1
        ev = {"turn": self.turns, "player": p, "facing": {"top": self.top, "color": self.color,
                                                          "stack": self.stack}}
        if self.stack > 0:
            opts = sorted({c for c in self.hands[p] if self.stackable(c)})
            ch = self.decide("stack_or_accept", p, opts + ["accept"])
            if ch != "accept":
                ev["action"] = "stack"
                ev["card"] = ch
                self.play_card(p, ch, ev)
            else:
                total = self.stack
                self.stack = self.stackv = 0
                drawn = []
                for _ in range(total):
                    c = self.draw_one(p)
                    if c is None:
                        break
                    drawn.append(c)
                ev["action"] = "accept_penalty"
                ev["drawn"] = drawn
                self.cur = self.next_alive(p, self.dir)
        else:
            opts = sorted({c for c in self.hands[p] if self.playable(c)})
            if opts:
                ch = self.decide("play", p, opts)
                ev["action"] = "play"
                ev["card"] = ch
                self.play_card(p, ch, ev)
            else:
                drawn = []
                while True:
                    c = self.draw_one(p)
                    if c is None:
                        break
                    drawn.append(c)
                    if self.playable(c):
                        break
                ev["action"] = "draw_until_playable"
                ev["drawn"] = drawn
                if drawn and self.playable(drawn[-1]):
                    ev["card"] = drawn[-1]         # after_draw 0: must play it (forced)
                    self.play_card(p, drawn[-1], ev)
                else:
                    need(False, "a player could neither play nor draw (stuck position)")
        if self.log:
            ev["nature"] = self.log
        return ev

    def play_card(self, p, t, ev):
        self.hands[p].remove(t)
        self.disc.append(self.top)
        self.top = t
        k, c = kind(t), color(t)
        if is_wild(t):
            if k != "Roulette":
                self.color = self.decide("wild_color", p, list(COLORS))
                ev["wild_color"] = self.color
        else:
            self.color = c
        if k == "DiscardAll":
            same = [x for x in self.hands[p] if color(x) == c]
            for x in same:
                self.hands[p].remove(x)
                self.disc.append(x)
            ev["discarded_with_it"] = same
        fin = False
        if not self.hands[p]:
            if self.end_rule == 0:
                self.over, self.winner = True, p
                ev["result"] = f"p{p} emptied their hand and wins"
                return
            fin = True
            self.alive[p] = False
            self.finished.append(p)
            ev["finished"] = p
            if self.nalive() == 1:
                self.over, self.winner = True, self.finished[0]
                return
        if k in ("D2", "D4", "WD6", "WD10"):
            self.stack += drawval(t)
            self.stackv = drawval(t)
            self.cur = self.next_alive(p, self.dir)
        elif k == "WRD4":
            self.stack += 4
            self.stackv = 4
            if not fin and self.nalive() == 2:
                self.dir = -self.dir
                self.cur = p
            else:
                self.dir = -self.dir
                self.cur = self.next_alive(p, self.dir)
        elif k == "Skip":
            self.cur = self.next_alive(self.next_alive(p, self.dir), self.dir)
        elif k == "SkipAll":
            self.cur = self.next_alive(p, self.dir) if fin else p
        elif k == "Rev":
            self.dir = -self.dir
            self.cur = p if (not fin and self.nalive() == 2) else self.next_alive(p, self.dir)
        elif k == "Roulette":
            victim = self.next_alive(p, self.dir)
            self.turns += 1                    # the victim's (lost) turn counts as a turn
            col = self.decide("roulette_color", victim, list(COLORS))
            self.color = col
            revealed = []
            while True:
                x = self.draw_one(victim)
                if x is None:
                    break
                revealed.append(x)
                if color(x) == col:
                    break
            ev["roulette"] = {"victim": victim, "color": col, "revealed": revealed, "victim_turn": self.turns}
            self.cur = self.next_alive(victim, self.dir)
        elif k == "0":
            order = [q for q in range(self.np) if self.alive[q]]
            new = {}
            for q in order:
                new[self.next_alive(q, self.dir)] = self.hands[q]
            for q in order:
                self.hands[q] = new[q]
            self.cur = self.next_alive(p, self.dir)
        elif k == "7":
            if not fin:
                q = self.decide("seven_target", p, [q for q in range(self.np) if q != p and self.alive[q]])
                self.hands[p], self.hands[q] = self.hands[q], self.hands[p]
                ev["seven_target"] = q
            self.cur = self.next_alive(p, self.dir)
        else:
            self.cur = self.next_alive(p, self.dir)

    # -- state ----------------------------------------------------------------
    def summary(self):
        return {"cur": self.cur, "dir": self.dir, "top": self.top, "color": self.color,
                "stack": self.stack, "stackv": self.stackv, "hand_sizes": [len(h) for h in self.hands],
                "alive": list(self.alive), "pile": len(self.pile), "disc": len(self.disc)}

    def full_state(self):
        return {"cur": self.cur, "dir": self.dir, "top": self.top, "color": self.color,
                "stack": self.stack, "stackv": self.stackv, "alive": list(self.alive),
                "hands": [sorted(h) for h in self.hands], "pile_top_first": list(self.pile),
                "discard_below_top": sorted(self.disc)}


def replay(W, end_rule):
    """Replay witness W under the given end rule. Returns (game, events)."""
    g = Game(W["players"], end_rule, W["deck_top_first"], W["dealer"])
    need(g.cur == W["first_player"], "first player mismatch")
    need(g.top == W["opening_flip"]["top"], "opening top mismatch")
    need(g.disc == W["opening_flip"]["ignored_action_cards"], "opening flip ignored cards mismatch")
    for s in range(g.np):
        need(sorted(g.hands[s]) == sorted(W["initial_hands"][str(s)]), f"initial hand of seat {s} mismatch")
    decisions = list(W["decisions"])
    reshuffles = list(W["reshuffles"])

    def dcb(what, player, options):
        need(decisions, f"ran out of decisions at {what} by p{player}")
        d = decisions.pop(0)
        need(d["what"] == what and d["player"] == player, f"decision mismatch: expected {what}/p{player}, got {d}")
        need(d.get("forced", False) == (len(options) == 1), f"decision 'forced' flag wrong: {d} options {options}")
        return d["choice"]

    def rcb(cards):
        need(reshuffles, "ran out of reshuffle orders")
        r = reshuffles.pop(0)
        return r["draw_order"]

    g.decide_cb, g.reshuffle_cb = dcb, rcb
    events = []
    rec = W["turns"]
    for i, want in enumerate(rec):
        need(not g.over, f"game ended early at record {i}")
        ev = g.take_turn()
        ev["after"] = g.summary()
        for key in ("turn", "player", "action", "after"):
            need(ev.get(key) == want.get(key), f"turn {ev['turn']}: {key} mismatch {ev.get(key)} vs {want.get(key)}")
        if "card" in want or "card" in ev:
            need(ev.get("card") == want.get("card"), f"turn {ev['turn']}: card mismatch")
        events.append(ev)
    need(not decisions, f"{len(decisions)} unused decisions")
    need(not reshuffles, f"{len(reshuffles)} unused reshuffles")
    fs = g.full_state()
    need(fs == W["loop"]["entry_state"], "final state differs from the witness's loop entry state")
    return g, events


def check_loop(g, period, max_turns=50):
    """From g's current state, play with forced_only=True; return the period found."""
    start = json.dumps(g.full_state(), sort_keys=True)
    g.forced_only = True
    for k in range(1, max_turns + 1):
        ev = g.take_turn()
        need(not g.over, "the game ended inside the claimed loop")
        need(all(len(h) > 0 for q, h in enumerate(g.hands) if g.alive[q]), "someone emptied their hand")
        if json.dumps(g.full_state(), sort_keys=True) == start:
            need(k == period, f"state recurred after {k} turns, witness claims {period}")
            return k
    raise Rejected("state did not recur")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "results/no_mercy/witness_p3.json"
    W = json.load(open(path))
    rules = W["end_rules_claimed"]
    for er in rules:
        g, events = replay(W, er)
        per = check_loop(g, W["loop"]["period"])
        print(f"end_rule {er}: {len(events)} recorded turns replayed legally; from turn {g.turns - per} on "
              f"the state repeats every {per} turns with no choice and no random event -> the game never ends")
    print("WITNESS OK")


if __name__ == "__main__":
    try:
        main()
    except Rejected as e:
        print("WITNESS REJECTED:", e)
        sys.exit(1)
