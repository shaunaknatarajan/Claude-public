#!/usr/bin/env python3
"""Step-by-step UNO Show 'Em No Mercy engine for games played by AI players with personalities.

The rules are exactly those of ../RULES.md (default options), the same as the verified C
simulator ../sim/nomercy.c and the Python reference ../crosscheck/ref_nomercy.py. Unlike those,
this engine stops at every decision that has more than one option and waits for the player,
who only ever sees their own hand plus what is public at the table.

Game state lives in <game-dir>/state.pkl, and every event is appended to <game-dir>/log.txt.

CLI:
  engine.py new  --game DIR --players Name1,Name2,... [--seed S]
  engine.py view --game DIR            # what the player to move can see, with numbered options
  engine.py act  --game DIR --player NAME --choice K [--note TEXT]
  engine.py status --game DIR          # one-line JSON: whose decision, or the result
  engine.py autoplay --players N --games G [--seed S]   # random play, to validate against the C simulator

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
COLORS = ["Red", "Yellow", "Green", "Blue"]
KIND_LONG = {K_D2: "Draw 2", K_D4: "Draw 4", K_SKIP: "Skip", K_SKIPALL: "Skip Everyone", K_REV: "Reverse",
             K_DALL: "Discard All"}
WILD_LONG = {WRD4: "Wild Reverse Draw 4", WD6: "Wild Draw 6", WD10: "Wild Draw 10", ROUL: "Wild Color Roulette"}


def build_deck():
    deck = []
    for c in range(4):
        b = c * 16
        for num in range(10):
            deck += [b + num] * 2
        deck += [b + K_D2] * 3 + [b + K_D4] * 2 + [b + K_SKIP] * 3 + [b + K_SKIPALL] * 2
        deck += [b + K_REV] * 3 + [b + K_DALL] * 3
    deck += [WRD4] * 8 + [WD6] * 4 + [WD10] * 4 + [ROUL] * 8
    assert len(deck) == 168
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


# ----------------------------------------------------------------------------- game
class Game:
    def __init__(self, names, seed):
        n = len(names)
        assert 2 <= n <= 6, "the official game is for 2-6 players"
        self.names = list(names)
        self.n = n
        self.rng = random.Random(seed)
        self.pile = build_deck()
        self.rng.shuffle(self.pile)
        self.discard = []          # below the top card; knocked-out hands are added here (set aside)
        self.hands = [Counter() for _ in range(n)]
        self.alive = [True] * n
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

    # ------------------------------------------------------------------ helpers
    def say(self, msg):
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

    def draw_one(self, p):
        """Give p one card. Returns the card, or None if p was knocked out (Mercy rule)."""
        if not self.pile:
            if not self.discard:
                raise RuntimeError("no card left to draw (impossible with 2-6 players and the Mercy rule)")
            self.pile = self.discard
            self.discard = []
            self.rng.shuffle(self.pile)
            self.reshuffles += 1
            self.say("The discard pile is shuffled into a new draw pile.")
        t = self.pile.pop()
        self.hands[p][t] += 1
        self.draws += 1
        if self.size(p) >= MERCY:
            self.knock_out(p)
            return None
        return t

    def knock_out(self, p):
        self.say(f"{self.names[p]} reaches {MERCY} cards and is knocked out by the Mercy rule!")
        for t, k in self.hands[p].items():
            self.discard += [t] * k
        self.hands[p] = Counter()
        self.alive[p] = False
        self.knockouts.append((self.turns, self.names[p]))
        if self.n_alive() == 1:
            w = self.alive.index(True)
            self.finish(w, "last player standing")

    def finish(self, w, reason):
        if not self.over:
            self.over, self.winner, self.end_reason = True, w, reason
            self.decision = None
            self.say(f"GAME OVER after {self.turns} turns: {self.names[w]} wins ({reason}).")

    # ------------------------------------------------------------------ turn flow
    def begin_turn(self):
        """Start the current player's turn; resolve everything automatic until a decision is needed."""
        while not self.over:
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
        for _ in range(total):
            if self.draw_one(p) is None:
                break
        if not self.over:
            self.cur = self.nxt(p)

    def draw_until_playable(self, p):
        k = 0
        while True:
            t = self.draw_one(p)
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
        if self.size(p) == 0:
            self.finish(p, "played their last card")
            return
        v = draw_value(t)
        if t == WRD4:
            self.pending += v
            self.last_dv = v
            self.dir = -self.dir
            self.cur = p if self.n_alive() == 2 else self.nxt(p)
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
            self.cur = p
            self.say(f"Everyone else is skipped; {self.names[p]} goes again.")
        elif k == K_REV:
            self.dir = -self.dir
            self.cur = p if self.n_alive() == 2 else self.nxt(p)
            self.say("Direction reverses.")
        elif t == ROUL:
            victim = self.nxt(p)
            self.turns += 1  # the victim's (lost) turn, as in RULES.md section 6
            self.decision = {"player": victim, "kind": "roulette_color",
                             "options": [("color", None, c) for c in range(4)], "roulette_by": p}
            return
        elif k == 0:
            order = [q for q in range(self.n) if self.alive[q]]
            new = [None] * self.n
            for q in order:
                new[self.nxt(q)] = self.hands[q]
            for q in order:
                self.hands[q] = new[q]
            self.cur = self.nxt(p)
            self.say("Everyone passes their hand to the next player.")
        elif k == 7:
            self.hands[p], self.hands[x] = self.hands[x], self.hands[p]
            self.cur = self.nxt(p)
            self.say(f"{self.names[p]} swaps hands with {self.names[x]}.")
        else:
            self.cur = self.nxt(p)

    def roulette(self, victim, c):
        self.color = c
        k = 0
        while True:
            t = self.draw_one(victim)
            k += 1
            if t is None:
                break
            if t < 64 and (t >> 4) == c:
                break
        if self.alive[victim]:
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

    def view(self, p):
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
        kind = d["kind"]
        if kind == "roulette_color":
            head = (f"{self.names[d['roulette_by']]} played a Wild Color Roulette on you! Name a color; you will "
                    "reveal cards from the draw pile until that color appears and keep them all (wilds don't count):")
        else:
            head = {"play": "Your turn. You must play one of these (strict must-play rule):",
                    "penalty": "A penalty is pending on you. Choose:",
                    "forced_color": "You drew a wild and must play it. Choose its color:",
                    "forced_swap": "You drew a 7 and must play it. Choose whom to swap hands with:"}[kind]
        lines.append(head)
        for i, o in enumerate(d["options"]):
            lines.append(f"  {i}: {self.describe_option(o)}")
        return "\n".join(lines)

    def status(self):
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
        assert total == 168, total
        for q in range(self.n):
            assert self.alive[q] or self.size(q) == 0
            assert not self.alive[q] or self.size(q) < MERCY


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


