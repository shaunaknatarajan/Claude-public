#!/usr/bin/env python3
"""Step-by-step UNO Show 'Em No Mercy engine for games played by AI players with personalities.

The rules are exactly those of ../RULES.md, the same as the verified C simulator
../sim/nomercy.c and the Python reference ../crosscheck/ref_nomercy.py. Unlike those, this
engine stops at every decision that has more than one option and waits for the player, who only
ever sees their own hand plus what is public at the table.

Game state lives in <game-dir>/state.pkl, and every event is appended to <game-dir>/log.txt.

CLI:
  engine.py new  --game DIR --players Name1,Name2,... [--seed S] [--end-rule first|last] [--mercy N]
  engine.py view --game DIR            # what the player to move can see, with numbered options
  engine.py act  --game DIR --player NAME --choice K [--note TEXT]
  engine.py status --game DIR          # one-line JSON: whose decision, or the result
  engine.py autoplay --players N --games G [--seed S] [--end-rule first|last] [--mercy N] [--jobs J]
                                       # random play, to validate against the C simulator

Rule options (defaults = the official game; C simulator flags in brackets):
  --end-rule first   Official: the first player to empty their hand wins and the game ends
                     [-end_rule 0].
  --end-rule last    RULES.md section 7, "play until one player is left" [-end_rule 1
                     -finish_effect 1]. A player who empties their hand FINISHES and leaves the
                     game; the finishing card still takes effect on the players still in (a 0
                     passes hands among them only, a 7 does nothing, Skip Everyone passes the turn
                     on, and the two-player Wild Reverse Draw 4 self-hit and Reverse-as-Skip rules
                     do not apply to a finisher). The game ends when one player is left in play.
                     Places: finishers in finishing order, then the last player in play, then
                     knocked-out players (last knocked out first). The first finisher wins (if
                     nobody finished, the last player standing does); the last place is the loser.
                     Without the Mercy rule that is simply the last player still holding cards.
  --mercy N          A hand of N or more cards is knocked out (Mercy rule; default 25). 0, or any
                     N above 167 such as 1000, means no Mercy rule: nobody is ever knocked out
                     [-mercy 1000].

Without the Mercy rule the draw pile and the discard pile (below its top card) can both run dry.
Then, as in RULES.md section 7, a player who can neither play nor draw passes; a penalty or a
Roulette reveal stops when nothing is left to draw. If every player still in passes twice in a
row with nothing changing, the game is stuck forever (end_reason "stuck forever", status
"stuck": true). The engine also recognises a provably endless game: the complete position
repeats with no free decision and no random shuffle in between, so it would repeat forever
(status "endless": true). Both need the draw pile and discard pile to hold 2 cards or fewer
between them, so neither can happen with the 25-card Mercy rule.

A turn is counted exactly as in RULES.md section 6 (a Roulette victim's reveal is a turn), so
game lengths are directly comparable with the robot simulations.
"""
import argparse
import json
import os
import pickle
import random
import sys
from collections import Counter

# ----------------------------------------------------------------------------- cards
K_D2, K_D4, K_SKIP, K_SKIPALL, K_REV, K_DALL = 10, 11, 12, 13, 14, 15
WRD4, WD6, WD10, ROUL = 64, 65, 66, 67
MERCY = 25
HAND0 = 7
DECK = 168
EMPTY = -1                 # draw_one: nothing left to draw anywhere (only possible without the Mercy rule)
LOOP_MEMORY = 200000       # loop detection: forget older positions beyond this many (keeps it sound)
COLORS = ["Red", "Yellow", "Green", "Blue"]
KIND_LONG = {K_D2: "Draw 2", K_D4: "Draw 4", K_SKIP: "Skip", K_SKIPALL: "Skip Everyone", K_REV: "Reverse",
             K_DALL: "Discard All"}
WILD_LONG = {WRD4: "Wild Reverse Draw 4", WD6: "Wild Draw 6", WD10: "Wild Draw 10", ROUL: "Wild Color Roulette"}
PRONOUN = {"Maya": "her", "Priya": "her", "Zoe": "her", "Joe": "his", "Tyler": "his", "Leo": "his"}


def build_deck():
    deck = []
    for c in range(4):
        b = c * 16
        for num in range(10):
            deck += [b + num] * 2
        deck += [b + K_D2] * 3 + [b + K_D4] * 2 + [b + K_SKIP] * 3 + [b + K_SKIPALL] * 2
        deck += [b + K_REV] * 3 + [b + K_DALL] * 3
    deck += [WRD4] * 8 + [WD6] * 4 + [WD10] * 4 + [ROUL] * 8
    assert len(deck) == DECK
    return deck


def color_of(t):
    return -1 if t >= 64 else t >> 4


def kind_of(t):
    return t if t >= 64 else t & 15


