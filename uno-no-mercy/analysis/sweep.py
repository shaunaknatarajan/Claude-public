"""Run the simulator over rule variants x player counts x policies and tabulate game length.

usage: python3 sweep.py <nomercy-binary> <out.json> [games-per-cell]
"""
import json
import subprocess
import sys

BIN, OUT = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 1_000_000

VARIANTS = [
    ("default (official reading)", []),
    ("deck: rajatghate5 (38/colour, 16 wilds)", ["-deck", "1"]),
    ("deck: open-mercy (one 0/colour, 4 plain wilds)", ["-deck", "2"]),
    ("may decline a playable card and draw", ["-voluntary_draw", "1"]),
    ("drawn playable card may be kept", ["-after_draw", "1"]),
    ("drawn card never played that turn", ["-after_draw", "2"]),
    ("stacking must also match colour/symbol", ["-stack_rule", "1"]),
    ("no stacking", ["-stack_rule", "2"]),
    ("stacking mandatory when able", ["-stack_mandatory", "1"]),
    ("Roulette colour named by its player", ["-roulette_chooser", "1"]),
    ("knocked-out hands shuffled in at once", ["-elim_cards", "0"]),
    ("knocked-out hands to bottom of pile", ["-elim_cards", "1"]),
    ("Mercy checked at end of the draw action", ["-mercy_immediate", "0"]),
    ("no 0/7 hand rules", ["-zero_seven", "0"]),
    ("2p Wild Reverse Draw 4 hits opponent", ["-wrd4_2p_self", "0"]),
]
PLAYERS = [2, 3, 4, 6]
POLICIES = ["random", "greedy"]

rows = []
for name, flags in VARIANTS:
    for pol in POLICIES:
        # "may decline" is only exercised by a policy that sometimes declines
        polname = "randomv" if (pol == "random" and "-voluntary_draw" in flags) else pol
        for p in PLAYERS:
            cmd = [BIN, "-p", str(p), "-n", str(N), "-threads", "4", "-seed", "2026", "-policy", polname] + flags
            d = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
            n = d["games"]
            row = {"variant": name, "flags": " ".join(flags), "policy": polname, "players": p, "games": n,
                   "mean": d["mean_turns"], "sem": d["sem_turns"], "sd": d["sd_turns"], "max": d["max_turns"],
                   "p50": d["quantiles"]["p50"], "p99": d["quantiles"]["p99"], "p9999": d["quantiles"]["p9999"],
                   "emptied_frac": d["end_emptied_hand"] / n, "mean_elims": d["mean_eliminations"],
                   "capped": d["end_capped"], "overflow": d["overflow"]}
            rows.append(row)
            print(f"{name:48s} {polname:8s} p={p} mean={row['mean']:8.2f} ±{row['sem']:.2f} max={row['max']:6d} "
                  f"went_out={row['emptied_frac']:.3f}", flush=True)
json.dump(rows, open(OUT, "w"), indent=1)
