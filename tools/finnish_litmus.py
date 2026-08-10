"""Push real Finnish through the candidate ciphers and see what comes out.

The litmus test CLAUDE.md asks for, with a real plaintext instead of a
synthetic stand-in: encrypt Finnish under each surviving candidate and check
whether the result reproduces constraints 2, 3 and 5 (flat IoC, zero adjacent
repeats, gap-4 excess). A candidate that cannot produce them from plausible
plaintext is dead regardless of how appealing its algebra is.

Plaintext model: Finnish prose syllabified and restricted to the 83 most
common syllables, which is the syllabary reading of the 83-symbol alphabet.
Restriction cuts the stream rather than folding rare syllables into a catch-all
symbol, so the runs are shorter but the distribution is not distorted.

Run: python3 tools/finnish_litmus.py [path/to/finnish.txt]
"""
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, ioc, load  # noqa: E402
from dedup import segments  # noqa: E402
from finnish import top83_stream  # noqa: E402

OBSERVED = {2: 0.48, 3: 0.78, 4: 1.98, 5: 1.00, 6: 1.21, 7: 1.13, 8: 1.03}


def gap_ratio(runs, k):
    hit = sum(1 for v in runs for i in range(len(v) - k) if v[i] == v[i + k])
    pairs = sum(max(0, len(v) - k) for v in runs)
    return hit / (pairs / N) if pairs else float("nan")


def adjacent(runs):
    return sum(1 for v in runs for i in range(1, len(v)) if v[i] == v[i - 1])


def report(label, runs):
    flat = [x for v in runs for x in v]
    n = len(flat)
    ratios = "  ".join(f"{gap_ratio(runs, k):5.2f}" for k in range(2, 9))
    adj = adjacent(runs)
    per1027 = adj / max(1, n) * 1027
    print(f"  {label:<34} {ioc(flat):5.2f}  {ratios}   {adj:>5} ({per1027:.1f})")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if not src:
        raise SystemExit("usage: python3 tools/finnish_litmus.py FINNISH_TEXT")
    text = Path(src).read_text(encoding="utf-8", errors="ignore")
    runs = [r for r in top83_stream(text) if len(r) > 8]
    n = sum(len(r) for r in runs)
    print(f"Finnish plaintext: {len(runs)} runs, {n} syllable symbols "
          f"(top-83 syllabary)\n")

    print(f"  {'':<34} {'IoC':>5}  " +
          "  ".join(f"{'g' + str(k):>5}" for k in range(2, 9)) +
          "   adj (per 1027)")
    print("  " + "-" * 88)

    report("PLAINTEXT itself", runs)

    rng = random.Random(1)
    pi = list(range(N))
    rng.shuffle(pi)

    # H2 sub-case 2: c[i] = pi(p[i] + p[i-1])
    h2 = [[pi[(v[i] + v[i - 1]) % N] for i in range(1, len(v))] for v in runs]
    report("H2: pi(p[i] + p[i-1])", h2)

    # H1 for contrast: c[i] = p[i] + c[i-1]
    h1 = []
    for v in runs:
        c = [v[0]]
        for x in v[1:]:
            c.append((x + c[-1]) % N)
        h1.append(c)
    report("H1: p[i] + c[i-1] (falsified)", h1)

    # Period-4 additive key: the simplest thing that could make gap 4 special
    key = [rng.randrange(N) for _ in range(4)]
    p4 = [[(v[i] + key[i % 4]) % N for i in range(len(v))] for v in runs]
    report("period-4 additive key", p4)

    obs = segments(load())
    print("  " + "-" * 88)
    print(f"  {'OBSERVED eye messages':<34} "
          f"{ioc([x for s in obs for x in s]):5.2f}  " +
          "  ".join(f"{OBSERVED[k]:5.2f}" for k in range(2, 9)) +
          f"   {0:>5} (0.0)")

    print("\nReadings:")
    print("  - Finnish syllables repeat at every distance above 1: a plateau,")
    print("    not a spike. A cipher that passes repeats through inherits the")
    print("    whole plateau. The messages sit at chance for gaps 5-8, so most")
    print("    plaintext repetition is being destroyed -- but gap 4 survives.")
    print("  - The period-4 additive key is the one candidate here that")
    print("    reproduces that shape: it passes distance-4 plaintext repeats")
    print("    through untouched while scrambling every other distance. It is")
    print("    also the simplest thing on the list -- a four-symbol key.")
    print("    It still fails constraint 3 outright (adjacent repeats, not 0).")
    print("  - H2 does NOT flatten to the observed IoC: it lands near 1.4 where")
    print("    the messages read 1.02, and it inherits the plaintext's")
    print("    distance-2 repeats as adjacent ciphertext repeats. Both are")
    print("    problems for the current leading hypothesis.")


if __name__ == "__main__":
    main()
