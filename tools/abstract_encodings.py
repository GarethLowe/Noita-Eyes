"""Abstract encodings: values as movement or hidden-state shifts, not symbols.

The challenge under test: a trigram value does not need to BE a character. It
can be an instruction. The space of such readings factors into three classes:

  A. FIXED abstract maps (value -> cell in a layout, letter at a keyboard
     position, rune in a table). Any fixed map is a monoalphabetic
     substitution, and constraint 2 (flat frequencies, IoC ~ 1.0) killed
     substitution long ago. Dead on arrival, no new test needed.

  B. CUMULATIVE readings ("shifting hidden values"). Each value rotates a
     hidden wheel or moves a pointer along a ring; the message is the pointer
     position after each step: p[i] = (c[0] + ... + c[i]) mod m. This is the
     exact dual of the first-difference test that killed H1, and it was not
     yet tested. If true, the running sum is the plaintext and must be lumpy
     like language. Tested at ring sizes 83, 29, 26, 25, 21 (the plausible
     alphabet sizes).

  C. SPATIAL walks ("moving through space"). Each eye or digit is a step in
     2D; the message is a path - a drawing, a traced shape, a route. The map
     from orientation to direction is unknown, but boundedness is invariant:
     a walk that draws glyphs stays in a small box (radius far below a random
     walk), a deliberate route drifts (radius far above). Both tails tested,
     over a family of direction schemes, Bonferroni-corrected.

Nulls reshuffle deduped segments under the no-adjacent-repeat constraint, as
everywhere in this project. Positive controls: difference-encoded Finnish for
B (the battery must recover the language), a boxed walk and a drifting walk
for C (the battery must flag both tails).

Run: python3 tools/abstract_encodings.py
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, load  # noqa: E402
from dedup import segments  # noqa: E402
from eye_level import eye_stream, norm_ioc  # noqa: E402
from finnish import load_runs  # noqa: E402
from h1_ciphertext_autokey import shuffle_no_repeat  # noqa: E402

RINGS = (83, 29, 26, 25, 21)
TRIALS_RING = 2000
TRIALS_WALK = 500


# --- Part B: cumulative readings ---------------------------------------

def cumsum_stream(segs, m):
    """Pointer positions on an m-ring, chain reset per segment."""
    out = []
    for s in segs:
        acc, run = 0, []
        for v in s:
            acc = (acc + v) % m
            run.append(acc)
        out.append(run)
    return out


def ring_battery(segs, trials=TRIALS_RING, seed=41):
    rng = random.Random(seed)
    nulls = {m: [] for m in RINGS}
    for _ in range(trials):
        sh = [shuffle_no_repeat(list(s), rng) for s in segs]
        for m in RINGS:
            flat = [x for r in cumsum_stream(sh, m) for x in r]
            nulls[m].append(norm_ioc(flat, m))
    rows = []
    for m in RINGS:
        flat = [x for r in cumsum_stream(segs, m) for x in r]
        obs = norm_ioc(flat, m)
        nl = nulls[m]
        mean = sum(nl) / len(nl)
        sd = (sum((x - mean) ** 2 for x in nl) / (len(nl) - 1)) ** 0.5
        z = (obs - mean) / sd if sd else 0.0
        p = (sum(1 for x in nl if x >= obs) + 1) / (trials + 1)
        rows.append((m, obs, mean, sd, z, p))
    return rows


# --- Part C: spatial walks ---------------------------------------------

def compass_schemes():
    """Representative orientation->direction maps, one 'stay' choice x three
    pairings of the rest to N/E/S/W (all others are square symmetries)."""
    dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    out = []
    for stay in range(5):
        rest = [o for o in range(5) if o != stay]
        for perm in ((0, 1, 2, 3), (0, 2, 1, 3), (0, 3, 1, 2)):
            m = {stay: (0, 0)}
            for k in range(4):
                m[rest[perm[k]]] = dirs[k]
            out.append((f"compass stay={stay} p{perm}", m))
    return out


def pentagon_scheme():
    return {o: (math.cos(2 * math.pi * o / 5), math.sin(2 * math.pi * o / 5))
            for o in range(5)}


def walk_radius(steps):
    """Radius of gyration of the path traced by the given (dx, dy) steps."""
    xs, ys, x, y = [], [], 0.0, 0.0
    for dx, dy in steps:
        x += dx
        y += dy
        xs.append(x)
        ys.append(y)
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    return (sum((a - mx) ** 2 + (b - my) ** 2
                for a, b in zip(xs, ys)) / len(xs)) ** 0.5


def scheme_stat(segs, to_steps):
    """Length-weighted mean radius over segments (length >= 12)."""
    tot = wsum = 0.0
    for s in segs:
        st = to_steps(s)
        if len(st) < 12:
            continue
        tot += walk_radius(st) * len(st)
        wsum += len(st)
    return tot / wsum


def walk_battery(segs, trials=TRIALS_WALK, seed=47):
    schemes = []
    for name, m in compass_schemes():
        schemes.append((f"eye {name}",
                        lambda s, m=m: [m[o] for o in eye_stream(s)]))
    pent = pentagon_scheme()
    schemes.append(("eye pentagon 72deg",
                    lambda s: [pent[o] for o in eye_stream(s)]))
    schemes.append(("digit pair (b-2, c-2)",
                    lambda s: [((v // 5) % 5 - 2, v % 5 - 2) for v in s]))

    rng = random.Random(seed)
    shuffles = [[shuffle_no_repeat(list(s), rng) for s in segs]
                for _ in range(trials)]
    rows = []
    for name, fn in schemes:
        obs = scheme_stat(segs, fn)
        nl = [scheme_stat(sh, fn) for sh in shuffles]
        mean = sum(nl) / len(nl)
        sd = (sum((x - mean) ** 2 for x in nl) / (len(nl) - 1)) ** 0.5
        z = (obs - mean) / sd if sd else 0.0
        lo = (sum(1 for x in nl if x <= obs) + 1) / (trials + 1)
        hi = (sum(1 for x in nl if x >= obs) + 1) / (trials + 1)
        rows.append((name, obs, mean, sd, z, min(lo, hi) * 2))
    return rows


# --- controls -----------------------------------------------------------

def control_ring():
    """Difference-encode Finnish on the 83-ring; the battery must recover it."""
    runs = [r for r in load_runs() if len(r) >= 8][:300]
    enc = []
    for r in runs:
        prev, out = 0, []
        for v in r:
            out.append((v - prev) % N)
            prev = v
        enc.append(out)
    flat = [x for r in cumsum_stream(enc, 83) for x in r]
    rng = random.Random(3)
    nl = []
    for _ in range(300):
        sh = [shuffle_no_repeat(list(s), rng) for s in enc]
        nl.append(norm_ioc([x for r in cumsum_stream(sh, 83) for x in r], 83))
    mean = sum(nl) / len(nl)
    sd = (sum((x - mean) ** 2 for x in nl) / (len(nl) - 1)) ** 0.5
    return norm_ioc(flat, 83), mean, sd


def control_walks():
    """A boxed 'drawing' walk and a biased 'route' walk, against shuffle nulls."""
    rng = random.Random(5)
    dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]

    def boxed(n):
        x = y = 0
        st = []
        for _ in range(n):
            while True:
                dx, dy = dirs[rng.randrange(4)]
                if abs(x + dx) <= 2 and abs(y + dy) <= 2:
                    break
            x += dx
            y += dy
            st.append((dx, dy))
        return st

    def streaky(n):
        """Line-tracing: hold each direction for 3-7 steps, like pen strokes.

        Note what the null can and cannot see. Shuffling steps preserves the
        multiset, hence the exact endpoint - so pure drift is invisible to
        this test. A MEANINGFUL route differs from random order by its
        stroke structure (runs and turns), and that is what this control
        exercises: shuffling destroys strokes, so the radius collapses.
        """
        st = []
        while len(st) < n:
            d = dirs[rng.randrange(4)]
            st.extend([d] * rng.randint(3, 7))
        return st[:n]

    out = []
    for label, gen in (("boxed drawing", boxed), ("stroke tracing", streaky)):
        walks = [gen(100) for _ in range(20)]
        obs = sum(walk_radius(w) for w in walks) / len(walks)
        nl = []
        for _ in range(300):
            sh = []
            for w in walks:
                v = list(w)
                rng.shuffle(v)
                sh.append(v)
            nl.append(sum(walk_radius(w) for w in sh) / len(sh))
        mean = sum(nl) / len(nl)
        sd = (sum((x - mean) ** 2 for x in nl) / (len(nl) - 1)) ** 0.5
        out.append((label, obs, mean, sd, (obs - mean) / sd))
    return out


def main():
    segs = segments(load())

    print("Class A: fixed abstract maps")
    print("=" * 70)
    print("  Any fixed map from value to meaning is a monoalphabetic")
    print("  substitution. Constraint 2 (IoC ~ 1.0) killed that class long")
    print("  ago. No new test needed; recorded for completeness.")

    print("\nClass B: cumulative readings -- p[i] = running sum mod m")
    print("=" * 70)
    print(f"  {'ring m':>7} {'IoC obs':>8} {'null':>15} {'z':>7} {'p_hi':>7}")
    for m, obs, mean, sd, z, p in ring_battery(segs):
        print(f"  {m:>7} {obs:>8.3f} {mean:>7.3f}+-{sd:<6.3f} {z:>+7.2f} "
              f"{p:>7.4f}")
    co, cm, cs = control_ring()
    print(f"\n  positive control (difference-encoded Finnish, m=83): "
          f"IoC {co:.2f} vs null {cm:.2f}+-{cs:.2f} "
          f"(z=+{(co - cm) / cs:.0f}) -- the battery has power")

    print("\nClass C: spatial walks -- radius of gyration vs shuffle null")
    print("=" * 70)
    rows = walk_battery(segs)
    k = len(rows)
    flagged = [(n, o, m, s, z, p) for n, o, m, s, z, p in rows
               if p * k < 0.05]
    zs = [z for _, _, _, _, z, _ in rows]
    print(f"  {k} direction schemes tested (15 compass, pentagon, digit-pair)")
    print(f"  z range across schemes: {min(zs):+.2f} .. {max(zs):+.2f}")
    print(f"  schemes significant after Bonferroni x{k}: {len(flagged)}")
    for n, o, m, s, z, p in sorted(rows, key=lambda r: r[5])[:3]:
        print(f"    closest: {n:<28} obs={o:7.2f} null={m:7.2f}+-{s:5.2f} "
              f"z={z:+5.2f} p2={p:.3f}")
    for label, o, m, s, z in control_walks():
        print(f"  control {label:<16} obs={o:6.2f} null={m:6.2f}+-{s:4.2f} "
              f"z={z:+6.1f}")


if __name__ == "__main__":
    main()
