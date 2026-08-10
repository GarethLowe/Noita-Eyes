"""H6: period-4 key components combined with chaining, on real Finnish.

The state of play going in. The gap-4 excess (constraint 5) is plausibly the
plaintext's own distance-4 repetition passing through a period-4 key. The
re-convergence evidence (constraint 4) says the state must derive from the
plaintext or position, not from ciphertext history. Zero adjacent repeats
(constraint 3) is the hard one: nothing plaintext-derived tested so far
produces exactly zero. This battery tests the simple combinations.

Candidates (all mod 83, position 0 outside the chain, shared initial state):

  p4        c[i] = p[i] + k[i%4]                      stateless + period-4
  ct+p4     c[i] = p[i] + k[i%4] + c[i-1]             ciphertext chain + period-4
  pt+p4     c[i] = p[i] + p[i-1] + k[i%4]             plaintext chain + period-4
  tab(pt)+p4   c[i] = pi(p[i]+p[i-1]) + k[i%4]        table variant of pt+p4
  tab(pt+p4)   c[i] = pi(p[i]+p[i-1]+k[i%4])          table over the whole sum
  pt+p4+fix    pt+p4, then if c[i]==c[i-1]: c[i]+=1   the game-dev collision fix

The fix variant models a developer patching collisions after the fact
("if output equals the previous one, bump it") - it guarantees constraint 3 by
construction and barely disturbs anything else.

For the un-fixed chains, adjacent repeats depend on the key hitting rare
plaintext values, so the battery reports both random-key averages and the best
key found ("could a lucky key give exactly zero?").

Plaintext is real Finnish prose syllables (cached runs, concatenated to the
nine real message lengths; the joins add slight noise, which damps language
structure and is therefore conservative).

Run: python3 tools/h6_hybrid.py
"""
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, ioc, load  # noqa: E402
from finnish import load_runs, load_table  # noqa: E402
from resync_analysis import reconvergences  # noqa: E402

SEEDS = 30
LENGTHS = [99, 103, 118, 102, 137, 124, 119, 120, 114]
OBSERVED = {"ioc": 1.07, "adj": 0.0,
            "gaps": {2: 0.48, 3: 0.78, 4: 1.98, 5: 1.00, 6: 1.21, 8: 1.03}}


# --- encryptors ---------------------------------------------------------

def enc_p4(p, key, pi):
    return [(x + key[i % 4]) % N for i, x in enumerate(p)]


def enc_ct_p4(p, key, pi):
    c, prev = [], 0
    for i, x in enumerate(p):
        prev = (x + key[i % 4] + prev) % N
        c.append(prev)
    return c


def dec_ct_p4(c, key):
    prev, p = 0, []
    for i, x in enumerate(c):
        p.append((x - key[i % 4] - prev) % N)
        prev = x
    return p


def enc_pt_p4(p, key, pi):
    c, last = [], 0
    for i, x in enumerate(p):
        c.append((x + last + key[i % 4]) % N)
        last = x
    return c


def dec_pt_p4(c, key):
    last, p = 0, []
    for i, x in enumerate(c):
        v = (x - last - key[i % 4]) % N
        p.append(v)
        last = v
    return p


def enc_tab_pt_p4(p, key, pi):
    c, last = [], 0
    for i, x in enumerate(p):
        c.append((pi[(x + last) % N] + key[i % 4]) % N)
        last = x
    return c


def enc_tab_ptk(p, key, pi):
    c, last = [], 0
    for i, x in enumerate(p):
        c.append(pi[(x + last + key[i % 4]) % N])
        last = x
    return c


def enc_pt_p4_fix(p, key, pi):
    c, last, prev = [], 0, None
    for i, x in enumerate(p):
        v = (x + last + key[i % 4]) % N
        if v == prev:
            v = (v + 1) % N
        c.append(v)
        last, prev = x, v
    return c


CANDIDATES = [
    ("p4 (stateless)", enc_p4),
    ("ct-chain + p4", enc_ct_p4),
    ("pt-chain + p4", enc_pt_p4),
    ("tab(pt) + p4", enc_tab_pt_p4),
    ("tab(pt + p4)", enc_tab_ptk),
    ("pt-chain + p4 + FIX", enc_pt_p4_fix),
]


# --- plaintext supply ---------------------------------------------------

def messages(rng, runs):
    """Concatenate cached Finnish runs into the nine real message lengths."""
    pool = list(runs)
    rng.shuffle(pool)
    out, cur, it = [], [], iter(pool)
    for n in LENGTHS:
        while len(cur) < n:
            try:
                cur += next(it)
            except StopIteration:
                pool2 = list(runs)
                rng.shuffle(pool2)
                it = iter(pool2)
        out.append(cur[:n])
        cur = cur[n:]
    return out


