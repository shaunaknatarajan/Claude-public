"""Put each AI-personality game in context: where its length falls among 200,000 games of the
same table played by the rule-based personality bots, and among random-play games.

usage: python3 humans/compare.py   (run from uno-no-mercy/)
"""
import json
import os
import subprocess

import numpy as np

TABLES = [  # AI game directory, rule-based table, players, description
    ("g1_2p_shark_vs_gremlin", "t1_2p_shark_vs_gremlin", 2, "Shark vs Gremlin"),
    ("g2_2p_grandpa_vs_grudge", "t2_2p_grandpa_vs_grudge", 2, "Grandpa vs Grudge Holder"),
    ("g8_3p_mixed", "t8_3p_mixed", 3, "Shark, Peacekeeper, Gremlin"),
    ("g3_4p_mixed", "t3_4p_mixed", 4, "Shark, Grandpa, Gremlin, Grudge Holder"),
    ("g4_4p_mixed", "t4_4p_mixed", 4, "Peacekeeper, Engineer, Never-Ending, Gremlin"),
    ("g6_4p_stallers", "t6_4p_stallers", 4, "4 x Never-Ending (all want it to last forever)"),
    ("g5_6p_mixed", "t5_6p_mixed", 6, "Shark, Grandpa, Gremlin, Grudge, Peacekeeper, Engineer"),
    ("g7_6p_stallers", "t7_6p_stallers", 6, "6 x Never-Ending (all want it to last forever)"),
]


def hist(path):
    d = json.load(open(path))
    h = {int(k): v for k, v in d["hist"].items()}
    t = np.array(sorted(h))
    c = np.array([h[x] for x in t], dtype=float)
    return d, t, c


def pct(t, c, x):
    """Fraction of games strictly shorter than x, plus half of the ties (mid-rank percentile)."""
    below = c[t < x].sum()
    eq = c[t == x].sum()
    return (below + 0.5 * eq) / c.sum()


rows = []
for g, bot, p, desc in TABLES:
    gdir = f"humans/games/{g}"
    if not os.path.exists(f"{gdir}/state.pkl"):
        continue
    st = json.loads(subprocess.run(["python3", "humans/engine.py", "status", "--game", gdir], capture_output=True,
                                   text=True).stdout)
    if not st.get("game_over"):
        continue
    d, t, c = hist(f"results/personas/{bot}.json")
    dr, tr, cr = hist(f"results/final/random_p{p}.json")
    rows.append({"game": g, "table": desc, "players": p, "ai_turns": st["turns"], "winner": st["winner"],
                 "how": st["end_reason"], "knockouts": len(st["knockouts"]),
                 "bot_mean": d["mean_turns"], "bot_median": d["quantiles"]["p50"], "bot_max": d["max_turns"],
                 "ai_percentile_among_bots": pct(t, c, st["turns"]),
                 "random_mean": dr["mean_turns"], "ai_percentile_among_random": pct(tr, cr, st["turns"])})
json.dump(rows, open("results/personas/ai_vs_bots.json", "w"), indent=1)
print(f"{'table':55s} {'AI turns':>8s} {'bots mean':>9s} {'pctile':>6s}  winner")
for r in rows:
    print(f"{r['table'][:55]:55s} {r['ai_turns']:8d} {r['bot_mean']:9.1f} {100 * r['ai_percentile_among_bots']:5.0f}%  "
          f"{r['winner']} ({r['how']}, {r['knockouts']} knocked out)")
