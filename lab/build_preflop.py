"""
build_preflop.py - precompute preflop equity vs a random hand for every
suit-isomorphism class of 5-card hands. Writes data/preflop.npz.

    python lab/build_preflop.py --samples 3000
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brain import canonical_key, equity  # noqa: E402


def _work(args):
    chunk, samples, seed = args
    rng = np.random.default_rng(seed)
    out = []
    for key, hole in chunk:
        out.append((key, equity(hole, (), samples, rng)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    t = time.time()
    reps = {}
    for hole in combinations(range(36), 5):
        k = canonical_key(hole)
        if k not in reps:
            reps[k] = hole
    print(f"{len(reps)} classes ({time.time() - t:.0f}s)", flush=True)
    items = sorted(reps.items())
    chunks = [items[i::64] for i in range(64)]
    res = []
    with ProcessPoolExecutor(args.workers) as ex:
        for i, part in enumerate(ex.map(_work, [(c, args.samples, i) for i, c in enumerate(chunks)])):
            res.extend(part)
    res.sort()
    keys = np.array([k for k, _ in res], dtype=np.int64)
    eq = np.array([e for _, e in res], dtype=np.float32)
    (ROOT / "data").mkdir(exist_ok=True)
    np.savez_compressed(ROOT / "data" / "preflop.npz", keys=keys, eq=eq)
    print(f"done in {time.time() - t:.0f}s; equity range {eq.min():.3f}..{eq.max():.3f}")


if __name__ == "__main__":
    main()
