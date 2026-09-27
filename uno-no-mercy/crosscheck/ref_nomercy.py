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

House variant, RULES.md section 7 (--end-rule last), implemented from the spec text only
  * A player who plays their last card (also via Discard All) FINISHES: their seat leaves
    play like a knocked-out seat (skipped, no 7-swap target, not in the 0-pass chain).
  * The game ends when only one player is left in play (by a finish or a Mercy knockout).
    Winner = first finisher; if nobody finished, the last player standing.  If the finish
    itself leaves one player, the game is over at once and the card has no effect.
  * --finish-effect 1 (default): the finishing card acts on the players still in, starting
    from the finisher's seat.  Draw cards add to the pending penalty (total and stacking
    threshold, as any Draw Card) for the next player (WRD4: reverse first; no 2-player
    self-hit).  Skip skips the next player.  Reverse reverses and the next player in the
    new direction plays (no 2-player "go again").  Skip Everyone passes the turn on.  A
    wild's colour is named by the finisher.  Roulette hits the next player, who names the
    colour and reveals as usual (the reveal is a turn, sec. 6).  0 passes hands among the
    remaining players; 7 does nothing.
  * --finish-effect 0: the finishing card only sets the colour (a wild's colour, Roulette
    included, is named by the finisher).  A penalty that was already pending stays,
    unchanged (total AND stacking threshold), with the next player in the unchanged
    direction.
  * --mercy N sets the knockout threshold (1000 = variant B, no Mercy rule).  With N > 25 the
    draw and discard piles can both run dry.  A player who must draw and cannot: in
    draw-until-playable, keeps what was drawn and passes; accepting a penalty, draws what
    there is and the rest lapses; a Roulette victim keeps what was revealed and stops.  A
    turn in which a player passes without having drawn anything is an idle pass;
    2 x (players still in) consecutive idle passes = stuck game.
  * Safety nets (recorded separately, never dropped): --max-turns caps a game;
    --detect-loops flags a provably endless game: the full state repeats with no free
    decision (a choice between two or more distinct options) and no random event (a draw
    from a pile holding two or more distinct cards) in between.

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

