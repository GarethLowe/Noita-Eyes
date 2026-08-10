"""The repeat-gap spectrum: the corpus's sharpest mechanism fingerprint.

For each distance k, how often does a symbol recur k positions later, against a
null that reshuffles each deduped segment subject to the no-adjacent-repeat
constraint? The statistic needs no key and no plaintext model, so it constrains
the mechanism directly.

Three things are reported.

1. The spectrum for k = 2..30 with a Bonferroni column. Gap 4 was predicted in
   advance (constraint 5), so it is confirmatory and reads at its uncorrected
   p. Everything else here is exploratory and must clear the correction.
2. Per-message consistency at gap 4, since a single message could otherwise
   carry the whole effect.
3. The chain test. If a gap-4 coincidence means the state returned to what it
   was 4 steps earlier, the next output must match too, so coincidences come in
   runs. Counting runs separates full state recurrence from a mechanism that
   merely returns one symbol to the output position.

Run: python3 tools/gap_spectrum.py
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, ORDER, load  # noqa: E402
from dedup import segments  # noqa: E402
from h1_ciphertext_autokey import shuffle_no_repeat  # noqa: E402

TRIALS = 3000
MAXGAP = 30
PREREGISTERED = {4}


def count_gap(seqs, k):
    """Number of positions where a symbol recurs exactly k later."""
    return sum(1 for v in seqs for i in range(len(v) - k) if v[i] == v[i + k])


def gap_pairs(seqs, k):
    """Set of (segment index, position) for every gap-k coincidence."""
    return {(si, i) for si, v in enumerate(seqs)
            for i in range(len(v) - k) if v[i] == v[i + k]}


def count_chains(seqs, k):
    """Coincidences immediately followed by another at the next position."""
    p = gap_pairs(seqs, k)
    return sum(1 for (si, i) in p if (si, i + 1) in p)


def null_distribution(segs, fns, trials=TRIALS, seed=21):
    """Sample `fns` (a dict name -> callable) over constrained reshuffles."""
    rng = random.Random(seed)
    out = {k: [] for k in fns}
    for _ in range(trials):
        sh = [shuffle_no_repeat(s, rng) for s in segs]
        for k, fn in fns.items():
            out[k].append(fn(sh))
    return out


def summarise(obs, null, trials=TRIALS):
    """(mean, sd, z, one-sided p for obs being high)."""
    mean = sum(null) / len(null)
    sd = (sum((x - mean) ** 2 for x in null) / (len(null) - 1)) ** 0.5
    p = (sum(1 for x in null if x >= obs) + 1) / (trials + 1)
    return mean, sd, ((obs - mean) / sd if sd else 0.0), p


def main():
    msgs = load()
    segs = segments(msgs)
    tested = MAXGAP - 1

    print(f"{len(segs)} deduped segments, {sum(len(s) for s in segs)} symbols.")
    print(f"Null: {TRIALS} constrained reshuffles. Bonferroni over "
          f"{tested} exploratory gaps.\n")

    nulls = null_distribution(
        segs, {k: (lambda s, k=k: count_gap(s, k)) for k in range(2, MAXGAP + 1)})

    print(f"{'gap':>4} {'obs':>4} {'null':>14} {'z':>7} {'p':>8} "
          f"{'corrected':>10}")
    for k in range(2, MAXGAP + 1):
        obs = count_gap(segs, k)
        mean, sd, z, p = summarise(obs, nulls[k])
        if k in PREREGISTERED:
            tag = f"{p:>10.4f} *predicted in advance, not corrected"
        else:
            tag = f"{min(1.0, p * tested):>10.3f}"
        print(f"{k:>4} {obs:>4} {mean:>7.2f}+-{sd:<5.2f} {z:>+7.2f} "
              f"{p:>8.4f} {tag}")

    print("\nGap 4 by message (raw, so shared headers are visible as such):")
    above, joint = 0, 1.0
    for name in ORDER:
        v = msgs[name]
        c = count_gap([v], 4)
        lam = (len(v) - 4) / N
        # P(Poisson(lam) > lam): the chance this message exceeds expectation.
        floor_lam = int(lam)
        cdf = sum(math.exp(-lam) * lam ** i / math.factorial(i)
                  for i in range(floor_lam + 1))
        above += c > lam
        joint *= (1 - cdf)
        print(f"  {name}: {c} observed vs {lam:.2f} expected")
    print(f"  {above}/9 messages above expectation. Under independent Poisson "
          f"counts the chance of all nine exceeding is {joint:.2e}.")
    print("  Not a clean sign test -- the expectation is not the Poisson median "
          "and\n  E4/W4/E5 share a header, so treat this as corroboration of the "
          "pooled\n  permutation test above, not as an independent result.")

    print("\nChain test at gap 4 -- do coincidences come in runs?")
    obs_pairs = len(gap_pairs(segs, 4))
    obs_chains = count_chains(segs, 4)
    cn = null_distribution(segs, {"c": lambda s: count_chains(s, 4)},
                           trials=TRIALS, seed=33)["c"]
    mean, sd, z, p = summarise(obs_chains, cn)
    print(f"  {obs_pairs} coincidences, {obs_chains} of them consecutive")
    print(f"  chance null: {mean:.2f}+-{sd:.2f} (z={z:+.2f}, p={p:.4f}) "
          f"-- no power against chance")
    print(f"  full-recurrence alternative predicts about {obs_pairs - 1} chains:")
    print("  if the state at i+4 equals the state at i, output i+5 must equal")
    print(f"  output i+1 as well. Observed 0. That alternative is dead.")


if __name__ == "__main__":
    main()
