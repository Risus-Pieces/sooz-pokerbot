"""
parambot.py - a parameterized bot family for exploit search against hunter.

Use as a bot file directly (DEFAULT parameters) or build variants:

    import parambot
    P = parambot.decode(x)            # x: flat vector in [0, 1]^D (normalized)
    parambot.new_half(cfg, memory, P) # then choose_action / on_hand_end as usual
    parambot.write_variant(path, x)   # a standalone-loadable bot file for sim.py

Features (about 1 ms per postflop decision):
    pct    preflop: share of random hands this hand beats (0..1)
    eq     win chance vs a random hand (preflop table / 48-sample rollout)
    made   postflop: share of random hands whose CURRENT made hand is worse
    draw   eq - made (positive for draws, negative for vulnerable made hands)

Policy (s = flop/turn/river index 0..2):
  preflop open (SB first in): raise if pct > pre_open, limp if pct > pre_limp, else fold
  preflop BB vs limp: raise if pct > pre_iso else check
  preflop facing a raise: re-raise if pct > pre_3b; call if eq > odds + pre_call
  postflop unopened:
      if eq > mon and rnd < slow: check (trap; check-raise later)
      elif eq > vb[s]: bet
      elif draw > dthr and rnd < semi[s] * A: bet (semi-bluff)
      elif eq < bcap and rnd < bluff[s] * A: bet (bluff)
      size: pot with prob pz[s] else half
  postflop facing a bet/raise:
      raise if eq > rv[s] (+ 0.08 per extra raise already on the street)
      or (we checked this street, i.e. check-raise) and draw > dthr and rnd < crd[s] * A
      or (we checked this street) and rnd < crb[s] * A (pure bluff check-raise)
      call  if eq > odds * cmul + ca[s] (+ car if they raised OUR bet)
      else fold
  A = aggression multiplier: early_mult before hand `switch`, late_mult after,
      times (1 + kf * (observed hunter fold-rate to our bets - 0.35)), clipped to [0, 3].
  ca[s] is also shifted by -ka * (observed hunter bet-when-checked-to rate - 0.35).
v2/v3 extras (appended to the vector; older shorter vectors decode them as neutral):
  stab_f/t/r  extra bet prob for non-value hands when hunter checked to us this street
  cpot        extra equity needed to call a POT-sized bet/raise (hunter's size tell)
  rbh         bluff-raise prob vs a HALF-pot bet on flop/turn
  early_ca    extra equity needed to call before hand `switch` (fold early, punish later)
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
import numpy as np  # noqa: E402

from brain import Rollout, preflop_equity, preflop_top_fraction  # noqa: E402
from fasteval import score_one  # noqa: E402
from game import Action, Street  # noqa: E402

RAISES = (Action.RAISE_HALF, Action.RAISE_POT)

# (name, low, high, default). Per-street names end in _f/_t/_r.
SPEC = [
    ("pre_open", 0.0, 1.0, 0.35),
    ("pre_limp", 0.0, 1.0, 0.15),
    ("pre_iso", 0.0, 1.0, 0.70),
    ("pre_3b", 0.3, 1.0, 0.85),
    ("pre_call", -0.15, 0.15, 0.0),
    ("pre_pz", 0.0, 1.0, 0.8),
    ("mon", 0.6, 1.0, 0.85),
    ("slow", 0.0, 1.0, 0.1),
    ("dthr", 0.0, 0.5, 0.15),
    ("bcap", 0.1, 0.6, 0.35),
    ("cmul", 0.6, 1.6, 1.0),
    ("car", -0.1, 0.3, 0.05),
]
for _s in ("f", "t", "r"):
    SPEC += [
        (f"vb_{_s}", 0.4, 1.0, 0.68),
        (f"semi_{_s}", 0.0, 1.0, 0.5),
        (f"bluff_{_s}", 0.0, 1.0, 0.3),
        (f"pz_{_s}", 0.0, 1.0, 0.7),
        (f"rv_{_s}", 0.5, 1.0, 0.80),
        (f"crd_{_s}", 0.0, 1.0, 0.2),
        (f"crb_{_s}", 0.0, 0.6, 0.05),
        (f"ca_{_s}", -0.15, 0.35, 0.03),
    ]
SPEC += [
    ("switch", 0.0, 1000.0, 0.0),
    ("early_mult", 0.0, 2.0, 1.0),
    ("late_mult", 0.0, 2.0, 1.0),
    ("kf", -3.0, 3.0, 0.0),
    ("ka", -0.5, 0.5, 0.0),
    # v2 additions (appended; shorter vectors decode with these defaults = neutral)
    ("stab_f", 0.0, 1.0, 0.0),     # extra bet prob for non-value hands when hunter checked to us
    ("stab_t", 0.0, 1.0, 0.0),
    ("stab_r", 0.0, 1.0, 0.0),
    ("cpot", -0.1, 0.3, 0.0),      # extra equity needed vs a POT-sized bet/raise (size tell)
    ("rbh", 0.0, 1.0, 0.0),        # bluff-raise prob vs a HALF-pot bet (flop/turn)
    # v3 addition: phase-dependent defence ("teach it we fold, then stop folding")
    ("early_ca", -0.1, 0.4, 0.0),  # extra equity needed to call before hand `switch`
]
NAMES = [s[0] for s in SPEC]
LO = np.array([s[1] for s in SPEC])
HI = np.array([s[2] for s in SPEC])
DEF = np.array([s[3] for s in SPEC])
DIM = len(SPEC)


def encode(params: dict) -> np.ndarray:
    v = np.array([params.get(n, d) for n, d in zip(NAMES, DEF)], dtype=float)
    return (v - LO) / (HI - LO)


def decode(x) -> dict:
    x = np.asarray(x, dtype=float)
    if len(x) < DIM:      # older, shorter vectors: pad with defaults
        x = np.concatenate([x, ((DEF - LO) / (HI - LO))[len(x):]])
    x = np.clip(x, 0.0, 1.0)
    v = LO + x * (HI - LO)
    return {n: float(a) for n, a in zip(NAMES, v)}


DEFAULT = decode(encode({}))


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


def new_half(config, memory, P: dict | None = None):
    memory["P"] = dict(P or DEFAULT)
    memory["rng"] = np.random.default_rng(12345)
    # observed hunter tendencies (Beta-smoothed counts)
    memory["fold"] = [3.5, 6.5]    # [folds, responses] to our postflop bets
    memory["lead"] = [3.5, 10.0]   # [bets, chances] when hunter is checked to / first in
    memory["pending"] = False
    memory["seen"] = (-1, 0)


def _observe(obs, memory):
    hand, seen = memory["seen"]
    if hand != obs.hand_index:
        seen = 0
    street = Street.PREFLOP
    my_tot, opp_tot = (1, 2) if obs.is_button else (2, 1)
    last_me_raise = False
    for i, a in enumerate(obs.action_history):
        if a.street != street:
            street = a.street
            my_tot = opp_tot = 0
            last_me_raise = False
        if a.is_me:
            my_tot = a.street_total
            last_me_raise = a.action in RAISES
            continue
        if i >= seen and street != Street.PREFLOP:
            if last_me_raise:
                memory["fold"][1] += 1.0     # responded without folding
                memory["pending"] = False
            elif my_tot == opp_tot:
                memory["lead"][1] += 1.0
                if a.action in RAISES:
                    memory["lead"][0] += 1.0
        opp_tot = a.street_total
        last_me_raise = False
    memory["seen"] = (obs.hand_index, len(obs.action_history))


def choose_action(obs, memory):
    P = memory["P"]
    rng = memory["rng"]
    legal = obs.legal_actions
    _observe(obs, memory)
    can_raise = Action.RAISE_POT in legal
    eq, pct, made = _feat(obs, rng)
    to_call, pot = obs.to_call, obs.pot
    odds = to_call / (pot + to_call) if to_call else 0.0
    st = obs.street
    hist_st = [a for a in obs.action_history if a.street == st]
    opp_raises = sum(1 for a in hist_st if not a.is_me and a.action in RAISES)
    my_raises = sum(1 for a in hist_st if a.is_me and a.action in RAISES)
    i_checked = any(a.is_me and a.action == Action.CHECK_CALL and a.amount == 0 for a in hist_st)
    opp_checked = any((not a.is_me) and a.action == Action.CHECK_CALL and a.amount == 0 for a in hist_st)
    last_opp = next((a for a in reversed(hist_st) if not a.is_me), None)

    mult = P["early_mult"] if obs.hand_index < P["switch"] else P["late_mult"]
    ff = memory["fold"][0] / memory["fold"][1]
    A = min(3.0, max(0.0, mult * (1.0 + P["kf"] * (ff - 0.35))))
    lead = memory["lead"][0] / memory["lead"][1]

    def bet(pz):
        if not can_raise:
            return Action.CHECK_CALL
        return Action.RAISE_POT if rng.random() < pz else Action.RAISE_HALF

    def out(a):
        if a in RAISES and st != Street.PREFLOP:
            memory["pending"] = True
        return a if a in legal else Action.CHECK_CALL

    if st == Street.PREFLOP:
        if opp_raises == 0:
            if to_call == 1:          # SB first in
                if pct > P["pre_open"] and can_raise:
                    return out(bet(P["pre_pz"]))
                if pct > P["pre_limp"]:
                    return out(Action.CHECK_CALL)
                return out(Action.FOLD)
            if to_call == 0:          # BB after a limp
                if pct > P["pre_iso"] and can_raise:
                    return out(bet(P["pre_pz"]))
                return out(Action.CHECK_CALL)
        # facing a raise
        if can_raise and pct > P["pre_3b"] + 0.04 * my_raises:
            return out(bet(P["pre_pz"]))
        if to_call == 0 or eq > odds + P["pre_call"]:
            return out(Action.CHECK_CALL)
        return out(Action.FOLD)

    s = "ftr"[int(st) - 1]
    draw = eq - made
    if to_call == 0:
        if eq > P["mon"] and rng.random() < P["slow"] and st != Street.RIVER:
            return out(Action.CHECK_CALL)
        if eq > P[f"vb_{s}"]:
            return out(bet(P[f"pz_{s}"]))
        if st != Street.RIVER and draw > P["dthr"] and rng.random() < P[f"semi_{s}"] * A:
            return out(bet(P[f"pz_{s}"]))
        if eq < P["bcap"] and rng.random() < P[f"bluff_{s}"] * A:
            return out(bet(P[f"pz_{s}"]))
        if opp_checked and rng.random() < P.get(f"stab_{s}", 0.0) * A:
            return out(bet(P[f"pz_{s}"]))
        return out(Action.CHECK_CALL)
    # facing a bet or raise
    if can_raise:
        if eq > P[f"rv_{s}"] + 0.08 * my_raises:
            return out(Action.RAISE_POT)
        if i_checked and my_raises == 0:
            if st != Street.RIVER and draw > P["dthr"] and rng.random() < P[f"crd_{s}"] * A:
                return out(Action.RAISE_POT)
            if rng.random() < P[f"crb_{s}"] * A:
                return out(Action.RAISE_POT)
        if (st != Street.RIVER and last_opp is not None and last_opp.action == Action.RAISE_HALF
                and my_raises == 0 and rng.random() < P.get("rbh", 0.0) * A):
            return out(Action.RAISE_POT)
    need = odds * P["cmul"] + P[f"ca_{s}"] - P["ka"] * (lead - 0.35)
    if last_opp is not None and last_opp.action == Action.RAISE_POT:
        need += P.get("cpot", 0.0)
    if my_raises:
        need += P["car"]
    if obs.hand_index < P["switch"]:
        need += P.get("early_ca", 0.0)
    if eq > need:
        return out(Action.CHECK_CALL)
    return out(Action.FOLD)


def on_hand_end(result, memory):
    if memory.get("pending"):
        memory["fold"][1] += 1.0
        if (not result.went_to_showdown) and result.winner == "me":
            memory["fold"][0] += 1.0
    memory["pending"] = False


_VARIANT = '''"""Generated parambot variant."""
import os, sys
sys.path.insert(0, {lab!r})
import parambot as _pb
P = _pb.decode({x!r})


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
'''


def write_variant(path: str, x) -> str:
    with open(path, "w") as f:
        f.write(_VARIANT.format(lab=_HERE, x=[round(float(v), 5) for v in np.clip(x, 0, 1)]))
    return path
