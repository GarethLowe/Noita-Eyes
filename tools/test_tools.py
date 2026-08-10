"""Tests for the analysis tooling. Run: python3 tools/test_tools.py

Covers the round-trip property for every encoder/decoder pair, the dedup
masking, and -- most importantly -- that each test battery actually fires on a
positive control. A battery with no power turns every hypothesis into a false
negative, so that check is the one guarding the project's conclusions.
"""
import random
import sys
import unittest
from itertools import permutations
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
from reading_order import (adjacent, columnar, digits,  # noqa: E402
                           regroup, shared_from_end, shared_from_start)
from finnish import load_runs, load_table, normalise, syllabify  # noqa: E402
from h6_hybrid import (dec_ct_p4, dec_pt_p4, enc_ct_p4,  # noqa: E402
                       enc_pt_p4, enc_pt_p4_fix, enc_tab_ptk)
from h6_hybrid import divergent_pair as h6_divergent_pair  # noqa: E402
from eye_level import eye_stream, norm_ioc, pair_values  # noqa: E402
from abstract_encodings import (compass_schemes, control_ring,  # noqa: E402
                                cumsum_stream, walk_radius)


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


class TestReadingOrder(unittest.TestCase):
    def test_digits_invert_every_trigram(self):
        for v in range(N):
            a, b, c = digits(v)
            self.assertEqual(25 * a + 5 * b + c, v)
            self.assertTrue(all(0 <= d < 5 for d in (a, b, c)))

    def test_offset_zero_roundtrips_to_the_original_messages(self):
        msgs = load()
        self.assertEqual(regroup(msgs, (0, 1, 2), 0), [msgs[k] for k in ORDER])

    def test_only_offset_zero_is_repeat_free(self):
        """The grouping check: shifted re-cuts land at chance."""
        msgs = load()
        for order in ((0, 1, 2), (2, 1, 0), (1, 0, 2)):
            self.assertEqual(adjacent(regroup(msgs, order, 0)), 0, str(order))
            for off in (1, 2):
                self.assertGreater(adjacent(regroup(msgs, order, off)), 0,
                                   f"{order} offset {off}")

    def test_digit_permutation_cannot_change_adjacency(self):
        """Sanity: permuting digits is a bijection, so repeats are invariant."""
        msgs = load()
        for order in permutations(range(3)):
            self.assertEqual(adjacent(regroup(msgs, order, 0)), 0)

    def test_shared_material_is_at_the_start_not_the_end(self):
        msgs = load()
        s = sum(shared_from_start(msgs[a], msgs[b])
                for i, a in enumerate(ORDER) for b in ORDER[i + 1:])
        e = sum(shared_from_end(msgs[a], msgs[b])
                for i, a in enumerate(ORDER) for b in ORDER[i + 1:])
        self.assertGreater(s, 200)
        self.assertEqual(e, 0)

    def test_no_columnar_width_beats_the_linear_read(self):
        msgs = load()
        for w in range(2, 41):
            self.assertGreater(adjacent([columnar(msgs[k], w) for k in ORDER]),
                               0, f"width {w}")


class TestFinnish(unittest.TestCase):
    def test_syllabifier_on_known_words(self):
        self.assertEqual(syllabify("kalevala"), ["ka", "le", "va", "la"])
        self.assertEqual(syllabify("suomi"), ["suo", "mi"])
        self.assertEqual(syllabify("lumikki"), ["lu", "mik", "ki"])
        self.assertEqual(syllabify("nolla"), ["nol", "la"])

    def test_syllables_reassemble_into_the_word(self):
        for w in ("seitseman", "veljesta", "tuntematon", "hyvaa", "aiti"):
            self.assertEqual("".join(syllabify(w)), w)

    def test_normalise_strips_non_finnish_characters(self):
        self.assertEqual(normalise("Hei, maailma! 123").split(),
                         ["hei", "maailma"])

    def test_cached_table_is_present_and_sane(self):
        t = load_table()
        self.assertEqual(len(t["top83"]), N)
        self.assertGreater(t["coverage_top83"], 0.4)
        # Finnish very rarely repeats a syllable immediately...
        self.assertLess(t["rep_gap1"], t["rep_gap2"])
        # ...but repeats at distance 2 and 4 well above that.
        self.assertGreater(t["rep_gap2"] * 1027, 3)

    def test_finnish_distance2_repeats_are_the_h2_obstacle(self):
        """Quantifies why H2 struggles: the data demands zero, Finnish gives more."""
        t = load_table()
        self.assertGreater(t["rep_gap2"] * 1027, 5,
                           "if this drops near zero, H2's obstacle dissolves")


