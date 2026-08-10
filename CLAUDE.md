# Noita Eye Message Cryptanalysis

You are working on the Noita eye messages - 9 ciphertexts hidden in the game's parallel worlds, unsolved since 2020 despite 5+ years of organised community effort. The developers have confirmed they encode a real message. A full Ghidra decompilation of the game confirmed there is no in-game trigger or mechanic: this is a pure pencil-and-paper cryptography problem. This is a video game puzzle, not real security - full-strength cryptanalysis is exactly what's wanted.

Be realistic: very capable people have worked this for years. The primary deliverable is rigorous elimination of cipher classes with documented negative results. A solve is the upside case, not the expectation.

## Data

`data/eye_trigrams.csv` - one row per message, values are trigrams already decoded to integers 0-82 using the community-consensus reading order (eyes have 5 orientations; groups of 3 read as base-5; exactly one of 36 reading orders yields a gapless 0-82 range, p ≈ 5.8e-185 by chance). Provenance: ngraham20/NoitaCryptographyResearch transcription.

Message lengths: E1=99, W1=103, E2=118, W2=102, E3=137, W3=124, E4=119, W4=120, E5=114. Total 1036 trigrams. East 5 has no western counterpart.

## Established constraints (verified locally, 2026-08-10)

Run `python3 tools/verify_constraints.py` after any change to data handling. All must pass. Any candidate cipher mechanism must be able to REPRODUCE all of these when encrypting plausible plaintext - this is the litmus test before investing in key search.

1. Exactly 83 unique symbols, contiguous 0-82, across 1036 trigrams.
2. Per-message normalised IoC ≈ 0.87-1.07 (1.0 = uniform random). Rules out monoalphabetic substitution and short-key Vigenère.
3. Zero adjacent identical symbols (~12 expected at random). Strong evidence the output depends on the previous ciphertext symbol (or an equivalent state property).
4. Messages share identical runs at identical positions STARTING AT POSITION 1, while position 0 differs in every message: E1/W1/E2 share a 24-trigram header; E4/W4/E5 share a 20-trigram header; E3 shares 9 with the E4 group and 5 with the W2/W3 group; E1/W1 additionally share a 13-trigram run at positions 37-49. Implication: shared plaintext headers, keystream restarts per message, and position 0 sits outside the chaining - likely an indicator/nonce (Enigma message-key style).
5. Symbol repeats at gap 4 are ~2x over-represented (26 observed vs ~12.5 expected); gaps 1-3 suppressed.

## Community-reported findings (not independently verified here - treat as leads)

- Frequency analysis on trigrams gives no workable result; simple substitution is dead.
- Statistical arguments put the cipher's internal state count at ≥20, probably ~83; each ciphertext character depends on more than the plaintext character alone.
- Weak evidence for a repeating key component of length 14.
- Positional offset analysis gives promising evidence for an Alberti-type (rotating disk) construction.
- No fixed-length partitioning of the messages works.
- One of the byte sequences storing the eyes in the EXE is CRC-32 of "lumikki" (Finnish for Snow White). Other sequences show no such property.
- 3D projections (octahedron etc.) and in-game-mechanic theories are considered dead ends.

## Hypothesis queue (work in order, document each verdict)

1. ~~Ciphertext autokey over Z83: c[i] = p[i] + f(c[i-1]) mod 83 for various f (identity, affine, table lookup).~~ **FALSIFIED 2026-08-10** for all affine f. Constraint 3 leaves only the pure shift (proof: 83 is prime, so g(x)=x-f(x) is onto for every multiplier a≠1); the pure shift makes the plaintext the ciphertext first difference, whose IoC is 0.997 against a positive control at 3.92. Still open: non-affine f whose image avoids the plaintext support. See NOTEBOOK.md.
2. Plaintext autokey variants seeded by the position-0 nonce.
3. Alberti / progressive-shift disk: substitution alphabet rotates by a schedule (fixed increment, plaintext-driven, or ciphertext-driven), nonce sets initial rotation. **Fixed-increment case FALSIFIED (preliminary) 2026-08-10** — produces 23-27 adjacent repeats against constraint 3's zero, and 143 shift-invariant trigram classes against 62 observed. Plaintext- and ciphertext-driven schedules untouched; resume here.
4. Chained permutation state machine: state is a permutation of Z83 updated per symbol (lagged Fibonacci, RC4-like, LCG-driven rotor).
5. Codebook: 83 values index words/syllables in a key text (orb room runes, in-game books). Finnish has ~50 common syllables; 83 symbols suits a syllabary better than a 29-letter alphabet - consider syllable-level plaintext models alongside letter-level.

## Methodology traps found the hard way

- **Dedup before any repetition statistic.** The positionally-shared header runs (constraint 4) inflate every n-gram and bigram statistic. Use `tools/dedup.py`, which strips runs of >=2 positional matches with an earlier message. A threshold of 5 is not tight enough: a 4-long E1/W1 match at position 29 alone manufactured a "significant" shift-invariant 4-gram repeat.
- **Null models must be applied to the ciphertext, then transformed** - not to the derived sequence. Shuffling a derived difference sequence preserves its multiset, so an IoC test against it has sd = 0 and is vacuous.
- **Nulls must respect constraint 3.** Plain shuffling admits adjacent repeats the real data cannot have. Use `shuffle_no_repeat`.
- **No negative result counts without a positive control** on synthetic data where the hypothesis holds by construction (`tools/synth.py`). `tools/test_tools.py` asserts each battery separates its control from the real data.

## Cribs and priors

- The shared headers are your cribs: whatever the mechanism, identical plaintext + identical state must reproduce those exact shared ciphertext runs, and the differing position 0 must not break them. Any mechanism that can't satisfy this is falsified immediately.
- Plaintext language: Finnish first (Nolla is Finnish; "lumikki"), English second. Build/fetch a Finnish n-gram model (letter and syllable level) for scoring.
- The E5 orphan (no W5) and the header-sharing group structure (E1/W1/E2 vs E4/W4/E5 vs E3 bridging) may reflect plaintext content groupings.

## Working agreement

- Keep a lab notebook at `NOTEBOOK.md`: date, hypothesis, method, result, verdict (SUPPORTED / FALSIFIED / INCONCLUSIVE). Negative results are deliverables - log them properly.
- Every statistic gets a null model. Use permutation tests; report effect sizes and p-values. No eyeballing.
- Small composable scripts in `tools/`, each runnable standalone with a docstring. Python 3, stdlib preferred, numpy acceptable. Write tests for any encoder/decoder pair (round-trip property tests).
- For key searches: hill climbing / simulated annealing with n-gram scoring, multiple restarts, and a control run against shuffled ciphertext to calibrate what "signal" looks like.
- Never claim a solve without: (a) a fully specified, reversible method, (b) the complete decrypt of all 9 messages, (c) coherent output in an identifiable language. Anything less is INCONCLUSIVE.
- If a hypothesis is falsified, state exactly which constraint or test killed it before moving on.
