#!/usr/bin/env python3
"""
Independent reference implementation of UNO Show 'Em No Mercy.

Written only from ../RULES.md (default options everywhere), for cross-validating the C
simulator in ../sim/. Nothing in ../sim or ../results was consulted.

Default rules implemented
  * 168-card deck (sec. 1), 7 cards each, dealer uniform, dealer's left (seat+1) starts, dir +1.
  * Opening flip: action/wild cards are ignored and left in the discard pile until a number.
  * Strict must-play; with nothing playable, draw until playable, then play that card.
  * Stacking: any Draw Card with value >= value of the last Draw Card played; colour
    irrelevant; optional.  Wild Colour Roulette is not a Draw Card.
  * Wild Reverse Draw 4 with exactly 2 active players: its player faces the penalty
    (also when played into a stack).
  * Roulette: the victim names the colour, reveals until that colour (wilds do not count),
    keeps every revealed card, loses the turn; colour in play = victim's colour.
  * Mercy: 25+ cards knocks a player out, checked after every single drawn card.  The hand
    is set aside and joins the discard pile at the next reshuffle.
  * 0: all active hands pass to the next active player in the current direction.
    7: mandatory swap with a chosen other active player.
  * Discard All: every other card of its colour in hand goes under it (no effects).
  * Skip Everyone: same player goes again.  Skip / Reverse with 2 active players: go again.
  * Playing your last card wins immediately; its effect is not applied.
  * Game ends when a hand is emptied or only one player remains.

Random policy (fixed so that distributions are comparable across implementations)
  * normal turn: uniform over DISTINCT playable card types in hand (type = colour+kind for
    coloured cards, the wild kind for wilds); no voluntary drawing.
  * facing a penalty: uniform over {distinct stackable types} + {accept}.
  * wild colour: uniform over 4.  7-swap target: uniform over other active players.
  * roulette: victim names a colour uniformly.

Implementation note: the draw pile is kept as an UNORDERED multiset and each draw removes
a uniformly random element (swap-with-last + pop).  Since nobody ever looks at the order of
the draw pile, this is distributionally identical to shuffling once and drawing from the
top (it is exactly an on-demand Fisher-Yates shuffle).
"""

import argparse
import json
import math
import os
import random
import sys
import time
from collections import Counter
from multiprocessing import Pool

# --------------------------------------------------------------------------------------
# Card encoding
#   coloured card: t = colour*16 + kind   (colour 0..3)
#       kind 0..9  number
#       10 Draw 2, 11 Draw 4, 12 Skip, 13 Skip Everyone, 14 Reverse, 15 Discard All
#   wild card: 64 Wild Reverse Draw 4, 65 Wild Draw 6, 66 Wild Draw 10, 67 Wild Colour Roulette
# --------------------------------------------------------------------------------------
K_D2, K_D4, K_SKIP, K_SKIPALL, K_REV, K_DALL = 10, 11, 12, 13, 14, 15
WRD4, WD6, WD10, ROUL = 64, 65, 66, 67
N_TYPES = 68
DECK_SIZE = 168
MERCY = 25
HAND0 = 7

KIND_NAMES = {**{k: str(k) for k in range(10)},
              K_D2: "D2", K_D4: "D4", K_SKIP: "Skip", K_SKIPALL: "SkipAll",
              K_REV: "Rev", K_DALL: "DiscAll"}
WILD_NAMES = {WRD4: "WRD4", WD6: "WD6", WD10: "WD10", ROUL: "Roulette"}
COLOR_NAMES = "RGBY"


def card_name(t):
    if t >= 64:
        return WILD_NAMES[t]
    return COLOR_NAMES[t >> 4] + KIND_NAMES[t & 15]


def build_deck():
    deck = []
    for c in range(4):
        b = c * 16
        for num in range(10):
            deck += [b + num] * 2
        deck += [b + K_D2] * 3
        deck += [b + K_D4] * 2
        deck += [b + K_SKIP] * 3
        deck += [b + K_SKIPALL] * 2
        deck += [b + K_REV] * 3
        deck += [b + K_DALL] * 3
    deck += [WRD4] * 8 + [WD6] * 4 + [WD10] * 4 + [ROUL] * 8
    assert len(deck) == DECK_SIZE
    return deck


