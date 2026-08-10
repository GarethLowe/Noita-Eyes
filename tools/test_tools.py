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
from eyes import N, ORDER, load, ioc  # noqa: E402
import dedup  # noqa: E402
from dedup import segments, shared_mask  # noqa: E402
from synth import (corpus, decrypt_autokey, decrypt_progressive,  # noqa: E402
                   decrypt_vigenere, encrypt_autokey, encrypt_progressive,
                   encrypt_vigenere, language_like)
from h1_ciphertext_autokey import (bigram_rate, diff_segments,  # noqa: E402
                                   ioc_nonzero, shuffle_no_repeat)
from shift_invariant_ngrams import classes, stats  # noqa: E402
from gap_spectrum import count_chains, count_gap  # noqa: E402
from deck_models import MECHANISMS, full_shuffle, run, summarise  # noqa: E402
from resync_analysis import (agreement_runs, deck_pair,  # noqa: E402
                             divergent_pair, reconvergences)
from h2_plaintext_autokey import derive, parity_iocs  # noqa: E402


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


class TestGapSpectrum(unittest.TestCase):
    def test_count_gap_matches_a_hand_worked_case(self):
        self.assertEqual(count_gap([[1, 2, 3, 1, 5]], 3), 1)
        self.assertEqual(count_gap([[1, 2, 3, 1, 5]], 2), 0)
        self.assertEqual(count_gap([[7, 7, 7]], 1), 2)

    def test_gaps_do_not_span_segments(self):
        self.assertEqual(count_gap([[1, 2], [1, 2]], 2), 0)

    def test_chains_detect_a_planted_state_recurrence(self):
        """A repeated 4-block makes every coincidence chain into the next."""
        block = [10, 20, 30, 40]
        seq = block + block + block
        self.assertEqual(count_chains([seq], 4), count_gap([seq], 4) - 1)

    def test_no_chains_when_coincidences_are_isolated(self):
        self.assertEqual(count_chains([[1, 9, 9, 9, 1, 8, 8, 8, 2]], 4), 0)

    def test_observed_gap4_excess_is_present_and_dedup_survives(self):
        segs = segments(load())
        obs = count_gap(segs, 4)
        expected = sum(max(0, len(s) - 4) for s in segs) / N
        self.assertGreater(obs, 1.7 * expected)
        self.assertEqual(count_chains(segs, 4), 0)


class TestDeckModels(unittest.TestCase):
    def test_top_protecting_mechanisms_produce_no_adjacent_repeats(self):
        """The community's explanation of constraint 3, verified per mechanism."""
        for label, mech in MECHANISMS:
            if label in ("base rotate + swap", "RC4-like state"):
                continue  # these deliberately do not protect the top card
            segs = run(mech, [120, 90], random.Random(4))
            adj = sum(1 for v in segs for i in range(1, len(v))
                      if v[i] == v[i - 1])
            self.assertEqual(adj, 0, label)

    def test_mechanisms_that_ignore_the_top_card_break_constraint_3(self):
        for label, mech in MECHANISMS:
            if label not in ("base rotate + swap", "RC4-like state"):
                continue
            segs = run(mech, [400, 400], random.Random(4))
            adj = sum(1 for v in segs for i in range(1, len(v))
                      if v[i] == v[i - 1])
            self.assertGreater(adj, 0, label)

    def test_deck_output_is_always_a_valid_symbol(self):
        for _, mech in MECHANISMS:
            for v in run(mech, [60], random.Random(6)):
                self.assertTrue(all(0 <= x < N for x in v))

    def test_perfect_mixing_limit_has_a_flat_profile_above_gap_1(self):
        prof, adj, _ = summarise(full_shuffle, [200, 200], seeds=8)
        self.assertEqual(adj, 0)
        self.assertEqual(prof[0], 0.0)
        for k in range(1, 8):
            self.assertAlmostEqual(prof[k], 1.0, delta=0.35)

    def test_no_mechanism_reproduces_the_gap4_excess(self):
        """The load-bearing negative: this is the H4 verdict in one assertion.

        If some mechanism ever does clear this bar, the test fails loudly and
        the notebook's verdict has to be revisited -- which is the point.
        """
        segs = segments(load())
        lengths = [len(s) for s in segs]
        obs_ratio = count_gap(segs, 4) / (
            sum(max(0, len(s) - 4) for s in segs) / N)
        self.assertGreater(obs_ratio, 1.7)
        for label, mech in MECHANISMS:
            prof, _, _ = summarise(mech, lengths, seeds=8)
            self.assertFalse(1.7 <= prof[3] <= 2.3 and
                             all(abs(prof[k] - 1.0) < 0.4 for k in (4, 5, 6, 7)),
                             f"{label} now matches the observed profile")