# RULES.md section 6 counts a Roulette victim's reveal as a turn. The first cross-check
# (ref_results.json) was run with this set to False; see COMPARISON.md.
COUNT_ROULETTE_TURN = True

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
MAX_COPIES = 8          # most copies of any one type in the deck (WRD4, Roulette)
LOOP_WARMUP = 16        # deterministic turns in a row before loop hashing starts

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
assert max(DECK_COUNTS.values()) == MAX_COPIES

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
                 "winner", "turns", "plays", "draws", "reshuffles", "elims", "check",
                 # RULES.md section 7 (house variant), --mercy and the safety nets
                 "end_last", "fin_eff", "mercy", "can_stall", "det", "cap", "rand_ev",
                 "finished", "first_fin", "t_first_fin", "last_exit_fin", "last_standing",
                 "roul_played", "roul_hits", "passes", "lapses", "rstops",
                 "idle", "idle_turn", "stuck", "looped", "capped", "loop_len")

    def __init__(self, n, rng, check=False, end_last=False, finish_effect=1, mercy=MERCY,
                 detect_loops=False, max_turns=0):
        assert 2 <= n <= 6
        self.n = n
        self.rng = rng
        self.check = check
        self.end_last = end_last            # True: play until one player is left (sec. 7)
        self.fin_eff = finish_effect        # sec. 7: does the finishing card take effect?
        self.mercy = mercy                  # knockout threshold (25 official; 1000 = none)
        self.can_stall = mercy > MERCY      # piles can run dry only without the 25 rule
        self.det = detect_loops             # track free decisions / random events
        self.cap = max_turns                # 0 = no cap
        self.rand_ev = False                # a free decision or random event this turn
        self.finished = []                  # seats in finishing order
        self.first_fin = -1
        self.t_first_fin = -1               # turn count when the first player finished
        self.last_exit_fin = False          # was the most recent exit a finish?
        self.last_standing = -1
        self.roul_played = self.roul_hits = 0
        self.passes = self.lapses = self.rstops = 0
        self.idle = 0                       # consecutive idle passes ...
        self.idle_turn = -2                 # ... the last of which was this turn
        self.stuck = self.looped = self.capped = False
        self.loop_len = 0
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
        """Discard pile minus its top card, plus set-aside hands, become the draw pile.
        Returns False if there is nothing to reshuffle (possible only with --mercy > 25)."""
        if len(self.discard) <= 1 and not self.set_aside:
            if self.can_stall:
                return False
            raise InvariantError("deadlock: draw pile and discard pile both exhausted")
        top = self.discard.pop()
        pool = self.discard
        pool.extend(self.set_aside)          # knocked-out hands join at the reshuffle
        self.set_aside = []
        self.discard = [top]
        self.draw_pile = pool                # unordered; each draw picks uniformly
        self.reshuffles += 1
        return True

    def _draw_card(self):
        """A uniformly random card from the draw pile; None if no card can be drawn at all
        (possible only with --mercy > 25)."""
        dp = self.draw_pile
        if not dp:
            if not self._reshuffle():
                return None
            dp = self.draw_pile
        if self.det and not self.rand_ev:
            m = len(dp)                      # random unless every card left is the same type
            if m > 1 and (m > MAX_COPIES or dp.count(dp[0]) != m):
                self.rand_ev = True
        self.draws += 1
        return self._pop_random()

    def _name_colour(self):
        """A player names a colour (free decision)."""
        if self.det:
            self.rand_ev = True
        return int(self.rng.random() * 4)

    # ---------------------------------------------------------------- hand handling
    def _receive(self, p, t):
        """Give card t to p; apply the mercy rule immediately. Returns True if p is knocked out."""
        h = self.hands[p]
        h[t] = h.get(t, 0) + 1
        s = self.size[p] + 1
        self.size[p] = s
        if s >= self.mercy:
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
        self.last_exit_fin = False

    def _remove(self, p, t):
        h = self.hands[p]
        k = h[t]
        if k == 1:
            del h[t]
        else:
            h[t] = k - 1
        self.size[p] -= 1

    def _next(self, p):
        """Next active player after seat p in the current direction (p itself may be out)."""
        n, d, alive = self.n, self.dir, self.alive
        q = (p + d) % n
        while not alive[q]:
            q = (q + d) % n
        return q

    def _end(self, emptied, winner):
        self.over = True
        if self.end_last:
            # sec. 7: over when one player is left; the first finisher is the winner, or,
            # if nobody finished, the last player standing. `emptied` = final exit was a finish.
            self.last_standing = self.alive.index(True)
            winner = self.first_fin if self.first_fin >= 0 else self.last_standing
            emptied = self.last_exit_fin
        self.emptied = emptied
        self.winner = winner
        return True

    def _abandon(self):
        """Stuck / looped / capped: the game never ends; nobody is recorded as winner."""
        self.over = True
        self.winner = -1
        self.emptied = False
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
            if opts and self.det:
                self.rand_ev = True                      # stack or accept: a free decision
            k = int(rng.random() * (len(opts) + 1))
            if k == len(opts):                           # accept the penalty
                amt = self.pending
                self.pending = 0
                self.last_dv = 0
                for _ in range(amt):
                    c = self._draw_card()
                    if c is None:                        # piles dry (--mercy > 25): rest lapses
                        self.lapses += 1
                        break
                    if self._receive(p, c):
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
                if self.det and len(opts) > 1:
                    self.rand_ev = True                  # choice between distinct cards
                t = opts[int(rng.random() * len(opts))]
            else:                                        # draw until playable, then play it
                d0 = self.draws
                while True:
                    c = self._draw_card()
                    if c is None:                        # cannot draw (--mercy > 25): pass
                        return self._pass(p, self.draws == d0)
                    if self._receive(p, c):
                        if self.n_alive == 1:
                            return self._end(False, self._next(p))
                        self.cur = self._next(p)
                        return False
                    if pt[c]:
                        t = c
                        break
        return self._play(p, t)

    def _pass(self, p, idle):
        """p could not play and the piles ran dry: the turn passes on. An idle pass (nothing
        drawn this turn) changes nothing; 2 x (players in) idle passes in a row = stuck."""
        self.passes += 1
        self.cur = self._next(p)
        if not idle:
            return False
        self.idle = self.idle + 1 if self.idle_turn == self.turns - 1 else 1
        self.idle_turn = self.turns
        if self.idle >= 2 * self.n_alive:
            self.stuck = True
            return self._abandon()
        return False

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
        if t == ROUL:
            self.roul_played += 1
        if self.size[p] == 0:
            if self.end_last:
                return self._finish(p, t)                # sec. 7: finish, play goes on
            return self._end(True, p)                    # last card: win, no effect applied
        return self._effect(p, t, False)

    def _finish(self, p, t):
        """sec. 7: p has just played its last card t (already on the discard pile)."""
        self.alive[p] = False
        self.n_alive -= 1
        self.finished.append(p)
        self.last_exit_fin = True
        if self.first_fin < 0:
            self.first_fin = p
            self.t_first_fin = self.turns
        if self.n_alive == 1:
            return self._end(True, p)                    # one player left: game over
        if self.fin_eff:
            return self._effect(p, t, True)
        # --finish-effect 0: only the colour is set; any pending penalty is left as it was
        self.color = self._name_colour() if t >= 64 else t >> 4
        self.cur = self._next(p)
        return False

    def _effect(self, p, t, fin):
        """Apply card t just played by p. fin: p has just finished (sec. 7) and is out, so
        nothing can come back to p (no swap, no extra turn, no 2-player self-hit)."""
        rng = self.rng
        if t < 64:
            self.color = t >> 4
            kind = t & 15
            if kind < 10:
                if kind == 0:
                    self._pass_hands(p)
                elif kind == 7 and not fin:
                    self._swap7(p)
                self.cur = self._next(p)
            elif kind == K_D2 or kind == K_D4:
                v = DRAW_VAL[t]
                self.pending += v
                self.last_dv = v
                self.cur = self._next(p)
            elif kind == K_SKIP:
                self.cur = self._next(self._next(p))     # 2 active -> back to p (never if fin)
            elif kind == K_SKIPALL:
                self.cur = self._next(p) if fin else p
            elif kind == K_REV:
                self.dir = -self.dir
                self.cur = p if (self.n_alive == 2 and not fin) else self._next(p)
            else:                                        # Discard All (shedding done above)
                self.cur = self._next(p)
            return False

        if t == ROUL:
            victim = self._next(p)
            self.roul_hits += 1
            if COUNT_ROULETTE_TURN:
                self.turns += 1   # RULES.md section 6 (current): the victim's reveal counts as a turn
            c = self._name_colour()                      # victim names the colour
            self.color = c
            while True:
                card = self._draw_card()
                if card is None:                         # piles dry (--mercy > 25): stop
                    self.rstops += 1
                    break
                if self._receive(victim, card):
                    break
                if card < 64 and (card >> 4) == c:       # wilds do not count
                    break
            if not self.alive[victim] and self.n_alive == 1:
                return self._end(False, p)
            self.cur = self._next(victim)                # victim loses the turn
            return False

        # WRD4 / WD6 / WD10
        self.color = self._name_colour()
        v = DRAW_VAL[t]
        self.pending += v
        self.last_dv = v
        if t == WRD4:
            self.dir = -self.dir
            self.cur = p if (self.n_alive == 2 and not fin) else self._next(p)
        else:
            self.cur = self._next(p)
        return False

    def _pass_hands(self, p):
        """0: every active hand moves to the next active player in the current direction.
        p (the player of the 0) is out of the chain if it has just finished."""
        s0 = p if self.alive[p] else self._next(p)
        seats = [s0]
        q = self._next(s0)
        while q != s0:
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
        if self.det and len(others) > 1:
            self.rand_ev = True
        q = others[int(self.rng.random() * len(others))]
        self.hands[p], self.hands[q] = self.hands[q], self.hands[p]
        self.size[p], self.size[q] = self.size[q], self.size[p]

    # ---------------------------------------------------------------- driver / checks
    def state_key(self):
        """Everything the future of the game depends on. The discard pile below its top is
        implied by card conservation, and its order never matters (reshuffles are uniform)."""
        idle = self.idle if self.idle_turn == self.turns else 0
        return (self.cur, self.dir, self.pending, self.last_dv, self.color, self.discard[-1],
                tuple(tuple(sorted(h.items())) if self.alive[i] else None
                      for i, h in enumerate(self.hands)),
                tuple(sorted(self.draw_pile)), tuple(sorted(self.set_aside)), idle)

    def play(self, watchdog=10**9):
        step = self.step
        if self.det or self.cap:
            return self._play_guarded(watchdog)
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

    def _play_guarded(self, watchdog):
        """Game loop with the variant-B safety nets: turn cap and provable-loop detection."""
        step, check, det = self.step, self.check, self.det
        cap = self.cap if self.cap else 1 << 62
        seen = {}
        streak = 0
        while not step():
            if check:
                self.check_invariants()
                if self.turns > watchdog:
                    raise RuntimeError("watchdog")
            if det:
                if self.rand_ev:
                    self.rand_ev = False
                    if streak:
                        streak = 0
                        seen.clear()
                else:
                    streak += 1
                    if streak >= LOOP_WARMUP:
                        k = self.state_key()
                        t0 = seen.get(k)
                        if t0 is not None:           # same state, nothing random in between
                            self.looped = True
                            self.loop_len = self.turns - t0
                            self._abandon()
                            break
                        seen[k] = self.turns
            if self.turns >= cap:
                self.capped = True
                self._abandon()
                break
        if check:
            self.check_invariants()
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
                if self.size[p] >= self.mercy:
                    fail(f"active seat {p} holds {self.size[p]} >= {self.mercy} cards")
                if self.end_last and not self.over and self.size[p] == 0:
                    fail(f"active seat {p} holds no cards")     # sec. 7: empty = finished
            elif self.size[p] != 0:
                fail(f"eliminated or finished seat {p} still holds cards")
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
        if self.n - self.n_alive != self.elims + len(self.finished):
            fail("exits != eliminations + finishes")
        if self.finished and not self.end_last:
            fail("finished seats under the official end rule")
        if any(self.alive[s] for s in self.finished):
            fail("finished seat still active")
        if self.mercy > DECK_SIZE and (self.elims or self.set_aside):
            fail("knockout without a Mercy rule")
        if not self.discard:
            fail("empty discard pile")
        if not 0 <= self.color < 4:
            fail("bad colour")
        if self.pending < 0 or (self.pending > 0) != (self.last_dv > 0):
            fail("pending/last_dv inconsistent")
        if self.pending and self.last_dv not in (2, 4, 6, 10):
            fail("bad last_dv")
        abandoned = self.stuck or self.looped or self.capped
        if not self.over or abandoned:
            if not self.alive[self.cur]:
                fail("current player is not active")
            if self.n_alive < 2:
                fail("game should have ended")
            if not self.pending:
                top = self.discard[-1]
                if top < 64 and self.color != (top >> 4):
                    fail("colour in play differs from coloured top card")
            if abandoned and self.winner != -1:
                fail("abandoned game has a winner")
        elif self.end_last:
            if self.n_alive != 1:
                fail("sec. 7 game over with more than one player in")
            if self.first_fin >= 0:
                if self.winner != self.first_fin or self.finished[0] != self.first_fin:
                    fail("sec. 7 winner is not the first finisher")
            elif self.winner != self.alive.index(True):
                fail("sec. 7 winner without finishers is not the last player standing")
        else:
            if self.emptied:
                if self.size[self.winner] != 0 or not self.alive[self.winner]:
                    fail("winner bookkeeping")
            elif self.n_alive != 1:
                fail("last-standing end with n_alive != 1")