DECK_COUNTS = Counter(build_deck())

# Draw value of each type (0 = not a Draw Card; Roulette is not a Draw Card).
DRAW_VAL = [0] * N_TYPES
for _c in range(4):
    DRAW_VAL[_c * 16 + K_D2] = 2
    DRAW_VAL[_c * 16 + K_D4] = 4
DRAW_VAL[WRD4] = 4
DRAW_VAL[WD6] = 6
DRAW_VAL[WD10] = 10


def _playable(t, top, color):
    """Normal-turn legality of playing type t onto discard top `top` with colour in play `color`."""
    if t >= 64:
        return True                      # any wild
    if (t >> 4) == color:
        return True                      # colour match
    if top < 64 and (t & 15) == (top & 15):
        return True                      # same number or same action symbol
    return False


# PLAY_TAB[top*4 + color][t] -> bool
PLAY_TAB = [tuple(_playable(t, top, col) for t in range(N_TYPES))
            for top in range(N_TYPES) for col in range(4)]
# STACK_TAB[v][t] -> bool: t is a Draw Card with value >= v
STACK_TAB = {v: tuple(DRAW_VAL[t] > 0 and DRAW_VAL[t] >= v for t in range(N_TYPES))
             for v in (2, 4, 6, 10)}


class InvariantError(AssertionError):
    pass


