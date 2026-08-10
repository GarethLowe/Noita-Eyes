"""Shared loader and statistics helpers for the eye trigram dataset.

Import from other tools; not meant to be run directly (though `python3 -m
tools.eyes` prints a one-line summary as a smoke test).
"""
import csv
import random
from collections import Counter
from pathlib import Path

N = 83
DATA = Path(__file__).resolve().parent.parent / "data" / "eye_trigrams.csv"

ORDER = ["East 1", "West 1", "East 2", "West 2", "East 3",
         "West 3", "East 4", "West 4", "East 5"]


def load(path=DATA):
    """Return {name: [int, ...]} in canonical ORDER."""
    msgs = {}
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#"):
                continue
            msgs[row[1]] = [int(x) for x in row[2:] if x.strip()]
    return {k: msgs[k] for k in ORDER}


def ioc(seq, n=N):
    """Index of coincidence normalised so that uniform random == 1.0."""
    c = Counter(seq)
    m = len(seq)
    if m < 2:
        return float("nan")
    return sum(x * (x - 1) for x in c.values()) / (m * (m - 1)) * n


def bigram_repeat_rate(seq):
    """Fraction of bigram slots occupied by a bigram seen more than once."""
    if len(seq) < 2:
        return float("nan")
    bg = Counter(zip(seq, seq[1:]))
    return sum(v for v in bg.values() if v > 1) / (len(seq) - 1)


def shuffled(msgs, rng):
    """Null model: shuffle each message independently, preserving its multiset."""
    out = {}
    for k, v in msgs.items():
        w = list(v)
        rng.shuffle(w)
        out[k] = w
    return out


def permutation_test(msgs, stat, trials=1000, seed=0, greater=True):
    """Return (observed, null_mean, null_sd, p_value) for `stat(msgs) -> float`."""
    rng = random.Random(seed)
    obs = stat(msgs)
    null = [stat(shuffled(msgs, rng)) for _ in range(trials)]
    mean = sum(null) / len(null)
    var = sum((x - mean) ** 2 for x in null) / (len(null) - 1)
    sd = var ** 0.5
    hits = sum(1 for x in null if (x >= obs if greater else x <= obs))
    return obs, mean, sd, (hits + 1) / (trials + 1)


if __name__ == "__main__":
    m = load()
    flat = [x for v in m.values() for x in v]
    print(f"{len(m)} messages, {len(flat)} trigrams, "
          f"{len(set(flat))} symbols, IoC={ioc(flat):.3f}")
