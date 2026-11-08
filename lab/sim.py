"""
sim.py - fast in-process duplicate matches (no HTTP), scored exactly like the judge.

    python lab/sim.py agent.py lab/field/eqbot.py --deals 1000 --seed 7
    python lab/sim.py agent.py --field --deals 500 --seeds 3     # vs every field bot

Each bot file must define new_half(config, memory), choose_action(obs, memory)
and on_hand_end(result, memory). Every half gets a freshly imported copy of
each bot (like the tournament's fresh process per half) and a fresh memory.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import (BIG_BLIND, CHOP_Z, AgentConfig, Game, IllegalActionError,  # noqa: E402
                  button_for_deal, default_action, make_deal)

FIELD_DIR = ROOT / "lab" / "field"
_counter = itertools.count()


def load_bot(path: str):
    """Import a bot file as a brand-new module (fresh globals every time)."""
    name = f"bot_{Path(path).stem}_{next(_counter)}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def play_half(path_a: str, path_b: str, seed, deals: int, half: int):
    """agent A sits in seat 0 in half 1 and seat 1 in half 2. Returns A's net
    chips per deal, error counts and A's thinking time."""
    bots = [load_bot(path_a), load_bot(path_b)]
    a_seat = 0 if half == 1 else 1
    seat_bot = {a_seat: bots[0], 1 - a_seat: bots[1]}
    mem = {0: {}, 1: {}}
    cfg = AgentConfig()
    errors = {0: 0, 1: 0}
    think = {0: 0.0, 1: 0.0}
    for s in (0, 1):
        seat_bot[s].new_half(cfg, mem[s])
    nets = []
    for d in range(deals):
        g = Game(make_deal(seed, d), button_for_deal(d), hand_index=d)
        while not g.is_terminal:
            s = g.to_act
            obs = g.observation(s)
            t = time.perf_counter()
            try:
                act = seat_bot[s].choose_action(obs, mem[s])
                ok = act in obs.legal_actions
            except Exception as exc:  # noqa: BLE001
                ok = False
                if errors[s] == 0:
                    import traceback
                    traceback.print_exc()
            think[s] += time.perf_counter() - t
            if not ok:
                errors[s] += 1
                act = default_action(obs.to_call)
            g.apply(act)
        for s in (0, 1):
            try:
                seat_bot[s].on_hand_end(g.hand_result(s), mem[s])
            except Exception:  # noqa: BLE001
                errors[s] += 1
        nets.append(g.result().nets[a_seat])
    return nets, errors[a_seat], errors[1 - a_seat], think[a_seat], think[1 - a_seat]


def play_match(path_a: str, path_b: str, seed, deals: int):
    h1 = play_half(path_a, path_b, seed, deals, 1)
    h2 = play_half(path_a, path_b, seed, deals, 2)
    paired = [(x + y) / BIG_BLIND for x, y in zip(h1[0], h2[0])]
    n = len(paired)
    mean = sum(paired) / n
    sd = math.sqrt(sum((p - mean) ** 2 for p in paired) / (n - 1))
    se = sd / math.sqrt(n)
    lo, hi = mean - CHOP_Z * se, mean + CHOP_Z * se
    forfeit_a = h1[1] >= 5 or h2[1] >= 5
    forfeit_b = h1[2] >= 5 or h2[2] >= 5
    if forfeit_a or forfeit_b:
        pts = 0.0 if forfeit_a else 1.0
    else:
        pts = 1.0 if lo > 0 else 0.0 if hi < 0 else 0.5
    return {
        "a": path_a, "b": path_b, "seed": seed, "mean": mean, "se": se, "lo": lo, "hi": hi,
        "points": pts, "err_a": h1[1] + h2[1], "err_b": h1[2] + h2[2],
        "think_a": max(h1[3], h2[3]), "think_b": max(h1[4], h2[4]),
    }


def expected_points(z: float) -> float:
    """Chance-weighted points for a match whose true z-statistic is z (win 1, chop 0.5)."""
    phi = lambda x: 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    win, lose = phi(z - CHOP_Z), phi(-z - CHOP_Z)
    return win + 0.5 * (1.0 - win - lose)


def field_paths() -> list[str]:
    return sorted(str(p) for p in FIELD_DIR.glob("*.py") if not p.name.startswith("_"))


def _run(args):
    return play_match(*args)


def run_many(jobs, workers: int | None = None):
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_run, jobs))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b", nargs="*")
    ap.add_argument("--field", action="store_true", help="play A against every bot in lab/field")
    ap.add_argument("--deals", type=int, default=1000)
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--seed0", type=int, default=100)
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    opps = (field_paths() if args.field else []) + list(args.b)
    jobs = [(args.a, o, f"s{args.seed0 + k}", args.deals) for o in opps for k in range(args.seeds)]
    t = time.time()
    results = run_many(jobs, args.workers)
    total = 0.0
    print(f"{'opponent':28}{'seed':>6}{'bb/deal':>9}{'95% CI':>20}{'z':>7}{'pts':>5}{'errA':>5}{'thinkA s':>9}")
    ep = 0.0
    for r in results:
        total += r["points"]
        z = r["mean"] / r["se"] if r["se"] > 0 else 0.0
        ep += expected_points(z)
        print(f"{Path(r['b']).stem:28}{r['seed']:>6}{r['mean']:9.3f}   [{r['lo']:7.3f},{r['hi']:7.3f}]"
              f"{z:7.2f}{r['points']:5.1f}{r['err_a']:5d}{r['think_a']:9.2f}")
    print(f"points {total}/{len(results)}   expected points {ep:.2f}   ({time.time() - t:.0f}s)")


if __name__ == "__main__":
    main()
