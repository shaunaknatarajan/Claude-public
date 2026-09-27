#!/usr/bin/env python3
"""A live card table for AI players with personalities who can talk to each other.

Wraps the validated game engine (engine.py) for the user's table rules: no Mercy rule, play
until one player is left (RULES.md section 7). Every seat is played by its own AI agent, and
all agents run at the same time. A seat waits for something to happen, sees only what that
player could see at a real table (their own hand, the table, public talk, their own notes),
acts when it is their decision, and may say something to the table at any time.

Files in the game directory (besides the engine's state.pkl and log.txt):
  meta.json          start time, time limit, and (once reached) where the time limit stopped play
  chat.jsonl         public table talk: {i, turn, player, text, t}
  decisions.jsonl    one record per decision: {turn, player, kind, n_options, hand_size, pending, t}
  notes_<name>.jsonl a player's private notes (only that player's seat ever sees them)
  repeats.json       full positions seen while the piles are nearly dry; a repeat is flagged

CLI:
  table.py new    --game DIR --players A,B,... --seed S [--time-limit-hours 5]
  table.py wait   --game DIR --player NAME --seen N [--timeout SECONDS]
  table.py act    --game DIR --player NAME --choice K [--say TEXT] [--note TEXT]
  table.py say    --game DIR --player NAME --text TEXT
  table.py note   --game DIR --player NAME --text TEXT
  table.py status --game DIR
"""
import argparse
import fcntl
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402

sys.modules["__main__"].Game = engine.Game  # pickles saved by engine.py's CLI refer to __main__.Game

MAX_SAY = 300
REPEAT_WINDOW = 10  # remember positions only while draw pile + discard hold at most this many cards


# ----------------------------------------------------------------------------- files
def path(gdir, name):
    return os.path.join(gdir, name)


class Lock:
    def __init__(self, gdir):
        self.f = open(path(gdir, ".lock"), "a")

    def __enter__(self):
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def read_jsonl(p):
    if not os.path.exists(p):
        return []
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass  # a line being written right now
    return out


def append_jsonl(p, rec):
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def meta(gdir):
    return json.load(open(path(gdir, "meta.json")))


def seat_of(g, name):
    if name not in g.names:
        raise SystemExit(json.dumps({"error": f"no player called {name}"}))
    return g.names.index(name)


def time_up(gdir, g):
    m = meta(gdir)
    if m.get("stopped"):
        return True
    if g.over or time.time() - m["t_start"] < m["time_limit_s"]:
        return False
    with Lock(gdir):
        m = meta(gdir)
        if not m.get("stopped"):
            m["stopped"] = {"turn": g.turns, "decisions": g.decisions, "t": time.time(),
                            "reason": f"time limit of {m['time_limit_s'] / 3600:g} hours reached"}
            json.dump(m, open(path(gdir, "meta.json"), "w"), indent=1)
    return True


# ----------------------------------------------------------------------------- what a seat sees
def talk_lines(gdir, since=0, last=12):
    chat = read_jsonl(path(gdir, "chat.jsonl"))
    new = [c for c in chat if c["i"] >= since]
    shown = new[-last:]
    lines = []
    if len(new) > len(shown):
        lines.append(f"  ({len(new) - len(shown)} earlier messages not shown)")
    lines += [f"  [turn {c['turn']}] {c['player']}: \"{c['text']}\"" for c in shown]
    return lines, (chat[-1]["i"] + 1 if chat else 0)


def note_lines(gdir, me):
    notes = read_jsonl(path(gdir, f"notes_{me}.jsonl"))
    return [f"  - (turn {n['turn']}) {n['text']}" for n in notes[-6:]]


def table_lines(g, p):
    lines = [g.rule_line(), f"Your hand ({g.size(p)} cards):"] + g.hand_lines(p)
    lines.append(f"Top of discard pile: {engine.name(g.top)}. Color in play: {engine.COLORS[g.color]}.")
    seats, q = [], p
    for _ in range(g.n):
        if g.alive[q]:
            sz = g.size(q)
            seats.append(f"{'You' if q == p else g.names[q]}: {engine.cards(sz)}{' (UNO!)' if sz == 1 else ''}")
        q = (q + g.dir) % g.n
    lines.append(f"Still in ({g.n_alive()}), in turn order from you: " + " -> ".join(seats))
    if g.finished:
        lines.append("Finished (out of the game, placed): " + ", ".join(
            f"{engine.ordinal(i + 1)} {g.names[q]} (turn {t})" for i, (t, q) in enumerate(g.finished)))
    lines.append(f"Draw pile: {engine.cards(len(g.pile))}. Discard pile: {engine.cards(len(g.discard) + 1)}.")
    return lines


