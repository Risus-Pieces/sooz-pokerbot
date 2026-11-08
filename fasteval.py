"""
fasteval.py - vectorized Short Deck PLO5 hand scoring with numpy.

Scores match evaluator.omaha_score exactly, but whole batches of hands are
scored at once. A five-card hand's score depends only on its rank multiset
and whether it is a flush, so the key is sum(5 ** rank) (each rank appears
at most 4 times, so base 5 is collision-free) and two flat tables hold the
scores: one for flushes and one for everything else.
"""

from __future__ import annotations

from itertools import combinations, combinations_with_replacement

import numpy as np

from evaluator import _score_ranks

POW5 = 5 ** np.arange(9, dtype=np.int64)
_TABLE_SIZE = 5 ** 9


def _build_tables() -> tuple[np.ndarray, np.ndarray]:
    plain = np.zeros(_TABLE_SIZE, dtype=np.int32)
    flush = np.zeros(_TABLE_SIZE, dtype=np.int32)
    for ranks in combinations_with_replacement(range(9), 5):
        if max(ranks.count(r) for r in ranks) > 4:
            continue
        key = int(sum(5 ** r for r in ranks))
        desc = tuple(sorted(ranks, reverse=True))
        plain[key] = _score_ranks(desc, False)
        if len(set(ranks)) == 5:
            flush[key] = _score_ranks(desc, True)
    return plain, flush


PLAIN, FLUSH_T = _build_tables()
# One interleaved table so a single gather scores a hand: index = 2 * key + is_flush.
BOTH = np.empty(2 * _TABLE_SIZE, dtype=np.int32)
BOTH[0::2] = PLAIN
BOTH[1::2] = FLUSH_T

PAIRS = np.array(list(combinations(range(5), 2)), dtype=np.int64)          # (10, 2)
TRIPLES = {n: np.array(list(combinations(range(n), 3)), dtype=np.int64) for n in (3, 4, 5)}


def _pair_parts(hole: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """hole: (N, 5) cards -> (N, 10) rank keys and (N, 10) suit (-1 if offsuit)."""
    r = POW5[hole >> 2]
    s = hole & 3
    a, b = PAIRS[:, 0], PAIRS[:, 1]
    key = r[:, a] + r[:, b]
    suit = np.where(s[:, a] == s[:, b], s[:, a], -1)
    return key, suit


def _triple_parts(board: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """board: (N, n) cards, n in 3..5 -> (N, T) rank keys and suit (-2 if not monotone)."""
    t = TRIPLES[board.shape[1]]
    r = POW5[board >> 2]
    s = board & 3
    a, b, c = t[:, 0], t[:, 1], t[:, 2]
    key = r[:, a] + r[:, b] + r[:, c]
    suit = np.where((s[:, a] == s[:, b]) & (s[:, b] == s[:, c]), s[:, a], -2)
    return key, suit


pair_parts = _pair_parts
triple_parts = _triple_parts


def combine(hk, hs, bk, bs) -> np.ndarray:
    """Best score per row from precomputed parts; rows broadcast (1 vs N is fine)."""
    idx = 2 * (hk[:, :, None] + bk[:, None, :]) + (hs[:, :, None] == bs[:, None, :])
    return BOTH[idx].reshape(idx.shape[0], -1).max(axis=1)


def best_scores(hole: np.ndarray, board: np.ndarray) -> np.ndarray:
    """Best Omaha (exactly 2 + 3) score for each row. hole (N, 5), board (N, n>=3).

    With a 3- or 4-card board this is the best hand made so far.
    """
    hk, hs = _pair_parts(hole)
    bk, bs = _triple_parts(board)
    return combine(hk, hs, bk, bs)


def score_one(hole, board) -> int:
    """Best score for one hand (board of 3 to 5 cards)."""
    return int(best_scores(np.asarray(hole, dtype=np.int64)[None, :],
                           np.asarray(board, dtype=np.int64)[None, :])[0])
