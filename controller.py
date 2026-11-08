"""
controller.py - stop-loss arm controller: hunter (H) by default, the MCCFR
blueprint (B) as a hedge.

Hunter exploits weak bots far better than the blueprint does, so it plays
every hand unless the evidence says it is losing badly: after at least
`min_hands` hands, if hunter's luck-adjusted result per hand has
mean < `loss_mean` and z < `loss_z`, the controller starts Thompson sampling
between the two arms (per hand, normal posteriors on luck-adjusted bb/hand,
with a prior that slightly favours hunter). Luck adjustment: when a hand
goes all-in before the river and reaches showdown, the realized result is
replaced by its equity-weighted expectation over the remaining board cards.
"""

from __future__ import annotations

import math
from itertools import combinations

import numpy as np

from fasteval import best_scores
from game import Action, Street

CFG = {
    "min_hands": 150,
    "check_every": 25,
    "loss_mean": -0.15,     # bb per hand
    "loss_z": -2.0,
    "prior_sd": 0.6,        # prior on an arm's true mean (bb/hand)
    "prior_b": -0.05,       # B starts slightly behind H
    "hand_sd": 8.0,         # fallback per-hand sd before enough data
    "start_mode": "H",      # "H" = stop-loss only; "compare" = Thompson sampling from hand 0
    "warmup_hunter": 0,     # in compare mode: play hunter only for this many hands first
}
RAISES = (Action.RAISE_HALF, Action.RAISE_POT)


class ArmStats:
    def __init__(self) -> None:
        self.n = 0
        self.s = 0.0
        self.ss = 0.0

    def add(self, x: float) -> None:
        self.n += 1
        self.s += x
        self.ss += x * x

    def mean(self) -> float:
        return self.s / self.n if self.n else 0.0

    def sd(self) -> float:
        if self.n < 20:
            return CFG["hand_sd"]
        m = self.mean()
        return math.sqrt(max(1.0, self.ss / self.n - m * m))

    def posterior(self, prior_mean: float) -> tuple[float, float]:
        v0 = CFG["prior_sd"] ** 2
        if self.n == 0:
            return prior_mean, math.sqrt(v0)
        vd = self.sd() ** 2 / self.n
        v = 1.0 / (1.0 / v0 + 1.0 / vd)
        return v * (prior_mean / v0 + self.mean() / vd), math.sqrt(v)


def init(memory: dict) -> None:
    memory["arms"] = {"H": ArmStats(), "B": ArmStats()}
    memory["ctl_mode"] = CFG["start_mode"]
    memory["arm"] = "H"
    memory["arm_hand"] = -1


def pick_arm(obs, memory: dict, bp_ok: bool, tier: int, rng) -> str:
    """Choose the arm once per hand (at our first decision of the hand)."""
    if memory.get("arm_hand") == obs.hand_index:
        return memory["arm"]
    memory["arm_hand"] = obs.hand_index
    arm = "H"
    if bp_ok and tier <= 1:
        H, B = memory["arms"]["H"], memory["arms"]["B"]
        if memory["ctl_mode"] == "H" and H.n >= CFG["min_hands"] and obs.hand_index % CFG["check_every"] == 0:
            z = H.mean() / (H.sd() / math.sqrt(H.n))
            if H.mean() < CFG["loss_mean"] and z < CFG["loss_z"]:
                memory["ctl_mode"] = "compare"
        if memory["ctl_mode"] == "compare" and obs.hand_index >= CFG["warmup_hunter"]:
            mh, sh = H.posterior(0.0)
            mb, sb = B.posterior(CFG["prior_b"])
            arm = "B" if rng.normal(mb, sb) > rng.normal(mh, sh) else "H"
    memory["arm"] = arm
    return arm


def opp_raised_this_street(obs) -> bool:
    return any(a.street == obs.street and not a.is_me and a.action in RAISES for a in obs.action_history)


def _allin_ev(my_hole, opp_hole, board_seen, full_board, pot: int, rng) -> float | None:
    """Equity-weighted net (chips) of an all-in decided with `board_seen` known."""
    known = len(board_seen)
    if known >= 5:
        return None
    used = set(my_hole) | set(opp_hole) | set(board_seen)
    rem = np.array([c for c in range(36) if c not in used], dtype=np.int64)
    k = 5 - known
    if k <= 2:
        runs = np.array(list(combinations(rem, k)), dtype=np.int64)
    else:
        runs = np.stack([rng.choice(rem, k, replace=False) for _ in range(300)])
    n = len(runs)
    boards = np.concatenate([np.broadcast_to(np.asarray(board_seen, dtype=np.int64), (n, known)), runs], axis=1)
    mine = best_scores(np.broadcast_to(np.asarray(my_hole, dtype=np.int64), (n, 5)), boards)
    theirs = best_scores(np.broadcast_to(np.asarray(opp_hole, dtype=np.int64), (n, 5)), boards)
    eq = float(((mine > theirs) + 0.5 * (mine == theirs)).mean())
    return (2.0 * eq - 1.0) * pot / 2.0


def record_hand(result, memory: dict, rng) -> None:
    """Credit the hand's luck-adjusted result (bb) to the arm that played it."""
    arm = memory.get("arm", "H") if memory.get("arm_hand") == result.hand_index else "H"
    net = float(result.my_net)
    if result.went_to_showdown and result.opp_hole is not None and result.pot >= 160:
        seen = memory.get("last_board", ())
        try:
            ev = _allin_ev(memory.get("my_hole", ()), result.opp_hole, seen, result.board, result.pot, rng)
            if ev is not None:
                net = ev
        except Exception:  # noqa: BLE001
            pass
    memory["arms"][arm].add(net / 2.0)