def divergent_pair(rng, runs, n=99):
    """Finnish plaintext pair: identical except over 25-28 and 33-36."""
    table = load_table()
    syms = list(range(N))
    weights = [table["top83_counts"][s] for s in table["top83"]]
    pa = messages(rng, runs)[0][:n]
    pb = list(pa)
    for lo, hi in ((25, 29), (33, 37)):
        for i in range(lo, hi):
            while True:
                v = rng.choices(syms, weights)[0]
                if v != pa[i]:
                    break
            pb[i] = v
    return pa, pb


# --- metrics ------------------------------------------------------------

def gap_ratio(msgs, k):
    hit = sum(1 for v in msgs for i in range(len(v) - k) if v[i] == v[i + k])
    pairs = sum(max(0, len(v) - k) for v in msgs)
    return hit / (pairs / N) if pairs else float("nan")


def adjacent(msgs):
    return sum(1 for v in msgs for i in range(1, len(v)) if v[i] == v[i - 1])


def battery(enc, runs, seeds=SEEDS):
    accs = {"ioc": [], "adj": [], "reconv": []}
    gaps = {k: [] for k in (2, 3, 4, 5, 6, 8)}
    for s in range(seeds):
        rng = random.Random(500 + s)
        key = [rng.randrange(N) for _ in range(4)]
        pi = list(range(N))
        rng.shuffle(pi)
        ms = [enc(p, key, pi) for p in messages(rng, runs)]
        accs["ioc"].append(sum(ioc(m) for m in ms) / len(ms))
        accs["adj"].append(adjacent(ms) / sum(len(m) for m in ms) * 1027)
        for k in gaps:
            gaps[k].append(gap_ratio(ms, k))
        pa, pb = divergent_pair(rng, runs)
        rc = reconvergences(enc(pa, key, pi), enc(pb, key, pi))
        accs["reconv"].append(1 if len(rc) >= 2 else 0)
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    return (mean(accs["ioc"]), mean(accs["adj"]),
            {k: mean(v) for k, v in gaps.items()},
            mean(accs["reconv"]))


def best_key_analysis(runs, seeds=10):
    """Could a chosen key make the un-fixed chains repeat-free?"""
    rng = random.Random(9)
    ms = []
    for s in range(seeds):
        ms.extend(messages(random.Random(700 + s), runs))

    # ct+p4: repeat iff p[i] == -k[i%4]. Independent per phase.
    phase_counts = [Counter() for _ in range(4)]
    for p in ms:
        for i, x in enumerate(p):
            phase_counts[i % 4][x] += 1
    total = sum(len(p) for p in ms)
    best_ct = sum(min(pc[s] for s in range(N)) for pc in phase_counts)

    # pt+p4: repeat iff p[i]-p[i-2] == D[i%4] with D[0]+D[1]+D[2]+D[3] == 0.
    diff_counts = [Counter() for _ in range(4)]
    for p in ms:
        for i in range(2, len(p)):
            diff_counts[i % 4][(p[i] - p[i - 2]) % N] += 1
    best_pt = None
    for _ in range(30000):
        d = [rng.randrange(N) for _ in range(3)]
        d.append((-sum(d)) % N)
        v = sum(diff_counts[j][d[j]] for j in range(4))
        if best_pt is None or v < best_pt:
            best_pt = v
    return best_ct / total * 1027, best_pt / total * 1027


def main():
    runs = load_runs()

    print("H6 hybrid battery -- real Finnish prose syllables, "
          f"{SEEDS} seeds, message lengths matching the corpus\n")
    print(f"{'candidate':<22} {'IoC/msg':>8} {'adj/1027':>9} "
          f"{'g2':>6} {'g3':>6} {'g4':>6} {'g5':>6} {'g6':>6} {'g8':>6} "
          f"{'reconv':>7}")
    print("-" * 92)
    for name, enc in CANDIDATES:
        i, a, g, r = battery(enc, runs)
        print(f"{name:<22} {i:>8.3f} {a:>9.1f} "
              + " ".join(f"{g[k]:>6.2f}" for k in (2, 3, 4, 5, 6, 8))
              + f" {r:>6.0%}")
    o = OBSERVED
    print("-" * 92)
    print(f"{'OBSERVED (messages)':<22} {'<=1.07':>8} {0.0:>9.1f} "
          + " ".join(f"{o['gaps'][k]:>6.2f}" for k in (2, 3, 4, 5, 6, 8))
          + f" {'yes':>7}")

    print("\nBest-key analysis: minimum adjacent repeats achievable per 1027")
    bc, bp = best_key_analysis(runs)
    print(f"  ct-chain + p4, best key found: {bc:.1f}")
    print(f"  pt-chain + p4, best key found: {bp:.1f}")
    print("  (0.0 means a lucky key alone explains constraint 3;")
    print("   anything clearly above 0 means it cannot.)")

    print("\nNotes")
    print("  - 'reconv' = fraction of trials where a divergent plaintext pair")
    print("    re-converges at least twice, as E1/W1 does. The data needs ~100%.")
    print("  - The table variants are statistically identical to pt-chain+p4 for")
    print("    every column here (a fixed bijection cannot change repeat or")
    print("    coincidence counts); they differ only for key search later.")


if __name__ == "__main__":
    main()
