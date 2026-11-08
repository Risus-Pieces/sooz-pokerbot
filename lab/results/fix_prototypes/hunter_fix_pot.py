"""Prototype fix F1a: hunter_v2 but every postflop raise uses RAISE_POT (no size tell)."""
import os
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(_ROOT, "lab", "field"))
sys.path.insert(0, _ROOT)

import importlib.util
spec = importlib.util.spec_from_file_location("hv2_inner_pot", os.path.join(_ROOT, "lab", "field", "hunter_v2.py"))
H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
from game import Action, Street
_orig = H.choose
def _choose(obs, memory, params):
    a = _orig(obs, memory, params)
    if a == Action.RAISE_HALF and obs.street != Street.PREFLOP and Action.RAISE_POT in obs.legal_actions:
        return Action.RAISE_POT
    return a
H.choose = _choose
new_half, choose_action, on_hand_end = H.new_half, H.choose_action, H.on_hand_end
choose = _choose
