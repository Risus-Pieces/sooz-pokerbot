"""
tune.py - paired A/B tests of strategy parameters against the field.

Every variant plays the same opponents on the same seeds (common random
numbers), so differences between variants are mostly skill, not cards.
    python lab/tune.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lab"))
import sim  # noqa: E402

VAR_DIR = ROOT / "lab" / "variants"
TEMPLATE = '''import json, sys
sys.path.insert(0, {root!r})
import agent as _a
import strategy as _s
_s.PARAMS = dict(_s.PARAMS, **json.loads({params!r}))
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
'''


def variant(name: str, params: dict) -> str:
    VAR_DIR.mkdir(exist_ok=True)
    p = VAR_DIR / f"{name}.py"
    p.write_text(TEMPLATE.format(root=str(ROOT), params=json.dumps(params)))
    return str(p)


def main():
    grid = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    opps = [str(ROOT / "lab/field" / f"{n}.py") for n in
            ("eqbot", "lag", "nit", "madehand", "hunter_v1", "station")]
    seeds, deals = int(sys.argv[2]) if len(sys.argv) > 2 else 2, 1000
    variants = {"base": variant("base", {})}
    for k, vals in grid.items():
        for v in vals:
            variants[f"{k}={v}"] = variant(f"v_{k}_{v}".replace(".", "p"), {k: v})
    jobs = [(path, o, f"t{s}", deals) for path in variants.values() for o in opps for s in range(seeds)]
    res = sim.run_many(jobs, 6)
    by = {}
    for r in res:
        by.setdefault(r["a"], []).append(r)
    print(f"{'variant':24}" + "".join(f"{Path(o).stem[:9]:>10}" for o in opps) + f"{'mean':>8}{'pts':>6}")
    for name, path in variants.items():
        rs = by[path]
        per = [sum(r["mean"] for r in rs if r["b"] == o) / seeds for o in opps]
        print(f"{name:24}" + "".join(f"{x:10.2f}" for x in per)
              + f"{sum(per) / len(per):8.2f}{sum(r['points'] for r in rs):6.1f}")


if __name__ == "__main__":
    main()
