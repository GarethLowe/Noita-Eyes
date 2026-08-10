"""H1: ciphertext autokey over Z83 -- c[i] = p[i] + f(c[i-1]) mod 83.

Four parts:

1. An exact argument that constraint 3 (zero adjacent repeats) kills every
   affine f except the pure shift f(x) = x + b, because 83 is prime.
2. Given that, the recovered plaintext is forced to be the ciphertext first
   difference up to a constant shift, so H1 stands or falls on whether that
   difference sequence looks like language.
3. A positive control: synthetic language-like plaintext encrypted under H1,
   put through the identical battery, to show the tests have the power to
   detect H1 when it is true.
4. The same battery on reverse chaining, f applied to c[i+1].

Method notes. Positionally-shared header runs are stripped first (see
dedup.py) or they fake repetition structure on their own. The null model
reshuffles each surviving segment subject to the no-adjacent-repeat
constraint, so the null differences are non-zero exactly as the observed ones
are and the comparison is not biased by constraint 3 itself.

Run: python3 tools/h1_ciphertext_autokey.py
"""
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, load  # noqa: E402
from dedup import segments  # noqa: E402
from synth import corpus  # noqa: E402

TRIALS = 2000
SEED = 1


def diff_segments(segs, a=1, reverse=False):
    """p[i] = c[i] - a*c[i-1] mod 83 within each segment (b=0; b only relabels)."""
    out = []
    for s in segs:
        w = s[::-1] if reverse else s
        if len(w) > 1:
            out.append([(w[i] - a * w[i - 1]) % N for i in range(1, len(w))])
    return out


def ioc_nonzero(segs):
    """IoC over the 82 attainable difference values, normalised to 1.0 = flat."""
    vals = [x for s in segs for x in s]
    c = Counter(vals)
    m = len(vals)
    return sum(x * (x - 1) for x in c.values()) / (m * (m - 1)) * (N - 1)


def bigram_rate(segs):
    """Fraction of within-segment bigrams that occur more than once."""
    bg = Counter()
    slots = 0
    for s in segs:
        bg.update(zip(s, s[1:]))
        slots += max(0, len(s) - 1)
    return sum(v for v in bg.values() if v > 1) / slots


def shuffle_no_repeat(seq, rng, tries=200):
    """Shuffle preserving the multiset and the no-adjacent-repeat property."""
    for _ in range(tries):
        w = list(seq)
        rng.shuffle(w)
        for _ in range(40):
            bad = [i for i in range(1, len(w)) if w[i] == w[i - 1]]
            if not bad:
                return w
            for i in bad:
                j = rng.randrange(len(w))
                w[i], w[j] = w[j], w[i]
    return w


def battery(title, segs, reverse=False, trials=TRIALS, seed=SEED):
    """Run IoC and bigram tests on the H1-derived plaintext, with a null."""
    derived = diff_segments(segs, reverse=reverse)
    vals = [x for s in derived for x in s]
    c = Counter(vals)

    rng = random.Random(seed)
    nulls = {"ioc": [], "bg": []}
    for _ in range(trials):
        sh = [shuffle_no_repeat(s, rng) for s in segs]
        d = diff_segments(sh, reverse=reverse)
        nulls["ioc"].append(ioc_nonzero(d))
        nulls["bg"].append(bigram_rate(d))

    print(f"\n--- {title} ---")
    print(f"  symbols used {len(c)}/83, top: {c.most_common(3)}")
    results = {}
    for key, label, obs in (("ioc", "IoC", ioc_nonzero(derived)),
                            ("bg", "bigram repeat rate", bigram_rate(derived))):
        nl = nulls[key]
        mean = sum(nl) / len(nl)
        sd = (sum((x - mean) ** 2 for x in nl) / (len(nl) - 1)) ** 0.5
        p = (sum(1 for x in nl if x >= obs) + 1) / (trials + 1)
        z = (obs - mean) / sd if sd else float("nan")
        print(f"  {label:<20} obs={obs:.4f}  null={mean:.4f}+-{sd:.4f}  "
              f"z={z:+.2f}  p={p:.4f}")
        results[key] = (obs, z, p)
    return results


def main():
    msgs = load()
    segs = segments(msgs)
    kept = sum(len(s) for s in segs)

    print("=" * 70)
    print("Part 1: affine f under constraint 3 (zero adjacent repeats)")
    print("=" * 70)
    onto = [a for a in range(N)
            if len({((1 - a) * x) % N for x in range(N)}) == N]
    print(f"  multipliers a for which g(x)=x-f(x) is onto Z83: {len(onto)}/83 "
          f"(all except a={[a for a in range(N) if a not in onto]})")
    print("  A repeat occurs iff p[i] = g(c[i-1]). All 83 symbols appear in the")
    print("  ciphertext, so if g is onto, avoiding repeats means the plaintext")
    print("  avoids every symbol in the alphabet. Impossible.")
    print("  => within the affine family only the pure shift a=1 survives.")

    print()
    print("=" * 70)
    print("Part 2: a=1 -- derived plaintext is the ciphertext first difference")
    print("=" * 70)
    print(f"  corpus after stripping shared runs: {len(segs)} segments, "
          f"{kept}/1036 symbols")
    print("  d[i] != 0 by construction (that IS constraint 3), so the absent")
    print("  value carries no evidence; the rest of the shape is the test.")
    fwd = battery("forward chain: p[i] = c[i] - c[i-1]", segs)
    rev = battery("reverse chain: p[i] = c[i] - c[i+1]", segs, reverse=True)

    print()
    print("=" * 70)
    print("Part 3: positive control -- synthetic language encrypted under H1")
    print("=" * 70)
    ctrl = corpus("autokey", [len(s) for s in segs], seed=7)
    ctl = battery("synthetic H1 ciphertext (should light up)", ctrl,
                  trials=200, seed=3)

    print()
    print("=" * 70)
    print("Verdict inputs")
    print("=" * 70)
    for name, r in (("forward", fwd), ("reverse", rev), ("control", ctl)):
        print(f"  {name:<8} IoC z={r['ioc'][1]:+7.2f} p={r['ioc'][2]:.4f}   "
              f"bigram z={r['bg'][1]:+7.2f} p={r['bg'][2]:.4f}")


if __name__ == "__main__":
    main()
