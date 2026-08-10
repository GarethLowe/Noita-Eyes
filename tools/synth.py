"""Synthetic plaintext and reference cipher implementations, for controls.

Every negative result in this project needs a matching positive control: the
same test battery run on data where the hypothesis is true by construction. If
the control does not light up, the battery has no power and the negative result
means nothing.

`language_like` is deliberately crude -- a Zipfian unigram distribution over a
30-symbol alphabet plus sticky bigram successors. It is not Finnish. It only
has to be lumpy and repetitive the way every natural language is, which is what
the batteries measure.

Every encryptor takes explicit key material and has an exact inverse; see
test_tools.py for the round-trip properties.
"""
import random

from eyes import N

ALPHABET_SIZE = 30


def language_like(rng, n, alphabet_size=ALPHABET_SIZE, stickiness=0.6):
    """Return n symbols from 1..alphabet_size with Zipfian and bigram structure.

    Symbol 0 is never emitted, so ciphertext-autokey encryption of this text
    produces zero adjacent repeats -- matching constraint 3.
    """
    alphabet = list(range(1, alphabet_size + 1))
    weights = [1.0 / (i + 1) for i in range(alphabet_size)]
    succ = {a: rng.sample(alphabet, 6) for a in alphabet}
    out = [rng.choices(alphabet, weights)[0]]
    while len(out) < n:
        out.append(rng.choice(succ[out[-1]]) if rng.random() < stickiness
                   else rng.choices(alphabet, weights)[0])
    return out[:n]


def encrypt_autokey(p, nonce):
    """H1: c[0] = nonce, c[i+1] = p[i] + c[i] mod 83. Output is len(p)+1."""
    c = [nonce % N]
    for v in p:
        c.append((v + c[-1]) % N)
    return c


def decrypt_autokey(c):
    """Inverse of encrypt_autokey; drops the nonce, returns len(c)-1 symbols."""
    return [(c[i] - c[i - 1]) % N for i in range(1, len(c))]


def encrypt_progressive(p, start, step):
    """H3 additive Alberti: c[i] = p[i] + (start + i*step) mod 83."""
    return [(v + start + i * step) % N for i, v in enumerate(p)]


def decrypt_progressive(c, start, step):
    """Inverse of encrypt_progressive."""
    return [(v - start - i * step) % N for i, v in enumerate(c)]


def encrypt_vigenere(p, key):
    """Repeating additive key."""
    return [(v + key[i % len(key)]) % N for i, v in enumerate(p)]


def decrypt_vigenere(c, key):
    """Inverse of encrypt_vigenere."""
    return [(v - key[i % len(key)]) % N for i, v in enumerate(c)]


def corpus(kind, lengths, seed, step=1, period=14):
    """Build segments of the given lengths under `kind`, with random keys.

    kind: "autokey" | "progressive" | "vigenere".
    """
    rng = random.Random(seed)
    out = []
    for n in lengths:
        if n < 2:
            continue
        if kind == "autokey":
            out.append(encrypt_autokey(language_like(rng, n - 1),
                                       rng.randrange(N)))
        elif kind == "progressive":
            out.append(encrypt_progressive(language_like(rng, n),
                                           rng.randrange(N), step))
        elif kind == "vigenere":
            key = [rng.randrange(N) for _ in range(period)]
            out.append(encrypt_vigenere(language_like(rng, n), key))
        else:
            raise ValueError(f"unknown kind {kind!r}")
    return out