class TestResync(unittest.TestCase):
    """The state-size argument, which is now the project's main structural claim."""

    def test_agreement_runs_skip_position_zero_and_respect_min_run(self):
        a = [1, 5, 5, 5, 9, 2]
        b = [7, 5, 5, 5, 8, 3]
        self.assertEqual(agreement_runs(a, b, min_run=3), [(1, 3, 3)])
        self.assertEqual(agreement_runs(a, b, min_run=4), [])

    def test_reconvergences_exclude_the_shared_header(self):
        a = [0, 1, 2, 3, 9, 9, 7, 7, 7]
        b = [5, 1, 2, 3, 4, 4, 7, 7, 7]
        self.assertEqual(agreement_runs(a, b), [(1, 3, 3), (6, 8, 3)])
        self.assertEqual(reconvergences(a, b), [(6, 8, 3)])

    def test_the_observed_reconvergences_are_present(self):
        msgs = load()
        e1w1 = reconvergences(msgs["East 1"], msgs["West 1"])
        self.assertEqual([(s, e, n) for s, e, n in e1w1],
                         [(29, 32, 4), (37, 49, 13)])
        self.assertEqual(len(reconvergences(msgs["East 4"], msgs["East 5"])), 3)

    def test_plaintext_chaining_reconverges_but_ciphertext_chaining_does_not(self):
        """The load-bearing discriminator behind the H2 pivot."""
        rng = random.Random(3)
        pa, pb = divergent_pair(rng)
        pt = [[(p[i] + p[i - 1]) % N for i in range(1, len(p))] for p in (pa, pb)]
        self.assertTrue(reconvergences(*pt),
                        "plaintext chaining must rejoin after divergence")

        ct = []
        for p in (pa, pb):
            c = [0]
            for v in p:
                c.append((v + c[-1]) % N)
            ct.append(c)
        self.assertEqual(reconvergences(*ct), [],
                         "ciphertext chaining must not rejoin by itself")

    def test_deck_cipher_cannot_reconverge_from_a_shared_initial_deck(self):
        rng = random.Random(3)
        pa, pb = divergent_pair(rng)
        ca, cb = deck_pair(full_shuffle, [pa, pb], seed=11)
        self.assertEqual(reconvergences(ca, cb), [])

    def test_deck_pair_reproduces_shared_headers(self):
        """Identical plaintext prefix from one initial deck must match."""
        rng = random.Random(3)
        pa, pb = divergent_pair(rng)
        ca, cb = deck_pair(full_shuffle, [pa, pb], seed=11)
        self.assertEqual(ca[:25], cb[:25])


class TestH2(unittest.TestCase):
    def test_derive_inverts_the_plaintext_autokey(self):
        rng = random.Random(5)
        p = language_like(rng, 80, alphabet_size=45)
        c = [p[0]] + [(p[i] + p[i - 1]) % N for i in range(1, len(p))]
        self.assertEqual(derive(c, p[0]), p)

    def test_parity_iocs_do_not_depend_on_the_p0_guess(self):
        c = load()["East 1"]
        base = parity_iocs(c)
        for guess in (0, 7, 40, 82):
            p = derive(c, guess)
            self.assertAlmostEqual(ioc(p[0::2]), base[0], places=9)
            self.assertAlmostEqual(ioc(p[1::2]), base[1], places=9)

    def test_h2_battery_separates_control_from_real_data(self):
        rng = random.Random(0)
        ctrl = language_like(rng, 1000, alphabet_size=45)
        cc = [ctrl[0]] + [(ctrl[i] + ctrl[i - 1]) % N
                          for i in range(1, len(ctrl))]
        self.assertGreater(min(parity_iocs(cc)), 2.0)
        for k in ORDER:
            self.assertLess(max(parity_iocs(load()[k])), 1.5, k)


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
