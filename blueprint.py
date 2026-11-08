"""
blueprint.py - runtime player for the MCCFR blueprint strategy.

    bp = Blueprint(); bp.load("data/bp/latest.npz")
    probs = bp.policy(obs, cache, rng)    # dict[Action, float] over obs.legal_actions, or None

The strategy file (written by lab/export_bp.py from a solver/mccfr2 checkpoint)
is an uncompressed .npz with
    s0..s3  uint8[decision_nodes_s][buckets_s][4]  average strategy x255 (illegal = 0)
    nb      int32[4] bucket counts, meta (str)
The betting tree comes from data/tree.npz (exact tree of game.py, players are
ROLES: 0 = button, 1 = big blind) and the card abstraction from cardabs.py.

policy() walks obs.action_history from the root (incrementally, cached per hand
in `cache`), checks the node against the observation (actor, street, pot,
to_call, legal actions) and returns None on any mismatch or error so the
caller can fall back. It never raises.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import cardabs
from game import Action

ROOT = Path(__file__).resolve().parent
DEFAULT_PATH = ROOT / "data" / "bp" / "latest.npz"
TREE_PATH = ROOT / "data" / "tree.npz"

ACTIONS = (Action.FOLD, Action.CHECK_CALL, Action.RAISE_HALF, Action.RAISE_POT)
TOTAL_CHIPS = 160      # 2 x 80, the only configuration the tree is valid for


class Blueprint:
    def __init__(self) -> None:
        self.ok = False
        self.tree = None
        self.dindex = None
        self.strat = None
        self.nb = None
        self.meta = ""

    # ------------------------------------------------------------------ loading
    def load(self, path=None, tree_path=None) -> bool:
        try:
            z = np.load(tree_path or TREE_PATH)
            tree = np.ascontiguousarray(z["tree"], dtype=np.int32)
            dindex = np.ascontiguousarray(z["dindex"], dtype=np.int32)
            s = np.load(path or DEFAULT_PATH, allow_pickle=False)
            strat = [np.ascontiguousarray(s[f"s{k}"]) for k in range(4)]
            nb = s["nb"].astype(np.int64)
            dec = tree[:, 1] >= 0
            for k in range(4):
                nd = int((dec & (tree[:, 0] == k)).sum())
                if strat[k].shape != (nd, int(nb[k]), 4):
                    raise ValueError(f"street {k}: strategy shape {strat[k].shape} != {(nd, int(nb[k]), 4)}")
            if not cardabs.load():
                raise ValueError("cardabs.load failed")
            if [int(x) for x in cardabs._A["nb"]] != [int(x) for x in nb]:
                raise ValueError(f"abs nb {cardabs._A['nb']} != strategy nb {nb}")
            self.tree, self.dindex, self.strat, self.nb = tree, dindex, strat, nb
            self.meta = str(s["meta"]) if "meta" in s.files else ""
            self.ok = True
        except Exception:  # noqa: BLE001
            self.ok = False
        return self.ok

    # ------------------------------------------------------------------ walking
    def walk(self, obs, cache: dict | None = None):
        """Tree node for the current decision, or None if the history does not fit the tree."""
        T = self.tree
        hist = obs.action_history
        role = 0 if obs.is_button else 1
        node, start = 0, 0
        w = cache.get("bpw") if cache is not None else None
        if w is not None and w[0] == obs.hand_index and w[1] <= len(hist):
            start, node = w[1], w[2]
        for k in range(start, len(hist)):
            a = hist[k]
            row = T[node]
            actor = role if a.is_me else 1 - role
            if row[1] != actor or row[0] != int(a.street):
                return None
            nxt = int(row[6 + int(a.action)])
            if nxt < 0:
                return None
            node = nxt
        if cache is not None:
            cache["bpw"] = (obs.hand_index, len(hist), node)
        return node

    def check(self, node: int, obs) -> bool:
        row = self.tree[node]
        role = 0 if obs.is_button else 1
        if row[1] != role or row[0] != int(obs.street):
            return False
        cb, co = int(row[4]), int(row[5])
        mine = cb if role == 0 else co
        if cb + co != obs.pot or max(cb, co) - mine != obs.to_call:
            return False
        if obs.pot + obs.my_stack + obs.opp_stack != TOTAL_CHIPS:
            return False
        legal = {a for a in ACTIONS if row[6 + int(a)] >= 0}
        return legal == set(obs.legal_actions)

    # ------------------------------------------------------------------ policy
    def bucket(self, obs, cache: dict | None = None) -> int:
        st = int(obs.street)
        key = ("bk", obs.hand_index, st)
        if cache is not None and key in cache:
            return cache[key]
        b = cardabs.bucket(obs.hole_cards, obs.board[: (0, 3, 4, 5)[st]])
        if cache is not None:
            cache[key] = b
        return b

    def probs_at(self, node: int, bucket: int) -> np.ndarray:
        """float64[4] strategy at a decision node for a bucket (illegal = 0, sums to 1)."""
        row = self.tree[node]
        st = int(row[0])
        p = self.strat[st][self.dindex[node], bucket].astype(np.float64)
        legal = row[6:10] >= 0
        p[~legal] = 0.0
        tot = p.sum()
        if tot <= 0:
            p = legal.astype(np.float64)
            tot = p.sum()
        return p / tot

    def policy(self, obs, cache: dict | None = None, rng=None):
        """dict[Action, float] over obs.legal_actions, or None (no blueprint answer)."""
        try:
            if not self.ok:
                return None
            if cache is not None and cache.get("bph") != obs.hand_index:
                cache.clear()                     # keep only the current hand
                cache["bph"] = obs.hand_index
            node = self.walk(obs, cache)
            if node is None or not self.check(node, obs):
                return None
            b = self.bucket(obs, cache)
            if not (0 <= b < self.nb[int(obs.street)]):
                return None
            p = self.probs_at(node, b)
            return {a: float(p[int(a)]) for a in obs.legal_actions}
        except Exception:  # noqa: BLE001
            return None


def sample(probs: dict, rng, min_prob: float = 0.0):
    """Sample an Action from a policy dict; actions below min_prob are dropped first."""
    items = [(a, p) for a, p in probs.items() if p >= min_prob] or list(probs.items())
    tot = sum(p for _, p in items)
    if tot <= 0:
        return items[0][0]
    u = rng.random() * tot
    acc = 0.0
    for a, p in items:
        acc += p
        if u < acc:
            return a
    return items[-1][0]