def draw_value(t):
    if t >= 64:
        return {WRD4: 4, WD6: 6, WD10: 10}.get(t, 0)
    return {K_D2: 2, K_D4: 4}.get(t & 15, 0)


def name(t):
    if t >= 64:
        return WILD_LONG[t]
    k = t & 15
    return f"{COLORS[t >> 4]} {KIND_LONG.get(k, str(k))}"


def short_name(t):
    """Card name without its colour (the hand is shown grouped by colour)."""
    return WILD_LONG[t] if t >= 64 else KIND_LONG.get(t & 15, str(t & 15))


def ordinal(k):
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def norm_mercy(m):
    """Mercy threshold, or 0 for no Mercy rule (a hand can never reach more than 167 cards)."""
    if m is None or m <= 0 or m >= DECK:
        return 0
    if m < 2:
        raise ValueError("--mercy must be 0 (no Mercy rule) or at least 2")
    return m


def new_attrs():
    """Attributes added after the first games were saved; old pickles get these defaults on load."""
    return {"end_rule": "first", "mercy": MERCY, "finished": [], "ko_seats": [], "loser": None, "placings": None,
            "stuck_run": 0, "stuck": False, "endless": False, "loop_seen": {}, "detect_loops": True,
            "zeros": 0, "sevens": 0, "roulettes": 0, "max_hand": HAND0, "dry_draws": 0, "quiet": False}


