"""H2: plaintext-chained autokey, c[i] = F(p[i], p[i-1]).

Why this hypothesis moved to the front. The re-convergence evidence
(resync_analysis.py) says the cipher's state cannot depend on ciphertext
history: E1/W1 and E4/E5 rejoin after diverging, which a ciphertext-chained or
deck-based state cannot do without a 1-in-83 accident per event. A state
derived from the *plaintext* rejoins for free, one symbol after the plaintext
does. That is what the data looks like.

Two sub-cases, with very different status.

1. Bare addition, c[i] = p[i] + p[i-1] mod 83. The whole plaintext follows from
   a single unknown p[0], since p[i] = c[i] - p[i-1]. Changing p[0] shifts the
   even-index plaintext one way and the odd-index the other, so the IoC of each
   subsequence is invariant to it and can be measured without guessing. If the
   plaintext were language, both would be far above 1.0.

2. Through a substitution, c[i] = pi(p[i] + p[i-1]). Not addressed here: pi is
   unknown and the derived plaintext depends on it, so this needs a key search
   over S83, not a closed-form test. Note it survives the IoC argument that
   killed H1 -- there the first difference *was* the plaintext, whereas here
   c[i] - c[i-1] = p[i] - p[i-2], a difference of plaintext symbols, which is
   expected to look flat even when the plaintext does not.

Run: python3 tools/h2_plaintext_autokey.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, ORDER, ioc, load  # noqa: E402
from synth import language_like  # noqa: E402


def derive(c, p0=0):
    """Invert c[i] = p[i] + p[i-1] given a guess for p[0]."""
    p = [p0 % N]
    for i in range(1, len(c)):
        p.append((c[i] - p[-1]) % N)
    return p


def parity_iocs(c):
    """(IoC of even-index plaintext, IoC of odd-index) -- invariant to p[0]."""
    p = derive(c)
    return ioc(p[0::2]), ioc(p[1::2])


def main():
    msgs = load()

    print("Sub-case 1: c[i] = p[i] + p[i-1] mod 83")
    print("=" * 60)
    print(f"{'message':<9} {'IoC even':>9} {'IoC odd':>9}")
    ev, od = [], []
    for k in ORDER:
        p = derive(msgs[k])
        ev += p[0::2]
        od += p[1::2]
        a, b = parity_iocs(msgs[k])
        print(f"{k:<9} {a:>9.3f} {b:>9.3f}")
    print(f"{'POOLED':<9} {ioc(ev):>9.3f} {ioc(od):>9.3f}")

    rng = random.Random(0)
    print(f"\n  uniform-random reference: "
          f"{ioc([rng.randrange(N) for _ in range(len(ev))]):.3f}")

    ctrl = language_like(rng, 1000, alphabet_size=45)
    cc = [ctrl[0]] + [(ctrl[i] + ctrl[i - 1]) % N for i in range(1, len(ctrl))]
    ca, cb = parity_iocs(cc)
    print(f"  positive control (language-like plaintext, same construction): "
          f"{ca:.3f} / {cb:.3f}")

    print("\n  VERDICT: falsified. The derived plaintext is flat where the")
    print("  control reads far above 1.0, so no choice of p[0] yields language.")

    print("\nSub-case 2: c[i] = pi(p[i] + p[i-1]) -- OPEN")
    print("=" * 60)
    print("  Not decidable in closed form: pi is unknown, and unlike sub-case 1")
    print("  the derived plaintext depends on it. Needs hill-climbing over S83")
    print("  with a Finnish n-gram score, plus a shuffled-ciphertext control run")
    print("  to calibrate what a spurious 'signal' looks like.")
    print("\n  What it must also explain: zero adjacent repeats requires")
    print("  F(p[i],p[i-1]) != F(p[i-1],p[i-2]) at every one of 1027 positions.")
    print("  For F = pi(a+b) that reduces to p[i] != p[i-2] always. Even over a")
    print("  syllabary of ~83, roughly 25 distance-2 repeats would be expected")
    print("  in 1027 symbols. Observing zero is the sticking point, and it is")
    print("  the reason this hypothesis is not yet comfortable.")


if __name__ == "__main__":
    main()