# ------------------------------------------------------------------------------------------
# Deterministic rule scenario tests
# ------------------------------------------------------------------------------------------
class NoRNG:
    """random() must not be called."""

    def random(self):
        raise AssertionError("unexpected random number drawn")


class FixedRNG:
    """random() stub returning a scripted sequence (then 0.0)."""

    def __init__(self, seq=()):
        self.seq = list(seq)

    def random(self):
        return self.seq.pop(0) if self.seq else 0.0


def _scenario(n, hands, top, color, cur=0, dead=(), pile=None, rng=None, finished=(),
              end_last=False, finish_effect=1, mercy=MERCY, rest_to=None, conserve=True,
              detect_loops=False, max_turns=0):
    """Build a hand-crafted mid-game state. Cards not placed anywhere go to the draw pile
    (or, if `pile` is given, the draw pile is exactly `pile` and the rest is set aside so
    that card conservation still holds; `rest_to` = seat that receives the rest instead;
    conserve=False drops the rest: an unreachable state, for testing the stuck rule only).
    `dead` seats were knocked out, `finished` seats finished (in that order)."""
    g = Game(n, random.Random(12345), end_last=end_last, finish_effect=finish_effect,
             mercy=mercy, detect_loops=detect_loops, max_turns=max_turns)
    g.hands = [dict() for _ in range(n)]
    g.size = [0] * n
    for p, cards in hands.items():
        g.hands[p] = dict(Counter(cards))
        g.size[p] = len(cards)
    for p in dead:
        g.alive[p] = False
    g.elims = len(dead)
    for p in finished:
        g.alive[p] = False
        g.finished.append(p)
        g.last_exit_fin = True
    if finished:
        g.first_fin = finished[0]
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
        if rest_to is not None:
            h = g.hands[rest_to]
            for t in rest:
                h[t] = h.get(t, 0) + 1
            g.size[rest_to] += len(rest)
        elif conserve:
            g.set_aside = rest
    if rng is not None:
        g.rng = rng
    if conserve:
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

    ok += selftest_last()
    return ok


class _NoisyGame(Game):
    """Test helper: pretends that every turn contained a random event."""
    __slots__ = ()

    def step(self):
        r = Game.step(self)
        self.rand_ev = True
        return r


