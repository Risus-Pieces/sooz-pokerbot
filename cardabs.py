"""
cardabs.py - runtime card abstraction for the blueprint (pure numpy).

Features match solver/pool.cpp (core.hpp `features`):
  ehs = win chance (ties half) vs a uniformly random opponent hand, with the
        board run out to the river (opponent hand and runout drawn from the
        cards we cannot see)
  hs  = share of random opponent hands our CURRENT made hand beats on the
        current board (ties half); on the river hs = ehs
The pool estimates them with 600 Monte Carlo samples. Here we use pair tables
(score of every possible opponent 2-card combination against every board
triple) so the opponent side is nearly free, which gives lower noise than the
pool for the same time:
  river hs : exact pair table on the 5-card board + N_HS fixed opponent subsets
  turn  hs : exact pair table on the 4-card board + N_HS subsets
  turn ehs : pair tables for all 27 possible rivers + N_TURN (river, opponent) draws
  flop  hs : pair table on the flop + N_HS subsets
  flop ehs : pair/runout decomposition + N_FLOP (turn, river, opponent) draws
Random subsets are fixed tables (seeded) so results are deterministic.

Buckets use data/abs.npz (written by lab/bucketize.py):
  preflop = pre_class[colex(sorted hole)]  (lossless suit-isomorphism class)
  flop/turn = EHS bin * NB_H + HS bin within that EHS bin, river = HS bin.

API:
  load(path=None) -> bool
  features(hole, board) -> (ehs, hs)      (board of 3, 4 or 5 cards)
  bucket(hole, board) -> int              (board of 0, 3, 4 or 5 cards)
  bucket_cached(hole, board, cache, key) -> int
"""

from __future__ import annotations

from itertools import combinations
from math import comb
from pathlib import Path

import numpy as np

from fasteval import BOTH, POW5 as _POW5_64

POW5 = _POW5_64.astype(np.int32)

_ABS_PATH = Path(__file__).resolve().parent / "data" / "abs.npz"
_A: dict | None = None

_P10 = np.array(list(combinations(range(5), 2)), dtype=np.int64)          # (10,2) pairs of a 5-card hand
_PA, _PB = _P10[:, 0], _P10[:, 1]
_T = {n: np.array(list(combinations(range(n), 3)), dtype=np.int64) for n in (3, 4, 5)}
_B4PAIRS = np.array(list(combinations(range(4), 2)), dtype=np.int64)      # (6,2) pairs of board4
_B3PAIRS = np.array(list(combinations(range(3), 2)), dtype=np.int64)      # (3,2) pairs of the flop
_NB = len(BOTH) - 1      # clip for impossible combos (a card used twice); those values are never read
_COMB = np.array([[comb(n, k) for k in range(6)] for n in range(37)], dtype=np.int64)

N_HS = 1024
N_TURN = 2048
N_FLOP = 512


