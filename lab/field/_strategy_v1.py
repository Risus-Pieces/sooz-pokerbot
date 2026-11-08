"""
strategy.py - the decision logic: an expected-value chooser driven by a live
opponent model.

For every legal action we estimate its value in chips:
    fold   0
    call   e * (pot + to_call) - to_call
    raise  f * pot + (1 - f) * (e_c * final_pot - added)
where e is our win chance against the opponent's likely range, f is how
often this opponent folds to our raises (learned during the half), and e_c is
our win chance against the hands that continue. The opponent's range shrinks
as they show aggression, in proportion to how rarely they are aggressive.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from brain import Rollout, preflop_equity
from game import Action, Observation, Street

PARAMS = {
    "n_samples": 96,           # simulations per postflop decision
    "pre_range_k": 0.12,       # preflop equity drop vs a range that is "all strong"
    "raise_margin": 0.02,      # extra value (fraction of pot) a raise must beat a call by
    "oop_realize": 0.95,       # equity realized out of position before the river
    "min_top": 0.12,           # narrowest range we ever assume
    "time_target": 3.0,        # seconds of thinking we aim to use per half
}


@dataclass
class Stats:
    """Beta-smoothed counts of the opponent's habits for this half."""

    hands: int = 0
    # responses to OUR raises: [preflop, postflop] -> fold / call / raise
    resp: list = field(default_factory=lambda: [
        {"fold": 3.0, "call": 4.0, "raise": 1.0},
        {"fold": 3.0, "call": 4.0, "raise": 1.0}])
    # when nobody has bet yet this street: [preflop open, postflop] -> passive / aggressive
    open_: list = field(default_factory=lambda: [
        {"passive": 3.0, "aggr": 2.0}, {"passive": 3.0, "aggr": 2.0}])

    def record_response(self, street, kind: str) -> None:
        self.resp[0 if street == Street.PREFLOP else 1][kind] += 1.0

    def fold_rate(self, street) -> float:
        r = self.resp[0 if street == Street.PREFLOP else 1]
        return r["fold"] / (r["fold"] + r["call"] + r["raise"])

    def raise_rate(self, street) -> float:
        r = self.resp[0 if street == Street.PREFLOP else 1]
        return r["raise"] / (r["fold"] + r["call"] + r["raise"])

    def aggr_rate(self, street) -> float:
        o = self.open_[0 if street == Street.PREFLOP else 1]
        return o["aggr"] / (o["aggr"] + o["passive"])


def _update_model(obs: Observation, memory: dict) -> None:
    """Walk this hand's history and learn from opponent actions not yet seen."""
    stats: Stats = memory["stats"]
    hand, seen = memory.get("seen", (-1, 0))
    if hand != obs.hand_index:
        seen = 0
        memory["pending"] = None  # stale (on_hand_end already resolved it)
    # Rebuild street totals to know whether the opponent faced a bet.
    my_tot, opp_tot = (1, 2) if obs.is_button else (2, 1)
    street = Street.PREFLOP
    i_raised_last = False
    for i, a in enumerate(obs.action_history):
        if a.street != street:
            street = a.street
            my_tot = opp_tot = 0
            i_raised_last = False
        is_raise = a.action in (Action.RAISE_HALF, Action.RAISE_POT)
        if a.is_me:
            my_tot = a.street_total
            i_raised_last = is_raise
            continue
        if i >= seen:
            facing = my_tot > opp_tot
            if facing and i_raised_last:
                stats.record_response(street, "raise" if is_raise else "call")
                memory["pending"] = None
            elif not facing:
                o = stats.open_[0 if street == Street.PREFLOP else 1]
                o["aggr" if is_raise else "passive"] += 1.0
            elif street == Street.PREFLOP and not is_raise and my_tot == 2:
                stats.open_[0]["passive"] += 1.0     # limp from the small blind
            elif street == Street.PREFLOP and is_raise and my_tot == 2:
                stats.open_[0]["aggr"] += 1.0        # open raise from the small blind
        opp_tot = a.street_total
        i_raised_last = False if not a.is_me else i_raised_last
    memory["seen"] = (obs.hand_index, len(obs.action_history))


def _opp_aggressive_this_street(obs: Observation) -> int:
    """How many times the opponent bet/raised on the current street."""
    return sum(1 for a in obs.action_history
               if a.street == obs.street and not a.is_me
               and a.action in (Action.RAISE_HALF, Action.RAISE_POT))


def _n_samples(obs: Observation, memory: dict, params: dict) -> int:
    budget = params["time_target"] * (obs.hand_index + 1) / 1000.0
    used = memory.get("think", 0.0)
    if used > 7.0:
        return 0
    if used > budget * 1.6:
        return 32
    if used > budget * 1.2:
        return 64
    return params["n_samples"]


def choose(obs: Observation, memory: dict, params: dict) -> Action:
    _update_model(obs, memory)
    stats: Stats = memory["stats"]
    legal = obs.legal_actions
    pot, to_call = obs.pot, obs.to_call
    aggr_seen = _opp_aggressive_this_street(obs)

    # ----- our equity now (e) and against hands that would call a raise (e_c) -----
    if obs.street == Street.PREFLOP:
        base = preflop_equity(obs.hole_cards, memory["rng"])
        top = 1.0
        if aggr_seen:
            top = max(params["min_top"], stats.aggr_rate(obs.street) if aggr_seen == 1
                      else stats.raise_rate(obs.street))
        e = base - params["pre_range_k"] * (1.0 - top)

        def eq_cont(f: float) -> float:
            return base - params["pre_range_k"] * (1.0 - top * (1.0 - f))
    else:
        n = _n_samples(obs, memory, params)
        if n == 0:
            return Action.CHECK_CALL if to_call == 0 or to_call <= pot // 4 else (
                Action.FOLD if Action.FOLD in legal else Action.CHECK_CALL)
        roll = Rollout(obs.hole_cards, obs.board, n, memory["rng"])
        top = 1.0
        if aggr_seen:
            rate = stats.aggr_rate(obs.street) if aggr_seen == 1 else stats.raise_rate(obs.street)
            top = max(params["min_top"], min(1.0, rate))
        e = roll.eq(top)
        if not obs.is_button and obs.street != Street.RIVER:
            e *= params["oop_realize"]

        def eq_cont(f: float) -> float:
            v = roll.eq(max(params["min_top"], top * (1.0 - f)))
            if not obs.is_button and obs.street != Street.RIVER:
                v *= params["oop_realize"]
            return v

    # ----- value of each legal action -----
    values = {}
    if Action.FOLD in legal:
        values[Action.FOLD] = 0.0
    values[Action.CHECK_CALL] = e * (pot + to_call) - to_call
    f = stats.fold_rate(obs.street)
    e_c = eq_cont(f) if any(a in legal for a in (Action.RAISE_HALF, Action.RAISE_POT)) else e
    for a in (Action.RAISE_HALF, Action.RAISE_POT):
        if a in legal:
            r = obs.raise_to[a]
            added = r - obs.my_bet
            final_pot = pot + added + (r - obs.opp_bet)
            v = f * pot + (1.0 - f) * (e_c * final_pot - added)
            values[a] = v - params["raise_margin"] * pot
    best = max(values, key=values.get)
    if best in (Action.RAISE_HALF, Action.RAISE_POT):
        memory["pending"] = (obs.street, "raise")
    return best
