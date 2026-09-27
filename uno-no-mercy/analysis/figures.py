"""Figures for REPORT.md (PNG, light theme, palette validated with the dataviz validator).

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
# categorical slots 1-3 (validated)
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
        if not os.path.exists(path):
            continue
        d, t, S = survival(path)
        ax.semilogy(t, S, color=RAMP[p], label=f"{p} players")
        ax.annotate(f"{p}p", (t[-1], S[-1]), xytext=(4, 0), textcoords="offset points", color=INK2, fontsize=9,
                    va="center")
    ax.set_xlabel("game length t (turns)")
    ax.set_ylabel("P(game lasts longer than t)")
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(f"figures/{fname}", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig_survival("random", "survival_random.png", "Straight lines on a log scale = exponential tail (random robots)")
    fig_survival("greedy", "survival_greedy.png", "Same for greedy robots")
    print("figures written")
