"""
bucketize.py - card abstraction for the MCCFR blueprint, fit from a deal pool.

    python lab/bucketize.py POOL.bin OUTPREFIX [--fit-only] [--nb-e 32 --nb-h 8 --nb-r 192]

Abstraction ("abs v1"):
  preflop  lossless suit-isomorphism class (19,998 classes, id = index into
           data/preflop.npz keys), looked up through a colex table of all
           C(36,5) = 376,992 sorted holes (data/abs.npz: pre_class).
  flop     2-D: EHS quantile bin (NB_E) x HS quantile bin within that EHS bin (NB_H)
  turn     same construction with its own edges
  river    HS quantile bins (NB_R)
Edges are right-searchsorted: bin = searchsorted(edges, x, side='right').

Pool records (solver/pool.cpp, 64 bytes): cards[15] (button hole 5, bb hole 5,
board 5), int8 showdown, float feat[2][6] = pre_ehs, flop_ehs, flop_hs,
turn_ehs, turn_hs, river_hs.

Writes data/abs.npz (edges + pre_class table) unless --no-fit, and
OUTPREFIX_buckets.bin (uint16[n][2][4], role x street) and
OUTPREFIX_showdown.bin (int8[n]).
"""

from __future__ import annotations

import argparse
import sys
from itertools import combinations, permutations
from math import comb
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ABS_PATH = ROOT / "data" / "abs.npz"

REC = np.dtype([("cards", "u1", (15,)), ("sd", "i1"), ("feat", "<f4", (2, 6)), ("pad", "u1", (64 - 16 - 48,))])
assert REC.itemsize == 64

# colex rank of a sorted 5-card hole: sum C(c_i, i+1)
COMB = np.array([[comb(n, k) for k in range(6)] for n in range(37)], dtype=np.int64)


def colex(holes: np.ndarray) -> np.ndarray:
    """holes (N,5) any order -> colex index into the C(36,5) table."""
    h = np.sort(np.asarray(holes, dtype=np.int64), axis=1)
    return COMB[h[:, 0], 1] + COMB[h[:, 1], 2] + COMB[h[:, 2], 3] + COMB[h[:, 3], 4] + COMB[h[:, 4], 5]


def build_pre_class() -> np.ndarray:
    """uint16[376992]: colex(sorted hole) -> preflop class id (index in preflop.npz keys)."""
    holes = np.array(list(combinations(range(36), 5)), dtype=np.int64)
    best = None
    for p in permutations(range(4)):
        pm = np.array(p, dtype=np.int64)
        t = np.sort(((holes >> 2) << 2) | pm[holes & 3], axis=1)
        k = (((t[:, 0] * 36 + t[:, 1]) * 36 + t[:, 2]) * 36 + t[:, 3]) * 36 + t[:, 4]
        best = k if best is None else np.minimum(best, k)
    keys = np.load(ROOT / "data" / "preflop.npz")["keys"]
    cls = np.searchsorted(keys, best)
    assert np.all(keys[cls] == best), "canonical key missing from preflop.npz"
    out = np.zeros(comb(36, 5), dtype=np.uint16)
    out[colex(holes)] = cls.astype(np.uint16)
    return out


def quantile_edges(x: np.ndarray, nb: int) -> np.ndarray:
    """nb-1 right-searchsorted edges at the interior quantiles of x (deduplicated
    by nudging so every edge is strictly increasing)."""
    q = np.quantile(x, np.arange(1, nb) / nb).astype(np.float64)
    for i in range(1, len(q)):
        if q[i] <= q[i - 1]:
            q[i] = np.nextafter(q[i - 1], np.inf)
    return q.astype(np.float32)


def fit_2d(e: np.ndarray, h: np.ndarray, nb_e: int, nb_h: int):
    ee = quantile_edges(e, nb_e)
    be = np.searchsorted(ee, e, side="right")
    he = np.zeros((nb_e, nb_h - 1), dtype=np.float32)
    for k in range(nb_e):
        m = be == k
        he[k] = quantile_edges(h[m], nb_h) if m.sum() > nb_h else np.linspace(0, 1, nb_h + 1)[1:-1]
    return ee, he


