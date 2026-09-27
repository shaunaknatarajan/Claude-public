#!/usr/bin/env python3
"""Cross-check the witness with the C simulator's own rules code.

Copies sim/nomercy.c to a temporary directory (the original is not touched), replaces only the
body of rng_below() so that it returns the scripted values stored in the witness
(c_sim_rng_stream, with a check that each call's bound n matches), builds it, and runs

    nomercy -p 3 -n 1 -threads 1 -policy random -mercy 1000 -end_rule E
            -detect_cycles 1 -dumpcap 1 -debug 2

for E = 0 and 1. It then checks that the simulator reports a proven infinite cycle
(end_proven_cycle = 1, "back to the same state after 2 turns"), that the whole scripted stream
was consumed and nothing more (so the loop needs no further random numbers), and that the
simulator's state sequence (-debug 2) matches the witness's hand sizes turn by turn.

Usage: python3 analysis/witness_p3_csim_check.py [witness.json] [workdir]
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATCH = r'''
static long script_len = -1, script_pos = 0;
static uint32_t *script_v, *script_n;
static void script_report(void) {
    if (script_len >= 0) fprintf(stderr, "SCRIPT consumed %ld of %ld\n", script_pos, script_len);
}
__attribute__((constructor)) static void script_load(void) {
    const char *fn = getenv("SCRIPT_RNG");
    if (!fn) return;
    FILE *fp = fopen(fn, "r");
    if (!fp) { perror(fn); exit(3); }
    long cap = 1024; script_v = malloc(cap * 4); script_n = malloc(cap * 4); script_len = 0;
    unsigned v, n;
    while (fscanf(fp, "%u %u", &v, &n) == 2) {
        if (script_len == cap) { cap *= 2; script_v = realloc(script_v, cap * 4); script_n = realloc(script_n, cap * 4); }
        script_v[script_len] = v; script_n[script_len] = n; script_len++;
    }
    fclose(fp);
    atexit(script_report);
}
static inline uint32_t rng_below(Rng *r, uint32_t n) {
    if (script_len < 0) return rng_below_real(r, n);
    if (script_pos >= script_len) { fprintf(stderr, "SCRIPT EXHAUSTED at a call with n=%u\n", n); exit(3); }
    uint32_t v = script_v[script_pos], m = script_n[script_pos];
    if (m != n || v >= n) { fprintf(stderr, "SCRIPT MISMATCH at %ld: bound %u, script says %u (v=%u)\n", script_pos, n, m, v); exit(3); }
    script_pos++;
    return v;
}
'''


def main():
    wpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results/no_mercy/witness_p3.json")
    work = sys.argv[2] if len(sys.argv) > 2 else tempfile.mkdtemp(prefix="witness_p3_csim_")
    W = json.load(open(wpath))
    src = open(os.path.join(ROOT, "sim/nomercy.c")).read()
    head = "static inline uint32_t rng_below(Rng *r, uint32_t n) {"
    assert src.count(head) == 1
    src = src.replace(head, "static inline uint32_t rng_below_real(Rng *r, uint32_t n) {")
    tail = "    return (uint32_t)(m >> 32);\n}\n"
    i = src.index(tail, src.index("rng_below_real")) + len(tail)
    src = src[:i] + PATCH + src[i:]
    c = os.path.join(work, "nomercy_scripted.c")
    exe = os.path.join(work, "nomercy_scripted")
    open(c, "w").write(src)
    subprocess.run(["gcc", "-O2", "-pthread", "-o", exe, c, "-lm"], check=True)
    sf = os.path.join(work, "stream.txt")
    with open(sf, "w") as f:
        for v, n in zip(W["c_sim_rng_stream"], W["c_sim_rng_bounds"]):
            f.write(f"{v} {n}\n")
    total = len(W["c_sim_rng_stream"])
    ok = True
    for er in W["end_rules_claimed"]:
        p = subprocess.run([exe, "-p", "3", "-n", "1", "-threads", "1", "-policy", "random", "-mercy", "1000",
                            "-end_rule", str(er), "-detect_cycles", "1", "-dumpcap", "1", "-debug", "2"],
                           env=dict(os.environ, SCRIPT_RNG=sf), capture_output=True, text=True)
        err, out = p.stderr, p.stdout
        open(os.path.join(work, f"debug_end_rule{er}.txt"), "w").write(err)
        res = json.loads(out)
        consumed = re.search(r"SCRIPT consumed (\d+) of (\d+)", err)
        cyc = "=== proven infinite cycle" in err and "=== back to the same state after 2 turns" in err
        # the -debug 2 trace prints the state before each turn: "turn T cur=.. " then one line per seat
        states = re.findall(r"^turn (\d+) cur=(\d+) dir=(-?\d+) top=(\S+) color=(\S) stack=\S+ pile=(\d+) disc=(\d+)\n"
                            r"  p0\S?\s+\((\s*\d+)\):(.*)\n  p1\S?\s+\((\s*\d+)\):(.*)\n  p2\S?\s+\((\s*\d+)\):(.*)$",
                            err, re.M)
        sim_after, sim_hands = {}, {}
        for s in states:
            if int(s[0]) in sim_after:   # the cycle dump re-prints states; keep the first occurrence
                continue
            sim_after[int(s[0])] = (int(s[1]), int(s[2]), s[3], s[4], int(s[5]), int(s[6]),
                                    [int(s[7]), int(s[9]), int(s[11])])
            sim_hands[int(s[0])] = [sorted(s[8].split()), sorted(s[10].split()), sorted(s[12].split())]
        et = W["loop"]["entry_after_turn"]
        hands_ok = sim_hands.get(et) == W["loop"]["entry_state"]["hands"]
        mism = 0
        for e in W["turns"] + W["loop"]["period_turns"]:
            a = e["after"]
            # sim prints "turn <turns so far>" = the state after that turn (a Roulette adds the victim's turn)
            key = e["roulette"]["victim_turn"] if "roulette" in e else e["turn"]
            got = sim_after.get(key)
            if True:
                exp = (a["cur"], a["dir"], a["top"], a["color"], a["pile"], a["disc"], a["hand_sizes"])
                if got != exp:
                    mism += 1
                    print(f"  turn {key}: sim {got} vs witness {exp}")
        good = (res["end_proven_cycle"] == 1 and cyc and consumed and int(consumed.group(1)) == total
                and mism == 0 and hands_ok and res["end_emptied_hand"] == 0)
        ok &= bool(good)
        print(f"end_rule {er}: C simulator end_proven_cycle={res['end_proven_cycle']} "
              f"end_emptied_hand={res['end_emptied_hand']} cycle_dump={'yes' if cyc else 'no'} "
              f"stream consumed={consumed.group(1) if consumed else '?'}/{total} "
              f"states compared={len(W['turns']) + len(W['loop']['period_turns'])} "
              f"mismatches={mism} loop-entry hands identical={hands_ok} -> {'OK' if good else 'FAIL'}")
    print("trace files in", work)
    print("C-SIM CHECK OK" if ok else "C-SIM CHECK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
