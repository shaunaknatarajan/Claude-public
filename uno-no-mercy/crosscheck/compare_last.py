"""Cross-check the play-until-one-left rule (RULES.md section 7): the independent Python reference
(crosscheck/ref_results_last.json) against C simulator runs of the same rule.

Random play is used here only as a test harness: two independent implementations of the same
rules must produce the same game-length distribution under the same (random) players.

usage: python3 crosscheck/compare_last.py C_RESULTS_DIR   (run from uno-no-mercy/)
  C_RESULTS_DIR holds A_p{3..6}.json, A0_p{4,6}.json (Mercy rule on, finish effect 1 / 0)
  and B_p{2,3}.json (no Mercy rule), produced by sim/nomercy -policy random -end_rule 1 ...
"""
import json
import math
import os
import sys

ref = json.load(open("crosscheck/ref_results_last.json"))["runs"]
cdir = sys.argv[1]


def refrun(end, fe, mercy):
    for k, v in ref.items():
        if v["end_rule"] == end and v["finish_effect"] == fe and v["mercy"] == mercy:
            return v["per_players"]
    return {}


rows = []
for label, fe, mercy, prefix, players in [("A: Mercy rule on, finish effect 1", 1, 25, "A", [3, 4, 5, 6]),
                                          ("A: Mercy rule on, finish effect 0", 0, 25, "A0", [4, 6]),
                                          ("B: no Mercy rule (your table)", 1, 1000, "B", [2, 3])]:
    R = refrun("last", fe, mercy)
    for p in players:
        path = os.path.join(cdir, f"{prefix}_p{p}.json")
        if str(p) not in R or not os.path.exists(path):
            continue
        r, c = R[str(p)], json.load(open(path))
        rse = r["sd_turns"] / math.sqrt(r["games"])
        z = (r["mean_turns"] - c["mean_turns"]) / math.hypot(rse, c["sem_turns"])
        rows.append((label, p, r["games"], r["mean_turns"], rse, c["games"], c["mean_turns"], c["sem_turns"], z))

print("| Rule set | Players | Python games | Python mean ± SE | C games | C mean ± SE | z |")
print("|---|---:|---:|---:|---:|---:|---:|")
for label, p, rg, rm, rs, cg, cm, cs, z in rows:
    print(f"| {label} | {p} | {rg:,} | {rm:,.2f} ± {rs:,.2f} | {cg:,} | {cm:,.2f} ± {cs:,.2f} | {z:+.2f} |")
print(f"\nlargest |z| = {max(abs(r[-1]) for r in rows):.2f} over {len(rows)} comparisons")
