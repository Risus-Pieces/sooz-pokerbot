"""PROTOTYPE: the repo-root agent.py, but with strategy_ship_s6a (S6a: stab frequency counts decay 2% per observation (recent ~50 spots)) swapped in
for strategy.py. Loads agent.py's source as a fresh module after pointing sys.modules['strategy']
at the patched copy. Honours SOOZ_DET / SOOZ_NO_BP / SOOZ_PARAMS like agent.py."""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, _ROOT)
_spec = importlib.util.spec_from_file_location("strategy", os.path.join(_HERE, "strategy_ship_s6a.py"))
_strat = importlib.util.module_from_spec(_spec)
sys.modules["strategy"] = _strat
_spec.loader.exec_module(_strat)
_aspec = importlib.util.spec_from_file_location("agent_ship_s6a_inner", os.path.join(_ROOT, "agent.py"))
_agent = importlib.util.module_from_spec(_aspec)
_aspec.loader.exec_module(_agent)
assert _agent.Stats is _strat.Stats
choose = _agent.choose
new_half, choose_action, on_hand_end = _agent.new_half, _agent.choose_action, _agent.on_hand_end
