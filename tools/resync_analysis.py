"""State-size bound from re-convergence between message pairs.

Constraint 4 records that messages share runs. The part that matters is not the
shared header but what happens *after* two messages diverge: E1 and W1 diverge
at position 25, agree again for 4 at 29-32, diverge again, then agree for 13 at
37-49. E4 and E5 re-converge three times.

That is a bound on the cipher's state, and a hard one. Write S for the number of
internal states. Once two encryptions diverge, agreeing again for L consecutive
symbols requires either that the states coincide again -- probability on the
order of 1/S -- or L independent 1-in-83 coincidences.

  - Stateless position-keyed cipher (S = 1): identical plaintext at a position
    gives identical ciphertext no matter what came before. Re-convergence runs
    are free.
  - One-symbol chaining state (S = 83, e.g. an autokey): one coincidence
    re-synchronises, and every later shared plaintext symbol then matches.
    Re-convergence is cheap and, once paid for, self-sustaining.
  - Deck / group autokey over S83 (S = 83! ~ 10^124): the state can never
    realign. Ciphertext agreement can only ever be isolated 1-in-83 accidents,
    so a run of length L costs 83^-L.

A 13-long re-convergence costs 83^-13 ~ 10^-25 under the deck model. That is not
a marginal call.

Run: python3 tools/resync_analysis.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, ORDER, load  # noqa: E402
from synth import language_like  # noqa: E402
from deck_models import full_shuffle, swap_top_with_depth  # noqa: E402

MIN_RUN = 3


def agreement_runs(x, y, min_run=MIN_RUN):
    """Maximal runs of positional agreement of at least min_run, from index 1."""
    L = min(len(x), len(y))
    runs, k = [], 1
    while k < L:
        if x[k] == y[k]:
            j = k
            while j < L and x[j] == y[j]:
                j += 1
            if j - k >= min_run:
                runs.append((k, j - 1, j - k))
            k = j
        else:
            k += 1
    return runs


def reconvergences(x, y, min_run=MIN_RUN):
    """Agreement runs that begin after the pair has already diverged."""
    return [r for r in agreement_runs(x, y, min_run) if r[0] > 1]


def deck_pair(mech, plaintexts, seed):
    """Encrypt two plaintexts from the SAME initial deck, as the data requires.

    Constraint 4 forces a shared initial state: identical plaintext prefixes
    give identical ciphertext prefixes across messages, so there is no
    per-message key.
    """
    rng = random.Random(seed)
    deck0 = list(range(N))
    rng.shuffle(deck0)
    out = []
    for p in plaintexts:
        deck = list(deck0)
        state = {"i": 0, "j": 0, "rng": random.Random(seed), "base": 1,
                 "last": None}
        c = []
        for v in p:
            mech(deck, v, state)
            c.append(deck[0])
        out.append(c)
    return out


def divergent_pair(rng, n=100, diverge=(25, 29), rejoin=(33, 37)):
    """Two plaintexts that agree, differ over two windows, then agree again."""
    a = language_like(rng, n)
    b = list(a)
    for lo, hi in (diverge, rejoin):
        for i in range(lo, hi):
            b[i] = rng.choice([x for x in range(1, 31) if x != a[i]])
    return a, b


def main():
    msgs = load()

    print("Observed re-convergences (agreement runs starting after divergence)")
    print("=" * 70)
    total = []
    for i, a in enumerate(ORDER):
        for b in ORDER[i + 1:]:
            rc = reconvergences(msgs[a], msgs[b])
            if rc:
                total.extend(rc)
                print(f"  {a} vs {b}: " +
                      ", ".join(f"pos {s}-{e} (len {ln})" for s, e, ln in rc))
    longest = max(ln for _, _, ln in total)
    print(f"\n  {len(total)} re-convergence runs, longest {longest} symbols")

    print("\nCost of the longest run under each state-size model")
    print("=" * 70)
    print(f"  stateless position-keyed  : free -- identical plaintext at a")
    print(f"                              position always gives identical output")
    print(f"  one-symbol chaining (S=83): ~1/83 once, then self-sustaining")
    print(f"  deck / S83 group autokey  : 83^-{longest} = {83.0 ** -longest:.2e}")

    print("\nSimulation: same initial deck, plaintexts that diverge then rejoin")
    print("=" * 70)
    rng = random.Random(3)
    pa, pb = divergent_pair(rng)
    shared = [i for i in range(1, len(pa)) if pa[i] == pb[i]]
    print(f"  plaintexts agree at {len(shared)}/{len(pa) - 1} positions, "
          f"differing only over 25-28 and 33-36")
    for label, mech in (("group autokey, random gens", full_shuffle),
                        ("swap top with depth p", swap_top_with_depth)):
        ca, cb = deck_pair(mech, [pa, pb], seed=11)
        runs = agreement_runs(ca, cb)
        agree = sum(1 for i in range(1, len(ca)) if ca[i] == cb[i])
        print(f"  {label:<30} ciphertext agrees at {agree} positions, "
              f"runs>={MIN_RUN}: {runs}")

    print("\n  Ciphertext-chained autokey, c[i] = p[i] + c[i-1] (state = 83):")
    ca, cb = [0], [0]
    for v in pa:
        ca.append((v + ca[-1]) % N)
    for v in pb:
        cb.append((v + cb[-1]) % N)
    print(f"    agreement runs: {agreement_runs(ca, cb)}")
    print("    Re-convergence needs the accumulated plaintext difference over a")
    print("    divergent window to cancel mod 83: about 1/83 per window.")

    print("\n  Plaintext-chained autokey, c[i] = p[i] + p[i-1] (H2):")
    da = [(pa[i] + pa[i - 1]) % N for i in range(1, len(pa))]
    db = [(pb[i] + pb[i - 1]) % N for i in range(1, len(pb))]
    print(f"    agreement runs: {agreement_runs(da, db)}")
    print("    Re-converges one symbol after the plaintext does, for free, every")
    print("    time -- no coincidence required. This is the observed behaviour.")


if __name__ == "__main__":
    main()
