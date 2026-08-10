"""Strip positionally-shared runs so repeated headers cannot fake a signal.

Constraint 4 says several messages carry identical runs at identical positions
(shared plaintext headers). Any repetition statistic computed over the raw
corpus double-counts those runs, which shows up as language-like structure even
in a cipher with none. `segments()` keeps the first occurrence of each shared
run and drops later copies, returning a list of contiguous segments so that
adjacency-based statistics never span a cut.
"""
from eyes import ORDER

# Any run of >=2 positional matches with an earlier message is treated as
# shared plaintext. Cheap insurance: tightening from 5 to 2 costs only 15 of
# 916 symbols, and a run of 4 that slipped through at threshold 5 was enough to
# manufacture a spurious shift-invariant 4-gram repeat.
MIN_RUN = 2


def shared_mask(msgs, min_run=MIN_RUN):
    """Mark positions that duplicate an earlier message at the same index.

    Only runs of at least `min_run` consecutive matches are marked, so
    incidental coincidences are left alone.
    """
    names = [k for k in ORDER if k in msgs]
    masks = {k: [False] * len(msgs[k]) for k in names}
    for j, kj in enumerate(names):
        v = msgs[kj]
        for ki in names[:j]:
            w = msgs[ki]
            i = 0
            while i < min(len(v), len(w)):
                if v[i] != w[i]:
                    i += 1
                    continue
                start = i
                while i < min(len(v), len(w)) and v[i] == w[i]:
                    i += 1
                if i - start >= min_run:
                    for t in range(start, i):
                        masks[kj][t] = True
    return masks


def segments(msgs, min_run=MIN_RUN):
    """Return [[int, ...], ...]: contiguous runs left after dropping duplicates."""
    masks = shared_mask(msgs, min_run)
    out = []
    for k in (n for n in ORDER if n in msgs):
        cur = []
        for x, dup in zip(msgs[k], masks[k]):
            if dup:
                if cur:
                    out.append(cur)
                cur = []
            else:
                cur.append(x)
        if cur:
            out.append(cur)
    return out


if __name__ == "__main__":
    from eyes import load
    m = load()
    segs = segments(m)
    kept = sum(len(s) for s in segs)
    print(f"{len(segs)} segments, {kept}/{sum(len(v) for v in m.values())} "
          f"symbols kept, lengths {[len(s) for s in segs]}")