class Game:
    """One game. Hands are dicts {type: count}; sizes tracked separately."""

    __slots__ = ("n", "rng", "draw_pile", "discard", "set_aside", "hands", "size", "alive",
                 "n_alive", "dir", "pending", "last_dv", "color", "cur", "over", "emptied",
                 "winner", "turns", "plays", "draws", "reshuffles", "elims", "check")

    def __init__(self, n, rng, check=False):
        assert 2 <= n <= 6
        self.n = n
        self.rng = rng
        self.check = check
        self.draw_pile = build_deck()
        self.discard = []
        self.set_aside = []
        self.hands = [dict() for _ in range(n)]
        self.size = [0] * n
        self.alive = [True] * n
        self.n_alive = n
        self.dir = 1
        self.pending = 0
        self.last_dv = 0
        self.color = -1
        self.over = False
        self.emptied = False
        self.winner = -1
        self.turns = self.plays = self.draws = self.reshuffles = self.elims = 0

        # Deal 7 each (the initial deal is not counted as "draws").
        for _ in range(HAND0):
            for p in range(n):
                t = self._pop_random()
                h = self.hands[p]
                h[t] = h.get(t, 0) + 1
                self.size[p] += 1
        # Opening flip: ignore action/wild cards (they stay in the discard pile).
        while True:
            t = self._pop_random()
            self.discard.append(t)
            if t < 64 and (t & 15) < 10:
                break
        self.color = t >> 4
        dealer = int(rng.random() * n)
        self.cur = (dealer + 1) % n
        if check:
            self.check_invariants()

    # ---------------------------------------------------------------- pile handling
    def _pop_random(self):
        dp = self.draw_pile
        i = int(self.rng.random() * len(dp))
        c = dp[i]
        dp[i] = dp[-1]
        dp.pop()
        return c

    def _reshuffle(self):
        top = self.discard.pop()
        pool = self.discard
        pool.extend(self.set_aside)          # knocked-out hands join at the reshuffle
        self.set_aside = []
        self.discard = [top]
        if not pool:
            raise InvariantError("deadlock: draw pile and discard pile both exhausted")
        self.draw_pile = pool                # unordered; each draw picks uniformly
        self.reshuffles += 1

    def _draw_card(self):
        if not self.draw_pile:
            self._reshuffle()
        self.draws += 1
        return self._pop_random()

    # ---------------------------------------------------------------- hand handling
    def _receive(self, p, t):
        """Give card t to p; apply the mercy rule immediately. Returns True if p is knocked out."""
        h = self.hands[p]
        h[t] = h.get(t, 0) + 1
        s = self.size[p] + 1
        self.size[p] = s
        if s >= MERCY:
            self._eliminate(p)
            return True
        return False

    def _eliminate(self, p):
        sa = self.set_aside
        for t, k in self.hands[p].items():
            sa.extend([t] * k)
        self.hands[p] = {}
        self.size[p] = 0
        self.alive[p] = False
        self.n_alive -= 1
        self.elims += 1

    def _remove(self, p, t):
        h = self.hands[p]
        k = h[t]
        if k == 1:
            del h[t]
        else:
            h[t] = k - 1
        self.size[p] -= 1

    def _next(self, p):
        """Next active player after seat p in the current direction."""
        n, d, alive = self.n, self.dir, self.alive
        q = (p + d) % n
        while not alive[q]:
            q = (q + d) % n
        return q

    def _end(self, emptied, winner):
        self.over = True
        self.emptied = emptied
        self.winner = winner
        return True

    # ---------------------------------------------------------------- one turn
    def step(self):
        """Play one turn of the current player. Returns True when the game is over."""
        rng = self.rng
        p = self.cur
        self.turns += 1
        hand = self.hands[p]

        if self.pending:
            st = STACK_TAB[self.last_dv]
            opts = [t for t in hand if st[t]]
            k = int(rng.random() * (len(opts) + 1))
            if k == len(opts):                           # accept the penalty
                amt = self.pending
                self.pending = 0
                self.last_dv = 0
                for _ in range(amt):
                    if self._receive(p, self._draw_card()):
                        break                            # knocked out mid-penalty
                if not self.alive[p] and self.n_alive == 1:
                    return self._end(False, self._next(p))
                self.cur = self._next(p)                 # victim loses the turn
                return False
            t = opts[k]                                  # stack
        else:
            pt = PLAY_TAB[self.discard[-1] * 4 + self.color]
            opts = [t for t in hand if pt[t]]
            if opts:
                t = opts[int(rng.random() * len(opts))]
            else:                                        # draw until playable, then play it
                while True:
                    c = self._draw_card()
                    if self._receive(p, c):
                        if self.n_alive == 1:
                            return self._end(False, self._next(p))
                        self.cur = self._next(p)
                        return False
                    if pt[c]:
                        t = c
                        break
        return self._play(p, t)

    def _play(self, p, t):
        self._remove(p, t)
        self.plays += 1
        hand = self.hands[p]
        if t < 64 and (t & 15) == K_DALL:
            col = t >> 4
            shed = [u for u in hand if u < 64 and (u >> 4) == col]
            for u in shed:
                k = hand.pop(u)
                self.discard.extend([u] * k)             # placed under the Discard All
                self.size[p] -= k
        self.discard.append(t)
        if self.size[p] == 0:
            return self._end(True, p)                    # last card: win, no effect applied

        rng = self.rng
        if t < 64:
            self.color = t >> 4
            kind = t & 15
            if kind < 10:
                if kind == 0:
                    self._pass_hands(p)
                elif kind == 7:
                    self._swap7(p)
                self.cur = self._next(p)
            elif kind == K_D2 or kind == K_D4:
                v = DRAW_VAL[t]
                self.pending += v
                self.last_dv = v
                self.cur = self._next(p)
            elif kind == K_SKIP:
                self.cur = self._next(self._next(p))     # 2 active -> back to p
            elif kind == K_SKIPALL:
                self.cur = p
            elif kind == K_REV:
                self.dir = -self.dir
                self.cur = p if self.n_alive == 2 else self._next(p)
            else:                                        # Discard All (shedding done above)
                self.cur = self._next(p)
            return False

        if t == ROUL:
            victim = self._next(p)
            c = int(rng.random() * 4)                    # victim names the colour
            self.color = c
            while True:
                card = self._draw_card()
                if self._receive(victim, card):
                    break
                if card < 64 and (card >> 4) == c:       # wilds do not count
                    break
            if not self.alive[victim] and self.n_alive == 1:
                return self._end(False, p)
            self.cur = self._next(victim)                # victim loses the turn
            return False

        # WRD4 / WD6 / WD10
        self.color = int(rng.random() * 4)
        v = DRAW_VAL[t]
        self.pending += v
        self.last_dv = v
        if t == WRD4:
            self.dir = -self.dir
            self.cur = p if self.n_alive == 2 else self._next(p)
        else:
            self.cur = self._next(p)
        return False

    def _pass_hands(self, p):
        seats = [p]
        q = self._next(p)
        while q != p:
            seats.append(q)
            q = self._next(q)
        m = len(seats)
        hs = [self.hands[s] for s in seats]
        ss = [self.size[s] for s in seats]
        for i in range(m):
            j = seats[(i + 1) % m]
            self.hands[j] = hs[i]
            self.size[j] = ss[i]

    def _swap7(self, p):
        others = [q for q in range(self.n) if self.alive[q] and q != p]
        q = others[int(self.rng.random() * len(others))]
        self.hands[p], self.hands[q] = self.hands[q], self.hands[p]
        self.size[p], self.size[q] = self.size[q], self.size[p]

    # ---------------------------------------------------------------- driver / checks
    def play(self, watchdog=10**9):
        step = self.step
        if self.check:
            while not step():
                self.check_invariants()
                if self.turns > watchdog:
                    raise RuntimeError("watchdog")
            self.check_invariants()
        else:
            while not step():
                pass
            # no cap: a game that never ended would hang here, which we would notice
        return self

    def check_invariants(self):
        def fail(msg):
            raise InvariantError(msg)
        allc = Counter()
        for p in range(self.n):
            h = self.hands[p]
            if sum(h.values()) != self.size[p]:
                fail(f"size mismatch seat {p}")
            if any(k <= 0 for k in h.values()):
                fail("non-positive count in hand")
            if self.alive[p]:
                if self.size[p] >= MERCY:
                    fail(f"active seat {p} holds {self.size[p]} >= 25 cards")
            elif self.size[p] != 0:
                fail(f"eliminated seat {p} still holds cards")
            allc.update(h)
        allc.update(self.draw_pile)
        allc.update(self.discard)
        allc.update(self.set_aside)
        total = sum(allc.values())
        if total != DECK_SIZE:
            fail(f"card conservation broken: {total} != 168")
        if allc != DECK_COUNTS:
            fail("card multiset differs from the deck")
        if self.n_alive != sum(self.alive):
            fail("n_alive mismatch")
        if not self.discard:
            fail("empty discard pile")
        if not 0 <= self.color < 4:
            fail("bad colour")
        if self.pending < 0 or (self.pending > 0) != (self.last_dv > 0):
            fail("pending/last_dv inconsistent")
        if self.pending and self.last_dv not in (2, 4, 6, 10):
            fail("bad last_dv")
        if not self.over:
            if not self.alive[self.cur]:
                fail("current player is not active")
            if self.n_alive < 2:
                fail("game should have ended")
            if not self.pending:
                top = self.discard[-1]
                if top < 64 and self.color != (top >> 4):
                    fail("colour in play differs from coloured top card")
        else:
            if self.emptied:
                if self.size[self.winner] != 0 or not self.alive[self.winner]:
                    fail("winner bookkeeping")
            elif self.n_alive != 1:
                fail("last-standing end with n_alive != 1")


