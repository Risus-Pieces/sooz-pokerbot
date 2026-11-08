"""
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

import numpy as np

from brain import Rollout, postflop_top_fraction, preflop_equity, preflop_top_fraction
from evaluator import FULL_HOUSE, STRAIGHT, THREE_OF_A_KIND, TWO_PAIR, category_of
from fasteval import score_one
from game import Action, HandResult, Observation, Street

PARAMS = {
    "n_samples": 96,           # simulations per postflop decision
    "pre_range_k": 0.12,       # preflop equity drop vs a range that is "all strong"
    "raise_margin": -0.02,     # extra value (fraction of pot) a raise must beat a call by
    "oop_realize": 0.95,       # equity realized out of position before the river
    "min_top": 0.06,           # narrowest range we ever assume
    "prior_weight": 4.0,       # pseudo-showdowns behind the range prior
    "postflop_pot_only": True,  # bet/raise only pot-size after the flop (hides a sizing tell)
    "stab_range": True,        # after we check, judge their bet by how often they bet after our checks
    "preflop_pot_only": False, # also raise only pot-size preflop
    "reraise_ev": False,       # count being re-raised in the value of a bet (fold weak hands to it)
    "street_resp": True,       # fold/raise responses to our bets tracked per street (not pooled postflop)
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
    # postflop, after WE checked this street: passive / aggressive (their "stab" frequency)
    stab: dict = field(default_factory=lambda: {"passive": 2.0, "aggr": 2.0})
    # showdown evidence on how strong their aggressive hands are: [sum of top-shares, count]
    shown: list = field(default_factory=lambda: [[0.0, 0], [0.0, 0]])

    # the same responses kept per street (pre/flop/turn/river)
    resp4: list = field(default_factory=lambda: [
        [{"fold": 3.0, "call": 4.0, "raise": 1.0}, {"fold": 1.0, "call": 3.0, "raise": 2.0}] for _ in range(4)])
    per_street: bool = False

    def record_response(self, street, ctx: int, kind: str) -> None:
        self.resp[_g(street)][ctx][kind] += 1.0
        self.resp4[int(street)][ctx][kind] += 1.0

    def _r(self, street, ctx: int, kind: str) -> float:
        r = self.resp4[int(street)][ctx] if self.per_street else self.resp[_g(street)][ctx]
        return r[kind] / (r["fold"] + r["call"] + r["raise"])

    def fold_rate(self, street, ctx: int) -> float:
        return self._r(street, ctx, "fold")

    def raise_rate(self, street, ctx: int) -> float:
        return self._r(street, ctx, "raise")

    def aggr_rate(self, street) -> float:
        o = self.open_[_g(street)]
        return o["aggr"] / (o["aggr"] + o["passive"])

    def stab_rate(self) -> float:
        return self.stab["aggr"] / (self.stab["aggr"] + self.stab["passive"])

    def bet_range(self, street, prior_weight: float) -> float:
        """Estimated top fraction of hands this opponent bets with."""
        prior = self.aggr_rate(street)          # betting x% of the time suggests top x%
        s, n = self.shown[_g(street)]
        return min(1.0, (prior_weight * prior / 2.0 + s) / (prior_weight + n) * 2.0)


HALF_SEED = 20261108
PURPOSE = {"hunter": 1, "learn": 2, "autopilot": 3}


def rng_for(obs_or_hand, k: int, purpose: str) -> np.random.Generator:
    """Deterministic generator per (hand, decision, purpose): changing how many
    samples one decision uses can never shift any later decision."""
    hand = obs_or_hand if isinstance(obs_or_hand, int) else obs_or_hand.hand_index
    return np.random.default_rng([HALF_SEED, hand, k, PURPOSE[purpose]])


def made_hand_rule(obs: Observation) -> Action:
    """Zero-simulation fallback (~0.1 ms) used when the time bank is tight."""
    legal = obs.legal_actions
    cat = category_of(score_one(obs.hole_cards, obs.board))
    if obs.to_call == 0:
        need = THREE_OF_A_KIND if obs.street == Street.RIVER else STRAIGHT
        if cat >= need and Action.RAISE_HALF in legal:
            return Action.RAISE_HALF
        return Action.CHECK_CALL
    if cat >= FULL_HOUSE and Action.RAISE_POT in legal:
        return Action.RAISE_POT
    if cat >= STRAIGHT or (cat == TWO_PAIR and obs.to_call <= 0.5 * obs.pot):
        return Action.CHECK_CALL
    return Action.FOLD if Action.FOLD in legal else Action.CHECK_CALL


def _opp_decision(memory: dict, facing: bool, is_raise: bool, is_fold: bool) -> None:
    """Log one opponent decision for the autopilot detector."""
    is_default = (is_fold if facing else not is_raise)
    log = memory.setdefault("opp_dec", [])
    log.append((facing, is_default, is_fold))
    if len(log) > 400:
        del log[:200]
    ap = memory.get("autopilot", False)
    if ap and not is_default:
        memory["autopilot"] = False


def autopilot_check(memory: dict, hand_index: int) -> bool:
    """True when the opponent looks like it is being auto-played by the judge
    (time bank empty or forfeited: checks when free, folds otherwise)."""
    if memory.get("autopilot"):
        return True
    log = memory.get("opp_dec", [])
    if hand_index < 100 or len(log) < 40:
        return False
    streak = log[-15:]
    if not all(d for _, d, _ in streak):
        return False
    if sum(1 for f, _, fo in streak if f and fo) < 6:
        return False
    before = [x for x in log[:-15] if x[0]]
    if before and sum(1 for x in before if x[2]) / len(before) >= 0.6:
        return False   # it always folded this much: a real nit, not a timeout
    memory["autopilot"] = True
    return True


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
    i_checked_street = False
    opp_raised_street = False
    aggr_streets = set()
    for i, a in enumerate(obs.action_history):
        if a.street != street:
            street = a.street
            my_tot = opp_tot = 0
            i_raised_last = False
            i_checked_street = False
            opp_raised_street = False
        is_raise = a.action in RAISES
        if a.is_me:
            if a.action == Action.CHECK_CALL and my_tot == opp_tot:
                i_checked_street = True
            my_tot = a.street_total
            i_raised_last = is_raise
            continue
        if i >= seen:
            facing = my_tot > opp_tot
            _opp_decision(memory, facing, is_raise, False)
            if facing and i_raised_last:
                ctx = 1 if opp_raised_street else 0
                stats.record_response(street, ctx, "raise" if is_raise else "call")
                memory["pending"] = None
            elif not facing:
                stats.open_[_g(street)]["aggr" if is_raise else "passive"] += 1.0
                if street != Street.PREFLOP and i_checked_street:
                    stats.stab["aggr" if is_raise else "passive"] += 1.0
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
    if (not result.went_to_showdown) and result.winner == "me":
        _opp_decision(memory, True, False, True)   # they folded facing our bet
    memory["pending"] = None
    if result.went_to_showdown and result.opp_hole is not None:
        for s in memory.get("aggr_streets", ()):
            if s == 0:
                share = preflop_top_fraction(result.opp_hole)
            else:
                board = result.board[: 2 + s]   # flop 3, turn 4, river 5 cards
                share = postflop_top_fraction(result.opp_hole, board, memory.get("my_hole", ()),
                                              96, rng_for(result.hand_index, 99, "learn"))
            stats.shown[0 if s == 0 else 1][0] += share
            stats.shown[0 if s == 0 else 1][1] += 1
    memory["aggr_streets"] = set()
    stats.hands += 1


def choose(obs: Observation, memory: dict, params: dict) -> Action:
    _update_model(obs, memory)
    memory["stats"].per_street = bool(params.get("street_resp"))
    legal0 = obs.legal_actions
    if autopilot_check(memory, obs.hand_index):
        for a in (Action.RAISE_HALF, Action.RAISE_POT, Action.CHECK_CALL):
            if a in legal0:
                if a in RAISES:
                    memory["pending"] = (obs.street, 0)
                return a
    gov = memory.get("gov")
    tier = gov.tier(obs.hand_index) if gov is not None else 0
    if tier >= 5:
        return Action.CHECK_CALL if obs.to_call == 0 else (Action.FOLD if Action.FOLD in legal0 else Action.CHECK_CALL)
    rng = rng_for(obs, len(obs.action_history), "hunter")
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
        if (params.get("stab_range") and obs.street != Street.PREFLOP and opp_raises == 1
                and any(a.is_me and a.street == obs.street and a.action == Action.CHECK_CALL
                        for a in obs.action_history)):
            top = max(top, stats.stab_rate())
        if opp_raises >= 2:
            top *= max(0.25, stats.raise_rate(obs.street, 1))
        top = max(params["min_top"], top)

    if obs.street == Street.PREFLOP:
        base = preflop_equity(obs.hole_cards, rng)
        e = base - params["pre_range_k"] * (1.0 - top)

        def eq_cont(f: float) -> float:
            return base - params["pre_range_k"] * (1.0 - top * (1.0 - f))
    else:
        n = params["n_samples"] if tier == 0 else (gov.samples(tier) if gov is not None else 0)
        if n == 0:
            return made_hand_rule(obs)
        roll = Rollout(obs.hole_cards, obs.board, n, rng)
        realize = params["oop_realize"] if (not obs.is_button and obs.street != Street.RIVER) else 1.0
        e = roll.eq(top) * realize

        def eq_cont(f: float) -> float:
            return roll.eq(max(params["min_top"], top * (1.0 - f))) * realize

    values = {}
    if Action.FOLD in legal:
        values[Action.FOLD] = 0.0
    values[Action.CHECK_CALL] = e * (pot + to_call) - to_call
    if any(a in legal for a in RAISES):
        f = stats.fold_rate(obs.street, ctx)
        e_c = eq_cont(f)
        pot_only = params.get("preflop_pot_only") if obs.street == Street.PREFLOP else params.get("postflop_pot_only")
        sizes = (Action.RAISE_POT,) if pot_only else RAISES
        if Action.RAISE_POT not in legal:
            sizes = RAISES
        for a in sizes:
            if a in legal:
                r = obs.raise_to[a]
                added = r - obs.my_bet
                final_pot = pot + added + (r - obs.opp_bet)
                if params.get("reraise_ev"):
                    q = min(stats.raise_rate(obs.street, ctx), 1.0 - f)
                    e_r = eq_cont(1.0 - 0.4 * (1.0 - f))          # vs their narrower re-raising range
                    # facing a pot re-raise: call it if that is worth more than giving up `added`
                    reraise = max(-added, e_r * (3 * final_pot) - (added + final_pot))
                    values[a] = (f * pot + (1.0 - f - q) * (e_c * final_pot - added) + q * reraise
                                 - params["raise_margin"] * pot)
                else:
                    values[a] = f * pot + (1.0 - f) * (e_c * final_pot - added) - params["raise_margin"] * pot
    best = max(values, key=values.get)
    if best in RAISES:
        memory["pending"] = (obs.street, ctx)
    return best