def seat_view(gdir, g, p, seen_log, seen_chat):
    me = g.names[p]
    d = g.decision
    lines = [f"You are {me}. Turn {g.turns}."] + table_lines(g, p)
    new_events = g.log[seen_log:] if seen_log < len(g.log) else []
    lines.append("What happened since you last looked:" if new_events else "Recent events:")
    lines += ["  " + e for e in (new_events[-25:] if new_events else g.log[-6:])]
    if len(new_events) > 25:
        lines.insert(len(lines) - 25, f"  ({len(new_events) - 25} earlier events not shown)")
    tl, next_chat = talk_lines(gdir, since=seen_chat)
    lines.append("Table talk since you last looked:" if tl else "Table talk: (nothing new)")
    lines += tl
    nl = note_lines(gdir, me)
    if nl:
        lines.append("Your private notes:")
        lines += nl
    if d is not None and d["player"] == p:
        if g.pending and d["kind"] == "penalty":
            lines.append(f"PENDING PENALTY on you: {g.pending} cards (last Draw card was +{g.last_dv}; "
                         f"you may stack a Draw card of value >= {g.last_dv}, any color).")
        lines.append(g.decision_head(d))
        lines += g.option_lines(p, d["options"])
    elif d is not None:
        lines.append(f"It is {g.names[d['player']]}'s move. You can talk, or just keep watching.")
    return "\n".join(lines), next_chat


# ----------------------------------------------------------------------------- commands
def cmd_new(a):
    names = a.players.split(",")
    os.makedirs(a.game, exist_ok=True)
    g = engine.Game(names, a.seed, "last", 0)
    engine.save(g, a.game)
    json.dump({"t_start": time.time(), "time_limit_s": a.time_limit_hours * 3600, "talk": "public",
               "rules": "no Mercy rule; play until one player is left (RULES.md section 7)", "seed": a.seed,
               "players": names}, open(path(a.game, "meta.json"), "w"), indent=1)
    open(path(a.game, "chat.jsonl"), "a").close()
    print(json.dumps(g.status()))


def cmd_wait(a):
    deadline = time.time() + a.timeout
    seen_log, seen_chat = a.seen, a.seen_chat
    while True:
        g = engine.load(a.game)
        p = seat_of(g, a.player)
        head = {"turn": g.turns}
        if g.over:
            head.update(reason="game_over", status=g.status())
            print(json.dumps(head))
            return
        if time_up(a.game, g):
            head.update(reason="time_up", note="the session's time limit is reached; stop playing")
            print(json.dumps(head))
            return
        if not g.alive[p]:
            head.update(reason="you_finished", note="you are out of the game; stop playing")
            print(json.dumps(head))
            return
        mine = g.decision is not None and g.decision["player"] == p
        if mine or len(g.log) > seen_log:
            text, next_chat = seat_view(a.game, g, p, seen_log, seen_chat)
            head.update(reason="your_turn" if mine else "new_events", seen=len(g.log), seen_chat=next_chat)
            print(json.dumps(head))
            print(text)
            return
        if time.time() > deadline:
            head.update(reason="timeout", seen=seen_log, seen_chat=seen_chat, note="nothing new; wait again")
            print(json.dumps(head))
            return
        time.sleep(0.5)


def record_repeat(gdir, g):
    """Flag a full position that comes back while the piles are nearly dry (a possible endless loop that
    the players could still break by choosing differently)."""
    if len(g.pile) + len(g.discard) > REPEAT_WINDOW:
        return
    key = hashlib.sha1(repr(g.loop_key()).encode()).hexdigest()
    p = path(gdir, "repeats.json")
    r = json.load(open(p)) if os.path.exists(p) else {"seen": {}, "repeats": []}
    if key in r["seen"]:
        r["repeats"].append({"turn": g.turns, "first_turn": r["seen"][key]})
    else:
        r["seen"][key] = g.turns
    json.dump(r, open(p, "w"))


