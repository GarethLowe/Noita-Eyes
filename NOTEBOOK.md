# Lab Notebook

Reverse-chronological. Entry format: date / hypothesis / method / result / verdict.

---

## 2026-08-10 — Re-convergence bounds the state. The deck theory is in serious trouble.

**Prompted by a prior correction, not by new data.** The author is a small
indie game developer, not a cryptographer. That should have been weighting the
search from the start, and it was not: the previous entry ended by proposing to
characterise a shuffle group algebraically, which is a search for a mechanism
no game developer would build. Re-reading the corpus under the corrected prior
found something I had walked past twice.

**The observation.** Constraint 4 is recorded as a list of shared runs. What
matters is not the shared headers but what happens *after* two messages
diverge:

```
E1 vs W1:  pos 1-24 match | 25-28 differ | 29-32 MATCH | 33-36 differ | 37-49 MATCH
E4 vs E5:  pos 1-20 match | then re-converges three separate times
```

Five re-convergence runs across the corpus, the longest 13 symbols. **Two
encryptions that have diverged come back into exact agreement.** That is a
bound on the state, and a brutal one.

| model | states | cost of a 13-long re-convergence |
|---|---|---|
| stateless, position-keyed | 1 | free |
| plaintext-chained (H2) | n/a — state is a function of plaintext | free, one symbol after the plaintext rejoins |
| ciphertext-chained autokey | 83 | ~1/83 per event, then self-sustaining |
| **deck / group autokey over S₈₃** | **83! ≈ 10¹²⁴** | **83⁻¹³ ≈ 1.1 × 10⁻²⁵** |

Simulated directly in `tools/resync_analysis.py`, encrypting two plaintexts
that diverge and rejoin, from a shared initial deck as constraint 4 requires:
the deck cipher reproduces the header and then **never re-converges**;
ciphertext-chained autokey likewise; plaintext-chained autokey re-converges for
free, every time, one symbol after the plaintext does — reproducing the
observed shape.

**Verdict: the deck / group-autokey framing (H4) is effectively FALSIFIED,** and
by an argument that has nothing to do with the gap spectrum I spent the previous
entry on. A large-state chained cipher cannot produce a 13-symbol
re-convergence. The community's model is attractive because it explains
constraint 3 for free, but it cannot survive constraint 4 read properly. The
cipher's state does not depend on ciphertext history.

**So H2 came off the queue and got tested.** Sub-case `c[i] = p[i] + p[i-1]` is
completely determined by the single unknown `p[0]`, and the IoC of the even- and
odd-index plaintext subsequences is invariant to that unknown — so it needs no
guessing. Pooled: **1.10 / 1.09**, against a language-like positive control
through the same construction at **2.75 / 2.73** and a uniform reference at 1.00.
**Sub-case 1 FALSIFIED.**

Sub-case `c[i] = π(p[i] + p[i-1])` is **OPEN and is now the leading hypothesis.**
It fits the re-convergence evidence exactly, it is the kind of thing a
programmer builds in an afternoon (shuffle a table once, add the previous
symbol, look it up), and it survives the IoC argument that killed H1 — there the
first difference *was* the plaintext, whereas here `c[i] - c[i-1] = p[i] - p[i-2]`,
a difference of plaintext symbols, which is expected to look flat even when the
plaintext does not. Note this also rehabilitates the word "deck": the shuffled
deck of 83 would be the *table*, shuffled once, rather than re-shuffled per
letter.

**The honest problem with it.** Zero adjacent repeats requires
`F(p[i],p[i-1]) ≠ F(p[i-1],p[i-2])` at all 1027 positions, which for `F = π(a+b)`
reduces to `p[i] ≠ p[i-2]` always. Over a syllabary of ~83 symbols roughly 25
distance-2 repeats would be expected in 1027 symbols. Zero is observed. So the
leading hypothesis does not yet explain constraint 3, and I am not going to
pretend otherwise.

