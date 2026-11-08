"""hunter_v2 on a simulated 3x slower CPU: its own think-time accounting is inflated 3x
(decisions themselves are unchanged), which drives _n_samples() through 96 -> 64 -> 32 -> 0."""
import os
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(_ROOT, "lab", "field"))
sys.path.insert(0, _ROOT)

import time
import importlib.util
spec = importlib.util.spec_from_file_location("hv2_slow3", os.path.join(_ROOT, "lab", "field", "hunter_v2.py"))
H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
choose = H.choose
new_half, on_hand_end = H.new_half, H.on_hand_end
def choose_action(obs, memory):
    t0 = memory.get("think", 0.0)
    a = H.choose_action(obs, memory)
    memory["think"] = t0 + (memory["think"] - t0) * 3
    return a
