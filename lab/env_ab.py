"""
env_ab.py - paired comparison of agent.py under two environment settings
(e.g. hedge on/off) against the field plus the red-team bots.

    python lab/env_ab.py 'SOOZ_NO_BP=1' '' --seeds 1
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lab"))
import sim  # noqa: E402

ANTI = ["cma_v2", "sizetell", "baiter", "stabber", "barrel", "checkraise", "trapper", "drifter", "mirror_stationary"]


def run(env: str, opps, seeds, seed0, deals, workers):
    keep = dict(os.environ)
    for kv in filter(None, env.split(",")):
        k, v = kv.split("=", 1)
        os.environ[k] = v
    try:
        jobs = [(str(ROOT / "agent.py"), o, f"e{seed0 + s}", deals) for o in opps for s in range(seeds)]
        return sim.run_many(jobs, workers)
    finally:
        os.environ.clear()
        os.environ.update(keep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("env_a")
    ap.add_argument("env_b")
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--seed0", type=int, default=500)
    ap.add_argument("--deals", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    os.environ["SOOZ_DET"] = "1"
    opps = [p for p in sim.field_paths() if not any(x in p for x in ("checkfold", "timeout"))]
    opps += [str(ROOT / "lab/field/anti" / f"{b}.py") for b in ANTI if (ROOT / "lab/field/anti" / f"{b}.py").exists()]
    ra = run(args.env_a, opps, args.seeds, args.seed0, args.deals, args.workers)
    rb = run(args.env_b, opps, args.seeds, args.seed0, args.deals, args.workers)
    print(f"A: {args.env_a or '(default)'}   B: {args.env_b or '(default)'}")
    print(f"{'opponent':20}{'A bb':>8}{'B bb':>8}{'B-A':>8}{'zA':>7}{'zB':>7}{'thinkA':>8}{'thinkB':>8}")
    ep = [0.0, 0.0]
    tot = [0.0, 0.0]
    for o in opps:
        row = []
        for k, res in enumerate((ra, rb)):
            rs = [r for r in res if r["b"] == o]
            m = sum(r["mean"] for r in rs) / len(rs)
            z = sum(r["mean"] / r["se"] for r in rs) / len(rs)
            th = max(r["think_a"] for r in rs)
            ep[k] += sim.expected_points(z)
            tot[k] += m
            row.append((m, z, th))
        (ma, za, ta), (mb, zb, tb) = row
        print(f"{Path(o).stem:20}{ma:8.2f}{mb:8.2f}{mb - ma:8.2f}{za:7.1f}{zb:7.1f}{ta:8.2f}{tb:8.2f}")
    print(f"{'TOTAL':20}{tot[0]:8.2f}{tot[1]:8.2f}{tot[1] - tot[0]:8.2f}   expected points A {ep[0]:.2f}  B {ep[1]:.2f}  of {len(opps)}")


if __name__ == "__main__":
    main()
