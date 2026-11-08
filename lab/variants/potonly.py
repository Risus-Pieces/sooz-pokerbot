import json, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot')
import agent as _a
import strategy as _s
_s.PARAMS = dict(_s.PARAMS, **json.loads('{"postflop_pot_only": true}'))
new_half, on_hand_end = _a.new_half, _a.on_hand_end
def choose_action(obs, memory):
    return _a.choose_action.__wrapped__(obs, memory) if hasattr(_a.choose_action, "__wrapped__") else _choose(obs, memory)
def _choose(obs, memory):
    import time
    from game import Action
    t0 = time.perf_counter()
    try:
        a = _s.choose(obs, memory, _s.PARAMS)
    except Exception:
        a = None
    if a not in obs.legal_actions:
        a = Action.CHECK_CALL if Action.CHECK_CALL in obs.legal_actions else obs.legal_actions[0]
    memory["think"] = memory.get("think", 0.0) + time.perf_counter() - t0
    return a
