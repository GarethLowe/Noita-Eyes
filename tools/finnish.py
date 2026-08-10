"""Finnish letter and syllable statistics, for scoring and for controls.

Everything up to now used `synth.language_like`, which is lumpy in the way
languages are but is not Finnish. Real statistics matter here for one specific
reason: the leading hypothesis (H2, c[i] = pi(p[i] + p[i-1])) requires the
plaintext to never repeat a symbol at distance 2, and whether that is remotely
plausible is a measurable property of Finnish, not something to reason about
from an armchair.

Source text is Kalevala (Project Gutenberg #7000), public domain. It is archaic
poetic Finnish, which is a real caveat for letter frequencies and a smaller one
for syllable structure. Regenerate the cached table with:

    python3 tools/finnish.py --build path/to/finnish.txt

The cached table `data/finnish_syllables.json` is what the other tools read, so
the analysis is reproducible without the source text.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eyes import N  # noqa: E402

CACHE = Path(__file__).resolve().parent.parent / "data" / "finnish_syllables.json"

VOWELS = set("aeiouyäö")
DIPHTHONGS = {
    "ai", "ei", "oi", "ui", "yi", "äi", "öi", "au", "eu", "iu", "ou",
    "ey", "äy", "öy", "ie", "uo", "yö",
}
LONG = {v + v for v in "aeiouyäö"}


def normalise(text):
    """Lowercase, keep Finnish letters, collapse everything else to spaces."""
    text = text.lower()
    text = text.replace("å", "a")
    return re.sub(r"[^a-zäö]+", " ", text)


def syllabify(word):
    """Split a Finnish word into syllables.

    Standard approximation: break before a consonant that starts a CV cluster,
    break between two consonants, and break between adjacent vowels that do not
    form a diphthong or a long vowel.
    """
    if not word:
        return []
    out, cur = [], word[0]
    for i in range(1, len(word)):
        prev, ch = word[i - 1], word[i]
        brk = False
        if prev in VOWELS and ch in VOWELS:
            pair = prev + ch
            brk = pair not in DIPHTHONGS and pair not in LONG
        elif prev not in VOWELS and ch not in VOWELS:
            brk = True
        elif prev in VOWELS and ch not in VOWELS:
            # break before C only if a vowel follows it (open CV syllable)
            brk = i + 1 < len(word) and word[i + 1] in VOWELS
        if brk:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    out.append(cur)
    return out


def syllable_stream(text):
    """Syllables of the text, in order, as a flat list per word."""
    return [s for w in normalise(text).split() for s in syllabify(w)]


def build(path, out=CACHE):
    """Write the cached statistics table from a Finnish source text."""
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    letters = [c for c in normalise(text) if c != " "]
    syls = syllable_stream(text)
    counts = Counter(syls)
    top = [s for s, _ in counts.most_common(N)]
    data = {
        "source": Path(path).name,
        "n_letters": len(letters),
        "letter_counts": dict(Counter(letters)),
        "n_syllables": len(syls),
        "distinct_syllables": len(counts),
        "top83": top,
        "top83_counts": {s: counts[s] for s in top},
        # distance-1 and distance-2 repeat rates over the FULL syllable stream
        "rep_gap1": sum(1 for i in range(1, len(syls)) if syls[i] == syls[i - 1]) / (len(syls) - 1),
        "rep_gap2": sum(1 for i in range(2, len(syls)) if syls[i] == syls[i - 2]) / (len(syls) - 2),
        "rep_gap3": sum(1 for i in range(3, len(syls)) if syls[i] == syls[i - 3]) / (len(syls) - 3),
        "rep_gap4": sum(1 for i in range(4, len(syls)) if syls[i] == syls[i - 4]) / (len(syls) - 4),
        "coverage_top83": sum(counts[s] for s in top) / len(syls),
    }
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return data


def load_table(path=CACHE):
    if not path.exists():
        raise SystemExit(f"missing {path}; run: python3 tools/finnish.py --build FILE")
    return json.loads(path.read_text())


def top83_stream(text):
    """Map a text to symbols 0..82 via the top-83 syllables.

    Returns a list of contiguous runs: syllables outside the top 83 cut the
    stream rather than being folded into a catch-all symbol, which would put a
    spurious spike in the distribution.
    """
    table = load_table()
    idx = {s: i for i, s in enumerate(table["top83"])}
    runs, cur = [], []
    for s in syllable_stream(text):
        if s in idx:
            cur.append(idx[s])
        else:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
    if len(cur) > 1:
        runs.append(cur)
    return runs


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--build":
        d = build(sys.argv[2])
        print(f"built from {d['source']}: {d['n_syllables']} syllables, "
              f"{d['distinct_syllables']} distinct, "
              f"top-83 coverage {d['coverage_top83']:.1%}")
        return
    t = load_table()
    print(f"source: {t['source']}")
    print(f"letters: {t['n_letters']}, syllables: {t['n_syllables']}, "
          f"distinct syllables: {t['distinct_syllables']}")
    print(f"top-83 syllables cover {t['coverage_top83']:.1%} of the stream")
    print(f"most common: {t['top83'][:15]}")
    print("\nSyllable repeat rates in real Finnish (full inventory):")
    for k in (1, 2, 3, 4):
        r = t[f"rep_gap{k}"]
        print(f"  distance {k}: {r:.4f}  ->  {r * 1027:.1f} expected in 1027 symbols")


if __name__ == "__main__":
    main()
