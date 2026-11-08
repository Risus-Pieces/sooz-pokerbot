"""anti/mirror_stationary - near-balanced, unexploitable-ish baseline.

Value-bets the top of its range and adds bluffs so the bluff share of the
betting range equals bet/(pot + 2*bet) (what makes a caller indifferent);
defends against bets by pot odds plus a small margin and raises only strong
hands (plus a few draws). Not adaptive: a control for 'does hunter beat a
sane static strategy, and by how much'.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import numpy as np  # noqa: E402

from brain import Rollout, preflop_equity, preflop_top_fraction  # noqa: E402
from fasteval import score_one  # noqa: E402
from game import Action, Street  # noqa: E402

VALUE = {1: 0.70, 2: 0.72, 3: 0.75}      # bet thresholds by street (eq vs random)
WEAK = 0.35                               # bluff candidates live below this


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
    memory["rng"] = np.random.default_rng(5)


def choose_action(obs, memory):
    rng, legal = memory["rng"], obs.legal_actions
    can_raise = Action.RAISE_POT in legal
    eq, pct, made = _feat(obs, rng)
    odds = obs.to_call / (obs.pot + obs.to_call) if obs.to_call else 0.0
    if obs.street == Street.PREFLOP:
        if can_raise and (obs.raises_this_street == 0 and pct > 0.55 or pct > 0.85 and obs.raises_this_street < 3):
            return Action.RAISE_POT
        if obs.to_call == 0 or obs.to_call <= 1 or eq > odds + 0.02:
            return Action.CHECK_CALL
        return Action.FOLD
    v = VALUE[int(obs.street)]
    if obs.to_call == 0:
        if can_raise:
            if eq > v:
                return Action.RAISE_POT
            # value share of all hands ~ (1 - v); bluffs should be 1/3 of the betting range
            n_value = 1.0 - v
            p_bluff = min(1.0, 0.5 * n_value / WEAK)
            if eq < WEAK and rng.random() < p_bluff:
                return Action.RAISE_POT
            if obs.street != Street.RIVER and eq - made > 0.2 and rng.random() < 0.5:
                return Action.RAISE_HALF
        return Action.CHECK_CALL
    if can_raise and (eq > v + 0.1 or (obs.street != Street.RIVER and eq - made > 0.25 and rng.random() < 0.3)):
        return Action.RAISE_POT
    if eq > odds + 0.04:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