def cmd_act(a):
    with Lock(a.game):
        g = engine.load(a.game)
        if g.over:
            print(json.dumps(g.status()))
            return
        if time_up(a.game, g):
            print(json.dumps({"reason": "time_up", "note": "the session's time limit is reached; stop playing"}))
            return
        p = g.decision["player"]
        if a.player != g.names[p]:
            print(json.dumps({"error": f"it is {g.names[p]}'s decision, not {a.player}'s"}))
            sys.exit(1)
        if not 0 <= a.choice < len(g.decision["options"]):
            print(json.dumps({"error": f"choice must be 0..{len(g.decision['options']) - 1}"}))
            sys.exit(1)
        d = g.decision
        append_jsonl(path(a.game, "decisions.jsonl"), {
            "turn": g.turns, "player": a.player, "kind": d["kind"], "n_options": len(d["options"]),
            "hand_size": g.size(p), "pending": g.pending, "choice": a.choice,
            "option": g.describe_option(d["options"][a.choice]), "t": time.time()})
        if a.say:
            say(a.game, g, a.player, a.say)
        if a.note:
            append_jsonl(path(a.game, f"notes_{a.player}.jsonl"), {"turn": g.turns, "text": a.note[:MAX_SAY]})
        g.choose(a.choice)
        g.check()
        engine.save(g, a.game)
        record_repeat(a.game, g)
        s = g.status()
    print(json.dumps(s))


def say(gdir, g, who, text):
    chat = read_jsonl(path(gdir, "chat.jsonl"))
    append_jsonl(path(gdir, "chat.jsonl"), {"i": len(chat), "turn": g.turns, "player": who,
                                            "text": " ".join(text.split())[:MAX_SAY], "t": time.time()})


def cmd_say(a):
    with Lock(a.game):
        g = engine.load(a.game)
        p = seat_of(g, a.player)
        if g.over or not g.alive[p]:
            print(json.dumps({"error": "you are no longer in the game"}))
            return
        say(a.game, g, a.player, a.text)
    print(json.dumps({"ok": True}))


def cmd_note(a):
    with Lock(a.game):
        g = engine.load(a.game)
        seat_of(g, a.player)
        append_jsonl(path(a.game, f"notes_{a.player}.jsonl"), {"turn": g.turns, "text": a.text[:MAX_SAY]})
    print(json.dumps({"ok": True}))


def cmd_status(a):
    g = engine.load(a.game)
    s = g.status()
    m = meta(a.game)
    s["elapsed_hours"] = round((time.time() - m["t_start"]) / 3600, 3)
    s["stopped"] = m.get("stopped")
    s["chat_messages"] = len(read_jsonl(path(a.game, "chat.jsonl")))
    rp = path(a.game, "repeats.json")
    s["repeated_positions"] = len(json.load(open(rp))["repeats"]) if os.path.exists(rp) else 0
    print(json.dumps(s))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("new"); a.add_argument("--game", required=True); a.add_argument("--players", required=True)
    a.add_argument("--seed", type=int, default=1); a.add_argument("--time-limit-hours", type=float, default=5.0)
    a = sub.add_parser("wait"); a.add_argument("--game", required=True); a.add_argument("--player", required=True)
    a.add_argument("--seen", type=int, default=0, help="events already seen (from the last wait)")
    a.add_argument("--seen-chat", type=int, default=0, help="talk messages already seen (from the last wait)")
    a.add_argument("--timeout", type=float, default=100)
    a = sub.add_parser("act"); a.add_argument("--game", required=True); a.add_argument("--player", required=True)
    a.add_argument("--choice", type=int, required=True); a.add_argument("--say", default="")
    a.add_argument("--note", default="")
    a = sub.add_parser("say"); a.add_argument("--game", required=True); a.add_argument("--player", required=True)
    a.add_argument("--text", required=True)
    a = sub.add_parser("note"); a.add_argument("--game", required=True); a.add_argument("--player", required=True)
    a.add_argument("--text", required=True)
    a = sub.add_parser("status"); a.add_argument("--game", required=True)
    args = ap.parse_args()
    {"new": cmd_new, "wait": cmd_wait, "act": cmd_act, "say": cmd_say, "note": cmd_note,
     "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    main()
