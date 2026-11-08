"""anti/barrel - relentless multi-street aggression.

Idea: hunter's call/raise EV is one-street (it ignores that a called bet will
face more bets later), and its read of our betting range comes only from the
hands that reach showdown. A bot that fires pot-sized bets on every street
makes hunter pay 'per street' with medium hands it would never call a single
all-in with.

Policy:
  preflop  raise pot with the top ~70% of hands when unopened, call raises with
           pot odds, 3-bet the top ~20%.
  postflop when checked to (or first to act) bet pot nearly always; when hunter
           bets/raises into us raise strong hands, call with pot odds, else fold.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import numpy as np  # noqa: E402

from brain import Rollout, preflop_equity, preflop_top_fraction  # noqa: E402
from game import Action, Street  # noqa: E402

BET_FREQ = 0.92       # bet when checked to
RAISE_EQ = 0.74       # raise a bet with this equity vs random
CALL_SLACK = 0.02     # call if eq > pot odds - slack


def _feat(obs, rng):
    if obs.street == Street.PREFLOP:
        return preflop_equity(obs.hole_cards), 1.0 - preflop_top_fraction(obs.hole_cards)
    roll = Rollout(obs.hole_cards, obs.board, 48, rng)
    e = float(roll.win.mean())
    return e, e


def new_half(config, memory):
    memory["rng"] = np.random.default_rng(1)


def choose_action(obs, memory):
    rng, legal = memory["rng"], obs.legal_actions
    can_raise = Action.RAISE_POT in legal
    eq, pct = _feat(obs, rng)
    odds = obs.to_call / (obs.pot + obs.to_call) if obs.to_call else 0.0
    if obs.street == Street.PREFLOP:
        if obs.raises_this_street == 0 and can_raise:
            if pct > 0.30:
                return Action.RAISE_POT
            return Action.CHECK_CALL if obs.to_call <= 1 or pct > 0.15 else Action.FOLD
        if can_raise and pct > 0.80:
            return Action.RAISE_POT
        if obs.to_call == 0 or eq > odds - CALL_SLACK:
            return Action.CHECK_CALL
        return Action.FOLD
    if obs.to_call == 0:
        if can_raise and (eq > 0.55 or rng.random() < BET_FREQ):
            return Action.RAISE_POT
        return Action.CHECK_CALL
    if can_raise and eq > RAISE_EQ:
        return Action.RAISE_POT
    if eq > odds - CALL_SLACK:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