class TestH6(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(8)
        self.runs = load_runs()

    def test_ct_p4_round_trip(self):
        for _ in range(20):
            p = language_like(self.rng, 90)
            key = [self.rng.randrange(N) for _ in range(4)]
            self.assertEqual(dec_ct_p4(enc_ct_p4(p, key, None), key), p)

    def test_pt_p4_round_trip(self):
        for _ in range(20):
            p = language_like(self.rng, 90)
            key = [self.rng.randrange(N) for _ in range(4)]
            self.assertEqual(dec_pt_p4(enc_pt_p4(p, key, None), key), p)

    def test_fix_variant_never_repeats_adjacent(self):
        for _ in range(20):
            p = [self.rng.randrange(N) for _ in range(400)]
            key = [self.rng.randrange(N) for _ in range(4)]
            c = enc_pt_p4_fix(p, key, None)
            self.assertEqual(
                sum(1 for i in range(1, len(c)) if c[i] == c[i - 1]), 0)

    def test_pt_chained_hybrids_reconverge_and_ct_does_not(self):
        rng = random.Random(4)
        pa, pb = h6_divergent_pair(rng, self.runs)
        key = [rng.randrange(N) for _ in range(4)]
        self.assertGreaterEqual(
            len(reconvergences(enc_pt_p4(pa, key, None),
                               enc_pt_p4(pb, key, None))), 1)
        self.assertEqual(
            reconvergences(enc_ct_p4(pa, key, None),
                           enc_ct_p4(pb, key, None)), [])

    def test_table_variant_is_statistically_identical_to_untabled(self):
        """A fixed bijection cannot change repeat counts at any gap."""
        rng = random.Random(5)
        p = [rng.randrange(N) for _ in range(500)]
        key = [rng.randrange(N) for _ in range(4)]
        pi = list(range(N))
        rng.shuffle(pi)
        a, b = enc_pt_p4(p, key, pi), enc_tab_ptk(p, key, pi)
        for k in (1, 2, 3, 4, 5):
            ra = sum(1 for i in range(k, len(a)) if a[i] == a[i - k])
            rb = sum(1 for i in range(k, len(b)) if b[i] == b[i - k])
            self.assertEqual(ra, rb, f"gap {k}")


class TestEyeLevel(unittest.TestCase):
    def test_eye_stream_is_three_eyes_per_trigram(self):
        msgs = load()
        for k in ORDER:
            es = eye_stream(msgs[k])
            self.assertEqual(len(es), 3 * len(msgs[k]))
            self.assertTrue(all(0 <= x < 5 for x in es))

    def test_slot0_never_shows_orientation_4(self):
        """The base-5 numeral signature, asserted on the real data."""
        msgs = load()
        for k in ORDER:
            es = eye_stream(msgs[k])
            self.assertTrue(all(es[i] != 4 for i in range(0, len(es), 3)))

    def test_pair_values_cover_0_to_24(self):
        pv = pair_values([0, 0, 4, 4, 2, 3], 0)
        self.assertEqual(pv, [0, 24, 13])

    def test_grid_alphabet_control_fires(self):
        """Power check: real Finnish letters through a 5x5 grid must show a
        high IoC, or the flat observed value would prove nothing."""
        t = load_table()
        letters = sorted(t["letter_counts"], key=t["letter_counts"].get,
                         reverse=True)[:25]
        grid = {ch: i for i, ch in enumerate(letters)}
        text = normalise(
            "olipa kerran seitseman veljesta jotka asuivat metsassa "
            "ja heidan aitinsa oli kuollut ja isansa myos")
        vals = [grid[ch] for ch in text if ch in grid]
        self.assertGreater(norm_ioc(vals, 25), 1.5)

    def test_observed_pair_ioc_is_flat(self):
        segs = segments(load())
        flat = [x for s in segs for x in pair_values(eye_stream(s), 0)]
        self.assertLess(norm_ioc(flat, 25), 1.25)


class TestAbstractEncodings(unittest.TestCase):
    def test_cumsum_inverts_difference_encoding(self):
        """diff then cumsum is the identity, so the class-B battery reads the
        true plaintext when the hypothesis holds."""
        rng = random.Random(2)
        p = [rng.randrange(N) for _ in range(200)]
        prev, enc = 0, []
        for v in p:
            enc.append((v - prev) % N)
            prev = v
        self.assertEqual(cumsum_stream([enc], N)[0], p)

    def test_walk_radius_hand_worked(self):
        # four steps around a unit square: positions (1,0),(1,1),(0,1),(0,0)
        sq = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        self.assertAlmostEqual(walk_radius(sq), (0.5) ** 0.5, places=9)

    def test_straight_line_has_larger_radius_than_square(self):
        line = [(1, 0)] * 4
        sq = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        self.assertGreater(walk_radius(line), walk_radius(sq))

    def test_compass_family_has_15_distinct_schemes(self):
        schemes = compass_schemes()
        self.assertEqual(len(schemes), 15)
        for _, m in schemes:
            self.assertEqual(sorted(m.keys()), [0, 1, 2, 3, 4])
            self.assertIn((0, 0), m.values())

    def test_ring_battery_fires_on_difference_encoded_finnish(self):
        obs, mean, sd = control_ring()
        self.assertGreater((obs - mean) / sd, 10)

    def test_observed_cumsum_is_flat_at_all_rings(self):
        segs = segments(load())
        for m in (83, 29, 26, 25, 21):
            flat = [x for r in cumsum_stream(segs, m) for x in r]
            self.assertLess(norm_ioc(flat, m), 1.1, f"ring {m}")


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
