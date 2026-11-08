"""
PROTOTYPE fix1t: fix1 + trap/check-raise branch (F5).
fix1: identical to _strategy_v2 except postflop raises are always RAISE_POT
(only that size is evaluated), removing the e_c > 0.5 size tell.
strategy.py - the decision logic: an expected-value chooser driven by a live
opponent model.

For every legal action we estimate its value in chips:
    fold   0
    call   e * (pot + to_call) - to_call
    raise  f * pot + (1 - f) * (e_c * final_pot - added)
where e is our win chance against the opponent's likely range, f is how
often this opponent folds to this kind of raise (learned during the half),
and e_c is our win chance against the hands that continue.

The opponent's range when they bet is learned from showdowns: each time they
show down a hand they bet with, we measure what share of random hands is at
least that good. If they bet with their top x% uniformly, those shares
average x/2, so the range estimate is twice the running average.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from _brain_v2 import Rollout, postflop_top_fraction, preflop_equity, preflop_top_fraction
from game import Action, HandResult, Observation, Street

PARAMS = {
    "n_samples": 96,           # simulations per postflop decision
    "pre_range_k": 0.12,       # preflop equity drop vs a range that is "all strong"
    "raise_margin": -0.02,     # extra value (fraction of pot) a raise must beat a call by
    "oop_realize": 0.95,       # equity realized out of position before the river
    "min_top": 0.06,           # narrowest range we ever assume
    "time_target": 3.0,        # seconds of thinking we aim to use per half
    "prior_weight": 4.0,       # pseudo-showdowns behind the range prior
}

RAISES = (Action.RAISE_HALF, Action.RAISE_POT)


def _g(street) -> int:
    return 0 if street == Street.PREFLOP else 1


@dataclass
class Stats:
    """Beta-smoothed counts of the opponent's habits for this half."""

    hands: int = 0
    # responses to OUR raises, [preflop, postflop][ctx]; ctx 0 = they had not
    # raised this street yet (our bet / open), ctx 1 = we are re-raising them.
    resp: list = field(default_factory=lambda: [
        [{"fold": 3.0, "call": 4.0, "raise": 1.0}, {"fold": 1.0, "call": 3.0, "raise": 2.0}],
        [{"fold": 3.0, "call": 4.0, "raise": 1.0}, {"fold": 1.0, "call": 3.0, "raise": 2.0}]])
    # when nobody has bet yet this street: [preflop open, postflop] -> passive / aggressive
    open_: list = field(default_factory=lambda: [
        {"passive": 3.0, "aggr": 2.0}, {"passive": 3.0, "aggr": 2.0}])
    # showdown evidence on how strong their aggressive hands are: [sum of top-shares, count]
    shown: list = field(default_factory=lambda: [[0.0, 0], [0.0, 0]])

    def record_response(self, street, ctx: int, kind: str) -> None:
        self.resp[_g(street)][ctx][kind] += 1.0

    def _r(self, street, ctx: int, kind: str) -> float:
        r = self.resp[_g(street)][ctx]
        return r[kind] / (r["fold"] + r["call"] + r["raise"])

    def fold_rate(self, street, ctx: int) -> float:
        return self._r(street, ctx, "fold")

    def raise_rate(self, street, ctx: int) -> float:
        return self._r(street, ctx, "raise")

    def aggr_rate(self, street) -> float:
        o = self.open_[_g(street)]
        return o["aggr"] / (o["aggr"] + o["passive"])

    def bet_range(self, street, prior_weight: float) -> float:
        """Estimated top fraction of hands this opponent bets with."""
        prior = self.aggr_rate(street)          # betting x% of the time suggests top x%
        s, n = self.shown[_g(street)]
        return min(1.0, (prior_weight * prior / 2.0 + s) / (prior_weight + n) * 2.0)


def _update_model(obs: Observation, memory: dict) -> None:
    """Walk this hand's history and learn from opponent actions not yet seen."""
    stats: Stats = memory["stats"]
    hand, seen = memory.get("seen", (-1, 0))
    if hand != obs.hand_index:
        seen = 0
        memory["pending"] = None
    my_tot, opp_tot = (1, 2) if obs.is_button else (2, 1)
    street = Street.PREFLOP
    i_raised_last = False
    opp_raised_street = False
    aggr_streets = set()
    for i, a in enumerate(obs.action_history):
        if a.street != street:
            street = a.street
            my_tot = opp_tot = 0
            i_raised_last = False
            opp_raised_street = False
        is_raise = a.action in RAISES
        if a.is_me:
            my_tot = a.street_total
            i_raised_last = is_raise
            continue
        if i >= seen:
            facing = my_tot > opp_tot
            if facing and i_raised_last:
                ctx = 1 if opp_raised_street else 0
                stats.record_response(street, ctx, "raise" if is_raise else "call")
                memory["pending"] = None
            elif not facing:
                stats.open_[_g(street)]["aggr" if is_raise else "passive"] += 1.0
            elif street == Street.PREFLOP and my_tot == 2:
                stats.open_[0]["aggr" if is_raise else "passive"] += 1.0
        if is_raise:
            opp_raised_street = True
            aggr_streets.add(int(street))
        opp_tot = a.street_total
        i_raised_last = False
    memory["seen"] = (obs.hand_index, len(obs.action_history))
    memory["aggr_streets"] = aggr_streets
    memory["my_hole"] = obs.hole_cards