# ----------------------------------------------------------------------------- game
class Game:
    def __init__(self, names, seed, end_rule="first", mercy=MERCY, quiet=False):
        n = len(names)
        assert 2 <= n <= 6, "the official game is for 2-6 players"
        assert end_rule in ("first", "last"), end_rule
        self.__dict__.update(new_attrs())
        self.end_rule = end_rule
        self.mercy = norm_mercy(mercy)
        self.quiet = quiet
        self.names = list(names)
        self.n = n
        self.rng = random.Random(seed)
        self.pile = build_deck()
        self.rng.shuffle(self.pile)
        self.discard = []          # below the top card; knocked-out hands are added here (set aside)
        self.hands = [Counter() for _ in range(n)]
        self.alive = [True] * n    # still in play (not knocked out, not finished)
        self.dir = 1
        self.pending = 0
        self.last_dv = 0
        self.over = False
        self.winner = None
        self.end_reason = None
        self.turns = self.plays = self.draws = self.reshuffles = self.decisions = 0
        self.knockouts = []        # (turn, name)
        self.log = []
        self.notes = [[] for _ in range(n)]
        self.decision = None       # dict: player, kind, options
        self.after = None          # continuation after a mid-play decision (color / target)
        for _ in range(HAND0):
            for p in range(n):
                self.hands[p][self.pile.pop()] += 1
        while True:                # opening flip: ignore action and wild cards
            t = self.pile.pop()
            if t < 64 and (t & 15) <= 9:
                self.top, self.color = t, t >> 4
                break
            self.discard.append(t)
        dealer = self.rng.randrange(n)
        self.cur = (dealer + 1) % n
        self.say(f"{self.names[dealer]} deals. Starting card: {name(self.top)}. {self.names[self.cur]} goes first.")
        self.begin_turn()

    def __setstate__(self, state):
        # games saved before the rule options existed are official-rule games: fill in the defaults
        for k, v in new_attrs().items():
            state.setdefault(k, v)
        self.__dict__.update(state)

    # ------------------------------------------------------------------ helpers
    def official(self):
        return self.end_rule == "first" and self.mercy == MERCY

    def say(self, msg):
        if not self.quiet:
            self.log.append(f"[turn {self.turns}] {msg}")

    def size(self, p):
        return sum(self.hands[p].values())

    def n_alive(self):
        return sum(self.alive)

    def nxt(self, p, d=None):
        d = self.dir if d is None else d
        q = (p + d) % self.n
        while not self.alive[q]:
            q = (q + d) % self.n
        return q

    def playable(self, t):
        if t >= 64 or (t >> 4) == self.color:
            return True
        return self.top < 64 and (t & 15) == (self.top & 15)

    def pron(self, p):
        return PRONOUN.get(self.names[p], "their")

    def draw_one(self, p):
        """Give p one card. Returns the card, None if p was knocked out (Mercy rule), or EMPTY if the
        draw pile and the discard pile are both empty (possible only without the Mercy rule)."""
        if not self.pile:
            if not self.discard:
                self.dry_draws += 1
                return EMPTY
            self.pile = self.discard
            self.discard = []
            if len(self.pile) >= 2:
                self.loop_seen.clear()     # a random shuffle: the future is not determined any more
            self.rng.shuffle(self.pile)
            self.reshuffles += 1
            if self.official():
                self.say("The discard pile is shuffled into a new draw pile.")
            else:
                self.say(f"The discard pile is shuffled into a new draw pile ({len(self.pile)} card(s)).")
        t = self.pile.pop()
        self.hands[p][t] += 1
        self.draws += 1
        self.stuck_run = 0
        sz = self.size(p)
        if sz > self.max_hand:
            self.max_hand = sz
        if self.mercy and sz >= self.mercy:
            self.knock_out(p)
            return None
        return t

    def knock_out(self, p):
        self.say(f"{self.names[p]} reaches {self.mercy} cards and is knocked out by the Mercy rule!")
        for t, k in self.hands[p].items():
            self.discard += [t] * k
        self.hands[p] = Counter()
        self.alive[p] = False
        self.knockouts.append((self.turns, self.names[p]))
        self.ko_seats.append(p)
        if self.n_alive() == 1:
            if self.end_rule == "last":
                self.end_last()
            else:
                w = self.alive.index(True)
                self.finish(w, "last player standing")

    def finish(self, w, reason):
        """Official ending: w wins and the game is over."""
        if not self.over:
            self.over, self.winner, self.end_reason = True, w, reason
            self.decision = None
            self.say(f"GAME OVER after {self.turns} turns: {self.names[w]} wins ({reason}).")

    def player_finishes(self, p):
        """end_rule last: p has emptied their hand and leaves the game."""
        self.alive[p] = False
        self.finished.append((self.turns, p))
        k = len(self.finished)
        self.say(f"{self.names[p]} plays {self.pron(p)} last card and finishes {ordinal(k)}!"
                 + (" (the winner)" if k == 1 else ""))
        if self.n_alive() == 1:
            self.end_last()

    def end_last(self):
        """end_rule last: only one player is left in play."""
        if self.over:
            return
        left = [q for q in range(self.n) if self.alive[q]]
        self.placings = [q for _, q in self.finished] + left + self.ko_seats[::-1]
        self.over, self.winner, self.loser = True, self.placings[0], self.placings[-1]
        self.end_reason = "only one player left in play"
        self.decision = None
        last = self.names[left[0]]
        if self.finished:
            head = f"only {last} still holds cards"
            if not self.ko_seats:
                head += f", so {last} loses"
        else:
            head = f"{last} is the last player standing and wins"
        places = ", ".join(f"{ordinal(i + 1)} {self.names[q]}" + (" (knocked out)" if q in self.ko_seats else "")
                           for i, q in enumerate(self.placings))
        self.say(f"GAME OVER after {self.turns} turns: {head}. Places: {places}.")

    def end_never(self, kind, msg):
        """The game can never end: kind 'stuck' (nobody can play or draw) or 'endless' (a forced loop)."""
        self.over = True
        self.decision = None
        self.winner = self.finished[0][1] if self.finished else None
        self.loser = None
        if kind == "stuck":
            self.stuck = True
            self.end_reason = "stuck forever: nobody can play or draw"
        else:
            self.endless = True
            self.end_reason = "endless loop: the same position repeats forever with no choice to make"
        still = ", ".join(f"{self.names[q]} ({self.size(q)})" for q in range(self.n) if self.alive[q])
        self.say(f"{msg} GAME NEVER ENDS after {self.turns} turns. Still holding cards: {still}.")

    def loop_key(self):
        return (tuple(tuple(sorted(h.items())) for h in self.hands), tuple(self.alive), tuple(self.pile),
                tuple(sorted(self.discard)), self.top, self.color, self.cur, self.dir, self.pending, self.last_dv,
                self.stuck_run)

    def check_loop(self):
        """Called between turns while the draw and discard piles hold <= 2 cards (every position of a
        forced loop does). The positions seen since the last free decision or random shuffle are
        remembered; seeing one again proves the game repeats forever."""
        key = self.loop_key()
        seen = self.loop_seen
        if key in seen:
            self.end_never("endless", f"The same position has come back after {self.turns - seen[key]} turns "
                                      "with no choice to make and no shuffle in between, so it will repeat forever.")
            return True
        if len(seen) >= LOOP_MEMORY:
            seen.clear()
        seen[key] = self.turns
        return False

    # ------------------------------------------------------------------ turn flow
    def begin_turn(self):
        """Start the current player's turn; resolve everything automatic until a decision is needed."""
        while not self.over:
            if self.detect_loops and len(self.pile) + len(self.discard) <= 2 and self.check_loop():
                return
            p = self.cur
            self.turns += 1
            if self.pending:
                opts = [("accept", None, None)]
                for t in sorted(self.hands[p]):
                    if draw_value(t) >= self.last_dv > 0:
                        if t >= 64:
                            opts += [("stack", t, c) for c in range(4)]
                        else:
                            opts.append(("stack", t, None))
                if len(opts) == 1:
                    self.accept(p)
                    continue
                self.decision = {"player": p, "kind": "penalty", "options": opts}
                return
            opts = []
            for t in sorted(self.hands[p]):
                if not self.playable(t):
                    continue
                if t >= 64 and t != ROUL:
                    opts += [("play", t, c) for c in range(4)]
                elif t < 64 and (t & 15) == 7 and self.size(p) > 1:
                    opts += [("play", t, q) for q in range(self.n) if q != p and self.alive[q]]
                else:
                    opts.append(("play", t, None))
            if not opts:
                self.draw_until_playable(p)
                if self.decision or self.over:
                    return
                continue
            if len(opts) == 1:
                self.execute(p, opts[0])
                if self.decision or self.over:
                    return
                continue
            self.decision = {"player": p, "kind": "play", "options": opts}
            return

    def accept(self, p):
        total = self.pending
        self.pending = self.last_dv = 0
        self.say(f"{self.names[p]} can't or won't stack and draws the penalty of {total}.")
        got = 0
        for _ in range(total):
            t = self.draw_one(p)
            if t is None:
                break
            if t == EMPTY:
                self.say(f"The draw pile and the discard pile are empty: {self.names[p]} gets only {got} of the "
                         f"{total} cards ({self.size(p)} cards).")
                break
            got += 1
        if not self.over:
            self.cur = self.nxt(p)

    def draw_until_playable(self, p):
        k = 0
        while True:
            t = self.draw_one(p)
            if t == EMPTY:
                # without the Mercy rule the piles can run dry: the player can neither play nor draw, so passes
                self.stuck_run += 1
                got = f"draws {k} card(s), " if k else ""
                self.say(f"{self.names[p]} has nothing playable, {got}and there is no card left to draw "
                         f"(draw pile and discard pile empty): {self.names[p]} passes.")
                if self.stuck_run >= 2 * self.n_alive():
                    self.end_never("stuck", "Every player still in has passed twice in a row with nothing "
                                            "changing, so the game is stuck forever.")
                    return
                self.cur = self.nxt(p)
                return
            k += 1
            if t is None:
                if not self.over:
                    self.cur = self.nxt(p)
                return
            if self.playable(t):
                break
        self.say(f"{self.names[p]} has nothing playable, draws {k} card(s) and must play the {name(t)}.")
        # the drawn card must be played; it may still need a colour or a swap target
        if t >= 64 and t != ROUL:
            self.decision = {"player": p, "kind": "forced_color", "options": [("play", t, c) for c in range(4)]}
        elif t < 64 and (t & 15) == 7 and self.size(p) > 1:
            tg = [q for q in range(self.n) if q != p and self.alive[q]]
            if len(tg) == 1:
                self.play(p, t, tg[0])
            else:
                self.decision = {"player": p, "kind": "forced_swap", "options": [("play", t, q) for q in tg]}
        else:
            self.play(p, t, None)

    def execute(self, p, opt):
        act, t, x = opt
        if act == "accept":
            self.accept(p)
        else:
            self.play(p, t, x)

    def play(self, p, t, x):
        """p plays card t; x = colour for wilds (not Roulette) or target seat for a 7."""
        self.stuck_run = 0
        self.hands[p][t] -= 1
        if not self.hands[p][t]:
            del self.hands[p][t]
        self.discard.append(self.top)
        self.top = t
        self.plays += 1
        k = kind_of(t)
        if t >= 64 and t != ROUL:
            self.color = x
            desc = f"{name(t)}, naming {COLORS[x]}"
        elif t == ROUL:
            desc = name(t)
        else:
            self.color = t >> 4
            desc = name(t)
        extra = ""
        if k == K_DALL:
            c = t >> 4
            dumped = [u for u in list(self.hands[p]) if u < 64 and (u >> 4) == c]
            m = 0
            for u in dumped:
                m += self.hands[p][u]
                self.discard += [u] * self.hands[p][u]
                del self.hands[p][u]
            extra = f" and discards {m} more {COLORS[c]} card(s)"
        self.say(f"{self.names[p]} plays {desc}{extra}. ({self.size(p)} left)")
        fin = False                # end_rule last: p has just finished and is no longer in the game
        if self.size(p) == 0:
            if self.end_rule == "first":
                self.finish(p, "played their last card")
                return
            fin = True
            self.player_finishes(p)
            if self.over:
                return
        v = draw_value(t)
        if t == WRD4:
            self.pending += v
            self.last_dv = v
            self.dir = -self.dir
            # two players: the reverse acts as a skip, so the player hits themself (not a finisher)
            self.cur = p if self.n_alive() == 2 and not fin else self.nxt(p)
            self.say(f"Direction reverses; {self.names[self.cur]} now faces a penalty of {self.pending}.")
        elif v:
            self.pending += v
            self.last_dv = v
            self.cur = self.nxt(p)
            self.say(f"{self.names[self.cur]} faces a penalty of {self.pending}.")
        elif k == K_SKIP:
            skipped = self.nxt(p)
            self.cur = self.nxt(skipped)
            self.say(f"{self.names[skipped]} is skipped.")
        elif k == K_SKIPALL:
            if fin:
                self.cur = self.nxt(p)
                self.say(f"{self.names[p]} has finished and can't take another turn; {self.names[self.cur]} is next.")
            else:
                self.cur = p
                self.say(f"Everyone else is skipped; {self.names[p]} goes again.")
        elif k == K_REV:
            self.dir = -self.dir
            self.cur = p if self.n_alive() == 2 and not fin else self.nxt(p)
            self.say("Direction reverses.")
        elif t == ROUL:
            self.roulettes += 1
            victim = self.nxt(p)
            self.turns += 1  # the victim's (lost) turn, as in RULES.md section 6
            self.decision = {"player": victim, "kind": "roulette_color",
                             "options": [("color", None, c) for c in range(4)], "roulette_by": p}
            return
        elif k == 0:
            self.zeros += 1
            order = [q for q in range(self.n) if self.alive[q]]
            new = [None] * self.n
            for q in order:
                new[self.nxt(q)] = self.hands[q]
            for q in order:
                self.hands[q] = new[q]
            self.cur = self.nxt(p)
            self.say("Everyone still in passes their hand to the next player." if fin
                     else "Everyone passes their hand to the next player.")
        elif k == 7:
            self.cur = self.nxt(p)
            if fin:
                self.say(f"The 7 does nothing: {self.names[p]} has no hand left to swap.")
            else:
                self.sevens += 1
                self.hands[p], self.hands[x] = self.hands[x], self.hands[p]
                self.say(f"{self.names[p]} swaps hands with {self.names[x]}.")
        else:
            self.cur = self.nxt(p)

    def roulette(self, victim, c):
        self.color = c
        k = 0
        dry = False
        while True:
            t = self.draw_one(victim)
            if t == EMPTY:
                dry = True
                break
            k += 1
            if t is None:
                break
            if t < 64 and (t >> 4) == c:
                break
        if self.alive[victim]:
            if dry:
                self.say(f"{self.names[victim]} names {COLORS[c]} and reveals {k} card(s); the draw pile and discard "
                         f"pile run out before {COLORS[c]} appears. They keep them all ({self.size(victim)} cards).")
            else:
                self.say(f"{self.names[victim]} names {COLORS[c]} and reveals {k} card(s) until one appears; "
                         f"they keep them all ({self.size(victim)} cards).")
        if not self.over:
            self.cur = self.nxt(victim)

    # ------------------------------------------------------------------ decisions
    def choose(self, k):
        d = self.decision
        assert d is not None
        opt = d["options"][k]
        p = d["player"]
        self.decision = None
        self.decisions += 1
        self.loop_seen.clear()     # a free choice: the future is not determined any more
        if d["kind"] == "roulette_color":
            self.roulette(p, opt[2])
        else:
            self.execute(p, opt)
        if not self.over and self.decision is None:
            self.begin_turn()

    def describe_option(self, opt):
        act, t, x = opt
        if act == "accept":
            return f"Take the penalty: draw {self.pending} cards (your turn ends)"
        if act == "color":
            return f"Name {COLORS[x]}"
        if t >= 64 and t != ROUL:
            s = f"{'Stack' if act == 'stack' else 'Play'} {name(t)}, naming {COLORS[x]}"
        elif t < 64 and (t & 15) == 7 and x is not None:
            s = f"Play {name(t)} and swap hands with {self.names[x]} ({self.size(x)} cards)"
        else:
            s = f"{'Stack' if act == 'stack' else 'Play'} {name(t)}"
        return s

    def would_finish(self, p, t):
        """Does playing t empty p's hand (a last card, or a Discard All that takes every card left)?"""
        left = self.size(p) - 1
        if t < 64 and (t & 15) == K_DALL:
            left -= sum(m for u, m in self.hands[p].items() if u < 64 and (u >> 4) == (t >> 4)) - 1
        return left == 0

    def rule_line(self):
        if self.mercy:
            mercy = f"Mercy rule: reaching {self.mercy} cards knocks you out of the game."
        else:
            mercy = "No Mercy rule: nobody is ever knocked out, however many cards they hold."
        if self.end_rule == "last":
            return ("Table rule: play until one player is left. Emptying your hand makes you FINISH and leave the "
                    "game (1st to finish wins); play goes on until only one player still holds cards, and that "
                    "player loses. " + mercy)
        return "Table rule: the first player to empty their hand wins and the game ends. " + mercy

    def hand_lines(self, p):
        """The hand grouped by colour, with counts: compact even for 100+ cards."""
        out = []
        for c in (0, 1, 2, 3, -1):
            cards = sorted((t, m) for t, m in self.hands[p].items() if color_of(t) == c)
            if cards:
                items = ", ".join(short_name(t) + (f" x{m}" if m > 1 else "") for t, m in cards)
                out.append(f"  {'Wild' if c < 0 else COLORS[c]} ({sum(m for _, m in cards)}): {items}")
        return out

    def option_lines(self, p, opts):
        """Numbered options; the colour choices of one wild (or the targets of one 7) share a line."""
        lines = []
        i = 0
        while i < len(opts):
            act, t, x = opts[i]
            j = i
            while j + 1 < len(opts) and opts[j + 1][:2] == (act, t) and act in ("play", "stack") and x is not None:
                j += 1
            fin = act in ("play", "stack") and self.would_finish(p, t)
            tail = "  <- your last card: you FINISH" if fin else ""
            if j == i:
                lines.append(f"  {i}: {self.describe_option(opts[i])}{tail}")
            else:
                verb = "Stack" if act == "stack" else "Play"
                if t >= 64:
                    ch = ", ".join(f"{k} = {COLORS[opts[k][2]]}" for k in range(i, j + 1))
                    lines.append(f"  {verb} {name(t)}{tail}, naming:  {ch}")
                else:
                    ch = ", ".join(f"{k} = {self.names[opts[k][2]]} ({self.size(opts[k][2])} cards)"
                                   for k in range(i, j + 1))
                    lines.append(f"  {verb} {name(t)} and swap hands with:  {ch}")
            i = j + 1
        return lines

    def view(self, p):
        if self.official():
            return self.view_official(p)
        d = self.decision
        me = self.names[p]
        lines = [f"You are {me}. Turn {self.turns}.", self.rule_line()]
        lines.append(f"Your hand ({self.size(p)} cards):")
        lines += self.hand_lines(p)
        top = name(self.top) if self.top < 64 else f"{name(self.top)} (color in play: {COLORS[self.color]})"
        lines.append(f"Top of discard pile: {top}. Color in play: {COLORS[self.color]}.")
        if self.pending:
            lines.append(f"PENDING PENALTY on you: {self.pending} cards (last Draw card was +{self.last_dv}; "
                         f"you may stack a Draw card of value >= {self.last_dv}, any color).")
        seats = []
        q = p
        for _ in range(self.n):
            if self.alive[q]:
                sz = self.size(q)
                if self.mercy and sz >= self.mercy - 5:
                    tag = f" (!! near the {self.mercy}-card knockout)"
                else:
                    tag = " (UNO!)" if sz == 1 else ""
                seats.append(f"{'You' if q == p else self.names[q]}: {sz} card{'s' if sz != 1 else ''}{tag}")
            q = (q + self.dir) % self.n
        lines.append(f"Still in ({self.n_alive()}), in turn order from you: " + " -> ".join(seats))
        if self.finished:
            lines.append("Finished (out of the game, placed): " + ", ".join(
                f"{ordinal(i + 1)} {self.names[q]} (turn {t})" for i, (t, q) in enumerate(self.finished)))
        if self.knockouts:
            lines.append("Knocked out: " + ", ".join(f"{nm} (turn {t})" for t, nm in self.knockouts))
        lines.append(f"Draw pile: {len(self.pile)} cards. Discard pile: {len(self.discard) + 1} cards.")
        lines.append("Recent events:")
        lines += ["  " + e for e in self.log[-12:]]
        if self.notes[p]:
            lines.append("Your private notes from earlier turns:")
            lines += ["  - " + s for s in self.notes[p][-6:]]
        lines.append(self.decision_head(d))
        lines += self.option_lines(p, d["options"])
        return "\n".join(lines)

    def decision_head(self, d):
        if d["kind"] == "roulette_color":
            return (f"{self.names[d['roulette_by']]} played a Wild Color Roulette on you! Name a color; you will "
                    "reveal cards from the draw pile until that color appears and keep them all (wilds don't count):")
        return {"play": "Your turn. You must play one of these (strict must-play rule):",
                "penalty": "A penalty is pending on you. Choose:",
                "forced_color": "You drew a wild and must play it. Choose its color:",
                "forced_swap": "You drew a 7 and must play it. Choose whom to swap hands with:"}[d["kind"]]

    def view_official(self, p):
        d = self.decision
        lines = []
        me = self.names[p]
        lines.append(f"You are {me}. Turn {self.turns}.")
        hand = sorted(self.hands[p].elements(), key=lambda t: (color_of(t), kind_of(t)))
        lines.append(f"Your hand ({len(hand)} cards): " + ", ".join(name(t) for t in hand))
        top = name(self.top) if self.top < 64 else f"{name(self.top)} (color in play: {COLORS[self.color]})"
        lines.append(f"Top of discard pile: {top}. Color in play: {COLORS[self.color]}.")
        if self.pending:
            lines.append(f"PENDING PENALTY on you: {self.pending} cards (last Draw card was +{self.last_dv}; "
                         f"you may stack a Draw card of value >= {self.last_dv}, any color).")
        seats = []
        q = p
        for _ in range(self.n):
            if self.alive[q]:
                sz = self.size(q)
                tag = " (!! near the 25-card knockout)" if sz >= 20 else (" (UNO!)" if sz == 1 else "")
                seats.append(f"{'You' if q == p else self.names[q]}: {sz} cards{tag}")
            q = (q + self.dir) % self.n
        lines.append("Turn order from you: " + " -> ".join(seats))
        out = [self.names[q] for q in range(self.n) if not self.alive[q]]
        if out:
            lines.append("Knocked out: " + ", ".join(out))
        lines.append(f"Draw pile: {len(self.pile)} cards. Discard pile: {len(self.discard) + 1} cards.")
        lines.append("Recent events:")
        lines += ["  " + e for e in self.log[-12:]]
        if self.notes[p]:
            lines.append("Your private notes from earlier turns:")
            lines += ["  - " + s for s in self.notes[p][-6:]]
        lines.append(self.decision_head(d))
        for i, o in enumerate(d["options"]):
            lines.append(f"  {i}: {self.describe_option(o)}")
        return "\n".join(lines)

    def status(self):
        if self.official():
            return self.status_official()
        nm = lambda q: None if q is None else self.names[q]  # noqa: E731
        s = {"game_over": self.over, "turns": self.turns}
        if self.over:
            s.update({"winner": nm(self.winner), "end_reason": self.end_reason})
            if self.end_rule == "last":
                s["loser"] = nm(self.loser)
            if self.stuck:
                s["stuck"] = True
            if self.endless:
                s["endless"] = True
            s.update({"plays": self.plays, "draws": self.draws, "decisions": self.decisions})
        else:
            d = self.decision
            s.update({"decisions": self.decisions, "next_player": self.names[d["player"]],
                      "decision_kind": d["kind"], "n_options": len(d["options"])})
        s["hand_sizes"] = {self.names[q]: self.size(q) for q in range(self.n) if self.alive[q]}
        if self.end_rule == "last":
            s["finished"] = [{"name": self.names[q], "place": i + 1, "turn": t}
                             for i, (t, q) in enumerate(self.finished)]
            if self.placings:
                s["placings"] = [self.names[q] for q in self.placings]
        s["knockouts"] = self.knockouts
        if self.stuck_run and not self.over:
            s["passes_in_a_row"] = self.stuck_run
        s["rules"] = {"end_rule": self.end_rule, "mercy": self.mercy or None}
        return s

    def status_official(self):
        if self.over:
            return {"game_over": True, "winner": self.names[self.winner], "end_reason": self.end_reason,
                    "turns": self.turns, "plays": self.plays, "draws": self.draws, "decisions": self.decisions,
                    "knockouts": self.knockouts}
        d = self.decision
        return {"game_over": False, "turns": self.turns, "decisions": self.decisions,
                "next_player": self.names[d["player"]], "decision_kind": d["kind"], "n_options": len(d["options"]),
                "hand_sizes": {self.names[q]: self.size(q) for q in range(self.n) if self.alive[q]}}

    def check(self):
        total = len(self.pile) + len(self.discard) + 1 + sum(self.size(q) for q in range(self.n))
        assert total == DECK, total
        for q in range(self.n):
            assert self.alive[q] or self.size(q) == 0
            assert not self.alive[q] or not self.mercy or self.size(q) < self.mercy
            assert not self.alive[q] or self.over or self.size(q) > 0
        assert self.over or self.alive[self.decision["player"]]
        assert self.pending == 0 or self.last_dv > 0


