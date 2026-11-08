"""Tight-passive: plays only strong hands, rarely bluffs."""
import numpy as np
from brain import equity, preflop_equity
from game import Action, Street


def new_half(config, memory):
    memory["rng"] = np.random.default_rng(12)


def choose_action(obs, memory):
    legal = obs.legal_actions
    if obs.street == Street.PREFLOP:
        eq = preflop_equity(obs.hole_cards)
        if eq > 0.62 and Action.RAISE_POT in legal:
            return Action.RAISE_POT
        if eq > 0.55 or obs.to_call == 0:
            return Action.CHECK_CALL
        return Action.FOLD
    eq = equity(obs.hole_cards, obs.board, 100, memory["rng"])
    if eq > 0.85 and Action.RAISE_POT in legal:
        return Action.RAISE_POT
    if obs.to_call == 0 or eq > 0.65:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
