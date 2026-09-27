#!/usr/bin/env python3
"""Two players, no Mercy rule: is there a reachable forced endless loop?  (Answer: no.)

This is the check script behind results/no_mercy/witness_p2.json.  With two players a game
ends at the first exit under both the official ending and the "play until one player is
left" ending (RULES.md section 7), so one answer covers both.

Result.  No legal 2-player history can reach a forced cycle (a cycle of states in which no
player ever has a decision with two or more options).  The candidate loop (two Reverses of
two colours, the mover holding only cards that match neither) IS a forced 2-cycle once it
is on the table, but it cannot be reached.  The proof sketch is in witness_p2.json
("proof"); this script machine-checks every rules fact the proof uses, with a small
rules engine written from RULES.md and sim/nomercy.c (default rules, -mercy 1000):

  1. engine cross-check: the engine replays the 6-player proven cycle that the C simulator
     printed in results/no_mercy/cycle_example.txt and reproduces the C simulator's states.
  2. the candidate loops are genuine forced cycles once reached: the Reverse pair (the
     candidate from the task), a Skip pair, a Skip Everyone pair, and the two hand-swapping
     variants (a pair of 7s, a pair of 0s).  Each is run for 1000 turns with an assertion
     that every turn is forced and the state repeats with period 2.
  3. the lemmas of the proof, exhaustively over all 68 card types:
       L1 free-turn playability between coloured cards is symmetric
          (b playable on a  <=>  a playable on b);
       L2 a wild is playable on every free turn; a Wild Draw 10 can be stacked on every
          pending penalty;
       L3 with two players, the hand that plays a card of kind k acts again on a free turn
          iff k is Skip, Skip Everyone, Reverse, 0 or 7 (0 and 7 swap the two hands, so the
          same HAND moves again, from the other seat);
       L4 "last change of the wild hand" table: for every way the hand W that holds the
          wilds can change for the last time (play of any of the 68 types from a free
          turn, a stacking play, accepting a penalty, being a Roulette victim, drawing
          until playable), either the card left on top is not of a kind from L3, or the
          next actor is W itself on a free turn holding a playable wild, so W must change
          again.  Hence W has no last change before a forced cycle, a contradiction.
  4. (optional, --sim PATH) re-runs the C simulator on 2-player no-Mercy games with cycle
     detection under several policies and adversarial card order.

usage: python3 analysis/witness_p2.py [--sim /path/to/nomercy] [--games N]
exit status 0 = every check passed.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------- cards (as sim/nomercy.c)
# coloured type = colour*16 + kind, colour 0..3 = R, Y, G, B; wilds 64..67
K_D2, K_D4, K_SKIP, K_SKIPALL, K_REV, K_DISCALL = 10, 11, 12, 13, 14, 15
WRD4, WD6, WD10, ROUL = 64, 65, 66, 67
COLORS = "RYGB"
KIND_NAME = [str(i) for i in range(10)] + ["D2", "D4", "Skip", "SkipAll", "Rev", "DiscardAll"]
WILD_NAME = {WRD4: "WWRD4", WD6: "WWD6", WD10: "WWD10", ROUL: "WRoulette"}
COLORED_COUNT = [2] * 10 + [3, 2, 3, 2, 3, 3]
WILD_COUNT = {WRD4: 8, WD6: 4, WD10: 4, ROUL: 8}
ALL_TYPES = list(range(64)) + [WRD4, WD6, WD10, ROUL]
GO_AGAIN_KINDS = {0, 7, K_SKIP, K_SKIPALL, K_REV}


def name(t):
    return WILD_NAME[t] if t >= 64 else COLORS[t >> 4] + KIND_NAME[t & 15]


NAME2T = {name(t): t for t in ALL_TYPES}


def color(t):
    return 4 if t >= 64 else t >> 4


def kind(t):
    return 16 + (t - 64) if t >= 64 else t & 15


def drawval(t):
    return {K_D2: 2, K_D4: 4}.get(t & 15, 0) if t < 64 else {WRD4: 4, WD6: 6, WD10: 10}.get(t, 0)


def full_deck():
    c = Counter()
    for col in range(4):
        for k in range(16):
            c[col * 16 + k] = COLORED_COUNT[k]
    for w, n in WILD_COUNT.items():
        c[w] = n
    assert sum(c.values()) == 168
    return c


def playable(t, top, col):
    """Free-turn legality (sim/nomercy.c playable())."""
    if t >= 64:
        return True
    if t >> 4 == col:
        return True
    return top < 64 and (t & 15) == (top & 15)


def stackable(t, stackv):
    v = drawval(t)
    return v > 0 and v >= stackv


# ---------------------------------------------------------------- engine
class NotForced(Exception):
    """The turn contains a decision with >= 2 options or a genuinely random reshuffle."""


class State:
    def __init__(self, np_, hands, pile, disc, top, col, cur, dirn=1, stack=0, stackv=0):
        self.np = np_
        self.hands = [Counter(h) for h in hands]
        self.pile = list(pile)          # draw from the END
        self.disc = Counter(disc)       # discard pile below the top card
        self.top, self.color, self.cur, self.dir = top, col, cur, dirn
        self.stack, self.stackv = stack, stackv
        self.over = False
        self.check()

    def key(self):
        return (tuple(tuple(sorted((+h).items())) for h in self.hands), tuple(self.pile),
                tuple(sorted((+self.disc).items())), self.top, self.color, self.cur, self.dir,
                self.stack, self.stackv)

    def check(self):
        tot = Counter()
        for h in self.hands:
            tot.update(h)
        tot.update(self.pile)
        tot.update(self.disc)
        tot[self.top] += 1
        assert +tot == full_deck(), "card conservation violated"

    def nxt(self, p, d=None):
        return (p + (self.dir if d is None else d)) % self.np

    def summary(self):
        return {"cur": self.cur, "dir": self.dir, "top": name(self.top), "color": COLORS[self.color],
                "stack": self.stack, "pile": len(self.pile), "disc": sum(self.disc.values()),
                "hand_sizes": [sum(h.values()) for h in self.hands]}


def draw_one(s, p, forced):
    """sim/nomercy.c draw_one: reshuffle the discard pile when the draw pile is empty."""
    if not s.pile:
        cards = list((+s.disc).elements())
        if forced and len(cards) >= 2:
            raise NotForced("reshuffle of %d cards" % len(cards))
        s.pile = cards
        s.disc = Counter()
    if not s.pile:
        return None
    t = s.pile.pop()
    s.hands[p][t] += 1
    return t


def play_card(s, p, t, forced=True, wild_color=None, roulette_color=None):
    """sim/nomercy.c play_card for end_rule 0 (2 players: identical under end_rule 1)."""
    h = s.hands[p]
    assert h[t] > 0
    h[t] -= 1
    s.disc[s.top] += 1
    s.top = t
    k, c = kind(t), color(t)
    if c == 4:
        if forced:
            raise NotForced("wild colour choice")
        if k != 16 + 3:
            s.color = wild_color
    else:
        s.color = c
    if k == K_DISCALL:
        for kk in range(16):
            tt = c * 16 + kk
            if h[tt]:
                s.disc[tt] += h[tt]
                h[tt] = 0
    if sum(h.values()) == 0:
        s.over = True
        return
    v = drawval(t)
    if k in (K_D2, K_D4, 16 + 1, 16 + 2):
        s.stack += v
        s.stackv = v
        s.cur = s.nxt(p)
    elif k == 16:                                   # Wild Reverse Draw 4
        s.stack += v
        s.stackv = v
        s.dir = -s.dir
        s.cur = p if s.np == 2 else s.nxt(p)
    elif k == K_SKIP:
        s.cur = s.nxt(s.nxt(p))
    elif k == K_SKIPALL:
        s.cur = p
    elif k == K_REV:
        s.dir = -s.dir
        s.cur = p if s.np == 2 else s.nxt(p)
    elif k == 16 + 3:                               # Roulette: victim names colour, reveals
        victim = s.nxt(p)
        if forced:
            raise NotForced("roulette colour choice")
        s.color = roulette_color
        while True:
            d = draw_one(s, victim, forced)
            if d is None or color(d) == roulette_color:
                break
        s.cur = s.nxt(victim)
    elif k == 0:                                    # every hand passes on in the direction of play
        old = [Counter(x) for x in s.hands]
        for q in range(s.np):
            s.hands[s.nxt(q)] = old[q]
        s.cur = s.nxt(p)
    elif k == 7:                                    # swap; 2 players: the target is forced
        if forced and s.np > 2:
            raise NotForced("7 target choice")
        q = s.nxt(p)
        s.hands[p], s.hands[q] = s.hands[q], s.hands[p]
        s.cur = s.nxt(p)
    else:
        s.cur = s.nxt(p)


def forced_turn(s):
    """Play one turn that must be forced; raise NotForced otherwise.  Returns a log entry."""
    p = s.cur
    h = s.hands[p]
    if s.stack > 0:
        opts = sorted(t for t in h if h[t] and stackable(t, s.stackv))
        if opts:
            raise NotForced("stack or accept")
        total, s.stack, s.stackv = s.stack, 0, 0
        drawn = []
        for _ in range(total):
            d = draw_one(s, p, True)
            if d is None:
                break
            drawn.append(name(d))
        s.cur = s.nxt(p)
        return {"player": p, "action": "accept", "drawn": drawn}
    opts = sorted(t for t in h if h[t] and playable(t, s.top, s.color))
    if len(opts) >= 2:
        raise NotForced("%d playable types" % len(opts))
    drawn = []
    if opts:
        t = opts[0]
    else:
        while True:
            d = draw_one(s, p, True)
            if d is None:
                raise NotForced("stuck pass")     # never happens in the loops checked here
            drawn.append(name(d))
            if playable(d, s.top, s.color):
                t = d
                break
    play_card(s, p, t, forced=True)
    return {"player": p, "action": "play", "card": name(t), "drawn": drawn}


def run_forced(s, turns):
    """Run `turns` forced turns; return (period, log of the first period)."""
    seen = {s.key(): 0}
    log = []
    period = None
    for i in range(1, turns + 1):
        entry = forced_turn(s)
        s.check()
        assert not s.over, "the game ended"
        entry["state_after"] = s.summary()
        if period is None:
            log.append(entry)
        k = s.key()
        if k in seen and period is None:
            period = i - seen[k]
        seen.setdefault(k, i)
    return period, log


# ---------------------------------------------------------------- 1. engine vs C simulator
def parse_dump(path):
    """States printed by sim/nomercy.c print_state (results/no_mercy/cycle_example.txt)."""
    states, cur = [], None
    for line in open(path):
        m = re.match(r"turn (\d+) cur=(\d+) dir=(-?\d+) top=(\S+) color=(\S) stack=(\d+)/(\d+) pile=(\d+) disc=(\d+)", line)
        if m:
            cur = {"cur": int(m[2]), "dir": int(m[3]), "top": m[4], "color": m[5], "stack": int(m[6]),
                   "stackv": int(m[7]), "pile": int(m[8]), "disc": int(m[9]), "hands": []}
            states.append(cur)
            continue
        m = re.match(r"\s+p(\d+)\s*X?\s*\(\s*(\d+)\):(.*)", line)
        if m and cur is not None:
            cards = [NAME2T[x] for x in m[3].split()]
            assert len(cards) == int(m[2])
            cur["hands"].append(Counter(cards))
    return states


def check_engine_vs_c():
    path = os.path.join(ROOT, "results/no_mercy/cycle_example.txt")
    st = parse_dump(path)
    a = st[0]
    np_ = len(a["hands"])
    held = Counter()
    for h in a["hands"]:
        held.update(h)
    rest = full_deck() - held
    rest[NAME2T[a["top"]]] -= 1
    rest = +rest
    assert a["pile"] == 0 and sum(rest.values()) == a["disc"]
    s = State(np_, a["hands"], [], rest, NAME2T[a["top"]], COLORS.index(a["color"]), a["cur"], a["dir"],
              a["stack"], a["stackv"])
    for b in st[1:]:
        forced_turn(s)
        s.check()
        got = ([+h for h in s.hands], name(s.top), COLORS[s.color], s.cur, s.dir, len(s.pile),
               sum(s.disc.values()))
        want = ([+h for h in b["hands"]], b["top"], b["color"], b["cur"], b["dir"], b["pile"], b["disc"])
        assert got == want, "engine disagrees with the C simulator dump"
    return {"file": "results/no_mercy/cycle_example.txt", "players": np_, "turns_replayed": len(st) - 1,
            "matches_c_simulator": True}


# ---------------------------------------------------------------- 2. candidate loops
def loop_state(pair, mover_ok):
    """2 players. Seat 0 (A) to move; top = pair[0]; the only other loose card, pair[1], is
    the whole discard pile; the draw pile is empty; A holds every card that mover_ok accepts,
    B (seat 1) holds everything else."""
    deck = full_deck()
    deck[pair[0]] -= 1
    deck[pair[1]] -= 1
    a = Counter({t: n for t, n in deck.items() if n and mover_ok(t)})
    b = +(deck - a)
    return State(2, [a, b], [], [pair[1]], pair[0], color(pair[0]), 0, 1)


def check_candidate_loops():
    R, Y, G, B = 0, 1, 2, 3
    out = []
    specs = [
        ("reverse pair (task candidate): Red Reverse / Blue Reverse", (R * 16 + K_REV, B * 16 + K_REV),
         lambda t: t < 64 and t >> 4 in (Y, G) and t & 15 != K_REV, "A plays the drawn Reverse; with 2 players it acts as a Skip, so A moves again"),
        ("skip pair: Red Skip / Blue Skip", (R * 16 + K_SKIP, B * 16 + K_SKIP),
         lambda t: t < 64 and t >> 4 in (Y, G) and t & 15 != K_SKIP, "Skip with 2 players: A moves again"),
        ("skip-everyone pair: Red Skip Everyone / Blue Skip Everyone", (R * 16 + K_SKIPALL, B * 16 + K_SKIPALL),
         lambda t: t < 64 and t >> 4 in (Y, G) and t & 15 != K_SKIPALL, "Skip Everyone: A moves again"),
        ("7 pair: Red 7 / Blue 7 (hands swap every turn)", (R * 16 + 7, B * 16 + 7),
         lambda t: t < 64 and t >> 4 in (Y, G) and t & 15 != 7, "the 7 swaps the hands, so the small hand moves again from the other seat"),
        ("0 pair: Red 0 / Blue 0 (hands pass every turn)", (R * 16 + 0, B * 16 + 0),
         lambda t: t < 64 and t >> 4 in (Y, G) and t & 15 != 0, "the 0 passes the hands, so the small hand moves again from the other seat"),
    ]
    for label, pair, ok, why in specs:
        s = loop_state(pair, ok)
        start = s.summary()
        period, log = run_forced(s, 1000)
        assert period == 2, (label, period)
        out.append({"loop": label, "why_forced": why, "start": start,
                    "mover_hand": sorted(name(t) for t in s.hands[s.cur].elements()),
                    "forced_turns_checked": 1000, "period": period, "one_period": log})
    return out


# ---------------------------------------------------------------- 3. lemmas
def lemma_symmetry():
    bad = [(a, b) for a in range(64) for b in range(64)
           if playable(b, a, a >> 4) != playable(a, b, b >> 4)]
    assert not bad
    return "checked all 64x64 ordered pairs of coloured types: symmetric"


def lemma_wilds():
    for top in ALL_TYPES:
        for col in range(4):
            for w in (WRD4, WD6, WD10, ROUL):
                assert playable(w, top, col)
    for v in (2, 4, 6, 10):
        assert stackable(WD10, v)
    return "every wild is playable on every (top, colour); WD10 stacks on every penalty value 2/4/6/10"


def test_state(mover_card, mover_seat=0):
    """2 players: the mover holds `mover_card` plus Yellow 5; the other hand W holds every wild
    and every other card except the top and a few loose cards.  Top is a number of the
    mover card's colour (or Red 3 for a wild), so the card is playable."""
    deck = full_deck()
    col = color(mover_card)
    top = (col if col < 4 else 0) * 16 + 3
    loose = [NAME2T["G9"], NAME2T["G8"], NAME2T["G6"], NAME2T["B2"]]   # draw pile, then discard
    mover = Counter([mover_card, NAME2T["Y5"]])
    deck.subtract(mover)
    deck[top] -= 1
    for x in loose:
        deck[x] -= 1
    assert min(deck.values()) >= 0
    w = +deck
    hands = [None, None]
    hands[mover_seat], hands[1 - mover_seat] = mover, w
    return State(2, hands, loose[:2], loose[2:], top, col if col < 4 else 0, mover_seat)