# ----------------------------------------------------------------------------- storage
def load(gdir):
    with open(os.path.join(gdir, "state.pkl"), "rb") as f:
        return pickle.load(f)


def save(g, gdir):
    tmp = os.path.join(gdir, "state.pkl.tmp")
    with open(tmp, "wb") as f:
        pickle.dump(g, f)
    os.replace(tmp, os.path.join(gdir, "state.pkl"))
    with open(os.path.join(gdir, "log.txt"), "w") as f:
        f.write("\n".join(g.log) + "\n")


# ----------------------------------------------------------------------------- validation
def random_choice(g, rng):
    """The simulator's `random` policy: uniform over distinct card types, then colour/target."""
    d = g.decision
    opts = d["options"]
    if d["kind"] in ("roulette_color", "forced_color", "forced_swap"):
        return rng.randrange(len(opts))
    groups = {}
    for i, (act, t, x) in enumerate(opts):
        groups.setdefault((act, t), []).append(i)
    keys = list(groups)
    return rng.choice(groups[keys[rng.randrange(len(keys))]])


def play_random_games(n, first, count, seed, rng_seed, end_rule, mercy):
    """Games first .. first+count-1 (game i uses seed*1000003+i), random policy. Returns one tuple per game."""
    rng = random.Random(rng_seed)
    out = []
    for i in range(first, first + count):
        g = Game([f"P{j}" for j in range(n)], seed * 1000003 + i, end_rule, mercy, quiet=True)
        while not g.over:
            g.choose(random_choice(g, rng))
        g.check()
        out.append((g.turns, g.plays, g.draws, g.reshuffles, len(g.knockouts), len(g.finished), g.max_hand,
                    g.zeros, g.sevens, g.roulettes, g.end_reason, g.winner, g.loser, g.reshuffles + g.dry_draws))
    return out


