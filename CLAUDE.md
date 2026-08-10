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
4. Messages share identical runs at identical positions STARTING AT POSITION 1, while position 0 differs in every message: E1/W1/E2 share a 24-trigram header; E4/W4/E5 share a 20-trigram header; E3 shares 9 with the E4 group and 5 with the W2/W3 group; E1/W1 additionally share a 13-trigram run at positions 37-49. Implication: shared plaintext headers, a SHARED INITIAL STATE across all 9 messages (not a per-message key), and position 0 sits outside the chaining.
   **The load-bearing part is RE-CONVERGENCE, added 2026-08-10.** E1/W1 run: match 1-24, differ 25-28, MATCH 29-32, differ 33-36, MATCH 37-49. E4/E5 re-converge three times. Five re-convergence runs total, longest 13. Two diverged encryptions returning to exact agreement bounds the state hard: free for a stateless or plaintext-derived state, ~1/83 per event for a ciphertext-chained autokey, and 83^-13 = 1.1e-25 for a deck/group autokey over S83. **The cipher's state does not depend on ciphertext history.** This is the single most informative constraint in the corpus - `tools/resync_analysis.py`.
5. Symbol repeats at gap 4 are ~2x over-represented; gaps 1-3 suppressed. **CAUTION - this may be a PLAINTEXT property, not a mechanism one.** Finnish prose syllables already peak at distance 4 (1.81x chance), and a period-4 additive key passes distance-4 repeats through while scrambling all others, reproducing the observed shape (`tools/finnish_litmus.py`). Do not treat gap 4 as a mechanism fingerprint. Statistically it is solid - **reconfirmed 2026-08-10 after dedup** (the raw count of 26 double-counts shared headers): 20 observed vs a constrained-reshuffle null of 9.95 +- 3.04, z = +3.31, p = 0.0017, clearing Bonferroni over 29 gaps. All 9 messages independently exceed expectation. Gaps 5-30 are all at chance - `tools/gap_spectrum.py`. The EFFECT is solid; its INTERPRETATION is open.

## Community-reported findings (not independently verified here - treat as leads)

- Frequency analysis on trigrams gives no workable result; simple substitution is dead.
- Statistical arguments put the cipher's internal state count at ≥20, probably ~83; each ciphertext character depends on more than the plaintext character alone.
- Weak evidence for a repeating key component of length 14.
- Positional offset analysis gives promising evidence for an Alberti-type (rotating disk) construction.
- No fixed-length partitioning of the messages works.
- One of the byte sequences storing the eyes in the EXE is CRC-32 of "lumikki" (Finnish for Snow White). Other sequences show no such property.
- 3D projections (octahedron etc.) and in-game-mechanic theories are considered dead ends.
- Leading community candidate: a deck of 83 cards, each plaintext letter triggering a shuffle, top card as output = group autokey over S83. Shuffles believed to be few swaps from a shared base permutation. See hypothesis 4.
- Physical layout: rows of at most 39 eyes, every second row offset, trigrams are triangular groups spanning paired rows (so a line is 13 or 26 trigrams). Tested as a source of the gap structure and NOT supported - gap 13 is p=0.68 after correction, gap 26 nothing.

## Hypothesis queue (work in order, document each verdict)

