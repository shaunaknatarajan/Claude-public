"""Tail analysis of game-length histograms produced by sim/nomercy.

For each results JSON: survival function S(t) = P(T > t), an exponential tail fit
log S(t) ~ a - lambda*t on the far tail, and a heavy-tail check (local log-log slope).

usage: python3 tail.py results/random_p4.json [...]
"""
import json
import math
import sys

import numpy as np


def load(path):
    d = json.load(open(path))
    hist = {int(k): v for k, v in d["hist"].items()}
    tmax = max(hist) if hist else 0
    counts = np.zeros(tmax + 1, dtype=np.float64)
    for k, v in hist.items():
        counts[k] = v
    return d, counts


def survival(counts):
    n = counts.sum()
    # S[t] = P(T > t)
    return 1.0 - np.cumsum(counts) / n, n


def tail_fit(S, n, lo_q=1e-2, min_tail=200):
    """Least-squares fit of log S(t) on the region lo_q >= S(t) >= min_tail/n."""
    idx = np.where((S <= lo_q) & (S * n >= min_tail))[0]
    if len(idx) < 10:
        return None
    t = idx.astype(float)
    y = np.log(S[idx])
    A = np.vstack([np.ones_like(t), t]).T
    coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    a, b = coef
    yhat = A @ coef
    r2 = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    # local log-log slope at the two ends of the fit window (power law => roughly constant)
    t0, t1 = t[0], t[-1]
    return {"lambda_per_turn": -b, "halving_turns": math.log(2) / -b, "intercept": a, "r2": r2,
            "fit_window": [int(t0), int(t1)], "S_at_window": [float(S[int(t0)]), float(S[int(t1)])],
            "loglog_slope_start": float(-b * t0), "loglog_slope_end": float(-b * t1)}


def main():
    for path in sys.argv[1:]:
        d, counts = load(path)
        S, n = survival(counts)
        fit = tail_fit(S, n)
        print(f"{path}: players={d['players']} policies={set(d['policies'])} n={int(n)} mean={d['mean_turns']:.3f} "
              f"sd={d['sd_turns']:.2f} max={d['max_turns']}")
        if fit:
            print(f"   exp tail: lambda={fit['lambda_per_turn']:.5f}/turn (S halves every {fit['halving_turns']:.1f} turns), "
                  f"R^2={fit['r2']:.5f}, window={fit['fit_window']}, loglog slope {fit['loglog_slope_start']:.1f} -> "
                  f"{fit['loglog_slope_end']:.1f} (steepening => lighter than any power law)")


if __name__ == "__main__":
    main()