**Which raises a data-provenance question that should be settled before more
key search.** Constraints 1 and 3 — exactly 83 contiguous values, and exactly
zero adjacent repeats — are both properties of *one particular* trigram reading
order, chosen out of ~86,000 candidates because it produced a gapless 0-82
range. Regrouping the eyes changes which trigrams are adjacent, so constraint 3
is not invariant to that choice. If it is partly a selection artifact, the
inference "the output must depend on the previous output" weakens
substantially, and with it the reason H2 looks uncomfortable. **Testing this
needs the raw per-eye orientation sequences, which this repo does not have** —
`data/eye_trigrams.csv` is already decoded. Obtaining them is now the highest-
value data task in the project.

**Two smaller results from the same session.**

A concentration hypothesis for gap 4, tested and dead: if the increments
`d[i] = c[i]-c[i-1]` clustered near 83/4 ≈ 20.75, four steps would complete a
turn and the whole spectrum (2 and 3 suppressed, 4 enhanced) would follow from
one number. The circular mean of d does sit at **20.33**, seductively close —
but `|φ(1)| = 0.046` with Rayleigh p = 0.15, and the implied gap-4 boost is
~5 × 10⁻⁶ against the factor of 2 observed. Coincidence. The gap-4 excess comes
from *dependence* between successive increments, not from their marginal
distribution.

A bug fix that did not change a verdict: the "perfect mixing limit" mechanism in
the previous entry's H4 table ignored the plaintext entirely, making it a
keystream generator rather than a cipher. Replaced with a genuine group autokey
drawing one random generator per plaintext symbol, constrained to σ_p(0) ≠ 0.
The corrected profile is still flat (1.09/1.04/0.99/0.93 at gaps 2-5), so the
conclusion stands, but the earlier row was not measuring what its label claimed.

---

## 2026-08-10 — H4 / community deck theory, and H3 closed out

**The community theory, as stated.** The leading candidate is a **deck of 83
cards: each plaintext letter triggers a shuffle, and the top card after
shuffling is the ciphertext symbol** — formally a group autokey over the
symmetric group S₈₃, `c[i] = (σ_{p1}∘…∘σ_{pi})(top)`. Constraint 3 is said to
come free: if every shuffle moves the top card, consecutive outputs cannot be
equal. Reported alongside it: the internal state count is ~83, the shuffles are
believed to be "few swaps from a shared base permutation", and the ciphertext is
aperiodic with a flat distribution. Sources at the bottom of this entry.

**The claim about constraint 3 is correct, and that is the problem.** In deck
terms the requirement is exactly `σ_p(0) ≠ 0` for every letter p — the shuffle
must not fix the top position. That is a one-line condition satisfied by
essentially every mechanism in the family, so it discriminates nothing. It
explains constraint 3 without narrowing the search at all.

**The discriminating instrument is the repeat-gap spectrum.** How often a symbol
recurs k positions later needs no key and no plaintext model, only the
mechanism, so it filters candidates before any key search. Observed, on deduped
segments against a constrained-reshuffle null:

| gap | 1 | 2 | 3 | **4** | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| obs/chance | 0.00 | 0.48 | 0.78 | **1.98** | 1.00 | 1.21 | 1.13 | 1.03 |

Gap 4: 20 observed against a null of 9.95 ± 3.04, **z = +3.31, p = 0.0017**.
It clears Bonferroni over all 29 gaps tested (0.048) and does not need to,
since it was pre-registered as constraint 5 before this analysis. All nine
messages independently exceed expectation. It **survives dedup** (26 raw → 20),
so it is not a shared-header artifact — which was the first thing I checked,
having been burned by exactly that in the H1 entry below.

**Nine mechanisms, none of which reproduce it** (`tools/deck_models.py`,
40 seeds each, matched segment lengths):

| mechanism | g2 | g3 | g4 | g5 | adj | verdict |
|---|---|---|---|---|---|---|
| cut by p (plaintext-driven rotation) | 0.00 | 0.07 | 0.51 | 1.19 | 0 | too rigid |
| cut by previous output (ct-driven) | 10.6 | 8.9 | 18.9 | 6.7 | 0 | wildly periodic, IoC 2.62 |
| cut by p + previous output | 1.03 | 1.03 | 1.03 | 1.08 | 0 | flat — no gap-4 spike |
| insert top at depth p | 0.00 | 9.94 | 5.26 | 3.79 | 0 | mixes far too slowly |
| swap top with depth p | 3.76 | 3.56 | 3.59 | 3.59 | 0 | mixes far too slowly |
| base rotate + swap | 0.96 | 0.97 | 1.07 | 0.99 | **10** | breaks constraint 3 |
| riffle, cut at p | 0.00 | 9.88 | 3.90 | 2.70 | 0 | mixes far too slowly |
| RC4-like state | 1.14 | 1.08 | 0.94 | 0.98 | **11** | breaks constraint 3 |
| full reshuffle (mixing limit) | 1.02 | 0.97 | 1.03 | 0.96 | 0 | flat — no gap-4 spike |

