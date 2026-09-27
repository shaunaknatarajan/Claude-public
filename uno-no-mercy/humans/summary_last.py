"""Summary of the AI-personality games played under the user's table rules: no Mercy rule, play
until one player is left (RULES.md section 7). Prints a markdown table and writes
results/personas/ai_games_last.json.

usage: python3 humans/summary_last.py   (run from uno-no-mercy/)
"""
import glob
import json
import os
import re
import subprocess

PERSONA = {"Maya": "Shark", "Joe": "Grandpa", "Tyler": "Gremlin", "Priya": "Grudge Holder", "Sam": "Peacekeeper",
           "Leo": "Engineer"}


def persona(name):
    return PERSONA.get(name, "Never-Ending" if name.startswith("Z") else "?")


rows = []
for gdir in sorted(glob.glob("humans/games/h*/")):
    st = json.loads(subprocess.run(["python3", "humans/engine.py", "status", "--game", gdir], capture_output=True,
                                   text=True).stdout)
    log = open(os.path.join(gdir, "log.txt")).read()
    # biggest hand seen in the log: '(N left)' after plays, '(N cards)' after reveals (a hand right
    # after an accepted penalty is not logged, so this can undercount by up to that penalty)
    sizes = [int(x) for x in re.findall(r"(?<!pile )\((\d+) (?:left|cards)\)", log)]
    fin = st.get("finished", [])
    rows.append({
        "game": os.path.basename(gdir.rstrip("/")),
        "over": st["game_over"],
        "turns": st["turns"],
        "decisions": st.get("decisions"),
        "finished": fin,
        "loser": st.get("loser"),
        "end_reason": st.get("end_reason"),
        "hand_sizes_now": st.get("hand_sizes"),
        "biggest_hand_logged": max(sizes) if sizes else None,
        "stuck": st.get("stuck", False),
        "endless": st.get("endless", False),
    })

json.dump(rows, open("results/personas/ai_games_last.json", "w"), indent=1)
print("| Game | Status | Turns | Decisions | Finishing order (turn) | Left holding cards | Biggest hand |")
print("|---|---|---:|---:|---|---|---:|")
for r in rows:
    order = ", ".join(f"{f['name']} ({persona(f['name'])}) {f['turn']}" for f in r["finished"]) or "-"
    status = "over" if r["over"] else "still going"
    loser = f"{r['loser']} ({persona(r['loser'])})" if r["loser"] else "-"
    print(f"| {r['game']} | {status} | {r['turns']:,} | {r['decisions']:,} | {order} | {loser} | {r['biggest_hand_logged']} |")
