"""H4 / community deck theory: simulate deck ciphers and fingerprint them.

The community's leading candidate is a deck of 83 cards in which each plaintext
letter triggers a shuffle and the top card after shuffling is the ciphertext
symbol -- a group autokey over the symmetric group S83. Constraint 3 comes free
in that model: if every shuffle moves the top card, the output cannot repeat.

That explanation is correct but weak, because it is shared by every mechanism in
the family. The discriminating evidence is the *repeat-gap spectrum*: how often
a symbol recurs at distance k. That statistic needs no key and no plaintext
model, only the mechanism, so it separates candidates before any key search.

Observed (deduped): gap 1 is empty, gaps 2 and 3 are suppressed to roughly half
the chance rate, gap 4 runs at about twice the chance rate, and gaps 5+ sit at
chance. So the deck retains about four steps of memory and is fully mixed after
that. A mechanism must reproduce that shape, not merely the zero at gap 1.

Run: python3 tools/deck_models.py
"""
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, ioc, load  # noqa: E402
from dedup import segments  # noqa: E402
from synth import language_like  # noqa: E402

MAXGAP = 8
SEEDS = 40


# --- shuffle mechanisms -------------------------------------------------
# Each takes (deck, p, state) and mutates deck in place. `state` is a dict for
# mechanisms that carry pointers of their own. All but rc4_like guarantee the
# top card changes, which is the community's explanation of constraint 3.

def cut_by_p(deck, p, state):
    """Rotate the deck by p+1. Equivalent to an additive shift on the output."""
    r = (p % (N - 1)) + 1
    deck[:] = deck[r:] + deck[:r]


def cut_by_c(deck, p, state):
    """H3 ciphertext-driven rotation: rotate by the previous output plus 1."""
    r = ((state.get("prev") or 0) % (N - 1)) + 1
    deck[:] = deck[r:] + deck[:r]
    state["prev"] = deck[0]


def cut_by_p_and_c(deck, p, state):
    """H3 mixed schedule: rotation driven by plaintext and previous output."""
    r = ((p + (state.get("prev") or 0)) % (N - 1)) + 1
    deck[:] = deck[r:] + deck[:r]
    state["prev"] = deck[0]


def insert_top_at_depth(deck, p, state):
    """Deal the top card back into the deck at depth p+1."""
    d = (p % (N - 1)) + 1
    card = deck.pop(0)
    deck.insert(d, card)


def swap_top_with_depth(deck, p, state):
    """Swap the top card with the card at depth p+1."""
    d = (p % (N - 1)) + 1
    deck[0], deck[d] = deck[d], deck[0]


def base_rotate_then_swap(deck, p, state):
    """A fixed base shuffle plus one plaintext-dependent transposition.

    This is the community's 'few swaps from a shared base permutation' shape.
    """
    r = state["base"]
    deck[:] = deck[r:] + deck[:r]
    d = (p % (N - 1)) + 1
    deck[0], deck[d] = deck[d], deck[0]


def riffle_cut_by_p(deck, p, state):
    """Cut at p+1 and riffle the two halves together perfectly."""
    r = (p % (N - 1)) + 1
    a, b = deck[:r], deck[r:]
    out = []
    while a or b:
        if a:
            out.append(a.pop(0))
        if b:
            out.append(b.pop(0))
    deck[:] = out
    if len(deck) > 1 and out[0] == state.get("last"):
        deck[0], deck[1] = deck[1], deck[0]
    state["last"] = deck[0]


def rc4_like(deck, p, state):
    """RC4-style state update. Included as a mechanism that does NOT protect
    the top card, to show what constraint 3 costs a candidate."""
    state["i"] = (state["i"] + 1) % N
    state["j"] = (state["j"] + deck[state["i"]] + p) % N
    i, j = state["i"], state["j"]
    deck[i], deck[j] = deck[j], deck[i]
    k = (deck[i] + deck[j]) % N
    deck[0], deck[k] = deck[k], deck[0]


def full_shuffle(deck, p, state):
    """Group autokey with a random generator per plaintext symbol.

    The strong-mixing limit of the community's model, and the honest one: the
    deck is permuted by sigma_p, a permutation drawn once per plaintext symbol
    and reused whenever that symbol recurs, constrained to sigma_p(0) != 0 so
    the top card always moves. Being a genuine function of the plaintext, it is
    an actual cipher -- an earlier version reshuffled at random and ignored p,
    which made it a keystream generator with no message in it.
    """
    gens = state.get("gens")
    if gens is None:
        rng = state["rng"]
        gens = {}
        state["gens"] = gens
    if p not in gens:
        rng = state["rng"]
        while True:
            sigma = list(range(N))
            rng.shuffle(sigma)
            if sigma[0] != 0:
                break
        gens[p] = sigma
    sigma = gens[p]
    deck[:] = [deck[sigma[i]] for i in range(N)]