# ------------------------------------------------------------------------------------------
# Deterministic rule scenario tests
# ------------------------------------------------------------------------------------------
class FixedRNG:
    """random() stub returning a scripted sequence (then 0.0)."""

    def __init__(self, seq=()):
        self.seq = list(seq)

    def random(self):
        return self.seq.pop(0) if self.seq else 0.0


def _scenario(n, hands, top, color, cur=0, dead=(), pile=None, rng=None):
    """Build a hand-crafted mid-game state. Cards not placed anywhere go to the draw pile
    (or, if `pile` is given, the draw pile is exactly `pile` and the rest is set aside so
    that card conservation still holds)."""
    g = Game(n, random.Random(12345))
    g.hands = [dict() for _ in range(n)]
    g.size = [0] * n
    for p, cards in hands.items():
        g.hands[p] = dict(Counter(cards))
        g.size[p] = len(cards)
    for p in dead:
        g.alive[p] = False
    g.n_alive = sum(g.alive)
    g.discard = list(top) if isinstance(top, (list, tuple)) else [top]
    g.color = color
    g.cur = cur
    g.set_aside = []
    used = Counter()
    for h in g.hands:
        used.update(h)
    used.update(g.discard)
    if pile is not None:
        used.update(pile)
    assert not (used - DECK_COUNTS), "scenario uses more copies than the deck has"
    rest = list((DECK_COUNTS - used).elements())
    if pile is None:
        g.draw_pile = rest
    else:
        g.draw_pile = list(pile)
        g.set_aside = rest
    if rng is not None:
        g.rng = rng
    g.check_invariants()
    return g


