"""Typical 'LLM-written' bot: equity vs a random hand + pot odds."""
import numpy as np
from brain import equity, preflop_equity
from game import Action, Street


def new_half(config, memory):
    memory["rng"] = np.random.default_rng(11)


def choose_action(obs, memory):
    rng, legal = memory["rng"], obs.legal_actions
    eq = preflop_equity(obs.hole_cards) if obs.street == Street.PREFLOP else equity(obs.hole_cards, obs.board, 100, rng)
    if obs.to_call == 0:
        if eq > 0.70 and Action.RAISE_POT in legal:
            return Action.RAISE_POT
        if eq > 0.58 and Action.RAISE_HALF in legal:
            return Action.RAISE_HALF
        return Action.CHECK_CALL
    odds = obs.to_call / (obs.pot + obs.to_call)
    if eq > 0.75 and Action.RAISE_POT in legal:
        return Action.RAISE_POT
    if eq > odds + 0.03:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