def selftest_last():
    """RULES.md section 7: play until one player is left (--end-rule last), --mercy, and the
    variant-B safety nets."""
    R, G, B, Y = 0, 16, 32, 48
    L = dict(end_last=True)
    ok = 0

    # (1) finishing removes the seat: skipped from then on, never a 7-swap target; a plain
    #     number as the finishing card just passes the turn on
    g = _scenario(4, {0: [R + 3], 1: [R + 7, R + 9, G + 1], 2: [G + 2, B + 2], 3: [Y + 2, Y + 5]},
                  R + 4, 0, **L)
    assert not g.step()
    assert not g.alive[0] and g.finished == [0] and g.first_fin == 0 and g.n_alive == 3
    assert g.cur == 1 and g.last_exit_fin and not g.over and g.t_first_fin == 1
    g.check_invariants()
    g.dir = -1                                     # 3 -> 2 -> 1 -> (0 skipped) -> 3
    g.cur = 1
    g.rng = FixedRNG([0.0, 0.0])                   # R7 is the first playable; target = 2
    g.hands[1] = {R + 7: 1, R + 9: 1, G + 1: 1}
    g.step()
    assert g.discard[-1] == R + 7 and g.cur == 3   # 0 is skipped
    assert g.hands[2] == {R + 9: 1, G + 1: 1} and g.hands[1] == {G + 2: 1, B + 2: 1}
    g.check_invariants()
    for s in range(200):                           # swap target never the finished seat
        g2 = _scenario(4, {1: [R + 7, G + 1], 2: [G + 2], 3: [B + 2]}, R + 4, 0, cur=1,
                       finished=(0,), rng=random.Random(s), **L)
        g2._play(1, R + 7)
        assert g2.size[0] == 0 and g2.hands[0] == {} and g2.size[1] == 1
    # Discard All that empties the hand also finishes
    g = _scenario(3, {0: [R + K_DALL, R + 3, R + K_D2], 1: [G + 1], 2: [G + 2]}, R + 4, 0, **L)
    assert not g._play(0, R + K_DALL) and g.finished == [0] and g.cur == 1 and g.pending == 0
    g.check_invariants()
    ok += 1

    # (2) 0 passes hands among the remaining players only
    g = _scenario(4, {0: [R + 0, R + 1], 1: [G + 1], 3: [B + 1, B + 2, B + 3]}, R + 4, 0,
                  finished=(2,), **L)                  # a non-finishing 0 after a finish
    g._play(0, R + 0)
    assert g.hands[1] == {R + 1: 1} and g.hands[3] == {G + 1: 1} and g.hands[2] == {}
    assert g.hands[0] == Counter([B + 1, B + 2, B + 3]) and g.cur == 1
    g.check_invariants()
    g = _scenario(4, {0: [R + 0], 1: [G + 1], 2: [G + 2, G + 3], 3: [B + 1, B + 2, B + 3]},
                  R + 4, 0, **L)                       # a finishing 0, direction +1
    assert not g._play(0, R + 0)
    assert g.hands[0] == {} and g.hands[2] == {G + 1: 1} and g.hands[3] == {G + 2: 1, G + 3: 1}
    assert g.hands[1] == Counter([B + 1, B + 2, B + 3]) and g.cur == 1
    g.check_invariants()
    g = _scenario(4, {0: [R + 0], 1: [G + 1], 2: [G + 2, G + 3], 3: [B + 1, B + 2, B + 3]},
                  R + 4, 0, **L)                       # ... direction -1
    g.dir = -1
    g._play(0, R + 0)
    assert g.hands[0] == {} and g.hands[2] == Counter([B + 1, B + 2, B + 3])
    assert g.hands[1] == {G + 2: 1, G + 3: 1} and g.hands[3] == {G + 1: 1} and g.cur == 3
    g = _scenario(3, {0: [R + 0], 1: [G + 1], 2: [G + 2, G + 3]}, R + 4, 0, **L)
    g._play(0, R + 0)                                  # two left: they swap
    assert g.hands[1] == {G + 2: 1, G + 3: 1} and g.hands[2] == {G + 1: 1} and g.cur == 1
    ok += 1

    # (3) 7 as the finishing card does nothing (and uses no random number)
    g = _scenario(4, {2: [R + 7], 0: [G + 1], 1: [G + 2, G + 3], 3: [B + 1]}, R + 4, 0, cur=2,
                  rng=NoRNG(), **L)
    g._play(2, R + 7)
    assert g.hands[0] == {G + 1: 1} and g.hands[1] == {G + 2: 1, G + 3: 1}
    assert g.hands[3] == {B + 1: 1} and g.cur == 3 and g.color == 0 and g.finished == [2]
    ok += 1

    # (4) Skip Everyone as the finishing card passes the turn on; Skip skips the next player
    for dirn, exp_all, exp_skip in ((1, 3, 0), (-1, 1, 0)):
        g = _scenario(4, {2: [B + K_SKIPALL], 0: [G + 1], 1: [G + 2], 3: [B + 1]}, B + 4, 2,
                      cur=2, **L)
        g.dir = dirn
        g._play(2, B + K_SKIPALL)
        assert g.cur == exp_all and g.dir == dirn and g.color == 2
        g = _scenario(4, {2: [B + K_SKIP], 0: [G + 1], 1: [G + 2], 3: [B + 1]}, B + 4, 2,
                      cur=2, **L)
        g.dir = dirn
        g._play(2, B + K_SKIP)
        assert g.cur == exp_skip
    g = _scenario(3, {1: [B + K_SKIP], 0: [G + 1], 2: [B + 1]}, B + 4, 2, cur=1, **L)
    g._play(1, B + K_SKIP)                             # two left: skip 2, back to 0
    assert g.cur == 0
    g = _scenario(3, {1: [B + K_SKIPALL], 0: [G + 1], 2: [B + 1]}, B + 4, 2, cur=1, **L)
    g._play(1, B + K_SKIPALL)                          # two left: next player, not the finisher
    assert g.cur == 2
    ok += 1

    # (5) Reverse / WRD4 as the finishing card when two players remain after the finish:
    #     reverse, then the next player in the new direction (no "go again", no self-hit)
    g = _scenario(3, {1: [R + K_REV], 0: [G + 1], 2: [B + 1]}, R + 4, 0, cur=1, **L)
    g._play(1, R + K_REV)
    assert g.dir == -1 and g.cur == 0 and not g.alive[1] and g.n_alive == 2
    g = _scenario(3, {1: [WRD4], 0: [G + 1], 2: [B + 1]}, R + 4, 0, cur=1,
                  rng=FixedRNG([0.8]), **L)
    g._play(1, WRD4)
    assert g.dir == -1 and g.cur == 0 and g.pending == 4 and g.last_dv == 4 and g.color == 3
    g.check_invariants()
    g = _scenario(5, {1: [R + K_REV], 0: [G + 1], 2: [B + 1], 4: [B + 2]}, R + 4, 0, cur=1,
                  finished=(3,), **L)                   # from 1 in direction -1: seat 0
    g._play(1, R + K_REV)
    assert g.dir == -1 and g.cur == 0
    #     ... whereas a Reverse / WRD4 that is NOT the last card, with two players left, is
    #     a "go again" / self-hit exactly as in sec. 4
    g = _scenario(3, {0: [R + K_REV, G + 5], 2: [B + 1]}, R + 4, 0, finished=(1,), **L)
    g._play(0, R + K_REV)
    assert g.cur == 0 and g.dir == -1
    g = _scenario(3, {0: [WRD4, G + 5], 2: [B + 1]}, R + 4, 0, finished=(1,), **L)
    g._play(0, WRD4)
    assert g.cur == 0 and g.pending == 4
    ok += 1

    # (6) a penalty from a finishing Draw card passes on and can be stacked
    g = _scenario(4, {0: [R + K_D2], 1: [G + K_D4, B + 1], 2: [G + 2], 3: [B + 2]}, R + 4, 0,
                  rng=FixedRNG([0.0]), **L)
    g.step()
    assert g.finished == [0] and g.pending == 2 and g.last_dv == 2 and g.cur == 1
    g.step()                                           # opts [G D4] + accept; 0.0 -> stack
    assert g.pending == 6 and g.last_dv == 4 and g.cur == 2 and g.size[1] == 1
    g = _scenario(4, {0: [WD10], 1: [G + 1], 2: [G + 2], 3: [B + 2]}, R + K_D2, 0,
                  rng=FixedRNG([0.0, 0.3]), **L)        # finishing INTO a stack
    g.pending, g.last_dv = 2, 2
    g.step()
    assert g.pending == 12 and g.last_dv == 10 and g.cur == 1 and g.color == 1
    g = _scenario(4, {0: [WRD4], 1: [G + 1], 2: [G + 2], 3: [B + 2]}, R + 4, 0,
                  rng=FixedRNG([0.0, 0.0]), **L)
    g.step()                                           # WRD4: reverse, then seat 3 faces 4
    assert g.dir == -1 and g.cur == 3 and g.pending == 4
    g.step()                                           # seat 3: nothing to stack -> draws 4
    assert g.size[3] == 5 and g.pending == 0 and g.cur == 2
    # a finishing Roulette hits the next player, who names the colour; the reveal is a turn
    g = _scenario(3, {0: [ROUL], 1: [Y + 1], 2: [Y + 2]}, R + 4, 0,
                  pile=[B + 5, G + 7], rng=FixedRNG([0.0, 0.5, 0.99, 0.0]), **L)
    g.step()
    assert g.turns == 2 and g.color == 2 and g.hands[1] == {Y + 1: 1, G + 7: 1, B + 5: 1}
    assert g.cur == 2 and g.roul_played == 1 and g.roul_hits == 1
    g.check_invariants()
    ok += 1

    # (7) the game ends when one player is left (by a finish or a knockout); the finishing
    #     card then has no effect
    g = _scenario(4, {0: [R + K_D2], 1: [G + 1]}, R + 4, 0, finished=(3, 2), **L)
    assert g.step() and g.over and g.n_alive == 1 and g.pending == 0
    assert g.finished == [3, 2, 0] and g.emptied and g.winner == 3
    g.check_invariants()
    hand20 = ([G + 1] * 2 + [B + 1] * 2 + [Y + 1] * 2 + [G + 2] * 2 + [B + 2] * 2
              + [Y + 2] * 2 + [G + 3] * 2 + [B + 3] * 2 + [Y + 3] * 2 + [G + 5] * 2)
    g = _scenario(3, {1: hand20, 2: [R + 1]}, WD10, 0, cur=1, finished=(0,),
                  rng=FixedRNG([0.999]), **L)
    g.pending, g.last_dv = 10, 10
    assert g.step() and not g.alive[1] and g.n_alive == 1
    assert g.winner == 0 and not g.emptied and g.elims == 1   # final exit: a knockout
    g.check_invariants()
    ok += 1

    # (8) the first finisher is recorded as the winner; with no finisher, the last standing
    g = _scenario(4, {0: [R + 3], 1: [R + 1], 2: [R + 5], 3: [B + 2, B + 3]}, R + 4, 0,
                  rng=FixedRNG([0.0] * 20), **L)
    assert not g.step() and g.first_fin == 0
    g.cur = 2
    assert not g.step() and g.finished == [0, 2] and g.cur == 3
    g.cur = 1
    assert g.step() and g.winner == 0 and g.finished == [0, 2, 1] and g.emptied
    assert g.last_standing == 3
    g.check_invariants()
    g = _scenario(3, {1: hand20, 0: [R + 1]}, WD10, 0, cur=1, dead=(2,),
                  rng=FixedRNG([0.999]), **L)
    g.pending, g.last_dv = 10, 10
    assert g.step() and g.winner == 0 and not g.emptied and g.finished == []
    ok += 1

    # (9) --finish-effect 0: the finishing card only sets the colour; a pending penalty stays
    #     with the next player unchanged (total and threshold); direction unchanged
    F0 = dict(end_last=True, finish_effect=0)
    g = _scenario(4, {0: [WD6], 1: [G + K_D4, B + 1], 2: [G + 2], 3: [B + 2]}, R + K_D4, 0,
                  rng=FixedRNG([0.0, 0.6]), **F0)
    g.pending, g.last_dv = 4, 4
    g.step()
    assert g.finished == [0] and g.pending == 4 and g.last_dv == 4 and g.cur == 1
    assert g.color == 2 and g.discard[-1] == WD6
    g.step()                                           # G D4 still stacks on the 4 threshold
    assert g.discard[-1] == G + K_D4 and g.pending == 8
    g = _scenario(4, {0: [WRD4], 1: [G + 1], 2: [G + 2], 3: [B + 2]}, R + K_D2, 0,
                  rng=FixedRNG([0.0, 0.1]), **F0)
    g.pending, g.last_dv = 2, 2
    g.step()
    assert g.dir == 1 and g.cur == 1 and g.pending == 2 and g.last_dv == 2 and g.color == 0
    for card, exp_cur in ((R + K_SKIP, 1), (R + K_REV, 1), (R + K_D2, 1), (R + K_SKIPALL, 1)):
        g = _scenario(4, {0: [card], 1: [G + 1], 2: [G + 2], 3: [B + 2]}, R + 4, 0, **F0)
        g.step()
        assert g.cur == exp_cur and g.dir == 1 and g.pending == 0 and g.color == 0
    g = _scenario(4, {0: [R + 0], 1: [G + 1], 2: [G + 2, G + 3], 3: [B + 1]}, R + 4, 0, **F0)
    g.step()                                           # a finishing 0 passes nothing
    assert g.hands[1] == {G + 1: 1} and g.hands[2] == {G + 2: 1, G + 3: 1} and g.cur == 1
    g = _scenario(3, {0: [ROUL], 1: [Y + 1], 2: [Y + 2]}, R + 4, 0,
                  rng=FixedRNG([0.0, 0.3]), **F0)
    g.step()                                           # Roulette: finisher names colour only
    assert g.color == 1 and g.size[1] == 1 and g.turns == 1 and g.cur == 1 and g.draws == 0
    ok += 1

    # (10) with no Mercy rule nobody is ever knocked out
    M0 = dict(end_last=True, mercy=1000)
    hand24 = hand20 + [G + 6, G + 6, B + 6, B + 6]
    g = _scenario(3, {1: hand24, 0: [R + 1], 2: [R + 2]}, WD10, 0, cur=1,
                  rng=FixedRNG([0.999]), **M0)
    g.pending, g.last_dv = 10, 10
    assert not g.step() and g.alive[1] and g.size[1] == 34 and g.elims == 0 and g.cur == 2
    g.check_invariants()
    for s in range(12):
        g = Game(2 + s % 3, random.Random(5 * 10**6 + s), check=True, end_last=True,
                 mercy=1000, detect_loops=True, max_turns=4000).play()
        assert g.elims == 0 and not g.set_aside
    for s in range(6):                                 # official end rule without Mercy too
        g = Game(2 + s % 5, random.Random(6 * 10**6 + s), check=True, mercy=1000,
                 detect_loops=True, max_turns=4000).play()
        assert g.elims == 0
    ok += 1

    # (11) dry piles (no Mercy rule): a player who cannot draw passes; a penalty lapses;
    #      a Roulette reveal stops; 2 x (players in) idle passes in a row = stuck
    g = _scenario(3, {0: [G + 1], 1: [G + 2], 2: [B + 3]}, [R + 9, R + 4], 0, pile=[],
                  rest_to=2, **M0)                     # discard below top: R9 (playable)
    g.step()
    assert g.discard[-1] == R + 9 and g.size[0] == 1 and g.reshuffles == 1 and g.cur == 1
    g = _scenario(3, {0: [G + 1], 1: [G + 2], 2: [B + 3]}, [Y + 9, R + 4], 0, pile=[],
                  rest_to=2, **M0)                     # draws Y9 (dead), then dry -> pass
    assert not g.step() and g.passes == 1 and g.size[0] == 2 and g.cur == 1 and g.plays == 0
    g.check_invariants()
    g = _scenario(3, {0: [G + 1], 1: [G + 2], 2: [B + 3]}, [Y + 9, R + K_D4], 0, pile=[B + 7],
                  rest_to=2, **M0)
    g.pending, g.last_dv = 4, 4
    assert not g.step() and g.size[0] == 3 and g.pending == 0 and g.lapses == 1 and g.cur == 1
    g.check_invariants()
    g = _scenario(3, {0: [ROUL, G + 1], 1: [G + 2], 2: [B + 3]}, R + 4, 0, pile=[G + 7],
                  rest_to=2, rng=FixedRNG([0.99]), **M0)
    g._play(0, ROUL)             # victim names Y, reveals G7, then R4 (reshuffled), dry
    assert g.hands[1] == {G + 2: 1, G + 7: 1, R + 4: 1} and g.rstops == 1 and g.reshuffles == 1
    assert g.color == 3 and g.cur == 2 and g.discard == [ROUL]
    g.check_invariants()
    g = _scenario(2, {0: [G + 1], 1: [B + 2]}, R + 5, 0, pile=[], conserve=False, **M0)
    for i in range(3):
        assert not g.step() and g.idle == i + 1
    assert g.step() and g.stuck and g.turns == 4 and g.winner == -1 and g.passes == 4
    g = _scenario(3, {0: [G + 1], 1: [B + 2], 2: [B + 3]}, R + 5, 0, pile=[Y + 9],
                  conserve=False, **M0)
    g.step()                                           # drew Y9: a pass, but not idle
    assert g.passes == 1 and g.idle == 0 and g.size[0] == 2
    for i in range(5):
        assert not g.step()
    assert g.step() and g.stuck and g.turns == 7
    ok += 1

    # (12) provably endless loop: seats 0 and 3 trade Reverses through a one-card pool
    #      (seats 1 and 2 never play); detected, and only with nothing random in between
    hand0 = [G + 1, G + 2, Y + 3]                      # no red, no Reverse, no wild
    hand3 = [R + 1, B + 2, Y + 4]                      # no green, no Reverse, no wild
    g = _scenario(4, {0: hand0, 3: hand3, 1: [B + 9]}, [G + K_REV, R + K_REV], 0, pile=[],
                  rest_to=2, detect_loops=True, max_turns=10**5, **M0)
    g.play()
    assert g.looped and g.over and g.loop_len == 2 and g.turns < LOOP_WARMUP + 10
    assert not g.capped and not g.stuck and g.size[1] == 1 and g.winner == -1
    g.check_invariants()
    g = _scenario(4, {0: hand0, 3: hand3, 1: [B + 9]}, [G + K_REV, R + K_REV], 0, pile=[],
                  rest_to=2, detect_loops=False, max_turns=500, **M0)
    g.play()                                           # without detection: the cap catches it
    assert g.capped and not g.looped and g.turns == 500 and g.over
    #      the same cycle with a random event in every turn: no loop may be claimed
    g = _scenario(4, {0: hand0, 3: hand3, 1: [B + 9]}, [G + K_REV, R + K_REV], 0, pile=[],
                  rest_to=2, detect_loops=True, max_turns=300, **M0)
    g.__class__ = _NoisyGame
    g.play()
    assert g.capped and not g.looped and g.turns == 300
    #      what counts as random: a draw from two or more distinct cards; a choice between
    #      two or more distinct cards, a colour, a 7-swap target among two or more players
    def flagged(g, f):
        g.rand_ev = False
        f()
        return g.rand_ev
    g = _scenario(3, {0: [G + 1], 1: [G + 2], 2: [B + 3]}, [Y + 9, Y + 9, R + 4], 0,
                  pile=[B + 7, B + 7], rest_to=2, detect_loops=True, **M0)
    assert not flagged(g, g._draw_card) and not flagged(g, g._draw_card)   # B7, B7
    assert not flagged(g, g._draw_card) and g.reshuffles == 1               # pool Y9, Y9
    g = _scenario(3, {0: [G + 1], 1: [G + 2], 2: [B + 3]}, R + 4, 0, pile=[B + 7, B + 8],
                  rest_to=2, detect_loops=True, **M0)
    assert flagged(g, g._draw_card) and not flagged(g, g._draw_card)
    g = _scenario(3, {0: [R + 1, R + 1, G + 4], 1: [G + 2], 2: [B + 3]}, R + 4, 0,
                  detect_loops=True, **M0)
    assert flagged(g, g.step)                          # R1 or G4
    g = _scenario(3, {0: [R + 1, R + 1, G + 5], 1: [G + 2], 2: [B + 3]}, R + 4, 0,
                  detect_loops=True, **M0)
    assert not flagged(g, g.step)                      # only R1 (twice): forced
    g = _scenario(3, {0: [R + K_D2, G + 5], 1: [G + K_D2], 2: [B + 3]}, R + 4, 0,
                  detect_loops=True, **M0)
    g.pending, g.last_dv = 2, 2
    g.cur = 1
    assert flagged(g, g.step)                          # stack or accept
    g = _scenario(3, {0: [R + 7, G + 5], 1: [G + 2], 2: [B + 3]}, R + 4, 0,
                  detect_loops=True, **M0)
    assert flagged(g, lambda: g._play(0, R + 7))       # swap target: 1 or 2
    g = _scenario(3, {0: [R + 7, G + 5], 2: [B + 3]}, R + 4, 0, finished=(1,),
                  detect_loops=True, **M0)
    assert not flagged(g, lambda: g._play(0, R + 7))   # only one possible target
    g = _scenario(3, {0: [WD6, G + 5], 1: [G + 2], 2: [B + 3]}, R + 4, 0,
                  detect_loops=True, **M0)
    assert flagged(g, lambda: g._play(0, WD6))         # colour
    ok += 1

    # (13) two players: play-until-one-left is exactly the official game (same random stream)
    for s in range(300):
        for mercy in ((MERCY, 1000) if s < 60 else (MERCY,)):
            a = Game(2, random.Random(s), mercy=mercy, max_turns=10**6).play()
            b = Game(2, random.Random(s), end_last=True, mercy=mercy, max_turns=10**6).play()
            assert (a.turns, a.winner, a.emptied, a.draws) == (b.turns, b.winner, b.emptied,
                                                                 b.draws)
    ok += 1

    # (14) random full games under the invariant checker (variant A, both finish effects)
    for s in range(1500):
        g = Game(2 + s % 5, random.Random(7 * 10**6 + s), check=True, end_last=True,
                 finish_effect=1 - (s // 5) % 2).play()
        assert g.n_alive == 1 and len(g.finished) + g.elims == g.n - 1
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


# per-game quantities summed (with squares) in variant runs
V_SUMS = ("finishes", "elims", "reshuffles", "roulettes", "roulette_hits", "plays", "draws",
          "passes", "lapses", "roulette_stops")


def run_chunk_variant(args):
    n, seed, games, n_check, opt = args
    rng = random.Random(seed)
    out = dict(n=n, turns=[], t_first_fin=[], exit_fin=0, exit_ko=0, stuck=[], looped=[],
               capped=[], loop_lens=[], winner_first=0,
               sums={k: 0 for k in V_SUMS}, sq={k: 0 for k in V_SUMS})
    sums, sq = out["sums"], out["sq"]
    for i in range(games):
        g = Game(n, rng, check=(i < n_check), end_last=opt["end_last"],
                 finish_effect=opt["finish_effect"], mercy=opt["mercy"],
                 detect_loops=opt["detect_loops"], max_turns=opt["max_turns"]).play()
        vals = (len(g.finished), g.elims, g.reshuffles, g.roul_played, g.roul_hits, g.plays,
                g.draws, g.passes, g.lapses, g.rstops)
        for k, v in zip(V_SUMS, vals):
            sums[k] += v
            sq[k] += v * v
        if g.stuck:
            out["stuck"].append(g.turns)
        elif g.looped:
            out["looped"].append(g.turns)
            out["loop_lens"].append(g.loop_len)
        elif g.capped:
            out["capped"].append(g.turns)
        else:
            out["turns"].append(g.turns)
            if g.emptied:
                out["exit_fin"] += 1
            else:
                out["exit_ko"] += 1
            if g.t_first_fin >= 0:
                out["t_first_fin"].append(g.t_first_fin)
    return out


def summarize_variant(parts, n, meta):
    import numpy as np
    T = np.asarray([t for P in parts for t in P["turns"]], dtype=np.int64)
    stuck = [t for P in parts for t in P["stuck"]]
    looped = [t for P in parts for t in P["looped"]]
    capped = [t for P in parts for t in P["capped"]]
    loop_lens = [x for P in parts for x in P["loop_lens"]]
    N_all = sum(len(P["turns"]) + len(P["stuck"]) + len(P["looped"]) + len(P["capped"])
                for P in parts)
    N = len(T)
    o = dict(meta)
    o["games"] = N_all
    o["completed"] = N
    if N:
        sd = float(T.std(ddof=1)) if N > 1 else 0.0
        p50, p90, p99 = (float(x) for x in np.percentile(T, [50, 90, 99]))
        o.update(mean_turns=float(T.mean()), sd_turns=sd, sem_turns=sd / math.sqrt(N),
                 p50=p50, p90=p90, p99=p99, max_turns=int(T.max()), min_turns=int(T.min()))
        o["p50_nearest_rank"], o["p90_nearest_rank"], o["p99_nearest_rank"] = (
            int(np.sort(T)[max(0, math.ceil(q * N) - 1)]) for q in (0.5, 0.9, 0.99))
        exit_fin = sum(P["exit_fin"] for P in parts)
        o["final_exit_finish_frac"] = exit_fin / N
        o["final_exit_knockout_frac"] = 1 - exit_fin / N
    TF = np.asarray([t for P in parts for t in P["t_first_fin"]], dtype=np.int64)
    if len(TF):
        o["mean_turns_to_first_finish"] = float(TF.mean())
        o["games_with_a_finish"] = int(len(TF))
    for k in V_SUMS:                                 # per-game means over ALL games
        s = sum(P["sums"][k] for P in parts)
        s2 = sum(P["sq"][k] for P in parts)
        m = s / N_all
        v = (s2 - N_all * m * m) / (N_all - 1) if N_all > 1 else 0.0
        o["mean_" + k] = m
        o["sem_" + k] = math.sqrt(max(v, 0.0) / N_all)
    o["stuck"] = len(stuck)
    o["looped"] = len(looped)
    o["capped"] = len(capped)
    o["stuck_turns"] = stuck[:1000]
    o["looped_turns"] = looped[:1000]
    o["loop_periods"] = sorted(Counter(loop_lens).items())
    o["capped_turns"] = capped[:1000]
    if capped and N:
        # never-ending games excluded above; with capped games counted at the cap the mean is
        # a strict lower bound for the (conditional) mean
        tot = float(T.sum()) + sum(capped)
        o["mean_turns_capped_at_cap_lower_bound"] = tot / (N + len(capped))
    if N:
        surv = {str(t): float((T > t).mean()) for t in (100, 200, 400, 800, 1600, 3200, 10**4,
                                                       3 * 10**4, 10**5, 3 * 10**5, 10**6)}
        o["survival_P(turns>t)"] = surv
        o["p999"] = float(np.percentile(T, 99.9))
    return o


def run_variant(a, players):
    detect = (a.mercy > MERCY) if a.detect_loops == "auto" else a.detect_loops == "1"
    opt = dict(end_last=(a.end_rule == "last"), finish_effect=a.finish_effect, mercy=a.mercy,
               detect_loops=detect, max_turns=a.max_turns)
    tasks = []
    for n in players:
        full, rem = divmod(a.games, a.chunk)
        sizes = [a.chunk] * full + ([rem] if rem else [])
        for ci, sz in enumerate(sizes):
            tasks.append((n, a.seed * 1000003 + n * 100019 + ci, sz, min(a.check, sz), opt))
    parts = {n: [] for n in players}
    t0 = time.time()
    with Pool(a.procs) as pool:
        for res in pool.imap_unordered(run_chunk_variant, tasks):
            parts[res["n"]].append(res)
    elapsed = time.time() - t0
    label = f"end_rule={a.end_rule},finish_effect={a.finish_effect},mercy={a.mercy}"
    per = {}
    for n in players:
        meta = dict(seed=a.seed, games_requested=a.games, chunk=a.chunk, max_turns=a.max_turns,
                    detect_loops=detect, invariant_checked_games=sum(t[3] for t in tasks
                                                                     if t[0] == n),
                    elapsed_s_whole_invocation=elapsed, procs=a.procs,
                    command=" ".join(sys.argv))
        per[str(n)] = summarize_variant(parts[n], n, meta)

    # merge into the output file (one entry per rule configuration and player count)
    doc = {"format": "ref_nomercy.py variant results (RULES.md sec. 7 / --mercy)",
           "percentile_method": "numpy linear (also nearest rank)", "runs": {}}
    if os.path.exists(a.out):
        with open(a.out) as f:
            old = json.load(f)
        if "runs" not in old:
            sys.exit(f"refusing to overwrite {a.out}: not a variant-results file")
        doc = old
    run = doc["runs"].setdefault(label, {"end_rule": a.end_rule,
                                         "finish_effect": a.finish_effect,
                                         "mercy": a.mercy, "per_players": {}})
    run["per_players"].update(per)
    run["per_players"] = dict(sorted(run["per_players"].items(), key=lambda kv: int(kv[0])))
    with open(a.out, "w") as f:
        json.dump(doc, f, indent=1)

    print(label)
    print(f"{'n':>2} {'games':>6} {'done':>6} {'mean':>10} {'sem':>8} {'sd':>9} {'p50':>8} "
          f"{'p90':>8} {'p99':>9} {'max':>8} {'fin':>5} {'KO':>5} {'exFin':>6} {'resh':>8} "
          f"{'roul':>7} {'stk':>3} {'loop':>4} {'cap':>3}")
    for n in players:
        o = per[str(n)]
        if not o["completed"]:
            print(f"{n:>2} {o['games']:>6} {0:>6}  (no completed games) stuck {o['stuck']} "
                  f"looped {o['looped']} capped {o['capped']}")
            continue
        print(f"{n:>2} {o['games']:>6} {o['completed']:>6} {o['mean_turns']:>10.2f} "
              f"{o['sem_turns']:>8.2f} {o['sd_turns']:>9.1f} {o['p50']:>8.1f} {o['p90']:>8.1f} "
              f"{o['p99']:>9.1f} {o['max_turns']:>8} {o['mean_finishes']:>5.3f} "
              f"{o['mean_elims']:>5.3f} {o['final_exit_finish_frac']:>6.4f} "
              f"{o['mean_reshuffles']:>8.3f} {o['mean_roulettes']:>7.3f} {o['stuck']:>3} "
              f"{o['looped']:>4} {o['capped']:>3}")
    print(f"elapsed {elapsed:.1f}s -> {a.out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200000, help="games per player count")
    ap.add_argument("--players", default="2,3,4,5,6")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20260927)
    ap.add_argument("--check", type=int, default=250, help="invariant-checked games per chunk")
    ap.add_argument("--out", default=None,
                    help="default: ref_results.json (official rules) or ref_results_last.json "
                         "(any other rule option); variant runs merge into an existing file")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--v1-turns", action="store_true",
                    help="old turn count (Roulette reveals not counted), as in ref_results.json")
    ap.add_argument("--end-rule", choices=("first", "last"), default="first",
                    help="first = official (first empty hand ends the game); last = RULES.md "
                         "sec. 7, play until one player is left")
    ap.add_argument("--finish-effect", type=int, choices=(0, 1), default=1,
                    help="sec. 7: does the finishing card take effect (end-rule last only)")
    ap.add_argument("--mercy", type=int, default=MERCY,
                    help="knockout threshold; 25 = official Mercy rule, 1000 = no Mercy rule")
    ap.add_argument("--max-turns", type=int, default=0,
                    help="safety cap per game (0 = none); capped games are reported separately")
    ap.add_argument("--detect-loops", choices=("auto", "0", "1"), default="auto",
                    help="flag provably endless games (auto: on iff --mercy > 25)")
    a = ap.parse_args()
    global COUNT_ROULETTE_TURN
    COUNT_ROULETTE_TURN = not a.v1_turns

    if a.selftest:
        k = selftest()
        print(f"selftest: {k} groups passed")
        return

    here = os.path.dirname(os.path.abspath(__file__))
    variant = (a.end_rule != "first" or a.mercy != MERCY or a.max_turns
               or a.detect_loops == "1")
    if a.finish_effect != 1 and a.end_rule == "first":
        ap.error("--finish-effect applies only with --end-rule last")
    if a.mercy < 2:
        ap.error("--mercy must be at least 2")
    if a.out is None:
        a.out = os.path.join(here, "ref_results_last.json" if variant else "ref_results.json")
    players = [int(x) for x in a.players.split(",")]
    if variant:
        return run_variant(a, players)

    import numpy as np
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