def _chunk(a):
    return play_random_games(*a)


def autoplay(n, games, seed, end_rule="first", mercy=MERCY, jobs=1):
    if jobs <= 1:  # the original single-process run (identical results for identical arguments)
        rows = play_random_games(n, 0, games, seed, seed, end_rule, mercy)
    else:          # game i is dealt identically; the players' random choices use one stream per job
        import multiprocessing
        k = -(-games // jobs)
        parts = [(n, j * k, min(k, games - j * k), seed, seed * 7919 + j + 1, end_rule, mercy)
                 for j in range(jobs) if j * k < games]
        with multiprocessing.Pool(len(parts)) as pool:
            rows = [r for part in pool.map(_chunk, parts) for r in part]
    turns = [r[0] for r in rows]
    m = sum(turns) / len(turns)
    sd = (sum((x - m) ** 2 for x in turns) / (len(turns) - 1)) ** 0.5
    mean = lambda j: sum(r[j] for r in rows) / len(rows)  # noqa: E731
    out = {"players": n, "games": games, "mean_turns": m, "sem": sd / len(turns) ** 0.5, "max": max(turns)}
    out.update({"end_rule": end_rule, "mercy": norm_mercy(mercy) or None, "seed": seed, "jobs": max(jobs, 1),
                "sd_turns": sd, "mean_plays": mean(1), "mean_draws": mean(2), "mean_reshuffles": mean(3),
                "mean_knockouts": mean(4), "mean_finishes": mean(5), "mean_max_hand": mean(6),
                "mean_zeros": mean(7), "mean_sevens": mean(8), "mean_roulettes": mean(9),
                # the C simulator also counts a draw from an empty draw pile AND empty discard as a reshuffle
                "mean_reshuffles_c_style": mean(13),
                "end_reasons": dict(Counter(r[10] for r in rows)),
                "wins_by_seat": [sum(1 for r in rows if r[11] == q) for q in range(n)],
                "losses_by_seat": [sum(1 for r in rows if r[12] == q) for q in range(n)]})
    print(json.dumps(out))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("new"); a.add_argument("--game", required=True); a.add_argument("--players", required=True)
    a.add_argument("--seed", type=int, default=1)
    a.add_argument("--end-rule", choices=["first", "last"], default="first",
                   help="first (official): first to empty their hand wins; last: play until one player is left")
    a.add_argument("--mercy", type=int, default=MERCY, help="knockout hand size (default 25); 0 or 1000 = none")
    a = sub.add_parser("view"); a.add_argument("--game", required=True)
    a = sub.add_parser("status"); a.add_argument("--game", required=True)
    a = sub.add_parser("act"); a.add_argument("--game", required=True); a.add_argument("--player", required=True)
    a.add_argument("--choice", type=int, required=True); a.add_argument("--note", default="")
    a = sub.add_parser("autoplay"); a.add_argument("--players", type=int, default=4)
    a.add_argument("--games", type=int, default=1000); a.add_argument("--seed", type=int, default=1)
    a.add_argument("--end-rule", choices=["first", "last"], default="first")
    a.add_argument("--mercy", type=int, default=MERCY)
    a.add_argument("--jobs", type=int, default=1, help="worker processes (default 1)")
    args = ap.parse_args()

    if args.cmd == "autoplay":
        autoplay(args.players, args.games, args.seed, args.end_rule, args.mercy, args.jobs)
        return
    if args.cmd == "new":
        names = args.players.split(",")
        if len(set(names)) != len(names):
            print(json.dumps({"error": "player names must be different"}))
            sys.exit(1)
        os.makedirs(args.game, exist_ok=True)
        g = Game(names, args.seed, args.end_rule, args.mercy)
        save(g, args.game)
        print(json.dumps(g.status()))
        return
    g = load(args.game)
    if args.cmd == "status":
        print(json.dumps(g.status()))
    elif args.cmd == "view":
        if g.over:
            print(json.dumps(g.status()))
        else:
            print(g.view(g.decision["player"]))
    elif args.cmd == "act":
        if g.over:
            print(json.dumps(g.status()))
            return
        p = g.decision["player"]
        if args.player != g.names[p]:
            print(json.dumps({"error": f"it is {g.names[p]}'s decision, not {args.player}'s"}))
            sys.exit(1)
        if not 0 <= args.choice < len(g.decision["options"]):
            print(json.dumps({"error": f"choice must be 0..{len(g.decision['options']) - 1}"}))
            sys.exit(1)
        if args.note:
            g.notes[p].append(f"(turn {g.turns}) {args.note[:200]}")
        g.choose(args.choice)
        g.check()
        save(g, args.game)
        print(json.dumps(g.status()))


if __name__ == "__main__":
    main()