1. ~~Ciphertext autokey over Z83: c[i] = p[i] + f(c[i-1]) mod 83 for various f (identity, affine, table lookup).~~ **FALSIFIED 2026-08-10** for all affine f. Constraint 3 leaves only the pure shift (proof: 83 is prime, so g(x)=x-f(x) is onto for every multiplier a≠1); the pure shift makes the plaintext the ciphertext first difference, whose IoC is 0.997 against a positive control at 3.92. Still open: non-affine f whose image avoids the plaintext support. See NOTEBOOK.md.
2. Plaintext-chained autokey, c[i] = F(p[i], p[i-1]). **THIS IS NOW THE LEADING HYPOTHESIS.** Sub-case F = a+b is **FALSIFIED** (the plaintext follows from the single unknown p[0]; parity IoCs are 1.10/1.09 against a control at 2.75). Sub-case **c[i] = pi(p[i] + p[i-1]) is OPEN** - it is the only tested model that reproduces the re-convergence in constraint 4, it is buildable in an afternoon (shuffle a table once, add the previous symbol, look it up), and it survives the IoC argument that killed H1 because here c[i]-c[i-1] = p[i]-p[i-2], a difference of plaintext symbols, which looks flat even when the plaintext is not. Two measured problems (2026-08-10, real Finnish prose syllabary): it gives IoC **1.44** where the messages read 1.02, failing constraint 2; and zero adjacent repeats reduces to p[i] != p[i-2] always, where an 83-syllable Finnish alphabet yields ~26 per 1027. It keeps the lead only because nothing else explains re-convergence. Next step is hill-climbing over S83 with a Finnish n-gram score and a shuffled-ciphertext control - but fix the IoC problem first, or the search is chasing a model that cannot produce the data.
6. Period-4 repeating key component. **CRUNCHED 2026-08-10, INCONCLUSIVE-LEANING-NEGATIVE** (`tools/h6_hybrid.py`, real Finnish, 30 seeds). Best survivor: **pt-chain + period-4 + collision fix** (c[i] = p[i] + p[i-1] + k[i mod 4]; if equal to previous output, bump by 1) - the FIRST construction to pass constraints 1-4 at once (IoC 1.049, adj 0 by construction, re-converges 97%). Fails the gap-4 magnitude: 1.28 vs observed 1.98 (CI low 1.73), because pt-chaining turns gap-4 into a pair-sum repeat, which is ~2x rarer than single-syllable repeats. Verse plaintext does not fix it (1.27). Exact tension: flattening IoC to 1.0 halves the gap-4 signal; keeping the signal leaves IoC ~1.17+. Needs plaintext repeating two-syllable units at distance 4 at ~2x prose rate - possible for a short formulaic message, unproven. The ct-chained variant absorbs c3 with a lucky key (best 0.7/1027) but re-converges 0% - constraint 4 kills the whole ct branch.
7. **Abstract encodings (values as instructions, not symbols). TESTED 2026-08-10** (`tools/abstract_encodings.py`). Class A, fixed abstract maps (value -> cell/letter/rune in any fixed layout): monoalphabetic substitution, dead by constraint 2, no new test needed. Class B, cumulative readings (value rotates a hidden pointer, plaintext = running sum mod m): **FALSIFIED** at ring sizes 83/29/26/25/21, all |z| <= 0.91, against a positive control (difference-encoded Finnish) at z = +90. Class C, spatial walks (eyes as 2D steps, message = path): **NOT SUPPORTED** - 17 direction schemes (15 compass+stay, pentagon, digit-pair), radius-of-gyration z range -0.99..+1.41, nothing near Bonferroni, controls fire at z = -8.6 (boxed drawing) and +13.3 (stroke tracing). Untested residue: turtle-style turn-relative movement; abstract reading + strong cipher (which reduces to the main queue).
8. **Eye-level / grid-alphabet readings (no trigrams). FALSIFIED 2026-08-10 as direct or substitution readings** (`tools/eye_level.py`). (a) Base-5 numeral signature: slot-0 of each trigram never shows orientation 4 and shows 3 only ~97 times (predicted ~100 for values 75-82); slots 1-2 near-uniform - the shape of numbers, not letters. (b) Eye-pairs through any fixed 5x5 grid would preserve language IoC (~2.0 for Finnish letters); observed 1.11-1.12 at both pairings = the trigram-preserving null exactly. (c) Single-eye bigrams at chance vs the same null. Residual: grid alphabet + strong cipher is not excluded, but then the cipher is the puzzle again and the slot signature still says numbers.
3. ~~Alberti / progressive-shift disk: substitution alphabet rotates by a schedule (fixed increment, plaintext-driven, or ciphertext-driven), nonce sets initial rotation.~~ **FALSIFIED 2026-08-10, all three schedules.** Fixed increment gives 23-27 adjacent repeats against constraint 3's zero. Plaintext-driven rotation gives a gap spectrum of 0.00/0.07/0.51 at gaps 2-4 against the observed 0.48/0.78/1.98. Ciphertext-driven is violently periodic (IoC 2.62 vs 1.02). The mixed schedule clears constraints 1-4 but is flat at gap 4. See NOTEBOOK.md.
4. ~~Chained permutation state machine / **the community's deck-of-83-cards theory**~~ **EFFECTIVELY FALSIFIED 2026-08-10 by the re-convergence argument (see constraint 4 below), independently of everything in this entry.** Retained for the record:: each plaintext letter shuffles a deck and the top card is the output, i.e. a group autokey over S83. **SEVERELY CONSTRAINED 2026-08-10, not falsified — this is the live hypothesis.** The framing survives, but every simple shuffle in it dies: slow shuffles (insert-at-depth, swap-with-depth, riffle) leave 3-10x too many short-range repeats; mechanisms that don't protect the top card give 10-11 adjacent repeats against zero; and everything that survives both has a flat gap spectrum and cannot produce the gap-4 excess. Note the community's "shuffle always moves the top card" explanation of constraint 3 is correct but discriminates nothing - it is just sigma_p(0) != 0, true of nearly every candidate. **The real target: a shuffle that mixes essentially completely in one step, yet whose 4-step composition fixes the top card about twice as often as chance without being the identity** (zero of 20 gap-4 coincidences chain, where full state recurrence predicts ~19). Next step is to characterise the shuffle group algebraically rather than guess mechanisms.
5. Codebook: 83 values index words/syllables in a key text (orb room runes, in-game books). Finnish has ~50 common syllables; 83 symbols suits a syllabary better than a 29-letter alphabet - consider syllable-level plaintext models alongside letter-level.

