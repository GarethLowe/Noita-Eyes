"""Assert the established, locally-verified facts about the eye message dataset.

Run this after ANY change to data loading or transcription handling. If an
assertion fails, the tooling is wrong - not the constraints. These were all
independently reproduced from the ngraham20 transcription on 2026-08-10.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "eye_trigrams.csv"

EXPECTED_LENGTHS = {
    "East 1": 99, "West 1": 103, "East 2": 118, "West 2": 102,
    "East 3": 137, "West 3": 124, "East 4": 119, "West 4": 120,
    "East 5": 114,
}


def load():
    msgs = {}
    with open(DATA) as f:
        for row in csv.reader(f):
            if row[0].startswith("#"):
                continue
            msgs[row[1]] = [int(x) for x in row[2:] if x.strip()]
    return msgs


def shared_prefix_len(a, b):
    """Length of identical run starting at position 1 (position 0 excluded)."""
    n = 0
    for x, y in zip(a[1:], b[1:]):
        if x != y:
            break
        n += 1
    return n


def main():
    msgs = load()
    checks = []

    def check(name, cond, detail=""):
        checks.append((name, cond, detail))

    # Structure
    check("9 messages present", set(msgs) == set(EXPECTED_LENGTHS))
    check("message lengths match", {k: len(v) for k, v in msgs.items()} == EXPECTED_LENGTHS)

    allv = [v for m in msgs.values() for v in m]
    c = Counter(allv)
    check("1036 trigrams total", len(allv) == 1036, f"got {len(allv)}")
    check("exactly 83 unique symbols, contiguous 0-82",
          len(c) == 83 and min(c) == 0 and max(c) == 82)

    # Zero adjacent identical symbols (the ciphertext-dependency smoking gun)
    adjacent = sum(1 for m in msgs.values() for i in range(1, len(m)) if m[i] == m[i - 1])
    check("zero adjacent repeats (expected ~12 if random)", adjacent == 0, f"got {adjacent}")

    # Shared headers start at position 1; position 0 differs everywhere
    firsts = [m[0] for m in msgs.values()]
    check("all position-0 values distinct (indicator/nonce)", len(set(firsts)) == 9, str(firsts))
    check("E1/W1 share 24-trigram header", shared_prefix_len(msgs["East 1"], msgs["West 1"]) == 24)
    check("E1/E2 share 24-trigram header", shared_prefix_len(msgs["East 1"], msgs["East 2"]) == 24)
    check("E4/W4 share 20-trigram header", shared_prefix_len(msgs["East 4"], msgs["West 4"]) == 20)
    check("E4/E5 share 20-trigram header", shared_prefix_len(msgs["East 4"], msgs["East 5"]) == 20)
    check("E3/E4 share 9-trigram header", shared_prefix_len(msgs["East 3"], msgs["East 4"]) == 9)

    # E1/W1 also share a mid-message run: positions 37..49 inclusive (13 trigrams)
    e1, w1 = msgs["East 1"], msgs["West 1"]
    check("E1/W1 mid-run at 37 len 13", all(e1[i] == w1[i] for i in range(37, 50)))

    # Flat-ish frequencies: normalised IoC near 1.0 per message (random-like)
    for k, v in msgs.items():
        cc = Counter(v)
        n = len(v)
        ioc = sum(x * (x - 1) for x in cc.values()) / (n * (n - 1)) * 83
        check(f"IoC({k}) in [0.85, 1.10]", 0.85 <= ioc <= 1.10, f"{ioc:.3f}")

    # Gap-4 over-representation of repeated symbols
    g = Counter()
    for v in msgs.values():
        last = {}
        for i, x in enumerate(v):
            if x in last and i - last[x] <= 6:
                g[i - last[x]] += 1
            last[x] = i
    check("gap-4 repeats over-represented (>=20)", g[4] >= 20, f"got {g[4]}")
    check("gap-1..3 repeats suppressed (<=20 combined)", g[1] + g[2] + g[3] <= 20, str(dict(g)))

    failed = [(n, d) for n, ok, d in checks if not ok]
    for n, ok, d in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n}" + (f"  [{d}]" if d and not ok else ""))
    print(f"\n{len(checks) - len(failed)}/{len(checks)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
