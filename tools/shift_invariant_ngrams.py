"""Count ciphertext n-grams that repeat up to a constant additive shift mod 83.

Motivation. Under any cipher whose key acts as an additive rotation over Z83 --
Vigenere, an Alberti disk with additive step, a progressive shift -- the same
plaintext n-gram enciphered at two different key offsets yields two ciphertext
n-grams with identical successive differences but different absolute values.
Absolute n-gram repeats are invisible to such a cipher; shift-invariant ones
are not. This is the natural repetition statistic for hypothesis 3, and the
residual that survived the hypothesis 1 battery.

An n-gram's shift class is its difference vector (c[i+1]-c[i], ...) of length
n-1. Positionally-shared header runs are stripped first (dedup.py). The null
reshuffles each segment subject to the no-adjacent-repeat constraint.

Run: python3 tools/shift_invariant_ngrams.py
"""
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, load  # noqa: E402
from dedup import segments  # noqa: E402
from h1_ciphertext_autokey import shuffle_no_repeat  # noqa: E402
from synth import corpus  # noqa: E402

TRIALS = 2000


def classes(segs, n):
    """Counter of shift classes (difference vectors) for every n-gram."""
    c = Counter()
    for s in segs:
        for i in range(len(s) - n + 1):
            c[tuple((s[i + j + 1] - s[i + j]) % N for j in range(n - 1))] += 1
    return c


def stats(segs, n):
    """(distinct repeated classes, n-gram slots inside a repeated class)."""
    c = classes(segs, n)
    rep = {k: v for k, v in c.items() if v > 1}
    return len(rep), sum(rep.values())


def main():
    segs = segments(load())
    rng = random.Random(11)

    print(f"corpus: {len(segs)} segments, {sum(len(s) for s in segs)} symbols "
          f"after stripping shared runs\n")
    print(f"{'n':>2}  {'repeated classes':>16}  {'null':>15}  {'z':>7}  "
          f"{'p':>7}   {'occurrences':>11}  {'null':>15}  {'z':>7}  {'p':>7}")

    nulls = {n: ([], []) for n in (3, 4, 5, 6)}
    for _ in range(TRIALS):
        sh = [shuffle_no_repeat(s, rng) for s in segs]
        for n in nulls:
            a, b = stats(sh, n)
            nulls[n][0].append(a)
            nulls[n][1].append(b)

    for n in (3, 4, 5, 6):
        obs = stats(segs, n)
        row = f"{n:>2}"
        for k in (0, 1):
            nl = nulls[n][k]
            mean = sum(nl) / len(nl)
            sd = (sum((x - mean) ** 2 for x in nl) / (len(nl) - 1)) ** 0.5
            p = (sum(1 for x in nl if x >= obs[k]) + 1) / (TRIALS + 1)
            z = (obs[k] - mean) / sd if sd else float("nan")
            row += f"  {obs[k]:>16}  {mean:>7.2f}+-{sd:<6.2f}  {z:>+7.2f}  {p:>7.4f}"
        print(row)

    print("\nLongest shift-invariant repeats observed:")
    for n in range(6, 12):
        c = classes(segs, n)
        rep = [k for k, v in c.items() if v > 1]
        if not rep:
            print(f"  none at n={n}")
            break
        print(f"  n={n}: {len(rep)} repeated class(es)")

    print("\nControls -- language-like plaintext under additive-key ciphers,")
    print("same segment lengths. A constant-increment key leaves every repeated")
    print("plaintext n-gram visible as a shift-invariant ciphertext repeat.")
    lengths = [len(s) for s in segs]
    controls = [
        ("progressive shift, step 1", "progressive", {"step": 1}),
        ("progressive shift, step 7", "progressive", {"step": 7}),
        ("Vigenere, period 14", "vigenere", {"period": 14}),
    ]
    print(f"\n  {'cipher':<28} {'n=3':>10} {'n=4':>10} {'n=5':>10} {'n=6':>10}"
          f" {'adj.repeats':>12}")
    for label, kind, kw in controls:
        cs = corpus(kind, lengths, seed=23, **kw)
        cells = "".join(f" {stats(cs, n)[0]:>10}" for n in (3, 4, 5, 6))
        adj = sum(1 for s in cs for i in range(1, len(s)) if s[i] == s[i - 1])
        print(f"  {label:<28}{cells} {adj:>12}")
    print(f"  {'OBSERVED (eye messages)':<28}"
          + "".join(f" {stats(segs, n)[0]:>10}" for n in (3, 4, 5, 6))
          + f" {0:>12}")


if __name__ == "__main__":
    main()
