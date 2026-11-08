"""anti/baiter - teach hunter that we fold, then stop folding.

Hunter's fold-rate model (Stats.resp) is a cumulative Beta count over the
whole half with no decay. Phase 1 (hands < SWITCH): fold to every postflop
bet without a strong hand, so hunter's f climbs and its EV formula
f*pot + (1-f)*(...) starts betting/bluffing nearly every hand (at f > 1/3 a
pure half-pot bluff already beats checking). Phase 2: call those bets wide
and raise half-pot bets; the stale counts keep hunter over-bluffing for
hundreds of hands. Both phases stab when hunter checks.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import numpy as np  # noqa: E402

from brain import Rollout, preflop_equity, preflop_top_fraction  # noqa: E402
from fasteval import score_one  # noqa: E402
from game import Action, Street  # noqa: E402

RAISES = (Action.RAISE_HALF, Action.RAISE_POT)
SWITCH = 250
VALUE = {1: 0.66, 2: 0.70, 3: 0.74}
STAB = {1: 0.7, 2: 0.65, 3: 0.55}


def _feat(obs, rng):
    if obs.street == Street.PREFLOP:
        p = 1.0 - preflop_top_fraction(obs.hole_cards)
        return preflop_equity(obs.hole_cards), p, p
    roll = Rollout(obs.hole_cards, obs.board, 48, rng)
    e = float(roll.win.mean())
    if obs.street == Street.RIVER:
        return e, e, e
    mine = score_one(obs.hole_cards, obs.board)
    made = float(((roll.now < mine) + 0.5 * (roll.now == mine)).mean())
    return e, e, made


def new_half(config, memory):
    memory["rng"] = np.random.default_rng(8)


def choose_action(obs, memory):
    rng, legal = memory["rng"], obs.legal_actions
    can_raise = Action.RAISE_POT in legal
    eq, pct, made = _feat(obs, rng)
    odds = obs.to_call / (obs.pot + obs.to_call) if obs.to_call else 0.0
    st = obs.street
    hist = [a for a in obs.action_history if a.street == st]
    my_raises = sum(1 for a in hist if a.is_me and a.action in RAISES)
    opp_checked = any((not a.is_me) and a.action == Action.CHECK_CALL and a.amount == 0 for a in hist)
    last_opp = next((a for a in reversed(hist) if not a.is_me), None)
    phase2 = obs.hand_index >= SWITCH
    if st == Street.PREFLOP:
        if can_raise and (obs.raises_this_street == 0 and pct > 0.5 or pct > 0.88 and obs.raises_this_street < 3):
            return Action.RAISE_POT
        if obs.to_call == 0 or obs.to_call <= 1 or eq > odds + 0.02:
            return Action.CHECK_CALL
        return Action.FOLD
    s = int(st)
    if obs.to_call == 0:
        if can_raise:
            if eq > VALUE[s]:
                return Action.RAISE_POT
            if opp_checked and rng.random() < STAB[s]:
                return Action.RAISE_HALF if eq < 0.5 else Action.RAISE_POT
            if st != Street.RIVER and eq - made > 0.2 and rng.random() < 0.5:
                return Action.RAISE_POT
        return Action.CHECK_CALL
    pot_sized = last_opp is not None and last_opp.action == Action.RAISE_POT
    if not phase2:
        if can_raise and eq > 0.85:
            return Action.RAISE_POT
        if eq > 0.75 or (eq > odds + 0.35):
            return Action.CHECK_CALL
        return Action.FOLD
    # phase 2: punish the over-bluffing hunter
    if can_raise and eq > VALUE[s] + 0.1 + 0.06 * my_raises:
        return Action.RAISE_POT
    if can_raise and not pot_sized and my_raises == 0 and st != Street.RIVER and rng.random() < 0.3:
        return Action.RAISE_POT
    need = odds + (0.12 if pot_sized else -0.06)
    if st == Street.RIVER:
        need += 0.05
    if eq > need:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
