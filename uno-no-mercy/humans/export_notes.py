"""Write each finished game's private player notes to notes.txt beside its log (run from uno-no-mercy/)."""
import glob
import pickle
import sys

sys.path.insert(0, "humans")
import engine  # noqa: E402

sys.modules["__main__"].Game = engine.Game
for path in sorted(glob.glob("humans/games/*/state.pkl")):
    g = pickle.load(open(path, "rb"))
    out = []
    for name, notes in zip(g.names, g.notes):
        out.append(f"== {name}")
        out += ["  " + s for s in notes] or ["  (no notes)"]
    open(path.replace("state.pkl", "notes.txt"), "w").write("\n".join(out) + "\n")