def is_wild_hand(h):
    return any(h[w] for w in (WRD4, WD6, WD10, ROUL))


def lemma_go_again():
    """L3: after the small hand plays card t, does the SAME hand act next on a free turn?"""
    table = {}
    for t in ALL_TYPES:
        s = test_state(t)
        small_before = +s.hands[0] - Counter([t])
        other_before = +s.hands[1]
        play_card(s, 0, t, forced=False, wild_color=0, roulette_color=0)
        nxt_hand = +s.hands[s.cur]
        other_hand = +s.hands[1 - s.cur] if nxt_hand == small_before else None
        # the same hand moves again, on a free turn, and the other hand is untouched
        same_hand_free = nxt_hand == small_before and s.stack == 0 and other_hand == other_before
        k = kind(t)
        kname = KIND_NAME[k] if k < 16 else WILD_NAME[t]
        prev = table.get(kname)
        assert prev is None or prev == same_hand_free
        table[kname] = same_hand_free
        if t < 64:
            assert same_hand_free == (k in GO_AGAIN_KINDS), (name(t), same_hand_free)
        else:
            assert not same_hand_free, name(t)
    return table


def lemma_last_change():
    """L4: every way the wild hand W can change leaves either a top card whose kind is not a
    go-again kind, or W itself to act next on a free turn with a playable wild."""
    rows = []
    # (a) W plays any card from a free turn (includes the card that ends a draw-until-playable)
    for t in ALL_TYPES:
        s = test_state(t, mover_seat=0)
        s.hands[0], s.hands[1] = s.hands[1], s.hands[0]      # the WILD hand W now moves
        s.hands[0][t] += 1
        s.hands[1][t] -= 1
        s.check()
        wset_after = +s.hands[0] - Counter([t])
        play_card(s, 0, t, forced=False, wild_color=0, roulette_color=0)
        top_kind_go_again = s.top < 64 and kind(s.top) in GO_AGAIN_KINDS
        nxt = +s.hands[s.cur]
        w_moves_free = s.stack == 0 and is_wild_hand(nxt) and nxt == wset_after
        ok = (not top_kind_go_again) or w_moves_free
        assert ok, name(t)
        if top_kind_go_again:
            assert any(playable(x, s.top, s.color) for x in nxt)
        rows.append({"event": "W plays " + name(t), "top_after": name(s.top),
                     "top_kind_is_go_again": top_kind_go_again, "W_moves_next_on_free_turn": w_moves_free})
    # (b) W stacks onto a pending penalty: the new top is a Draw Card (not a go-again kind)
    for t in ALL_TYPES:
        if drawval(t):
            assert kind(t) not in GO_AGAIN_KINDS
            rows.append({"event": "W stacks " + name(t), "top_after": name(t), "top_kind_is_go_again": False})
    # (c) W accepts a penalty: the top stays the Draw Card the other hand played
    rows.append({"event": "W accepts a penalty", "top_after": "a Draw Card (D2/D4/WRD4/WD6/WD10)",
                 "top_kind_is_go_again": False})
    # (d) W is a Roulette victim: the top is the Roulette, a wild
    rows.append({"event": "W reveals as a Roulette victim", "top_after": "WRoulette", "top_kind_is_go_again": False})
    # (e) W draws until playable: it then plays the drawn card in the same turn -> case (a)
    rows.append({"event": "W draws until playable", "top_after": "the card W then plays: see case (a)",
                 "top_kind_is_go_again": None})
    return rows


