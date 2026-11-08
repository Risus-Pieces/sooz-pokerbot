"""anti/checkraise - check-raise heavy.

Idea: hunter bets whenever f*pot + (1-f)*(e_c*final_pot - added) beats checking,
with f = our fold rate to its bets. It only learns that we RAISE its bets as a
reduced fold rate, and its raise EV ignores being re-raised. Out of position we
check everything and check-raise pot with strong hands, strong draws and a
share of air; in position we bet only strong hands and check back the rest.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import numpy as np  # noqa: E402

from brain import Rollout, preflop_equity, preflop_top_fraction  # noqa: E402
from fasteval import score_one  # noqa: E402
from game import Action, Street  # noqa: E402

CR_VALUE = 0.62      # check-raise for value above this equity
CR_DRAW = 0.18       # ...or when equity exceeds made-hand strength by this (draws)
CR_BLUFF = 0.30      # ...or as a pure bluff with this probability


def _feat(obs, rng):
    if obs.street == Street.PREFLOP:
        p = 1.0 - preflop_top_fraction(obs.hole_cards)
        return preflop_equity(obs.hole_cards), p, p
    roll = Rollout(obs.hole_cards, obs.board, 48, rng)
    e = float(roll.win.mean())
    mine = score_one(obs.hole_cards, obs.board)
    made = float(((roll.now < mine) + 0.5 * (roll.now == mine)).mean())
    return e, e, made


def new_half(config, memory):
    memory["rng"] = np.random.default_rng(2)


def choose_action(obs, memory):
    rng, legal = memory["rng"], obs.legal_actions
    can_raise = Action.RAISE_POT in legal
    eq, pct, made = _feat(obs, rng)
    odds = obs.to_call / (obs.pot + obs.to_call) if obs.to_call else 0.0
    if obs.street == Street.PREFLOP:
        if obs.raises_this_street == 0 and can_raise and pct > 0.6:
            return Action.RAISE_POT
        if can_raise and pct > 0.88:
            return Action.RAISE_POT
        if obs.to_call == 0 or obs.to_call <= 1 or eq > odds:
            return Action.CHECK_CALL
        return Action.FOLD
    if obs.to_call == 0:
        if obs.is_button and can_raise and eq > 0.70:
            return Action.RAISE_POT
        return Action.CHECK_CALL
    # facing a bet
    my_raises = sum(1 for a in obs.action_history if a.street == obs.street and a.is_me
                    and a.action in (Action.RAISE_HALF, Action.RAISE_POT))
    if can_raise and my_raises == 0:
        if eq > CR_VALUE or (eq - made) > CR_DRAW or rng.random() < CR_BLUFF:
            return Action.RAISE_POT
    if can_raise and eq > 0.82:
        return Action.RAISE_POT
    if eq > odds:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