## Methodology traps found the hard way

- **Dedup before any repetition statistic.** The positionally-shared header runs (constraint 4) inflate every n-gram and bigram statistic. Use `tools/dedup.py`, which strips runs of >=2 positional matches with an earlier message. This trap has now fired THREE times: a 4-long E1/W1 match manufactured a "significant" shift-invariant 4-gram repeat; the raw bigram battery read z=+9.8; and an eye-pair adjacency test read z=+2.94 (p=0.004) that dedup dissolved to z=+0.82. No repetition statistic on raw messages, ever.
- **Null models must be applied to the ciphertext, then transformed** - not to the derived sequence. Shuffling a derived difference sequence preserves its multiset, so an IoC test against it has sd = 0 and is vacuous.
- **Nulls must respect constraint 3.** Plain shuffling admits adjacent repeats the real data cannot have. Use `shuffle_no_repeat`.
- **No negative result counts without a positive control** on synthetic data where the hypothesis holds by construction (`tools/synth.py`). `tools/test_tools.py` asserts each battery separates its control from the real data.

## Reading order - LARGELY SETTLED 2026-08-10

The raw eye stream IS recoverable from the decoded CSV: a trigram is a 3-digit base-5 number, so v = 25a+5b+c inverts. (An earlier entry wrongly called obtaining it the top data task.) Tested all 6 spatial digit orders x 3 eye offsets in `tools/reading_order.py`:

- Only offset 0 gives ZERO adjacent repeats; shifted re-cuts land at chance (4-12).
- Only offset 0 with digit order (0,1,2) gives the contiguous 0-82 alphabet.
- The community selected on contiguity ALONE, so the repeat-free property is independent corroboration. The trigram consensus is right.
- Shared runs summed over 36 pairs: 240 symbols aligned from the START, 0 from the END. Backwards reading would turn a header-plus-leading-ID into a footer-plus-trailing-ID; the data does not decide it, but forward is the natural construction.
- Columnar/vertical reads at every width 2-40: none reaches zero adjacent repeats (best 5, chance baseline 12.0 +- 3.7, linear read 0). Vertical is NOT supported.

Residual caveat: this covers linear re-cuts, not every spatial traversal of the physical triangular layout.

## Finnish plaintext model

`tools/finnish.py` builds letter and syllable statistics; cached table at `data/finnish_syllables.json` so results reproduce without the source text. Built from *Seitseman veljesta* (prose, Gutenberg 11940).

**Do not use Kalevala as a plaintext control.** Its syllable gap profile spikes at gap 8 (7.44x) and gap 4 (3.42x) - that is trochaic tetrameter, and it manufactures exactly the periodicity under investigation. Use prose.

Finnish prose syllables repeat at EVERY distance above 1 (a plateau at 1.3-1.8x chance), mild max at distance 4. Distance-1 repeats are strongly suppressed (0.33x). Any cipher that passes repeats through inherits the whole plateau; the messages sit at chance for gaps 5-8, so most plaintext repetition is destroyed.

## Author prior

The messages were made by a small indie game developer, not a cryptographer. Weight the search accordingly: favour constructions buildable in an afternoon (a table shuffled once, modular addition, off-by-one and 1-based indexing, per-chunk processing) over anything requiring cryptographic sophistication. A mechanism that needs a carefully-constructed shuffle group is the wrong shape of answer regardless of how well it fits.

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
