# Lab Notebook

Reverse-chronological. Entry format: date / hypothesis / method / result / verdict.

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
- `tools/test_tools.py` — 23 tests: round-trip properties, dedup correctness, and battery-power checks.

`python3 tools/verify_constraints.py` — 23/23 pass.
`python3 tools/test_tools.py` — 23/23 pass.