# ---------------------------------------------------------------- 4. C simulator runs
def run_sim(sim, games):
    cfgs = [["-policy", "random"], ["-policy", "random", "-adv_nature", "1"], ["-policy", "greedy"],
            ["-policy", "random", "-end_rule", "1"]]
    res = []
    for c in cfgs:
        cmd = [sim, "-p", "2", "-n", str(games), "-threads", "1", "-seed", "2027", "-mercy", "1000",
               "-detect_cycles", "1", "-cap", "20000000"] + c
        d = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
        res.append({"cmd": " ".join(cmd[1:]), "games": d["games"], "mean_turns": d["mean_turns"],
                    "max_turns": d["max_turns"], "proven_cycles": d["end_proven_cycle"],
                    "stuck": d["end_stuck_forever"], "capped": d["end_capped"]})
        assert d["end_proven_cycle"] == 0 and d["end_stuck_forever"] == 0 and d["end_capped"] == 0
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", help="path to a compiled sim/nomercy.c (optional)")
    ap.add_argument("--games", type=int, default=2000)
    ap.add_argument("--json", help="write the check report to this file")
    a = ap.parse_args()
    rep = {}
    rep["engine_vs_c_simulator"] = check_engine_vs_c()
    print("1. engine reproduces the C simulator's 6-player cycle dump: OK")
    rep["candidate_loops"] = check_candidate_loops()
    for x in rep["candidate_loops"]:
        print("2. forced 2-cycle once reached (1000 forced turns):", x["loop"])
    rep["lemmas"] = {"L1_symmetry": lemma_symmetry(), "L2_wilds": lemma_wilds(),
                     "L3_same_hand_moves_again_on_free_turn": lemma_go_again(),
                     "L4_last_change_of_wild_hand": lemma_last_change()}
    print("3. L1 symmetry, L2 wilds, L3 go-again kinds =",
          sorted(k for k, v in rep["lemmas"]["L3_same_hand_moves_again_on_free_turn"].items() if v),
          ", L4 last-change table (%d events): OK" % len(rep["lemmas"]["L4_last_change_of_wild_hand"]))
    if a.sim:
        rep["c_simulator_runs"] = run_sim(a.sim, a.games)
        for r in rep["c_simulator_runs"]:
            print("4.", r)
    if a.json:
        json.dump(rep, open(a.json, "w"), indent=1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    sys.exit(main())
