"""Tables for the house rule "play until one player is left" (RULES.md section 7, -end_rule 1).

Prints markdown tables built from results/last_player/ and, for comparison, the official-rule
runs in results/final/. Missing files are skipped.

usage: python3 analysis/last_player.py   (run from uno-no-mercy/)
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tail import load, survival, tail_fit  # noqa: E402

L = "results/last_player"


def get(path):
    """Load a results file; None if it is missing or still being written."""
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return None


def halving(path):
    d, counts = load(path)
    S, n = survival(counts)
    fit = tail_fit(S, n)
    return fit


def natural(policy):
    print(f"\n**{policy.capitalize()} robots, play until one is left (Mercy rule on)**\n")
    print("| Players | Games | Mean turns (±SE) | Median | 99th pct | 99.99th pct | Longest | "
          "Finish / knocked out per game | Official rules: mean | Survival halves every |")
    print("|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|")
    for p in range(2, 7):
        path = f"{L}/{policy}_p{p}.json"
        d = get(path)
        if not d:
            continue
        off = get(f"results/final/{policy}_p{p}.json")
        q = d["quantiles"]
        fit = halving(path)
        hv = f"{fit['halving_turns']:.1f} turns (R² {fit['r2']:.3f})" if fit else "n/a"
        bad = d["end_capped"] + d["end_stuck_forever"] + d["end_proven_cycle"]
        assert bad == 0, f"{path}: {bad} games did not finish"
        print(f"| {p} | {d['games']:,} | {d['mean_turns']:.2f} ± {d['sem_turns']:.3f} | {q['p50']} | {q['p99']} | "
              f"{q['p9999']} | {d['max_turns']} | {d['mean_finishes']:.2f} / {d['mean_eliminations']:.2f} | "
              f"{off['mean_turns']:.2f} | {hv} |" if off else "")


def personas():
    print("\n**Personality bots, play until one is left (200,000 games per table)**\n")
    print("| Table | Mean turns | Longest | Official rules: mean (longest) | Survival halves every |")
    print("|---|---:|---:|---:|---:|")
    for path in sorted(glob.glob(f"{L}/personas/t*.json")):
        name = os.path.basename(path)
        d = get(path)
        o = get(f"results/personas/{name}")
        fit = halving(path)
        print(f"| {name[:-5]} | {d['mean_turns']:.1f} | {d['max_turns']:,} | {o['mean_turns']:.1f} ({o['max_turns']:,}) | "
              f"{fit['halving_turns']:.1f} turns |")


def finish_effect():
    print("\n**Does the finishing card take effect? (1,000,000 games each)**\n")
    print("| Players | Random: effect applies | Random: no effect | Greedy: effect applies | Greedy: no effect |")
    print("|---:|---:|---:|---:|---:|")
    for p in range(3, 7):
        row = [f"| {p} "]
        for pol in ("random", "greedy"):
            a, b = get(f"{L}/{pol}_p{p}.json"), get(f"{L}/fe0_{pol}_p{p}.json")
            row.append(f"| {a['mean_turns']:.1f} " if a else "| ")
            row.append(f"| {b['mean_turns']:.1f} " if b else "| ")
        print("".join(row) + "|")


def no_mercy():
    print("\n**No Mercy rule: finishing is the only way out (random robots, exact loop detection)**\n")
    print("| Players | Games | Proven endless loops | Stuck forever | Mean turns | Median | Longest |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for path in sorted(glob.glob(f"{L}/no_mercy/random_p*.json")) + sorted(glob.glob(f"{L}/no_mercy/greedy_p*.json")):
        d = get(path)
        pol = "greedy " if "greedy" in path else ""
        print(f"| {pol}{d['players']} | {d['games']:,} | {d['end_proven_cycle']} | {d['end_stuck_forever']} | "
              f"{d['mean_turns']:,.0f} | {d['quantiles']['p50']:,} | {d['max_turns']:,} |")
    rows = []
    for path in glob.glob(f"{L}/no_mercy/mercy*_p*.json"):
        d = get(path)
        rows.append((d["players"], d["rules"]["mercy"], d))
    if rows:
        print("\n**Mercy threshold (random robots, play until one is left)**\n")
        print("| Players | Knockout at | Games | Mean turns | Median | Longest | Proven endless |")
        print("|---:|---:|---:|---:|---:|---:|---:|")
        for p, m, d in sorted(rows, key=lambda r: (r[0], r[1])):
            print(f"| {p} | {m} | {d['games']:,} | {d['mean_turns']:,.0f} | {d['quantiles']['p50']:,} | "
                  f"{d['max_turns']:,} | {d['end_proven_cycle']} |")


def colluders():
    print("\n**Colluding robots trying to stall, play until one is left**\n")
    print("| Players | Fair shuffle: mean (median, longest) | Hostile deck: mean | Official rules, fair shuffle: mean |")
    print("|---:|---|---:|---:|")
    for p in range(3, 7):
        d = get(f"{L}/colluders/collude_p{p}.json")
        a = get(f"{L}/colluders/collude_adv_p{p}.json")
        o = get(f"results/colluders/collude_p{p}.json")
        if not d:
            continue
        print(f"| {p} | {d['mean_turns']:,.0f} ({d['quantiles']['p50']:,}, {d['max_turns']:,}) | "
              f"{a['mean_turns']:,.0f} | {o['mean_turns']:,.0f} |" if a and o else "")


if __name__ == "__main__":
    natural("random")
    natural("greedy")
    personas()
    finish_effect()
    no_mercy()
    colluders()