def bucket_2d(e, h, ee, he):
    e = np.asarray(e, dtype=np.float32)
    h = np.asarray(h, dtype=np.float32)
    be = np.searchsorted(ee, e, side="right")
    nb_h = he.shape[1] + 1
    # per-row searchsorted within the row's HS edges: count edges <= h
    bh = (he[be] <= h[:, None]).sum(axis=1)
    return (be * nb_h + bh).astype(np.int64)


def bucket_1d(x, edges):
    return np.searchsorted(edges, np.asarray(x, dtype=np.float32), side="right").astype(np.int64)


def load_abs(path=ABS_PATH):
    z = np.load(path)
    return {k: z[k] for k in z.files}


def buckets_from_features(A, pre_cls, feat):
    """feat (N,6) float32 per hand-instance -> (N,4) buckets."""
    out = np.empty((len(feat), 4), dtype=np.int64)
    out[:, 0] = pre_cls
    out[:, 1] = bucket_2d(feat[:, 1], feat[:, 2], A["flop_e"], A["flop_h"])
    out[:, 2] = bucket_2d(feat[:, 3], feat[:, 4], A["turn_e"], A["turn_h"])
    out[:, 3] = bucket_1d(feat[:, 5], A["river"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pool")
    ap.add_argument("out_prefix")
    ap.add_argument("--no-fit", action="store_true", help="reuse data/abs.npz")
    ap.add_argument("--fit-n", type=int, default=2_000_000, help="deals used to fit edges")
    ap.add_argument("--nb-e", type=int, default=32)
    ap.add_argument("--nb-h", type=int, default=8)
    ap.add_argument("--nb-r", type=int, default=192)
    a = ap.parse_args()

    recs = np.fromfile(a.pool, dtype=REC)
    n = len(recs)
    print(f"pool {a.pool}: {n} deals")
    feat = recs["feat"]                       # (n,2,6)
    if a.no_fit:
        A = load_abs()
    else:
        pre = build_pre_class()
        f = feat[: a.fit_n].reshape(-1, 6)
        fe, fh = fit_2d(f[:, 1], f[:, 2], a.nb_e, a.nb_h)
        te, th = fit_2d(f[:, 3], f[:, 4], a.nb_e, a.nb_h)
        rv = quantile_edges(f[:, 5], a.nb_r)
        A = dict(pre_class=pre, flop_e=fe, flop_h=fh, turn_e=te, turn_h=th, river=rv,
                 nb=np.array([19998, a.nb_e * a.nb_h, a.nb_e * a.nb_h, a.nb_r], dtype=np.int32))
        np.savez_compressed(ABS_PATH, **A)
        print(f"wrote {ABS_PATH}: nb {A['nb'].tolist()}")
    cards = recs["cards"].astype(np.int64)
    bk = np.empty((n, 2, 4), dtype=np.uint16)
    for p in range(2):
        cls = A["pre_class"][colex(cards[:, 5 * p: 5 * p + 5])]
        bk[:, p, :] = buckets_from_features(A, cls, feat[:, p, :])
    nb = A["nb"]
    for s in range(4):
        used = np.unique(bk[:, :, s]).size
        cnt = np.bincount(bk[:, :, s].ravel(), minlength=int(nb[s]))
        print(f"street {s}: {used}/{nb[s]} buckets used, min/median/max count {cnt.min()}/{int(np.median(cnt))}/{cnt.max()}")
        assert bk[:, :, s].max() < nb[s]
    bk.tofile(a.out_prefix + "_buckets.bin")
    recs["sd"].astype(np.int8).tofile(a.out_prefix + "_showdown.bin")
    print(f"wrote {a.out_prefix}_buckets.bin and _showdown.bin")


if __name__ == "__main__":
    main()
