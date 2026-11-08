"""Prototype fix F1b: hunter_v2 but postflop raise SIZE is a coin flip independent of hand strength."""
import os
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(_ROOT, "lab", "field"))
sys.path.insert(0, _ROOT)

import importlib.util
spec = importlib.util.spec_from_file_location("hv2_inner_rand", os.path.join(_ROOT, "lab", "field", "hunter_v2.py"))
H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
from game import Action, Street
_orig = H.choose
def _choose(obs, memory, params):
    a = _orig(obs, memory, params)
    if a in (Action.RAISE_HALF, Action.RAISE_POT) and obs.street != Street.PREFLOP:
        return Action.RAISE_POT if memory["rng"].random() < 0.5 else Action.RAISE_HALF
    return a
H.choose = _choose
new_half, choose_action, on_hand_end = H.new_half, H.choose_action, H.on_hand_end
choose = _choose