def autoplay(n, games, seed):
    rng = random.Random(seed)
    turns = []
    for i in range(games):
        g = Game([f"P{j}" for j in range(n)], seed * 1000003 + i)
        while not g.over:
            g.choose(random_choice(g, rng))
        g.check()
        turns.append(g.turns)
    m = sum(turns) / len(turns)
    sd = (sum((x - m) ** 2 for x in turns) / (len(turns) - 1)) ** 0.5
    print(json.dumps({"players": n, "games": games, "mean_turns": m, "sem": sd / len(turns) ** 0.5,
                      "max": max(turns)}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("new"); a.add_argument("--game", required=True); a.add_argument("--players", required=True)
    a.add_argument("--seed", type=int, default=1)
    a = sub.add_parser("view"); a.add_argument("--game", required=True)
    a = sub.add_parser("status"); a.add_argument("--game", required=True)
    a = sub.add_parser("act"); a.add_argument("--game", required=True); a.add_argument("--player", required=True)
    a.add_argument("--choice", type=int, required=True); a.add_argument("--note", default="")
    a = sub.add_parser("autoplay"); a.add_argument("--players", type=int, default=4)
    a.add_argument("--games", type=int, default=1000); a.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    if args.cmd == "autoplay":
        autoplay(args.players, args.games, args.seed)
        return
    if args.cmd == "new":
        os.makedirs(args.game, exist_ok=True)
        g = Game(args.players.split(","), args.seed)
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
