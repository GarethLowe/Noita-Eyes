"""Eye-level readings: no trigrams. Single eyes, pairs, grid alphabets.

The challenge under test: maybe the community is wrong about trigrams, and each
eye orientation is itself a character, or pairs of eyes index a grid alphabet
(a 5x5 Polybius square holds 25 letters; native Finnish uses about 21, so the
pair reading is a perfectly sensible construction a developer might pick).

What can be tested with the data in hand:

1. Single eyes as characters. Five symbols cannot carry an alphabet directly,
   but any code at the eye level (variable-length, Morse-like, anything) would
   leave structure in the eye stream beyond what the base-5 numeral reading
   explains. So: measure eye-level structure against a null that keeps the
   trigram-level content but shuffles it, preserving the base-5 skew.

2. Pairs of eyes as grid coordinates, both pairings (offset 0 and 1). If pairs
   are letters through a fixed grid, that is a monoalphabetic substitution of
   language, and substitution cannot hide language lumpiness: the pair-value
   IoC must sit far above flat, near the Finnish letter level. Measure it.

3. The base-5 signature. If trigrams really are 3-digit base-5 numbers capped
   at 82, the first eye of each trigram can never show orientation 4 (82 is
   312 in base 5). A slot-locked forbidden orientation is a loud, specific
   fingerprint of the numeral reading - and it is directly visible.

Honest limits: a grid alphabet followed by a STRONG cipher would look flat at
every level and cannot be excluded this way. What is tested here is the idea as
stated - eyes or eye-pairs read as characters directly or through a fixed map.

Run: python3 tools/eye_level.py
"""
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, ORDER, load  # noqa: E402
from dedup import segments  # noqa: E402
from finnish import load_table  # noqa: E402
from h1_ciphertext_autokey import shuffle_no_repeat  # noqa: E402
from reading_order import digits  # noqa: E402

TRIALS = 2000


def eye_stream(msg):
    out = []
    for v in msg:
        out.extend(digits(v))
    return out


def norm_ioc(seq, k):
    c = Counter(seq)
    n = len(seq)
    return sum(x * (x - 1) for x in c.values()) / (n * (n - 1)) * k


def pair_values(eyes, offset):
    e = eyes[offset:]
    return [5 * e[i] + e[i + 1] for i in range(0, len(e) - 1, 2)]


def adjacent(seqs):
    return sum(1 for v in seqs for i in range(1, len(v)) if v[i] == v[i - 1])


def null_stats(segs, offset, trials=TRIALS, seed=17):
    """Shuffle trigram content (no-adjacent-repeat preserved), re-derive eyes.

    This null keeps everything the base-5 numeral reading implies - the slot
    skew, the digit distributions - and destroys only cross-trigram order. Eye-
    and pair-level structure beyond it is evidence of a sub-trigram code.
    Input is DEDUPED segments: an early version ran on the raw messages and the
    triple-counted shared headers manufactured a z=+2.9 pair-adjacency excess
    that dedup dissolves. Third time that trap has fired in this project.
    """
    rng = random.Random(seed)
    iocs, adjs = [], []
    for _ in range(trials):
        sh = [shuffle_no_repeat(list(s), rng) for s in segs]
        pv = [pair_values(eye_stream(m), offset) for m in sh]
        flat = [x for v in pv for x in v]
        iocs.append(norm_ioc(flat, 25))
        adjs.append(adjacent(pv))
    return iocs, adjs


def summarise(obs, null):
    mean = sum(null) / len(null)
    sd = (sum((x - mean) ** 2 for x in null) / (len(null) - 1)) ** 0.5
    hi = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
    lo = (sum(1 for x in null if x <= obs) + 1) / (len(null) + 1)
    return mean, sd, ((obs - mean) / sd if sd else 0.0), min(hi, lo) * 2


def main():
    msgs = load()
    streams = {k: eye_stream(msgs[k]) for k in ORDER}
    all_eyes = [x for k in ORDER for x in streams[k]]

    print("1. The base-5 numeral signature")
    print("=" * 68)
    slot = [Counter() for _ in range(3)]
    for k in ORDER:
        for i, x in enumerate(streams[k]):
            slot[i % 3][x] += 1
    print("  orientation counts by position within each trigram:")
    print("        orient:      0      1      2      3      4")
    for j in range(3):
        print(f"  slot {j}:        " +
              " ".join(f"{slot[j][o]:>6}" for o in range(5)))
    print("\n  Slot 0 never shows orientation 4, and orientation 3 is rare")
    print("  there (82 = 312 in base 5, so the leading digit is 0-3, and 3")
    print("  only for values 75-82). Slots 1 and 2 are near-uniform. A code")
    print("  treating every eye as an equal character would have no reason to")
    print("  lock one orientation out of every third position. This is the")
    print("  shape of numbers, not letters.")

    print("\n2. How lumpy would a grid-alphabet reading have to be?")
    print("=" * 68)
    t = load_table()
    lc = t["letter_counts"]
    nl = sum(lc.values())
    fin_ioc = sum(v * (v - 1) for v in lc.values()) / (nl * (nl - 1)) * len(lc)
    print(f"  Finnish letters: {len(lc)} distinct, normalised IoC = {fin_ioc:.2f}")
    print("  A fixed grid map is a substitution, and substitution preserves")
    print("  IoC. So eye-pairs read through any fixed 5x5 grid must show an")
    print(f"  IoC near {fin_ioc:.1f} if they are Finnish letters. Flat ~1.0 kills it.")

    print("\n3. Eye pairs, both pairings, against the trigram-preserving null")
    print("   (deduped segments, so shared headers cannot fake a signal)")
    print("=" * 68)
    segs = segments(msgs)
    for off in (0, 1):
        pv = [pair_values(eye_stream(s), off) for s in segs]
        flat = [x for v in pv for x in v]
        obs_ioc = norm_ioc(flat, 25)
        obs_adj = adjacent(pv)
        iocs, adjs = null_stats(segs, off)
        for label, obs, null in (("IoC(25)", obs_ioc, iocs),
                                 ("adjacent pair repeats", obs_adj, adjs)):
            m, sd, z, p = summarise(obs, null)
            print(f"  offset {off}  {label:<22} obs={obs:>7.2f}  "
                  f"null={m:7.2f}+-{sd:5.2f}  z={z:+5.2f}  p={p:.3f}")
        print(f"  offset {off}  distinct pair values: {len(set(flat))}/25")

    print("\n4. Single-eye structure beyond the numeral reading")
    print("=" * 68)
    rng = random.Random(23)
    seg_eyes = [x for s in segs for x in eye_stream(s)]
    obs_bi = norm_ioc(list(zip(seg_eyes, seg_eyes[1:])), 1)
    null_bi = []
    for _ in range(400):
        sh = [x for s in segs
              for x in eye_stream(shuffle_no_repeat(list(s), rng))]
        null_bi.append(norm_ioc(list(zip(sh, sh[1:])), 1))
    m, sd, z, p = summarise(obs_bi, null_bi)
    print(f"  eye-bigram repeat mass: obs={obs_bi:.5f}  "
          f"null={m:.5f}+-{sd:.5f}  z={z:+.2f}  p={p:.3f}")
    print("  At chance against the trigram-preserving null: the eye stream")
    print("  carries no pairwise structure the numeral reading does not already")
    print("  explain.")


if __name__ == "__main__":
    main()
