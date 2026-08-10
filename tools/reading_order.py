"""Is the community's reading of the eyes right? Grouping, direction, direction.

Three challenges to the consensus reading, tested against the data we have.

1. GROUPING. The trigram values are 3-digit base-5 numbers, so they invert:
   v = 25a + 5b + c recovers the underlying eye orientations. That means the
   raw eye stream is recoverable after all, and alternative groupings can be
   tested. Regrouping at a 1- or 2-eye offset, under all 6 possible spatial
   orders of the digits, gives 18 candidate readings.

2. DIRECTION. If the messages were meant to be read backwards, the shared
   material would sit at the end rather than the start.

3. VERTICAL. A columnar read is a transposition of the trigram sequence, which
   preserves the alphabet but rearranges adjacency.

Run: python3 tools/reading_order.py
"""
import random
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, ORDER, load  # noqa: E402


def digits(v):
    """Invert a trigram to its three base-5 eye orientations."""
    return (v // 25, (v // 5) % 5, v % 5)


def regroup(msgs, order, offset):
    """Rebuild the eye stream under a digit order, then re-cut into trigrams."""
    out = []
    for k in ORDER:
        eyes = []
        for v in msgs[k]:
            d = digits(v)
            eyes += [d[order[0]], d[order[1]], d[order[2]]]
        e = eyes[offset:]
        out.append([25 * e[i] + 5 * e[i + 1] + e[i + 2]
                    for i in range(0, len(e) - 2, 3)])
    return out


def adjacent(seqs):
    return sum(1 for v in seqs for i in range(1, len(v)) if v[i] == v[i - 1])


def shared_from_start(a, b):
    n = 0
    for x, y in zip(a[1:], b[1:]):
        if x != y:
            break
        n += 1
    return n


def shared_from_end(a, b):
    n = 0
    for x, y in zip(reversed(a), reversed(b)):
        if x != y:
            break
        n += 1
    return n


def columnar(seq, w):
    rows = (len(seq) + w - 1) // w
    return [seq[r * w + c] for c in range(w) for r in range(rows)
            if r * w + c < len(seq)]


def main():
    msgs = load()

    print("1. GROUPING -- 6 digit orders x 3 eye offsets")
    print("=" * 68)
    print(f"{'digit order':<12} {'offset':>6} {'distinct':>9} {'range':>10} "
          f"{'contiguous':>11} {'adj repeats':>12}")
    for order in permutations(range(3)):
        for off in (0, 1, 2):
            segs = regroup(msgs, order, off)
            allv = [x for s in segs for x in s]
            c = Counter(allv)
            contig = (len(c) == max(allv) - min(allv) + 1)
            print(f"{str(order):<12} {off:>6} {len(c):>9} "
                  f"{str(min(allv)) + '-' + str(max(allv)):>10} "
                  f"{'YES' if contig else 'no':>11} {adjacent(segs):>12}")
    print("\n  Only offset 0 gives zero adjacent repeats, and only offset 0 with")
    print("  digit order (0,1,2) gives a contiguous 0-82 alphabet. The community")
    print("  selected on contiguity alone; the repeat property is independent")
    print("  corroboration that the grouping is right.")
    print("  Caveat: this covers linear re-cuts of the eye stream, not the full")
    print("  set of spatial traversals of the physical triangular layout.")

    print("\n2. DIRECTION -- where does the shared material sit?")
    print("=" * 68)
    ts = te = 0
    for i, a in enumerate(ORDER):
        for b in ORDER[i + 1:]:
            ts += shared_from_start(msgs[a], msgs[b])
            te += shared_from_end(msgs[a], msgs[b])
    print(f"  summed shared run length over 36 pairs, from the START: {ts}")
    print(f"  summed shared run length over 36 pairs, from the END:   {te}")
    print("\n  All shared material is aligned to one end. Reading forwards makes")
    print("  it a header preceded by a per-message identifier at position 0, the")
    print("  natural place for an initialisation value. Reading backwards makes")
    print("  it a footer followed by a trailing identifier. The data alone does")
    print("  not decide this -- reversal maps one story onto the other -- but the")
    print("  forward reading is the far more natural construction.")

    print("\n3. VERTICAL -- columnar reads at every plausible width")
    print("=" * 68)
    rows = []
    for w in range(2, 41):
        rows.append((adjacent([columnar(msgs[k], w) for k in ORDER]), w))
    rows.sort()
    print(f"  best (fewest adjacent repeats): "
          + ", ".join(f"w={w}: {a}" for a, w in rows[:5]))
    print(f"  worst: " + ", ".join(f"w={w}: {a}" for a, w in rows[-3:]))
    rng = random.Random(0)
    ctrl = []
    for _ in range(200):
        t = 0
        for k in ORDER:
            v = list(msgs[k])
            rng.shuffle(v)
            t += sum(1 for i in range(1, len(v)) if v[i] == v[i - 1])
        ctrl.append(t)
    mean = sum(ctrl) / len(ctrl)
    sd = (sum((x - mean) ** 2 for x in ctrl) / (len(ctrl) - 1)) ** 0.5
    print(f"  random-reordering baseline: {mean:.1f} +- {sd:.1f}")
    print(f"  linear read, as transcribed: {adjacent([msgs[k] for k in ORDER])}")
    print("\n  No columnar width reaches zero; the best manages 5 against a")
    print("  chance baseline of 12. The linear reading is unique in this respect,")
    print("  so a vertical read is not supported. Note width 4 is the WORST of")
    print("  the small widths, which is just constraint 5 restated: a columnar")
    print("  read at width 4 places the gap-4 coincidences next to each other.")


if __name__ == "__main__":
    main()
