"""Figures for REPORT.md (PNG, light theme; palette checked with the dataviz validator).

usage: python3 analysis/figures.py   (run from uno-no-mercy/)
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
# ordinal blue ramp for player counts 2..6 (validated: --ordinal, light surface)
RAMP = {2: "#86b6ef", 3: "#5598e7", 4: "#2a78d6", 5: "#1c5cab", 6: "#104281"}
# categorical slots 1-3 (validated, adjacent pairs)
CAT = ["#2a78d6", "#eb6834", "#1baf7a"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": AXIS, "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURFACE,
    "figure.facecolor": SURFACE, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2.0,
})
os.makedirs("figures", exist_ok=True)


def survival(path):
    d = json.load(open(path))
    h = {int(k): v for k, v in d["hist"].items()}
    tmax = max(h)
    c = np.zeros(tmax + 2)
    for k, v in h.items():
        c[k] = v
    S = 1.0 - np.cumsum(c) / c.sum()
    t = np.arange(len(S))
    keep = S > 0
    return d, t[keep], S[keep]


def fig_survival(policy, fname, title):
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for p in range(2, 7):
        path = f"results/final/{policy}_p{p}.json"
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            continue
        d, t, S = survival(path)
        ax.semilogy(t, S, color=RAMP[p], label=f"{p} players")
    ax.set_xlabel("game length t (turns)")
    ax.set_ylabel("P(game lasts longer than t)")
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(f"figures/{fname}", dpi=160)
    plt.close(fig)


def fig_colluders(fname):
    """6-player survival: random robots vs colluding robots (random deck) vs colluders (hostile deck)."""
    series = [("random robots", "results/final/random_p6.json", CAT[0]),
              ("colluding robots, hostile deck order", "results/colluders/collude_adv_p6.json", CAT[1]),
              ("colluding robots, fair shuffle", "results/colluders/collude_p6.json", CAT[2])]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for name, path, col in series:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            continue
        d, t, S = survival(path)
        ax.loglog(np.maximum(t, 1), S, color=col, label=f"{name} (mean {d['mean_turns']:.0f})")
    ax.set_xlabel("game length t (turns, log scale)")
    ax.set_ylabel("P(game lasts longer than t)")
    ax.set_title("6 players: stalling on purpose buys ~100x longer games, not infinite ones", loc="left",
                 fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(f"figures/{fname}", dpi=160)
    plt.close(fig)


def fig_mercy(fname):
    path = "results/no_mercy/mercy_sweep.json"
    if not os.path.exists(path):
        return
    rows = json.load(open(path))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for p in (2, 4, 6):
        r = sorted([x for x in rows if x["players"] == p], key=lambda x: x["mercy"])
        xs = [x["mercy"] if x["mercy"] < 1000 else 150 for x in r]
        ys = [x["median"] for x in r]
        ax.semilogy(xs, ys, marker="o", markersize=5, color=RAMP[p], label=f"{p} players")
    ax.set_xticks([25, 30, 35, 40, 50, 70, 100, 150])
    ax.set_xticklabels(["25\n(official)", "30", "35", "40", "50", "70", "100", "none"])
    ax.set_xlabel("Mercy rule threshold (hand size that knocks you out)")
    ax.set_ylabel("median game length (turns, log scale)")
    ax.set_title("The Mercy rule is what keeps games short", loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(f"figures/{fname}", dpi=160)
    plt.close(fig)


def fig_personas(fname):
    """Each AI-personality game (dot) against the spread of 200,000 bot games of the same table."""
    path = "results/personas/ai_vs_bots.json"
    if not os.path.exists(path):
        return
    rows = json.load(open(path))
    bots = {"g1": "t1_2p_shark_vs_gremlin", "g2": "t2_2p_grandpa_vs_grudge", "g3": "t3_4p_mixed",
            "g4": "t4_4p_mixed", "g5": "t5_6p_mixed", "g6": "t6_4p_stallers", "g7": "t7_6p_stallers",
            "g8": "t8_3p_mixed"}
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for i, r in enumerate(rows):
        d = json.load(open(f"results/personas/{bots[r['game'][:2]]}.json"))
        h = {int(k): v for k, v in d["hist"].items()}
        t = np.array(sorted(h))
        cdf = np.cumsum([h[x] for x in t]) / sum(h.values())
        q = lambda f: t[np.searchsorted(cdf, f)]
        y = len(rows) - 1 - i
        ax.plot([q(0.01), q(0.99)], [y, y], color=RAMP[2], lw=6, solid_capstyle="round",
                label="bots: middle 98% of 200,000 games" if i == 0 else None)
        ax.plot([q(0.25), q(0.75)], [y, y], color=RAMP[4], lw=6, solid_capstyle="round",
                label="bots: middle 50%" if i == 0 else None)
        ax.plot([d["max_turns"]], [y], marker="|", markersize=10, color=MUTED,
                label="bots: longest game" if i == 0 else None)
        ax.plot([r["ai_turns"]], [y], marker="o", markersize=8, color=CAT[1], markeredgecolor=SURFACE,
                markeredgewidth=2, linestyle="none", label="AI players with personalities" if i == 0 else None)
    ax.set_yticks(range(len(rows)))
    short = {"g1": "Shark v Gremlin", "g2": "Grandpa v Grudge", "g8": "Shark, Peace, Gremlin",
             "g3": "Shark, Grandpa, Gremlin, Grudge", "g4": "Peace, Engineer, Never-End, Gremlin",
             "g6": "4 x Never-Ending", "g5": "6 mixed personalities", "g7": "6 x Never-Ending"}
    ax.set_yticklabels([short[r["game"][:2]] for r in rows][::-1], fontsize=8.5, color=INK2)
    ax.set_xlabel("game length (turns)")
    ax.grid(axis="y", visible=False)
    ax.set_title("AI players' games vs 200,000 bot games per table", loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper right")
    fig.tight_layout()
    fig.savefig(f"figures/{fname}", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig_survival("random", "survival_random.png", "Straight lines on a log scale = exponential tail (random robots)")
    fig_survival("greedy", "survival_greedy.png", "Same for greedy robots")
    fig_colluders("survival_colluders.png")
    fig_mercy("mercy_threshold.png")
    fig_personas("personas.png")
    print("figures written")
