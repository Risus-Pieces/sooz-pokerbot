"""
brain.py - hand-strength estimates shared by the bot and the lab.

equity()          Monte Carlo win chance vs a random (or filtered) opponent hand.
preflop_equity()  Precomputed win chance vs a random hand (data/preflop.npz).
"""

from __future__ import annotations

from itertools import permutations
from pathlib import Path

import numpy as np

from fasteval import best_scores, combine, pair_parts, triple_parts

DECK = np.arange(36, dtype=np.int64)
_PERMS = [p for p in permutations(range(4))]
_PRE_PATH = Path(__file__).resolve().parent / "data" / "preflop.npz"
_PRE_KEYS: np.ndarray | None = None
_PRE_EQ: np.ndarray | None = None


def canonical_key(hole) -> int:
    """Suit-isomorphism class of a 5-card hand, as an int (base-36 digits)."""
    best = None
    for p in _PERMS:
        t = sorted(((c >> 2) << 2) | p[c & 3] for c in hole)
        k = (((t[0] * 36 + t[1]) * 36 + t[2]) * 36 + t[3]) * 36 + t[4]
        if best is None or k < best:
            best = k
    return best


def _load_preflop() -> None:
    global _PRE_KEYS, _PRE_EQ
    if _PRE_KEYS is None and _PRE_PATH.exists():
        z = np.load(_PRE_PATH)
        _PRE_KEYS, _PRE_EQ = z["keys"], z["eq"]


def preflop_equity(hole, rng=None) -> float:
    """Win chance vs a random hand before the flop (table lookup, MC fallback)."""
    _load_preflop()
    if _PRE_KEYS is not None:
        k = canonical_key(hole)
        i = int(np.searchsorted(_PRE_KEYS, k))
        if i < len(_PRE_KEYS) and _PRE_KEYS[i] == k:
            return float(_PRE_EQ[i])
    return equity(hole, (), 200, rng or np.random.default_rng())


_PRE_SORTED: np.ndarray | None = None


def preflop_top_fraction(hole) -> float:
    """Share of random hands whose preflop equity is at least this hand's."""
    global _PRE_SORTED
    if _PRE_SORTED is None:
        rng = np.random.default_rng(7)
        _PRE_SORTED = np.sort([preflop_equity(tuple(rng.choice(36, 5, replace=False)))
                               for _ in range(2000)])
    e = preflop_equity(hole)
    return float(1.0 - np.searchsorted(_PRE_SORTED, e, side="left") / len(_PRE_SORTED))


def warm() -> None:
    """Load tables at server start so the first decisions don't pay for it."""
    _load_preflop()
    preflop_top_fraction((0, 5, 10, 15, 20))
    Rollout((0, 5, 10, 15, 20), (1, 6, 11), 16, np.random.default_rng(0))


def postflop_top_fraction(hole, board, exclude, n: int, rng) -> float:
    """Share of random hands whose made hand on `board` is at least as good as `hole`'s."""
    hole = np.asarray(hole, dtype=np.int64)
    board = np.asarray(board, dtype=np.int64)
    used = np.zeros(36, dtype=bool)
    used[hole] = True
    used[board] = True
    used[np.asarray(list(exclude), dtype=np.int64)] = True
    rem = DECK[~used]
    others = _sample(rem, n, 5, rng)
    bk, bs = triple_parts(board[None, :])
    hk, hs = pair_parts(hole[None, :])
    mine = combine(hk, hs, bk, bs)[0]
    ok, os_ = pair_parts(others)
    theirs = combine(ok, os_, np.broadcast_to(bk, (n, bk.shape[1])), np.broadcast_to(bs, (n, bs.shape[1])))
    return float((theirs >= mine).mean())


def _sample(rem: np.ndarray, n: int, k: int, rng) -> np.ndarray:
    """n rows of k distinct cards drawn from rem."""
    idx = rng.random((n, len(rem))).argsort(axis=1)[:, :k]
    return rem[idx]


class Rollout:
    """One batch of simulated opponent hands and runouts, reusable for
    equity against several assumed opponent ranges."""

    def __init__(self, hole, board, n: int, rng) -> None:
        hole = np.asarray(hole, dtype=np.int64)
        board = np.asarray(board, dtype=np.int64)
        used = np.zeros(36, dtype=bool)
        used[hole] = True
        used[board] = True
        rem = DECK[~used]
        need = 5 - len(board)
        draw = _sample(rem, n, 5 + need, rng)
        opp = draw[:, :5]
        my_k, my_s = pair_parts(hole[None, :])
        op_k, op_s = pair_parts(opp)
        if need:
            full = np.concatenate([np.broadcast_to(board, (n, len(board))), draw[:, 5:]], axis=1)
            bk, bs = triple_parts(full)
            self.mine = combine(np.broadcast_to(my_k, (n, 10)), np.broadcast_to(my_s, (n, 10)), bk, bs)
        else:  # river: the board is fixed, so our score is one number
            bk, bs = triple_parts(board[None, :])
            self.mine = np.full(n, combine(my_k, my_s, bk, bs)[0])
        self.theirs = combine(op_k, op_s, np.broadcast_to(bk, (n, bk.shape[1])),
                              np.broadcast_to(bs, (n, bs.shape[1])))
        if len(board) >= 3:
            nk, ns = triple_parts(board[None, :])
            self.now = combine(op_k, op_s, np.broadcast_to(nk, (n, nk.shape[1])),
                               np.broadcast_to(ns, (n, ns.shape[1])))
            self.order = np.argsort(-self.now, kind="stable")
        else:
            self.now = None
            self.order = None
        self.win = (self.mine > self.theirs) + 0.5 * (self.mine == self.theirs)

    def eq(self, top_frac: float = 1.0) -> float:
        """Equity vs the opponent's top `top_frac` of hands by current made hand."""
        if top_frac >= 0.999 or self.order is None:
            return float(self.win.mean())
        k = max(8, int(round(len(self.win) * top_frac)))
        return float(self.win[self.order[:k]].mean())


def equity(hole, board, n: int, rng, top_frac: float = 1.0) -> float:
    """Chance to win (ties count half) against a random opponent hand.

    top_frac < 1 keeps only opponent hands whose made hand on the current
    board is in that top fraction of the sampled hands (a crude range read:
    "they bet, so they probably hold something"). Needs a flop or later.
    """
    hole = np.asarray(hole, dtype=np.int64)
    board = np.asarray(board, dtype=np.int64)
    used = np.zeros(36, dtype=bool)
    used[hole] = True
    used[board] = True
    rem = DECK[~used]
    need = 5 - len(board)
    draw = _sample(rem, n, 5 + need, rng)
    opp = draw[:, :5]
    full = np.concatenate([np.broadcast_to(board, (n, len(board))), draw[:, 5:]], axis=1)
    mine = best_scores(np.broadcast_to(hole, (n, 5)), full)
    theirs = best_scores(opp, full)
    if top_frac < 0.999 and len(board) >= 3:
        now = best_scores(opp, np.broadcast_to(board, (n, len(board))))
        cut = np.quantile(now, 1.0 - top_frac)
        keep = now >= cut
        if keep.sum() >= 8:
            mine, theirs = mine[keep], theirs[keep]
    return float(((mine > theirs) + 0.5 * (mine == theirs)).mean())
