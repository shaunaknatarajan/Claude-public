"""How the Mercy threshold controls game length (non-official variants; 25 is official).

With the Mercy rule weakened or removed, hands can hold almost the whole deck, the draw
pile can run dry and games can fall into provably infinite deterministic cycles
(-detect_cycles 1 detects them exactly: a repeated full state with no random event and no
free decision in between).

usage: python3 mercy_sweep.py <nomercy-binary> <out.json>
"""
import json
import subprocess
import sys

BIN, OUT = sys.argv[1], sys.argv[2]
rows = []
for p in (2, 4, 6):
    for mercy in (25, 30, 35, 40, 50, 70, 100, 1000):
        n = 200_000 if mercy <= 35 else 40_000
        cmd = [BIN, "-p", str(p), "-n", str(n), "-threads", "4", "-seed", "31337", "-policy", "random",
               "-mercy", str(mercy), "-cap", "5000000", "-detect_cycles", "1"]
        d = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
        finite = d["end_emptied_hand"] + d["end_last_standing"]
        row = {"players": p, "mercy": mercy, "games": d["games"], "mean_turns_all": d["mean_turns"],
               "median": d["quantiles"]["p50"], "p99": d["quantiles"]["p99"], "max_turns": d["max_turns"],
               "went_out": d["end_emptied_hand"], "last_standing": d["end_last_standing"],
               "proven_infinite_cycles": d["end_proven_cycle"], "stuck_forever": d["end_stuck_forever"],
               "capped": d["end_capped"], "finite_games": finite}
        rows.append(row)
        print(json.dumps(row), flush=True)
json.dump(rows, open(OUT, "w"), indent=1)
