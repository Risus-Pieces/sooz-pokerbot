"""hunter_v2 on a simulated FAST/idle CPU: its think-time accounting is reset after every decision,
so _n_samples() always returns the full 96 samples (no throttle, no 6.5 s cliff). Decisions are
otherwise identical to hunter_v2. Used to check that exploits do not depend on the loaded sim box."""
import os
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(_ROOT, "lab", "field"))
sys.path.insert(0, _ROOT)
import importlib.util
spec = importlib.util.spec_from_file_location("hv2_fast", os.path.join(_ROOT, "lab", "field", "hunter_v2.py"))
H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
choose = H.choose
new_half, on_hand_end = H.new_half, H.on_hand_end


def choose_action(obs, memory):
    a = H.choose_action(obs, memory)
    memory["think"] = 0.0
    return a