The family splits cleanly in three. Slow shuffles (insert, swap, riffle) leave
3–10× too many short-range repeats. Mechanisms that do not protect the top card
(base-rotate-plus-swap, RC4-like) produce 10–11 adjacent repeats where the data
has zero. Everything that survives both — the perfect-mixing limit, and rotation
driven by plaintext-plus-ciphertext — has a **flat** spectrum and cannot produce
the gap-4 excess.

**Verdict: H4 SEVERELY CONSTRAINED, not falsified.** The deck framing survives,
because a sufficiently strong plaintext-dependent shuffle reproduces constraints
1–4 comfortably. What is falsified is every *simple* shuffle in it. The target
now has a sharp and peculiar shape: **the mechanism must mix essentially
completely in a single step, yet return a symbol to the output position after
exactly four steps at twice the chance rate, with no such tendency at two,
three, or five-plus.** No natural shuffle I tested does both.

**And it is not a full state recurrence.** If a gap-4 coincidence meant the deck
had returned to its state four steps earlier, the *next* output would match too,
so coincidences would come in runs. Of 20 coincidences, **zero** are
consecutive; that alternative predicts about 19. So the 4-step composition
`σ_{p[i+1]}…σ_{p[i+4]}` **fixes the top card without being the identity.** That
is a precise algebraic condition on the shuffle group and is the most specific
handle this project has produced so far. (Note the chance null here expects only
0.12 chains, so this test has no power *against chance* — its power comes
entirely from the recurrence alternative's prediction of ~19.)

**Layout hypothesis tested and rejected.** The eyes are physically drawn in rows
of at most 39 glyphs with every second row offset, trigrams being triangular
groups spanning paired rows — so a line is 13 or 26 trigrams and vertical
adjacency would surface as a gap-13 or gap-26 spike. Gap 13 is elevated (16 vs
8.96, z = +2.35) but at p = 0.023 uncorrected it is **0.68 after correction over
the 29 exploratory gaps**, and gap 26 is nothing (z = +0.92). Gap 30 is the
other near-miss (z = +2.64, corrected 0.33). **Not supported.** Worth one
re-test if the corpus ever grows, and worth stating plainly that I went looking
for it because the layout suggested it, which is exactly when a correction is
mandatory.

**H3 (Alberti) — now FALSIFIED in full.** The fixed-increment case fell in the
entry below. The remaining driven-schedule half is covered here: plaintext-driven
rotation is `cut by p` (spectrum 0.00/0.07/0.51 against 0.48/0.78/1.98 — far too
rigid, and it is additively equivalent to H1's pure shift, already dead);
ciphertext-driven rotation is `cut by previous output` (violently periodic, IoC
2.62 against the observed 1.02); the mixed schedule survives constraints 1–4 but
is flat at gap 4 like every other well-mixing mechanism. No rotating-disk
schedule tested reproduces the fingerprint.

**Where to go next.** Characterise the shuffle group directly rather than
guessing mechanisms: enumerate small generating sets whose 4-fold products fix a
point without being the identity, and check which are compatible with a
one-step-mixing spectrum. Also worth a look — E4/W4/E5 carry gap-4 coincidences
at near-identical positions (6, ~35, ~74, ~91, drifting by 1–3), which past the
shared 20-trigram header hints at more shared plaintext than the header alone,
under small insertions. That would be a crib, and it is cheap to test with
alignment.

**Sources.** [Noita Wiki — Eye Messages](https://noita.wiki.gg/wiki/Eye_Messages),
[ngraham20/NoitaCryptographyResearch](https://github.com/ngraham20/NoitaCryptographyResearch),
[Unsolved Puzzles — The Eye Puzzle](https://unsolved-puzzles.github.io/unsolved-puzzles/noita/eye-puzzle.html),
[Noita Eye Glyph Messages (write-up)](https://www.scribd.com/document/911932819/Noita-Eye-Glyph-Messages).
The deck/group-autokey framing and the "few swaps from a shared base
permutation" remark are community claims restated here, not independently
verified; the gap-spectrum results above are mine and reproducible from this
repo.

---

## 2026-08-10 — H3 preliminary: constant-increment additive rotation (Alberti)

**Hypothesis.** The cipher is an additive rotation over Z83 whose offset advances
by a fixed increment per symbol: `c[i] = p[i] + (start + i*step) mod 83`.

**Why this got tested early.** It fell out of the H1 work below. The one residual
signal in the H1 battery was an excess of repeated *difference bigrams*, and a
repeated difference bigram is exactly a ciphertext trigram repeated up to a
constant additive shift — the signature this hypothesis predicts.

**Method.** `tools/shift_invariant_ngrams.py`. An n-gram's *shift class* is its
difference vector mod 83, so two n-grams share a class iff they are equal up to a
constant offset. Under a constant-increment key the keystream contributes the
same difference vector everywhere, so **every** repeated plaintext n-gram
survives into the ciphertext as a shift-invariant repeat. Counted repeated
classes for n=3..6 against the constrained-shuffle null, with matched-length
controls under progressive shift (step 1 and 7) and Vigenère period 14.

**Result.**

| cipher | n=3 | n=4 | n=5 | n=6 | adjacent repeats |
|---|---|---|---|---|---|
| progressive shift, step 1 | 143 | 4 | 0 | 0 | 27 |
| progressive shift, step 7 | 143 | 4 | 0 | 0 | 23 |
| Vigenère, period 14 | 60 | 2 | 0 | 0 | 7 |
| null (shuffled eye messages) | 51.2 ± 6.6 | 0.65 ± 0.80 | 0.0 | 0.0 | 0 by construction |
| **observed (eye messages)** | **62** | **2** | **0** | **0** | **0** |

Observed: n=3 z=+1.64 p=0.062, n=4 z=+1.69 p=0.150. Nothing at n≥5. Across four
n values, uncorrected — no signal.

**Verdict: constant-increment additive rotation FALSIFIED (preliminary).**
Killed twice over. The progressive controls produce 143 shift-invariant trigram
classes where the messages show 62 against a null of 51; and, independently and
more decisively, they produce 23–27 adjacent repeats against constraint 3's
observed zero. Any additive keystream that does not depend on the previous
ciphertext symbol fails constraint 3 the same way — the Vigenère control shows 7.

Held preliminary, not final, for two reasons. The n-gram arm leans on synthetic
plaintext whose repetitiveness is a guess, so its effect size is not
trustworthy; the adjacency arm does not depend on that and is solid. And the
result only covers a *constant* increment: a plaintext- or ciphertext-driven
rotation schedule, which is the more interesting half of H3, is untouched. That
half is where H3 should resume, and it must clear constraint 3 first.

**Incidental.** The shift-invariant statistic cannot separate the messages from
the Vigenère-14 control (60 vs 62 classes) — repeats only align at gaps that are
multiples of the period, so almost nothing survives. This statistic is a test for
constant-increment schedules specifically, not for periodic keys. The community's
reported length-14 key component needs a different instrument.

---

## 2026-08-10 — H1: ciphertext autokey over Z83

**Hypothesis.** `c[i] = p[i] + f(c[i-1]) mod 83`, position 0 held outside the
chain as the indicator (constraint 4).

**Method.** `tools/h1_ciphertext_autokey.py`, three parts: an exact argument
narrowing `f`, a language battery on the resulting plaintext, and a positive
control.

**Part 1 — constraint 3 collapses the affine family, exactly.** For
`f(x) = a*x + b`, an adjacent ciphertext repeat occurs iff
`p[i] = g(c[i-1])` where `g(x) = x - f(x) = (1-a)x - b`. 83 is prime, so for
every `a ≠ 1` the map `g` is a bijection on Z83 and its image is the whole
alphabet. All 83 symbols do appear in the ciphertext, so zero adjacent repeats
would require the plaintext to avoid every symbol in the alphabet. **Only
`a = 1`, the pure shift, survives.** This is a proof, not a statistic.

More generally, for arbitrary `f`, the image of `g` must be disjoint from the
plaintext's support. A plaintext using k distinct symbols admits only those `f`
with `|image(g)| ≤ 83 - k`. A syllabary using most of the alphabet forces `g`
constant, i.e. `f` a pure shift.

**Part 2 — the surviving variant is directly testable.** With `a = 1` the
recovered plaintext is the ciphertext first difference up to a constant shift:
`p[i] = c[i] - c[i-1] - b`. So H1 is true only if that difference sequence is
language. Note `d[i] ≠ 0` holds by construction — that *is* constraint 3 — so
the missing value is not evidence for anything; the rest of the distribution is
the test.

| | IoC | bigram repeat rate |
|---|---|---|
| forward `c[i]-c[i-1]` | 0.997 (z=−0.18, p=0.56) | 0.149 (z=+1.89, p=0.036) |
| reverse `c[i]-c[i+1]` | 0.997 (z=−0.18, p=0.56) | 0.149 (z=+1.89, p=0.036) |
| **control: H1-encrypted synthetic language** | **3.92 (z=+200, p=0.005)** | **0.71 (z=+42, p=0.005)** |

Forward and reverse agree to the digit because reversing a segment and negating
its differences maps each bigram `(x,y)` to `(-y,-x)`, a bijection — the
repetition counts are identical by construction, not by coincidence.

**Part 3 — the control confirms the battery has power.** Synthetic
language-like plaintext encrypted under H1 registers z=+200 on IoC. The eye
messages register z=−0.18. The test is not merely failing to find something.

**Verdict: H1 FALSIFIED.** Killed by constraint 3 for all affine `f` except the
pure shift, and by the flat IoC of the first-difference sequence for the shift
itself. The difference sequence is indistinguishable from a random sequence with
the same symbol counts. Whatever `f` is, `c[i] - f(c[i-1])` is not plaintext for
any `f` in the affine family.

**Scope of the claim.** This does not rule out a non-affine `f` whose image
avoids the plaintext support, nor a chain where the state carries more than
`c[i-1]`. It rules out the family in the hypothesis as written.

**Method note that changed a result.** The first run of this battery reported
bigram-repeat z=+9.8 and a "significant" shift-invariant 4-gram excess. Both
were artifacts of positionally-shared header runs being counted twice.
`tools/dedup.py` now strips any run of ≥2 positional matches with an earlier
message (120 of 1036 symbols) and the signal drops to z=+1.9. An earlier
threshold of 5 let a 4-long E1/W1 match at position 29 through, which alone
manufactured one of three apparently-significant 4-gram repeats. Any repetition
statistic on this corpus must dedup first. Separately, the IoC null must
reshuffle the *ciphertext* and re-difference it — shuffling the derived
differences preserves their multiset and makes the test vacuous (sd = 0).

---

## Tooling added

- `tools/eyes.py` — loader and shared statistics (IoC, bigram rate, permutation test).
- `tools/dedup.py` — strips positionally-shared runs into clean segments.
- `tools/synth.py` — synthetic language-like plaintext; autokey, progressive and Vigenère ciphers with exact inverses.
- `tools/h1_ciphertext_autokey.py` — the H1 battery.
- `tools/shift_invariant_ngrams.py` — shift-class repeat counts, the additive-family instrument.
- `tools/gap_spectrum.py` — repeat-gap spectrum with nulls, correction, per-message breakdown and the chain test.
- `tools/deck_models.py` — nine deck/shuffle mechanisms fingerprinted against the observed spectrum.
- `tools/resync_analysis.py` — re-convergence extraction and the state-size bound.
- `tools/h2_plaintext_autokey.py` — H2 sub-case 1 closed form, sub-case 2 scoped.
- `tools/test_tools.py` — 42 tests: round-trip properties, dedup correctness, battery-power checks, and a guard asserting no simulated mechanism reproduces the gap-4 profile.

`python3 tools/verify_constraints.py` — 23/23 pass.
`python3 tools/test_tools.py` — 42/42 pass.
