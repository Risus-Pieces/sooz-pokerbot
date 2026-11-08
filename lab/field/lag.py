"""Loose-aggressive: bluffs often, raises medium hands, calls wide."""
import numpy as np
from brain import equity, preflop_equity
from game import Action, Street


def new_half(config, memory):
    memory["rng"] = np.random.default_rng(13)


def choose_action(obs, memory):
    rng, legal = memory["rng"], obs.legal_actions
    eq = preflop_equity(obs.hole_cards) if obs.street == Street.PREFLOP else equity(obs.hole_cards, obs.board, 100, rng)
    can_raise = Action.RAISE_POT in legal
    if can_raise and (eq > 0.6 or rng.random() < 0.3):
        return Action.RAISE_POT if rng.random() < 0.6 else Action.RAISE_HALF
    if obs.to_call == 0:
        return Action.CHECK_CALL
    odds = obs.to_call / (obs.pot + obs.to_call)
    if eq > odds - 0.05:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