def learn_from_hand(result: HandResult, memory: dict) -> None:
    """Called from on_hand_end: resolve a pending raise and read showdowns."""
    stats: Stats = memory["stats"]
    pending = memory.get("pending")
    if pending is not None:
        street, ctx = pending
        folded = (not result.went_to_showdown) and result.winner == "me"
        stats.record_response(street, ctx, "fold" if folded else "call")
    memory["pending"] = None
    if result.went_to_showdown and result.opp_hole is not None:
        for s in memory.get("aggr_streets", ()):
            if s == 0:
                share = preflop_top_fraction(result.opp_hole)
            else:
                board = result.board[: 2 + s]   # flop 3, turn 4, river 5 cards
                share = postflop_top_fraction(result.opp_hole, board, memory.get("my_hole", ()),
                                              96, memory["rng"])
            stats.shown[0 if s == 0 else 1][0] += share
            stats.shown[0 if s == 0 else 1][1] += 1
    memory["aggr_streets"] = set()
    stats.hands += 1


def _n_samples(obs: Observation, memory: dict, params: dict) -> int:
    budget = params["time_target"] * (obs.hand_index + 1) / 1000.0
    used = memory.get("think", 0.0)
    if used > 6.5:
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
    opp_raises = sum(1 for a in obs.action_history
                     if a.street == obs.street and not a.is_me and a.action in RAISES)
    if obs.street == Street.PREFLOP and not obs.is_button and to_call > 0 and opp_raises == 0:
        opp_raises = 0  # facing only the blind
    ctx = 1 if opp_raises else 0
    pw = params["prior_weight"]

    top = 1.0
    if opp_raises:
        top = stats.bet_range(obs.street, pw)
        if opp_raises >= 2:
            top *= max(0.25, stats.raise_rate(obs.street, 1))
        top = max(params["min_top"], top)

    if obs.street == Street.PREFLOP:
        base = preflop_equity(obs.hole_cards, memory["rng"])
        e = base - params["pre_range_k"] * (1.0 - top)

        def eq_cont(f: float) -> float:
            return base - params["pre_range_k"] * (1.0 - top * (1.0 - f))
    else:
        n = _n_samples(obs, memory, params)
        if n == 0:
            if to_call == 0:
                return Action.CHECK_CALL
            return Action.FOLD if Action.FOLD in legal else Action.CHECK_CALL
        roll = Rollout(obs.hole_cards, obs.board, n, memory["rng"])
        realize = params["oop_realize"] if (not obs.is_button and obs.street != Street.RIVER) else 1.0
        e = roll.eq(top) * realize

        def eq_cont(f: float) -> float:
            return roll.eq(max(params["min_top"], top * (1.0 - f))) * realize

    # fix1t (F5): protect the checking range - OOP on flop/turn, sometimes check a strong hand
    # (the EV chooser then raises when bet into)
    if (to_call == 0 and not obs.is_button and obs.street in (Street.FLOP, Street.TURN)
            and e > params.get("trap_eq", 0.72) and memory["rng"].random() < params.get("trap_p", 0.25)):
        return Action.CHECK_CALL
    values = {}
    if Action.FOLD in legal:
        values[Action.FOLD] = 0.0
    values[Action.CHECK_CALL] = e * (pot + to_call) - to_call
    if any(a in legal for a in RAISES):
        f = stats.fold_rate(obs.street, ctx)
        e_c = eq_cont(f)
        # fix1: postflop only ONE size is ever evaluated/used, so size carries no information
        sizes = RAISES if obs.street == Street.PREFLOP else (Action.RAISE_POT,)
        for a in sizes:
            if a in legal:
                r = obs.raise_to[a]
                added = r - obs.my_bet
                final_pot = pot + added + (r - obs.opp_bet)
                values[a] = f * pot + (1.0 - f) * (e_c * final_pot - added) - params["raise_margin"] * pot
    best = max(values, key=values.get)
    if best in RAISES:
        memory["pending"] = (obs.street, ctx)
    return best
