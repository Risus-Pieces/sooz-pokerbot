"""Frozen snapshot of hunter v2 (the shipped bot at 2f47237), for regression tests."""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _strategy_v2 import PARAMS, Stats, choose, learn_from_hand  # noqa: E402
from game import Action  # noqa: E402


def new_half(config, memory):
    memory["rng"] = np.random.default_rng(99)
    memory["stats"] = Stats()
    memory["think"] = 0.0
    memory["pending"] = None
    memory["seen"] = (-1, 0)


def choose_action(obs, memory):
    t0 = time.perf_counter()
    try:
        a = choose(obs, memory, PARAMS)
    except Exception:
        a = None
    if a not in obs.legal_actions:
        a = Action.CHECK_CALL
    memory["think"] += time.perf_counter() - t0
    return a


def on_hand_end(result, memory):
    try:
        learn_from_hand(result, memory)
    except Exception:
        memory["pending"] = None
