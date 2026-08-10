"""Tests for the analysis tooling. Run: python3 tools/test_tools.py

Covers the round-trip property for every encoder/decoder pair, the dedup
masking, and -- most importantly -- that each test battery actually fires on a
positive control. A battery with no power turns every hypothesis into a false
negative, so that check is the one guarding the project's conclusions.
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N, load, ioc  # noqa: E402
import dedup  # noqa: E402
from dedup import segments, shared_mask  # noqa: E402
from synth import (corpus, decrypt_autokey, decrypt_progressive,  # noqa: E402
                   decrypt_vigenere, encrypt_autokey, encrypt_progressive,
                   encrypt_vigenere, language_like)
from h1_ciphertext_autokey import (bigram_rate, diff_segments,  # noqa: E402
                                   ioc_nonzero, shuffle_no_repeat)
from shift_invariant_ngrams import classes, stats  # noqa: E402


class TestRoundTrip(unittest.TestCase):
    """Encrypt-then-decrypt must be the identity for every cipher."""

    def setUp(self):
        self.rng = random.Random(0)

    def test_autokey(self):
        for _ in range(50):
            p = language_like(self.rng, self.rng.randint(2, 120))
            nonce = self.rng.randrange(N)
            c = encrypt_autokey(p, nonce)
            self.assertEqual(len(c), len(p) + 1)
            self.assertEqual(c[0], nonce)
            self.assertEqual(decrypt_autokey(c), p)

    def test_autokey_gives_no_adjacent_repeats(self):
        """The defining link between H1 and constraint 3."""
        for _ in range(50):
            c = encrypt_autokey(language_like(self.rng, 200),
                                self.rng.randrange(N))
            self.assertEqual(
                sum(1 for i in range(1, len(c)) if c[i] == c[i - 1]), 0)

    def test_progressive(self):
        for _ in range(50):
            p = language_like(self.rng, self.rng.randint(2, 120))
            start, step = self.rng.randrange(N), self.rng.randrange(N)
            self.assertEqual(
                decrypt_progressive(encrypt_progressive(p, start, step),
                                    start, step), p)

    def test_vigenere(self):
        for _ in range(50):
            p = language_like(self.rng, self.rng.randint(2, 120))
            key = [self.rng.randrange(N)
                   for _ in range(self.rng.randint(1, 20))]
            self.assertEqual(decrypt_vigenere(encrypt_vigenere(p, key), key), p)

    def test_outputs_in_range(self):
        p = language_like(self.rng, 300)
        for c in (encrypt_autokey(p, 5), encrypt_progressive(p, 5, 3),
                  encrypt_vigenere(p, [1, 2, 3])):
            self.assertTrue(all(0 <= x < N for x in c))


class TestDedup(unittest.TestCase):
    def test_removes_shared_header_from_later_message_only(self):
        msgs = {"East 1": [1, 2, 3, 4, 9], "West 1": [7, 2, 3, 4, 8]}
        mask = shared_mask(msgs, min_run=2)
        self.assertEqual(mask["East 1"], [False] * 5)
        self.assertEqual(mask["West 1"], [False, True, True, True, False])

    def test_short_matches_below_threshold_survive(self):
        msgs = {"East 1": [1, 2, 9], "West 1": [5, 2, 8]}
        self.assertEqual(shared_mask(msgs, min_run=2)["West 1"],
                         [False, False, False])

    def test_segments_do_not_span_a_cut(self):
        msgs = {"East 1": [1, 2, 3, 4, 5], "West 1": [9, 2, 3, 8, 7]}
        self.assertEqual(segments(msgs, min_run=2),
                         [[1, 2, 3, 4, 5], [9], [8, 7]])

    def test_real_corpus_drops_the_known_shared_runs(self):
        msgs = load()
        kept = sum(len(s) for s in segments(msgs))
        total = sum(len(v) for v in msgs.values())
        # The 24- and 20-trigram headers and the E1/W1 mid-run, at minimum.
        self.assertLess(kept, total)
        self.assertGreater(kept, total * 0.8)

    def test_no_cross_message_positional_duplicates_remain(self):
        """After dedup no bigram may appear at the same index in two messages."""
        msgs = load()
        mask = shared_mask(msgs)
        names = list(msgs)
        for j, kj in enumerate(names):
            for ki in names[:j]:
                for i in range(min(len(msgs[kj]), len(msgs[ki])) - 1):
                    if (msgs[kj][i] == msgs[ki][i]
                            and msgs[kj][i + 1] == msgs[ki][i + 1]):
                        self.assertTrue(mask[kj][i] and mask[kj][i + 1],
                                        f"{kj} vs {ki} at {i}")


class TestNullModel(unittest.TestCase):
    def test_shuffle_preserves_multiset_and_kills_repeats(self):
        rng = random.Random(3)
        for s in segments(load()):
            if len(s) < 2:
                continue
            w = shuffle_no_repeat(s, rng)
            self.assertEqual(sorted(w), sorted(s))
            self.assertEqual(
                sum(1 for i in range(1, len(w)) if w[i] == w[i - 1]), 0)

    def test_shuffle_handles_the_impossible_case_without_hanging(self):
        """A multiset that cannot avoid repeats must still return, not loop."""
        w = shuffle_no_repeat([4, 4, 4, 1], random.Random(0), tries=3)
        self.assertEqual(sorted(w), [1, 4, 4, 4])


class TestStatistics(unittest.TestCase):
    def test_ioc_of_uniform_is_about_one(self):
        rng = random.Random(1)
        seq = [rng.randrange(N) for _ in range(200000)]
        self.assertAlmostEqual(ioc(seq), 1.0, places=1)

    def test_ioc_of_constant_sequence_is_alphabet_size(self):
        self.assertAlmostEqual(ioc([7] * 100), float(N), places=6)

    def test_diff_segments_inverts_the_autokey(self):
        rng = random.Random(2)
        p = language_like(rng, 60)
        c = encrypt_autokey(p, rng.randrange(N))
        self.assertEqual(diff_segments([c])[0], p)

    def test_shift_classes_are_invariant_to_a_constant_shift(self):
        rng = random.Random(4)
        s = [rng.randrange(N) for _ in range(50)]
        for k in (0, 1, 40, 82):
            shifted = [(x + k) % N for x in s]
            self.assertEqual(classes([s], 4), classes([shifted], 4))

    def test_shift_classes_detect_a_planted_shifted_repeat(self):
        base = [3, 40, 11, 70, 25, 8, 61, 2]
        planted = base + [(x + 17) % N for x in base]
        self.assertGreaterEqual(stats([planted], 5)[0], 1)

    def test_bigram_rate_bounds(self):
        self.assertEqual(bigram_rate([[1, 2, 1, 2, 1]]), 1.0)
        self.assertEqual(bigram_rate([[1, 2, 3, 4]]), 0.0)


class TestBatteriesHavePower(unittest.TestCase):
    """The batteries must separate a true hypothesis from the real data.

    These are the load-bearing tests. If a battery cannot tell H1-encrypted
    language from the eye messages, then 'H1 falsified' means nothing.
    """

    def setUp(self):
        self.segs = segments(load())
        self.lengths = [len(s) for s in self.segs]

    def test_ioc_battery_separates_h1_control_from_real_data(self):
        ctrl = corpus("autokey", self.lengths, seed=7)
        self.assertGreater(ioc_nonzero(diff_segments(ctrl)), 2.5)
        self.assertLess(ioc_nonzero(diff_segments(self.segs)), 1.2)

    def test_bigram_battery_separates_h1_control_from_real_data(self):
        ctrl = corpus("autokey", self.lengths, seed=7)
        self.assertGreater(bigram_rate(diff_segments(ctrl)), 0.5)
        self.assertLess(bigram_rate(diff_segments(self.segs)), 0.25)

    def test_shift_invariant_battery_fires_on_a_progressive_cipher(self):
        ctrl = corpus("progressive", self.lengths, seed=23, step=1)
        self.assertGreater(stats(ctrl, 3)[0], 2 * stats(self.segs, 3)[0] - 40)
        self.assertGreater(stats(ctrl, 3)[0], 100)

    def test_additive_key_controls_violate_constraint_3(self):
        """Every keystream cipher without ciphertext feedback shows repeats."""
        for kind in ("progressive", "vigenere"):
            ctrl = corpus(kind, self.lengths, seed=23)
            adj = sum(1 for s in ctrl for i in range(1, len(s))
                      if s[i] == s[i - 1])
            self.assertGreater(adj, 0, kind)


class TestDataIntegrity(unittest.TestCase):
    def test_dataset_matches_the_established_constraints(self):
        msgs = load()
        flat = [x for v in msgs.values() for x in v]
        self.assertEqual(len(msgs), 9)
        self.assertEqual(len(flat), 1036)
        self.assertEqual(sorted(set(flat)), list(range(83)))
        self.assertEqual(
            sum(1 for v in msgs.values()
                for i in range(1, len(v)) if v[i] == v[i - 1]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
