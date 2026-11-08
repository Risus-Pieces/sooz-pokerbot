"""Field bot that plays the MCCFR blueprint (blueprint.py) directly.

Checkpoint: env BP_PATH (default data/bp/latest.npz).
Env BP_MINP (default 0): actions with blueprint probability below it are dropped
before sampling (purification). If the blueprint has no answer (tree mismatch,
load failure) it falls back to a pot-odds rule on cardabs equity.
"""
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import cardabs  # noqa: E402
from blueprint import Blueprint, sample  # noqa: E402
from brain import preflop_equity  # noqa: E402
from game import Action, Street  # noqa: E402

_BP_CACHE = {}


def _get_bp(path):
    bp = _BP_CACHE.get(path)
    if bp is None:
        bp = Blueprint()
        bp.load(path)
        _BP_CACHE[path] = bp
    return bp


def new_half(config, memory):
    path = os.environ.get("BP_PATH") or os.path.join(_ROOT, "data", "bp", "latest.npz")
    memory["bp"] = _get_bp(path)
    memory["minp"] = float(os.environ.get("BP_MINP", "0") or 0)
    memory["rng"] = np.random.default_rng(int(os.environ.get("BP_SEED", "1234")))
    memory["cache"] = {}
    memory["think"] = 0.0
    memory["fallbacks"] = 0
    memory["decisions"] = 0


def _fallback(obs):
    legal = obs.legal_actions
    try:
        if obs.street == Street.PREFLOP:
            eq = preflop_equity(obs.hole_cards)
        else:
            eq = cardabs.features(obs.hole_cards, obs.board)[0]
    except Exception:  # noqa: BLE001
        eq = 0.5
    if obs.to_call == 0:
        return Action.CHECK_CALL
    odds = obs.to_call / (obs.pot + obs.to_call)
    if eq > odds and Action.CHECK_CALL in legal:
        return Action.CHECK_CALL
    return Action.FOLD if Action.FOLD in legal else Action.CHECK_CALL


def choose_action(obs, memory):
    t0 = time.perf_counter()
    a = None
    try:
        memory["decisions"] += 1
        probs = memory["bp"].policy(obs, memory["cache"], memory["rng"])
        if probs:
            a = sample(probs, memory["rng"], memory["minp"])
    except Exception:  # noqa: BLE001
        a = None
    if a not in obs.legal_actions:
        memory["fallbacks"] += 1
        a = _fallback(obs)
    if a not in obs.legal_actions:
        a = Action.CHECK_CALL if obs.to_call == 0 else Action.FOLD
    memory["think"] += time.perf_counter() - t0
    return a


def on_hand_end(result, memory):
    pass