MECHANISMS = [
    ("cut by p (additive)", cut_by_p),
    ("cut by prev output (ct-driven)", cut_by_c),
    ("cut by p + prev output", cut_by_p_and_c),
    ("insert top at depth p", insert_top_at_depth),
    ("swap top with depth p", swap_top_with_depth),
    ("base rotate + swap", base_rotate_then_swap),
    ("riffle, cut at p", riffle_cut_by_p),
    ("RC4-like state", rc4_like),
    ("group autokey, random gens", full_shuffle),
]


# --- fingerprint --------------------------------------------------------

def gap_profile(seqs, maxgap=MAXGAP):
    """Observed/expected repeat rate at each gap. 1.0 == chance."""
    out = []
    for k in range(1, maxgap + 1):
        hit = sum(1 for v in seqs for i in range(len(v) - k) if v[i] == v[i + k])
        pairs = sum(max(0, len(v) - k) for v in seqs)
        out.append(hit / (pairs / N) if pairs else float("nan"))
    return out


def run(mech, lengths, rng, alphabet_size=30):
    """Encrypt language-like plaintext of the given lengths under `mech`."""
    segs = []
    for n in lengths:
        if n < 2:
            continue
        deck = list(range(N))
        rng.shuffle(deck)
        state = {"i": 0, "j": 0, "rng": rng, "base": rng.randrange(1, N),
                 "last": None}
        out = []
        for p in language_like(rng, n, alphabet_size=alphabet_size):
            mech(deck, p, state)
            out.append(deck[0])
        segs.append(out)
    return segs


def summarise(mech, lengths, seeds=SEEDS, alphabet_size=30):
    """Mean gap profile, adjacent-repeat count and IoC across seeds."""
    profs, adj, iocs = [], [], []
    for s in range(seeds):
        rng = random.Random(1000 + s)
        segs = run(mech, lengths, rng, alphabet_size)
        profs.append(gap_profile(segs))
        adj.append(sum(1 for v in segs for i in range(1, len(v))
                       if v[i] == v[i - 1]))
        iocs.append(ioc([x for v in segs for x in v]))
    mean = [sum(p[k] for p in profs) / seeds for k in range(MAXGAP)]
    return mean, sum(adj) / seeds, sum(iocs) / seeds


def bootstrap_observed(segs, trials=2000, seed=5):
    """Resample segments with replacement for a CI on the observed profile."""
    rng = random.Random(seed)
    draws = []
    for _ in range(trials):
        pick = [segs[rng.randrange(len(segs))] for _ in range(len(segs))]
        draws.append(gap_profile(pick))
    lo, hi = [], []
    for k in range(MAXGAP):
        col = sorted(d[k] for d in draws)
        lo.append(col[int(0.025 * trials)])
        hi.append(col[int(0.975 * trials)])
    return lo, hi


def main():
    segs = segments(load())
    lengths = [len(s) for s in segs]
    obs = gap_profile(segs)
    lo, hi = bootstrap_observed(segs)

    head = "  ".join(f"g{k}" for k in range(1, MAXGAP + 1))
    print(f"Repeat-gap profile, observed/expected (1.00 = chance). "
          f"{len(segs)} deduped segments.\n")
    print(f"{'mechanism':<32} {head}      adj    IoC")
    print(f"{'OBSERVED':<32} " + "  ".join(f"{v:.2f}" for v in obs)
          + f"     {0:>4}   {ioc([x for s in segs for x in s]):.2f}")
    print(f"{'  95% CI low':<32} " + "  ".join(f"{v:.2f}" for v in lo))
    print(f"{'  95% CI high':<32} " + "  ".join(f"{v:.2f}" for v in hi))
    print()

    for label, mech in MECHANISMS:
        prof, adj, ic = summarise(mech, lengths)
        flags = "".join("*" if not (lo[k] <= prof[k] <= hi[k]) else " "
                        for k in range(MAXGAP))
        print(f"{label:<32} " + "  ".join(f"{v:.2f}" for v in prof)
              + f"     {adj:>4.0f}   {ic:.2f}   {flags}")

    print("\n* marks a gap where the mechanism's mean profile falls outside the")
    print("  bootstrap 95% CI of the observed profile. 'adj' is adjacent")
    print("  repeats, which constraint 3 requires to be exactly 0.")

    print("\nSensitivity to plaintext alphabet size (swap top with depth p):")
    for a in (15, 30, 50, 82):
        prof, adj, ic = summarise(swap_top_with_depth, lengths,
                                  seeds=15, alphabet_size=a)
        print(f"  |alphabet|={a:>3}  " + "  ".join(f"{v:.2f}" for v in prof))


if __name__ == "__main__":
    main()
