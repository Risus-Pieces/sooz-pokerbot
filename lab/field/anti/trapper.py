"""anti/trapper - slowplay strong hands, bet weak ones.

Idea: hunter estimates our betting range from showdowns of hands we were
aggressive with, and treats checks as 'passive'. We invert the usual
correlation: monsters check/call until the river (then raise/bet pot), weak
hands bet half pot as bluffs, medium hands check and call with pot odds.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import numpy as np  # noqa: E402

from brain import Rollout, preflop_equity, preflop_top_fraction  # noqa: E402
from game import Action, Street  # noqa: E402

MONSTER = 0.78
WEAK = 0.33
BLUFF_FREQ = 0.65


def _feat(obs, rng):
    if obs.street == Street.PREFLOP:
        return preflop_equity(obs.hole_cards), 1.0 - preflop_top_fraction(obs.hole_cards)
    roll = Rollout(obs.hole_cards, obs.board, 48, rng)
    e = float(roll.win.mean())
    return e, e


def new_half(config, memory):
    memory["rng"] = np.random.default_rng(3)


def choose_action(obs, memory):
    rng, legal = memory["rng"], obs.legal_actions
    can_raise = Action.RAISE_POT in legal
    eq, pct = _feat(obs, rng)
    odds = obs.to_call / (obs.pot + obs.to_call) if obs.to_call else 0.0
    if obs.street == Street.PREFLOP:
        if pct > 0.85:   # trap preflop too: just call
            return Action.CHECK_CALL
        if obs.raises_this_street == 0 and can_raise and pct < 0.35 and rng.random() < 0.5:
            return Action.RAISE_HALF
        if obs.to_call <= 1 or obs.to_call == 0 or eq > odds:
            return Action.CHECK_CALL
        return Action.FOLD
    river = obs.street == Street.RIVER
    if eq > MONSTER:
        if river and can_raise:
            return Action.RAISE_POT
        return Action.CHECK_CALL
    if obs.to_call == 0:
        if can_raise and eq < WEAK and rng.random() < BLUFF_FREQ:
            return Action.RAISE_HALF
        return Action.CHECK_CALL
    if eq > odds:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