def selftest():
    R, G, B, Y = 0, 16, 32, 48
    ok = 0

    # deck composition
    d = Counter(build_deck())
    assert sum(d.values()) == 168 and sum(k for t, k in d.items() if t >= 64) == 24
    assert sum(k for t, k in d.items() if t < 64 and (t & 15) < 10) == 80
    assert d[R + 0] == 2 and d[B + K_SKIPALL] == 2 and d[G + K_DALL] == 3 and d[ROUL] == 8
    ok += 1

    # opening flip lands on a number; ignored action/wild cards remain in the discard pile
    for s in range(2000):
        g = Game(2 + s % 5, random.Random(s))
        top = g.discard[-1]
        assert top < 64 and (top & 15) < 10 and g.color == top >> 4
        assert all(not (t < 64 and (t & 15) < 10) for t in g.discard[:-1])
        assert all(sz == 7 for sz in g.size) and g.draws == 0 and g.dir == 1
        g.check_invariants()
    ok += 1

    # playability / stackability tables
    assert PLAY_TAB[(R + 5) * 4 + 0][R + 9] and PLAY_TAB[(R + 5) * 4 + 0][G + 5]
    assert not PLAY_TAB[(R + 5) * 4 + 0][G + 6]
    assert PLAY_TAB[(R + K_SKIP) * 4 + 0][B + K_SKIP]
    assert not PLAY_TAB[(R + K_D4) * 4 + 0][B + K_D2]
    assert PLAY_TAB[WD6 * 4 + 2][B + 3] and not PLAY_TAB[WD6 * 4 + 2][G + 3]
    assert all(PLAY_TAB[(R + 1) * 4 + 0][w] for w in (WRD4, WD6, WD10, ROUL))
    assert STACK_TAB[4][B + K_D4] and STACK_TAB[4][WRD4] and not STACK_TAB[4][G + K_D2]
    assert STACK_TAB[2][Y + K_D2] and not STACK_TAB[2][ROUL] and not STACK_TAB[2][R + K_SKIP]
    assert STACK_TAB[10][WD10] and not STACK_TAB[10][WD6]
    ok += 1

    # last card wins immediately; its effect is not applied
    g = _scenario(3, {0: [R + K_D2], 1: [G + 1], 2: [G + 2]}, R + 4, 0)
    assert g.step() and g.emptied and g.winner == 0 and g.pending == 0 and g.turns == 1
    ok += 1

    # Discard All sheds every same-colour card under itself; wins if the hand empties
    g = _scenario(3, {0: [R + K_DALL, R + 3, R + K_D2, R + 3, WD6, G + 4]}, R + 4, 0)
    g._play(0, R + K_DALL)
    assert g.hands[0] == {WD6: 1, G + 4: 1} and g.size[0] == 2 and g.pending == 0
    assert g.discard[-1] == R + K_DALL
    assert sorted(g.discard[1:-1]) == sorted([R + 3, R + 3, R + K_D2])
    assert g.cur == 1 and g.plays == 1 and g.color == 0
    g.check_invariants()
    g = _scenario(3, {0: [B + K_DALL, R + 3, R + K_D2]}, B + 4, 2)
    assert not g._play(0, B + K_DALL)       # sheds nothing red
    g = _scenario(3, {0: [R + K_DALL, R + 3, R + K_D2]}, R + 4, 0)
    assert g._play(0, R + K_DALL) and g.emptied
    ok += 1

    # Skip / Skip Everyone / Reverse with 3 and with 2 active players
    for dead, exp_skip, exp_rev in (((3,), 2, 2), ((2, 3), 0, 0)):
        hs = {0: [R + K_SKIP, R + K_REV, R + K_SKIPALL, G + 1], 1: [G + 2], 2: [G + 3]}
        g = _scenario(4, {p: h for p, h in hs.items() if p not in dead}, R + 4, 0, dead=dead)
        g._play(0, R + K_SKIP)
        assert g.cur == exp_skip, (dead, g.cur)
        g._play(0, R + K_SKIPALL)
        assert g.cur == 0
        g._play(0, R + K_REV)
        assert g.dir == -1 and g.cur == exp_rev, (dead, g.cur)
    ok += 1

    # Wild Reverse Draw 4: 3+ active -> reverse, new next player faces it; 2 active -> self,
    # also when played into a stack
    g = _scenario(4, {1: [WRD4, G + 1]}, R + 4, 0, cur=1, rng=FixedRNG([0.3]))
    g._play(1, WRD4)
    assert g.dir == -1 and g.cur == 0 and g.pending == 4 and g.last_dv == 4 and g.color == 1
    g = _scenario(4, {1: [WRD4, G + 1], 0: [B + 1]}, R + K_D2, 0, cur=1, dead=(2, 3))
    g.pending, g.last_dv = 6, 2
    g._play(1, WRD4)
    assert g.cur == 1 and g.pending == 10 and g.last_dv == 4
    ok += 1

    # Facing a stack: options = distinct stackable types + accept (duplicates count once)
    g = _scenario(3, {1: [G + K_D2, G + K_D2, B + K_D2, WD6, R + 5]}, R + K_D2, 0, cur=1,
                  rng=FixedRNG([0.5]))
    g.pending, g.last_dv = 2, 2
    # opts = 3 distinct stackable types + accept -> 4 options; 0.5*4 = 2 -> the 3rd option
    st = STACK_TAB[2]
    opts = [t for t in g.hands[1] if st[t]]
    assert len(opts) == 3
    g.step()
    assert g.discard[-1] == opts[2] and g.pending == 2 + DRAW_VAL[opts[2]] and g.cur == 2
    g = _scenario(3, {1: [G + K_D2, R + K_D4]}, WD6, 0, cur=1, rng=FixedRNG([0.0]))
    g.pending, g.last_dv = 6, 6                     # nothing stackable -> accept only
    g.step()
    assert g.size[1] == 8 and g.pending == 0 and g.cur == 2 and g.draws == 6
    ok += 1

    # Accepting a penalty: knocked out at exactly 25, mid-penalty; remaining penalty lapses
    hand20 = ([G + 1] * 2 + [B + 1] * 2 + [Y + 1] * 2 + [G + 2] * 2 + [B + 2] * 2
              + [Y + 2] * 2 + [G + 3] * 2 + [B + 3] * 2 + [Y + 3] * 2 + [G + 5] * 2)
    g = _scenario(3, {1: hand20, 0: [R + 1], 2: [R + 2]}, WD10, 0, cur=1,
                  rng=FixedRNG([0.999]))
    g.pending, g.last_dv = 10, 10
    over = g.step()
    assert not over and not g.alive[1] and g.draws == 5 and len(g.set_aside) == 25
    assert g.pending == 0 and g.cur == 2 and g.elims == 1 and g.n_alive == 2
    g.check_invariants()
    # ... and a knockout that leaves one player ends the game (last player standing)
    g = _scenario(3, {1: hand20, 0: [R + 1]}, WD10, 0, cur=1, dead=(2,), rng=FixedRNG([0.999]))
    g.pending, g.last_dv = 10, 10
    assert g.step() and not g.emptied and g.winner == 0
    ok += 1

    # Draw until playable: stops at the first playable card and must play it
    g = _scenario(3, {0: [G + 1, G + 2], 1: [G + 3], 2: [G + 4]}, R + 4, 0,
                  pile=[B + 9, R + 8, Y + 7], rng=FixedRNG([0.99, 0.0, 0.0]))
    g.step()                  # draws Y7 (dead), B9 (dead), R8 (playable) -> plays R8
    assert g.discard[-1] == R + 8 and g.draws == 3 and g.plays == 1 and g.turns == 1
    assert g.hands[0] == Counter([G + 1, G + 2, Y + 7, B + 9]) and g.cur == 1
    # knocked out while drawing: the 25th card is drawn -> out even if it is playable
    hand24 = hand20 + [G + 6, G + 6, B + 6, B + 6]
    g = _scenario(3, {0: hand24, 1: [G + 7], 2: [B + 7]}, R + 4, 0,
                  pile=[R + 8], rng=FixedRNG([0.0]))
    assert not g.step() and not g.alive[0] and g.plays == 0 and g.cur == 1
    ok += 1

    # Roulette: victim names colour, keeps all revealed incl. the match; wilds do not count
    g = _scenario(3, {0: [ROUL, G + 1], 1: [Y + 1], 2: [Y + 2]}, R + 4, 0,
                  pile=[B + 5, WD6, R + 2, G + 7],
                  rng=FixedRNG([0.5, 0.99, 0.99, 0.99, 0.99]))
    g._play(0, ROUL)          # colour -> Blue; reveals G7, R2, WD6, B5
    assert g.color == 2 and g.size[1] == 5 and g.hands[1].get(B + 5) == 1
    assert g.hands[1].get(WD6) == 1 and g.cur == 2 and g.draws == 4 and g.pending == 0
    g.check_invariants()
    ok += 1

    # 0: hands pass in the current direction among ACTIVE players only
    g = _scenario(4, {0: [R + 0, R + 1], 1: [G + 1], 3: [B + 1, B + 2, B + 3]}, R + 4, 0,
                  dead=(2,))
    g._play(0, R + 0)
    assert g.hands[1] == {R + 1: 1} and g.hands[3] == {G + 1: 1} and g.size[0] == 3
    assert g.hands[0] == Counter([B + 1, B + 2, B + 3]) and g.cur == 1
    g = _scenario(4, {0: [R + 0, R + 1], 1: [G + 1], 3: [B + 1, B + 2, B + 3]}, R + 4, 0,
                  dead=(2,))
    g.dir = -1
    g._play(0, R + 0)
    assert g.hands[3] == {R + 1: 1} and g.hands[0] == {G + 1: 1} and g.size[1] == 3
    assert g.cur == 3
    ok += 1

    # 7: mandatory swap with another active player
    g = _scenario(3, {0: [R + 7, R + 1], 1: [G + 1, G + 2, G + 3]}, R + 4, 0, dead=(2,))
    g._play(0, R + 7)
    assert g.size[0] == 3 and g.size[1] == 1 and g.hands[1] == {R + 1: 1} and g.cur == 1
    ok += 1

    # Reshuffle: discard minus top plus set-aside hands become the new draw pile
    g = _scenario(3, {0: [G + 1]}, [R + 1, G + 2, B + 3], 2, pile=[])
    sa = list(g.set_aside)
    g._reshuffle()
    assert g.discard == [B + 3] and sorted(g.draw_pile) == sorted([R + 1, G + 2] + sa)
    assert g.set_aside == [] and g.reshuffles == 1
    g.check_invariants()
    ok += 1

    # Random full games under the invariant checker
    for s in range(3000):
        Game(2 + s % 5, random.Random(10**6 + s), check=True).play()
    ok += 1
    return ok

