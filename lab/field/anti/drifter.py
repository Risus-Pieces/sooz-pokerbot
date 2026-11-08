"""anti/drifter - tight-passive for SWITCH hands, then maniac.

Idea: hunter's opponent model is a cumulative Beta count over the whole half
(no decay). 300 hands of nit play teach it that (a) we rarely bet, (b) our
shown aggressive hands are near-nuts (narrow range => it folds to bets),
(c) we fold to its bets. After the switch we bet/raise relentlessly and the
stale counts keep hunter folding for a long time.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import numpy as np  # noqa: E402

from brain import Rollout, preflop_equity, preflop_top_fraction  # noqa: E402
from game import Action, Street  # noqa: E402

SWITCH = 300


def _feat(obs, rng):
    if obs.street == Street.PREFLOP:
        return preflop_equity(obs.hole_cards), 1.0 - preflop_top_fraction(obs.hole_cards)
    roll = Rollout(obs.hole_cards, obs.board, 48, rng)
    e = float(roll.win.mean())
    return e, e


def new_half(config, memory):
    memory["rng"] = np.random.default_rng(4)


def _nit(obs, eq, pct, odds, can_raise):
    if obs.street == Street.PREFLOP:
        if can_raise and pct > 0.9:
            return Action.RAISE_POT
        if obs.to_call == 0 or (pct > 0.45 and eq > odds + 0.05):
            return Action.CHECK_CALL
        return Action.FOLD
    if can_raise and eq > 0.82:
        return Action.RAISE_POT
    if obs.to_call == 0:
        return Action.CHECK_CALL
    if eq > odds + 0.12:
        return Action.CHECK_CALL
    return Action.FOLD


def _maniac(obs, eq, pct, odds, can_raise, rng):
    if obs.street == Street.PREFLOP:
        if can_raise and (pct > 0.25 and obs.raises_this_street < 2 or pct > 0.85):
            return Action.RAISE_POT
        if obs.to_call == 0 or eq > odds - 0.03:
            return Action.CHECK_CALL
        return Action.FOLD
    if obs.to_call == 0:
        if can_raise and (eq > 0.5 or rng.random() < 0.9):
            return Action.RAISE_POT
        return Action.CHECK_CALL
    if can_raise and (eq > 0.72 or (obs.raises_this_street < 2 and rng.random() < 0.3)):
        return Action.RAISE_POT
    if eq > odds - 0.03:
        return Action.CHECK_CALL
    return Action.FOLD


def choose_action(obs, memory):
    rng, legal = memory["rng"], obs.legal_actions
    can_raise = Action.RAISE_POT in legal
    eq, pct = _feat(obs, rng)
    odds = obs.to_call / (obs.pot + obs.to_call) if obs.to_call else 0.0
    if obs.hand_index < SWITCH:
        return _nit(obs, eq, pct, odds, can_raise)
    return _maniac(obs, eq, pct, odds, can_raise, rng)


def on_hand_end(result, memory):
    pass