def _subsets(npos: int, k: int, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.argsort(rng.random((n, npos)), axis=1)[:, :k].astype(np.int64)


# pair numbering among m unseen cards (by position): pair p = (I[p], J[p]), I < J
_TRIU = {m: tuple(np.triu_indices(m, 1)) for m in (26, 27, 28)}
_PIDX = {}
for _m, (_i, _j) in _TRIU.items():
    _x = np.zeros((_m, _m), dtype=np.int64)
    _x[_i, _j] = np.arange(len(_i))
    _x[_j, _i] = np.arange(len(_i))
    _PIDX[_m] = _x


def _opp_pairs(S5: np.ndarray, m: int) -> np.ndarray:
    """(n,5) positions among m -> (n,10) pair indices of the opponent's 10 two-card combos."""
    return _PIDX[m][S5[:, _PA], S5[:, _PB]]


# fixed random position tables
_S_RIVER = _opp_pairs(_subsets(26, 5, N_HS, 101), 26)
_S_TURN_HS = _opp_pairs(_subsets(27, 5, N_HS, 102), 27)
_S_FLOP_HS = _opp_pairs(_subsets(28, 5, N_HS, 103), 28)
_st = _subsets(27, 6, N_TURN, 104)                    # [river, opp x5] among 27
_TURN_R = _st[:, 0]
_TURN_FLAT = _opp_pairs(_st[:, 1:], 27) * 27 + _TURN_R[:, None]      # into v (P,27) flattened
_sf = _subsets(28, 7, N_FLOP, 105)                    # [turn, river, opp x5] among 28
_FLOP_T, _FLOP_R = _sf[:, 0], _sf[:, 1]
_FLOP_P = _opp_pairs(_sf[:, 2:], 28)                  # (n,10) pair idx
_FLOP_GT = _FLOP_P * 28 + _FLOP_T[:, None]            # into G (P,28) flattened
_FLOP_GR = _FLOP_P * 28 + _FLOP_R[:, None]


def _card_parts(c: np.ndarray):
    c = c.astype(np.int32)
    return POW5[c >> 2], c & 3


def _rem(hole: np.ndarray, board: np.ndarray) -> np.ndarray:
    used = np.zeros(36, dtype=bool)
    used[hole] = True
    used[board] = True
    return np.flatnonzero(~used).astype(np.int64)


def _triples(board: np.ndarray):
    t = _T[len(board)]
    r, s = _card_parts(board)
    key = r[t[:, 0]] + r[t[:, 1]] + r[t[:, 2]]
    suit = np.where((s[t[:, 0]] == s[t[:, 1]]) & (s[t[:, 1]] == s[t[:, 2]]), s[t[:, 0]], -2)
    return key, suit


def _hole_pairs(hole: np.ndarray):
    r, s = _card_parts(hole)
    key = r[_PA] + r[_PB]
    suit = np.where(s[_PA] == s[_PB], s[_PA], -1)
    return key, suit


def _rem_pairs(rem: np.ndarray):
    """pair keys/suits of all unseen 2-card combos, in _TRIU order."""
    i, j = _TRIU[len(rem)]
    r, s = _card_parts(rem)
    return r[i] + r[j], np.where(s[i] == s[j], s[i], -1), r, s


def _wr(mine, theirs) -> float:
    return float(((mine > theirs).sum() + 0.5 * (mine == theirs).sum()) / theirs.size)


def _bmax(pk, ps, tks, tss, clip=False):
    """max over k of BOTH[2*(pk + tks[k]) + (ps == tss[k])]; tks/tss index along axis 0
    (each slice broadcastable against pk). Looping over the few triples keeps every
    temporary small and contiguous (much faster than a 3-D gather + max(axis))."""
    out = None
    for k in range(len(tks)):
        idx = (pk + tks[k]) * 2 + (ps == tss[k])
        if clip:
            np.minimum(idx, _NB, out=idx)
        v = BOTH[idx]
        out = v if out is None else np.maximum(out, v, out=out)
    return out


_R9 = POW5[:9]


_PK81 = (_R9[:, None] + _R9[None, :]).ravel()          # rank key of a 2-card rank combo id = ra*9 + rb
_R81 = _PK81                                             # same table used for (turn rank, river rank)


def _plain_x_table(bk_list):
    """flat (81*9,) plain score of (2-card rank combo id, card rank x) with board rank keys
    bk_list[k] (one or two board cards), max over k. Rank-only, so tiny; entries for
    impossible rank counts are clipped (never read)."""
    W = None
    for k in range(len(bk_list)):
        idx = (_PK81[:, None] + (bk_list[k] + _R9)[None, :]) * 2
        np.minimum(idx, _NB, out=idx)
        v = BOTH[idx]
        W = v if W is None else np.maximum(W, v, out=W)
    return W.ravel()


def _rank_ids(rem):
    """rank combo id (ra*9+rb) of every unseen pair in _TRIU order, and ranks of rem."""
    i, j = _TRIU[len(rem)]
    rk = rem >> 2
    return rk[i] * 9 + rk[j], rk


def _pair_x_table(pk, ps, rem, rr, rs, bpk, bps):
    """(P, m) best score of each unseen pair p with triples (board pair k + unseen card x),
    max over the board pairs k. Plain (non-flush) scores depend only on ranks (tabulated by
    _plain_x_table); flushes are patched in for the few suited pairs / suited x of a suited
    board pair (a flush always outscores the same ranks unsuited). Entries where x is one
    of the pair's cards are meaningless (never read)."""
    pid, rk = _rank_ids(rem)
    out = _plain_x_table(bpk)[(pid * 9)[:, None] + rk[None, :]]
    for k in range(len(bpk)):
        s = bps[k]
        if s < 0:
            continue
        sp = np.flatnonzero(ps == s)
        sx = np.flatnonzero(rs == s)
        if len(sp) == 0 or len(sx) == 0:
            continue
        idx = (pk[sp][:, None] + (bpk[k] + rr[sx])[None, :]) * 2 + 1
        np.minimum(idx, _NB, out=idx)
        ix = np.ix_(sp, sx)
        out[ix] = np.maximum(out[ix], BOTH[idx])
    return out


def _hs(hole, board, rem, SP) -> float:
    tk, ts = _triples(board)
    pk, ps, _, _ = _rem_pairs(rem)
    v = _bmax(pk, ps, tk, ts)                                  # (P,)
    theirs = v[SP].max(axis=1)
    hk, hs = _hole_pairs(hole)
    mine = _bmax(hk, hs, tk, ts).max()
    return _wr(mine, theirs)


def _turn_ehs(hole, board, rem) -> float:
    """board: 4 cards, rem: 27 unseen cards."""
    tk4, ts4 = _triples(board)                                 # 4 board-only triples
    br, bs = _card_parts(board)
    pa, pb = _B4PAIRS[:, 0], _B4PAIRS[:, 1]
    bpk = br[pa] + br[pb]                                      # (6,)
    bps = np.where(bs[pa] == bs[pb], bs[pa], -2)
    pk, ps, rr, rs = _rem_pairs(rem)
    tk = bpk[:, None] + rr[None, :]                            # (6,27) triples with the river
    ts = np.where(bps[:, None] == rs[None, :], rs[None, :], -2)
    base = _bmax(pk, ps, tk4, ts4)                             # (P,)
    withr = _pair_x_table(pk, ps, rem, rr, rs, bpk, bps)      # (P,27)
    v = np.maximum(base[:, None], withr).ravel()
    hk, hs = _hole_pairs(hole)
    mine4 = _bmax(hk, hs, tk4, ts4).max()
    mine_r = _bmax(hk[:, None], hs[:, None], tk[:, None, :], ts[:, None, :]).max(axis=0)   # (27,)
    mine_r = np.maximum(mine_r, mine4)
    theirs = v[_TURN_FLAT].max(axis=1)
    return _wr(mine_r[_TURN_R], theirs)


def _flop_ehs(hole, board, rem) -> float:
    """board: 3 cards, rem: 28 unseen cards.  board5 triples = flop (1) +
    two flop cards with turn (3) + two flop cards with river (3) + one flop card with turn and river (3)."""
    br, bs = _card_parts(board)
    fk = br.sum()
    fs = bs[0] if (bs[0] == bs[1] == bs[2]) else -2
    pa, pb = _B3PAIRS[:, 0], _B3PAIRS[:, 1]
    bpk = br[pa] + br[pb]                                      # (3,)
    bps = np.where(bs[pa] == bs[pb], bs[pa], -2)
    pk, ps, rr, rs = _rem_pairs(rem)
    gk = bpk[:, None] + rr[None, :]                            # (3,28) flop-pair + x
    gs = np.where(bps[:, None] == rs[None, :], rs[None, :], -2)
    F = BOTH[2 * (pk + fk) + (ps == fs)]                       # (P,)
    t, r = _FLOP_T, _FLOP_R
    P = _FLOP_P
    n = len(t)
    pid, rk = _rank_ids(rem)
    Wf = _plain_x_table(bpk)
    pidP9 = pid[P] * 9                                         # (n,10)
    GT = Wf[pidP9 + rk[t][:, None]]
    GR = Wf[pidP9 + rk[r][:, None]]
    opk, ops = pk[P], ps[P]                                    # (n,10)
    s_t, s_r = rs[t], rs[r]
    for k in range(3):                                         # flush patches (suited flop pair k)
        sk = bps[k]
        if sk < 0:
            continue
        for x, sx, Gx in ((t, s_t, GT), (r, s_r, GR)):
            m = np.flatnonzero(((ops == sk) & (sx == sk)[:, None]).ravel())
            if m.size:
                vals = BOTH[2 * (opk.ravel()[m] + bpk[k] + rr[x][m // 10]) + 1]
                rows, cols = m // 10, m % 10           # (Gx may not be C-contiguous: index, don't reshape)
                Gx[rows, cols] = np.maximum(Gx[rows, cols], vals)
    th = np.maximum(np.maximum(F[P], GT), GR)                                                     # (n,10)
    # H: one flop card + turn + river (3 triples)
    hk_tr = br[:, None] + (rr[t] + rr[r])[None, :]                                                # (3,n)
    hs_tr = np.where((bs[:, None] == s_t[None, :]) & (s_t == s_r)[None, :], s_t[None, :], -2)     # (3,n)
    H = _bmax(opk, ops, hk_tr[:, :, None], hs_tr[:, :, None])                                     # (n,10)
    theirs = np.maximum(th, H).max(axis=1)
    # ours, same decomposition
    hk, hs = _hole_pairs(hole)
    mF = BOTH[2 * (hk + fk) + (hs == fs)].max()
    mG = _bmax(hk[:, None], hs[:, None], gk[:, None, :], gs[:, None, :]).max(axis=0)              # (28,)
    # our H term: plain by (turn rank, river rank) table, exact recompute for same-suit runouts
    MH = None
    for k in range(3):
        idx = (hk[:, None] + (br[k] + _R81)[None, :]) * 2
        np.minimum(idx, _NB, out=idx)
        v = BOTH[idx].max(axis=0)
        MH = v if MH is None else np.maximum(MH, v, out=MH)
    mH = MH[rk[t] * 9 + rk[r]]
    same = np.flatnonzero(s_t == s_r)
    if same.size:
        mH[same] = _bmax(hk[:, None], hs[:, None], hk_tr[:, None, same], hs_tr[:, None, same]).max(axis=0)
    mine = np.maximum(np.maximum(np.maximum(mF, mG[t]), mG[r]), mH)
    return _wr(mine, theirs)


def features(hole, board) -> tuple[float, float]:
    """(ehs, hs) for a 3-, 4- or 5-card board (pool.cpp definitions)."""
    hole = np.asarray(hole, dtype=np.int64)
    board = np.asarray(board, dtype=np.int64)
    rem = _rem(hole, board)
    nb = len(board)
    if nb == 5:
        h = _hs(hole, board, rem, _S_RIVER)
        return h, h
    if nb == 4:
        return _turn_ehs(hole, board, rem), _hs(hole, board, rem, _S_TURN_HS)
    if nb == 3:
        return _flop_ehs(hole, board, rem), _hs(hole, board, rem, _S_FLOP_HS)
    raise ValueError("board must have 3, 4 or 5 cards")


# ----------------------------------------------------------------------------- buckets

def load(path=None) -> bool:
    global _A
    try:
        z = np.load(path or _ABS_PATH)
        _A = {k: z[k] for k in z.files}
        return True
    except Exception:  # noqa: BLE001
        _A = None
        return False


def colex(hole) -> int:
    h = sorted(int(c) for c in hole)
    return int(_COMB[h[0], 1] + _COMB[h[1], 2] + _COMB[h[2], 3] + _COMB[h[3], 4] + _COMB[h[4], 5])


def _b2(e, h, ee, he) -> int:
    be = int(np.searchsorted(ee, np.float32(e), side="right"))
    bh = int((he[be] <= np.float32(h)).sum())
    return be * (he.shape[1] + 1) + bh


def bucket_from_features(street: int, ehs: float, hs: float) -> int:
    A = _A
    if street == 1:
        return _b2(ehs, hs, A["flop_e"], A["flop_h"])
    if street == 2:
        return _b2(ehs, hs, A["turn_e"], A["turn_h"])
    return int(np.searchsorted(A["river"], np.float32(hs), side="right"))


def bucket(hole, board) -> int:
    if _A is None and not load():
        raise RuntimeError("abs.npz not loaded")
    nb = len(board)
    if nb == 0:
        return int(_A["pre_class"][colex(hole)])
    street = {3: 1, 4: 2, 5: 3}[nb]
    e, h = features(hole, board)
    return bucket_from_features(street, e, h)


def bucket_cached(hole, board, cache: dict, key) -> int:
    b = cache.get(key)
    if b is None:
        b = bucket(hole, board)
        cache[key] = b
    return b