# ------------------------------------------------------------------------------------------
# Batch simulation
# ------------------------------------------------------------------------------------------
def run_chunk(args):
    n, seed, games, n_check = args
    rng = random.Random(seed)
    turns = []
    plays = draws = resh = elims = emptied = 0
    plays2 = draws2 = resh2 = elims2 = 0
    for i in range(games):
        g = Game(n, rng, check=(i < n_check)).play()
        turns.append(g.turns)
        plays += g.plays
        draws += g.draws
        resh += g.reshuffles
        elims += g.elims
        plays2 += g.plays * g.plays
        draws2 += g.draws * g.draws
        resh2 += g.reshuffles * g.reshuffles
        elims2 += g.elims * g.elims
        emptied += g.emptied
    return n, turns, plays, draws, resh, elims, emptied, plays2, draws2, resh2, elims2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200000, help="games per player count")
    ap.add_argument("--players", default="2,3,4,5,6")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20260927)
    ap.add_argument("--check", type=int, default=250, help="invariant-checked games per chunk")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "ref_results.json"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        k = selftest()
        print(f"selftest: {k} groups passed")
        return

    import numpy as np
    players = [int(x) for x in a.players.split(",")]
    tasks = []
    for n in players:
        full, rem = divmod(a.games, a.chunk)
        sizes = [a.chunk] * full + ([rem] if rem else [])
        for ci, sz in enumerate(sizes):
            tasks.append((n, a.seed * 1000003 + n * 100019 + ci, sz, min(a.check, sz)))
    agg = {n: dict(turns=[], plays=0, draws=0, resh=0, elims=0, emptied=0,
                   plays2=0, draws2=0, resh2=0, elims2=0, checked=0) for n in players}
    t0 = time.time()
    with Pool(a.procs) as pool:
        for res in pool.imap_unordered(run_chunk, tasks):
            n, turns, plays, draws, resh, elims, emptied, p2, d2, r2, e2 = res
            A = agg[n]
            A["turns"].extend(turns)
            A["plays"] += plays
            A["draws"] += draws
            A["resh"] += resh
            A["elims"] += elims
            A["emptied"] += emptied
            A["plays2"] += p2
            A["draws2"] += d2
            A["resh2"] += r2
            A["elims2"] += e2
    for (n, _s, sz, nc) in tasks:
        agg[n]["checked"] += nc
    elapsed = time.time() - t0

    out, extra = {}, {}
    for n in players:
        A = agg[n]
        T = np.asarray(A["turns"], dtype=np.int64)
        N = len(T)
        mean = float(T.mean())
        sd = float(T.std(ddof=1))
        p50, p90, p99 = (float(x) for x in np.percentile(T, [50, 90, 99]))

        def msd(s, s2):
            m = s / N
            v = (s2 - N * m * m) / (N - 1)
            return m, math.sqrt(max(v, 0.0)) / math.sqrt(N)
        mp, sp = msd(A["plays"], A["plays2"])
        md, sdr = msd(A["draws"], A["draws2"])
        mr, sr = msd(A["resh"], A["resh2"])
        me, se = msd(A["elims"], A["elims2"])
        out[str(n)] = {
            "games": N,
            "mean_turns": mean,
            "sd_turns": sd,
            "sem_turns": sd / math.sqrt(N),
            "p50": p50,
            "p90": p90,
            "p99": p99,
            "max_turns": int(T.max()),
            "end_emptied_frac": A["emptied"] / N,
            "mean_elims": me,
            "mean_plays": mp,
            "mean_draws": md,
            "mean_reshuffles": mr,
        }
        surv = {str(t): float((T > t).mean()) for t in (50, 100, 200, 300, 400, 600, 800)}
        # empirical exponential tail rate between the 99th and 99.9th percentiles:
        # S(t) ~ exp(-lambda t)  =>  lambda = -(ln S(t2) - ln S(t1)) / (t2 - t1)
        t1, t2 = np.percentile(T, [99, 99.9])
        s1, s2 = float((T > t1).mean()), float((T > t2).mean())
        lam = (math.log(s1) - math.log(s2)) / (t2 - t1) if s1 > 0 and s2 > 0 and t2 > t1 else None
        extra[str(n)] = {
            "sem_plays": sp, "sem_draws": sdr, "sem_reshuffles": sr, "sem_elims": se,
            "p999": float(np.percentile(T, 99.9)),
            "min_turns": int(T.min()),
            "survival_P(turns>t)": surv,
            "tail_rate_per_turn_p99_to_p999": lam,
            "invariant_checked_games": A["checked"],
        }
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2)
    with open(a.out.replace(".json", "_extra.json"), "w") as f:
        json.dump({"elapsed_s": elapsed, "seed": a.seed, "percentile_method": "numpy linear",
                   "per_players": extra}, f, indent=2)
    hdr = f"{'n':>2} {'games':>7} {'mean':>9} {'sd':>8} {'sem':>6} {'p50':>6} {'p90':>6} " \
          f"{'p99':>6} {'max':>6} {'emptied':>8} {'elims':>6} {'plays':>7} {'draws':>7} {'resh':>6}"
    print(hdr)
    for n in players:
        o = out[str(n)]
        print(f"{n:>2} {o['games']:>7} {o['mean_turns']:>9.3f} {o['sd_turns']:>8.3f} "
              f"{o['sem_turns']:>6.3f} {o['p50']:>6.1f} {o['p90']:>6.1f} {o['p99']:>6.1f} "
              f"{o['max_turns']:>6} {o['end_emptied_frac']:>8.4f} {o['mean_elims']:>6.3f} "
              f"{o['mean_plays']:>7.2f} {o['mean_draws']:>7.2f} {o['mean_reshuffles']:>6.3f}")
    print(f"elapsed {elapsed:.1f}s")


if __name__ == "__main__":
    main()
